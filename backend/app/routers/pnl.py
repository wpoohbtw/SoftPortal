from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx
import websockets
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, HTMLResponse
from starlette.websockets import WebSocketState

from .. import config
from ..database import get_connection, utc_now
from ..dependencies import get_current_user, get_db, parse_utc
from ..security import hash_session_token

router = APIRouter(tags=['pnl'])

HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
}


def ensure_pnl_access(connection: sqlite3.Connection, user_id: int) -> None:
    access = connection.execute(
        """
        SELECT 1
        FROM projects
        JOIN project_access ON project_access.project_id = projects.id
        WHERE projects.key = 'pnl'
          AND projects.is_active = 1
          AND project_access.user_id = ?
          AND project_access.can_access = 1
        """,
        (user_id,),
    ).fetchone()
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project access denied')


def build_portal_headers(current_user) -> dict[str, str]:
    return {
        'X-Portal-User-Id': str(current_user['id']),
        'X-Portal-Username': current_user['username'],
    }


def filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() not in HOP_BY_HOP_HEADERS:
            filtered[key] = value
    return filtered


def pnl_dist_path() -> Path:
    return config.PNL_DIST_PATH.resolve()


def pnl_index_path() -> Path:
    return pnl_dist_path() / 'index.html'


async def authenticate_websocket(websocket: WebSocket):
    token = websocket.cookies.get(config.SESSION_COOKIE)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                users.id,
                users.username,
                users.display_name,
                users.is_admin,
                users.is_active,
                sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (hash_session_token(token),),
        ).fetchone()
        if not row or not row['is_active'] or parse_utc(row['expires_at']) <= parse_utc(utc_now()):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        ensure_pnl_access(connection, row['id'])
        connection.execute(
            'UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?',
            (utc_now(), hash_session_token(token)),
        )
        return row


@router.api_route('/pnl/api/v1/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def pnl_api_proxy(
    path: str,
    request: Request,
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> Response:
    ensure_pnl_access(connection, current_user['id'])
    target_url = f'{config.PNL_API_URL}/api/v1/{path}'
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() not in {'host', 'cookie', 'content-length'}
    }
    headers.update(build_portal_headers(current_user))

    async with httpx.AsyncClient(timeout=30.0) as client:
        proxied = await client.request(
            request.method,
            target_url,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=filter_response_headers(proxied.headers),
        media_type=proxied.headers.get('content-type'),
    )


@router.websocket('/pnl/api/v1/market/ws')
async def pnl_market_ws_proxy(websocket: WebSocket) -> None:
    current_user = await authenticate_websocket(websocket)
    if current_user is None:
        return

    await websocket.accept()
    query = websocket.url.query
    target_url = f'{config.PNL_WS_URL}/api/v1/market/ws'
    if query:
        target_url = f'{target_url}?{query}'

    async with websockets.connect(
        target_url,
        additional_headers=build_portal_headers(current_user),
        ping_interval=20,
        ping_timeout=20,
    ) as upstream:
        async def client_to_upstream() -> None:
            while True:
                message = await websocket.receive()
                if message['type'] == 'websocket.disconnect':
                    await upstream.close()
                    return
                if message.get('text') is not None:
                    await upstream.send(message['text'])
                elif message.get('bytes') is not None:
                    await upstream.send(message['bytes'])

        async def upstream_to_client() -> None:
            async for message in upstream:
                if websocket.client_state != WebSocketState.CONNECTED:
                    return
                if isinstance(message, bytes):
                    await websocket.send_bytes(message)
                else:
                    await websocket.send_text(message)

        try:
            import asyncio

            await asyncio.gather(client_to_upstream(), upstream_to_client())
        except (WebSocketDisconnect, websockets.ConnectionClosed):
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()


@router.get('/pnl')
@router.get('/pnl/{path:path}')
def pnl_static(
    path: str = '',
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    ensure_pnl_access(connection, current_user['id'])
    dist_path = pnl_dist_path()
    index_path = pnl_index_path()
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'PnLs frontend build not found: {index_path}',
        )

    normalized_path = path.strip('/')
    if normalized_path:
        candidate = (dist_path / normalized_path).resolve()
        if dist_path in candidate.parents and candidate.is_file():
            return FileResponse(candidate)

    return HTMLResponse(index_path.read_text(encoding='utf-8'))
