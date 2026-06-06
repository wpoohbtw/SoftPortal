import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status

from . import config
from .database import get_connection, utc_now
from .security import hash_session_token


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def touch_session_seen(connection: sqlite3.Connection, token_hash: str, last_seen_at: str) -> None:
    try:
        if parse_utc(last_seen_at) > datetime.now(timezone.utc) - timedelta(minutes=1):
            return
        connection.execute(
            'UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?',
            (utc_now(), token_hash),
        )
    except sqlite3.OperationalError as error:
        if 'locked' not in str(error).lower():
            raise


def get_db():
    with get_connection() as connection:
        yield connection


def get_current_user(
    request: Request,
    connection: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    token_hash = hash_session_token(token)
    row = connection.execute(
        """
        SELECT
            users.id,
            users.username,
            users.display_name,
            users.is_admin,
            users.is_active,
            sessions.expires_at,
            sessions.last_seen_at
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()

    if not row or not row['is_active']:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    if parse_utc(row['expires_at']) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired')

    touch_session_seen(connection, token_hash, row['last_seen_at'])
    return row


def get_current_admin(current_user=Depends(get_current_user)) -> sqlite3.Row:
    if not current_user['is_admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin access required')
    return current_user
