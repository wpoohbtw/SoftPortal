from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse

from .. import config
from ..dependencies import get_current_user, get_db
from .pnl import HOP_BY_HOP_HEADERS, build_portal_headers, filter_response_headers

router = APIRouter(tags=['fnup'])


def ensure_fnup_access(connection: sqlite3.Connection, user_id: int) -> None:
    access = connection.execute(
        """
        SELECT 1
        FROM projects
        JOIN project_access ON project_access.project_id = projects.id
        WHERE projects.key = 'fnup'
          AND projects.is_active = 1
          AND project_access.user_id = ?
          AND project_access.can_access = 1
        """,
        (user_id,),
    ).fetchone()
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project access denied')


def fnup_dist_path() -> Path:
    return config.FNUP_DIST_PATH.resolve()


def fnup_index_path() -> Path:
    return fnup_dist_path() / 'index.html'


async def proxy_fnup_request(
    path: str,
    request: Request,
    current_user,
    prefix: str,
) -> Response:
    target_url = f'{config.FNUP_API_URL}/{prefix}/{path}'
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() not in {'host', 'cookie', 'content-length'}
    }
    headers.update(build_portal_headers(current_user))

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            proxied = await client.request(
                request.method,
                target_url,
                params=request.query_params,
                content=body,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='FNUP backend is unavailable',
        ) from exc

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=filter_response_headers(proxied.headers),
        media_type=proxied.headers.get('content-type'),
    )


@router.api_route('/fnup/api/v1/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def fnup_api_proxy(
    path: str,
    request: Request,
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> Response:
    ensure_fnup_access(connection, current_user['id'])
    return await proxy_fnup_request(f'v1/{path}', request, current_user, 'api')


@router.api_route('/fnup/media/{path:path}', methods=['GET'])
async def fnup_media_proxy(
    path: str,
    request: Request,
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> Response:
    ensure_fnup_access(connection, current_user['id'])
    return await proxy_fnup_request(path, request, current_user, 'media')


@router.get('/fnup')
@router.get('/fnup/{path:path}')
def fnup_static(
    path: str = '',
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    ensure_fnup_access(connection, current_user['id'])
    dist_path = fnup_dist_path()
    index_path = fnup_index_path()
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'FNUP frontend build not found: {index_path}',
        )

    normalized_path = path.strip('/')
    if normalized_path:
        candidate = (dist_path / normalized_path).resolve()
        if dist_path in candidate.parents and candidate.is_file():
            return FileResponse(candidate)

    return HTMLResponse(index_path.read_text(encoding='utf-8'))
