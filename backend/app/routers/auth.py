import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import config
from ..database import delete_expired_sessions
from ..dependencies import get_current_user, get_db
from ..schemas import LoginRequest, OkResponse, SessionResponse, UserPublic
from ..security import create_session_token, hash_session_token, verify_password
from .projects import get_accessible_projects

router = APIRouter(prefix='/api/auth', tags=['auth'])


def build_session_response(connection: sqlite3.Connection, user) -> SessionResponse:
    public_user = UserPublic(
        id=user['id'],
        username=user['username'],
        display_name=user['display_name'],
        is_admin=bool(user['is_admin']),
    )
    return SessionResponse(
        user=public_user,
        projects=get_accessible_projects(connection, user['id']),
    )


@router.post('/login', response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    connection: sqlite3.Connection = Depends(get_db),
):
    user = connection.execute(
        """
        SELECT id, username, display_name, password_hash, is_admin, is_active
        FROM users
        WHERE username = ?
        """,
        (payload.username,),
    ).fetchone()

    if not user or not user['is_active'] or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid login or password')

    delete_expired_sessions(connection)
    token = create_session_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=config.SESSION_TTL_DAYS)
    connection.execute(
        """
        INSERT INTO sessions (user_id, token_hash, created_at, expires_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user['id'],
            hash_session_token(token),
            now.isoformat(),
            expires_at.isoformat(),
            now.isoformat(),
        ),
    )
    response.set_cookie(
        key=config.SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite=config.COOKIE_SAMESITE,
        max_age=config.SESSION_TTL_DAYS * 24 * 60 * 60,
        path='/',
    )
    return build_session_response(connection, user)


@router.get('/session', response_model=SessionResponse)
def session(
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    return build_session_response(connection, current_user)


@router.post('/logout', response_model=OkResponse)
def logout(
    request: Request,
    response: Response,
    _current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    token = request.cookies.get(config.SESSION_COOKIE)
    connection.execute(
        'DELETE FROM sessions WHERE token_hash = ?',
        (hash_session_token(token or ''),),
    )
    response.delete_cookie(config.SESSION_COOKIE, path='/')
    return OkResponse(ok=True)


@router.get('/proxy-check')
def proxy_check(
    request: Request,
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    original_uri = request.headers.get('x-original-uri') or request.headers.get('x-forwarded-uri') or ''
    if original_uri.startswith('/pnl/'):
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
            (current_user['id'],),
        ).fetchone()
        if not access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project access denied')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
