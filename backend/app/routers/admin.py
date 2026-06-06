import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import utc_now
from ..dependencies import get_current_admin, get_db
from ..schemas import AdminUserCreate, OkResponse, UserPublic
from ..security import hash_password

router = APIRouter(prefix='/api/admin', tags=['admin'])


def row_to_user(row: sqlite3.Row) -> UserPublic:
    return UserPublic(
        id=row['id'],
        username=row['username'],
        display_name=row['display_name'],
        is_admin=bool(row['is_admin']),
        is_active=bool(row['is_active']),
    )


@router.get('/users', response_model=list[UserPublic])
def list_users(
    _admin=Depends(get_current_admin),
    connection: sqlite3.Connection = Depends(get_db),
):
    rows = connection.execute(
        """
        SELECT id, username, display_name, is_admin, is_active
        FROM users
        WHERE is_active = 1
        ORDER BY is_admin DESC, username
        """
    ).fetchall()
    return [row_to_user(row) for row in rows]


@router.post('/users', response_model=UserPublic)
def create_user(
    payload: AdminUserCreate,
    _admin=Depends(get_current_admin),
    connection: sqlite3.Connection = Depends(get_db),
):
    now = utc_now()
    try:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                display_name,
                password_hash,
                is_admin,
                is_active,
                created_at,
                updated_at,
                password_changed_at
            )
            VALUES (?, ?, ?, 0, 1, ?, ?, ?)
            """,
            (
                payload.username,
                payload.username,
                hash_password(payload.password),
                now,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Username already exists') from exc

    connection.execute(
        """
        INSERT OR IGNORE INTO project_access (user_id, project_id, can_access)
        SELECT ?, id, 1
        FROM projects
        WHERE is_active = 1
        """,
        (cursor.lastrowid,),
    )
    user = connection.execute(
        """
        SELECT id, username, display_name, is_admin, is_active
        FROM users
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return row_to_user(user)


@router.delete('/users/{user_id}', response_model=OkResponse)
def delete_user(
    user_id: int,
    admin=Depends(get_current_admin),
    connection: sqlite3.Connection = Depends(get_db),
):
    user = connection.execute(
        'SELECT id, is_admin FROM users WHERE id = ? AND is_active = 1',
        (user_id,),
    ).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    if user['id'] == admin['id']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot delete current user')
    if user['is_admin']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot delete admin user')

    connection.execute('UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?', (utc_now(), user_id))
    connection.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    connection.execute('DELETE FROM project_access WHERE user_id = ?', (user_id,))
    return OkResponse(ok=True)
