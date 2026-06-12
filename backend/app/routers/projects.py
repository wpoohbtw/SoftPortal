import sqlite3

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user, get_db
from ..schemas import ProjectPublic

router = APIRouter(prefix='/api/projects', tags=['projects'])


def get_accessible_projects(
    connection: sqlite3.Connection,
    user_id: int,
) -> list[ProjectPublic]:
    rows = connection.execute(
        """
        SELECT projects.key, projects.name, projects.path, projects.description
        FROM projects
        JOIN project_access ON project_access.project_id = projects.id
        WHERE project_access.user_id = ?
          AND project_access.can_access = 1
          AND projects.is_active = 1
        ORDER BY
          CASE projects.key
            WHEN 'pnl' THEN 1
            WHEN 'fnup' THEN 2
            ELSE 10
          END,
          projects.id
        """,
        (user_id,),
    ).fetchall()
    return [ProjectPublic(**dict(row)) for row in rows]


@router.get('', response_model=list[ProjectPublic])
def list_projects(
    current_user=Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
):
    return get_accessible_projects(connection, current_user['id'])
