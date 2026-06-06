import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from . import config
from .security import hash_password


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode = WAL')
    connection.execute('PRAGMA busy_timeout = 30000')
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                password_changed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS project_access (
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                can_access INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, project_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )
        ensure_columns(connection)
        seed_admin(connection)
        seed_projects(connection)


def seed_admin(connection: sqlite3.Connection) -> None:
    existing = connection.execute(
        'SELECT id FROM users WHERE username = ?',
        (config.DEFAULT_ADMIN_USERNAME,),
    ).fetchone()
    if existing:
        return

    password = os.getenv('PORTAL_ADMIN_PASSWORD', config.DEFAULT_ADMIN_PASSWORD)
    now = utc_now()
    connection.execute(
        """
        INSERT INTO users (
            username,
            display_name,
            password_hash,
            is_admin,
            created_at,
            updated_at,
            password_changed_at
        )
        VALUES (?, ?, ?, 1, ?, ?, ?)
        """,
        (
            config.DEFAULT_ADMIN_USERNAME,
            config.DEFAULT_ADMIN_DISPLAY_NAME,
            hash_password(password),
            now,
            now,
            now,
        ),
    )


def seed_projects(connection: sqlite3.Connection) -> None:
    projects = [
        ('pnl', 'ProfitsNLosses', '/pnl/', 'Future protected route for finance tools'),
        ('vault', 'Vault Console', '/vault/', 'Admin-only workspace placeholder'),
        ('metrics', 'Metrics Lab', '/metrics/', 'Experiments and reports placeholder'),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO projects (key, name, path, description)
        VALUES (?, ?, ?, ?)
        """,
        projects,
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO project_access (user_id, project_id, can_access)
        SELECT users.id, projects.id, 1
        FROM users
        CROSS JOIN projects
        WHERE users.username = ?
        """,
        (config.DEFAULT_ADMIN_USERNAME,),
    )


def delete_expired_sessions(connection: sqlite3.Connection) -> None:
    connection.execute('DELETE FROM sessions WHERE expires_at <= ?', (utc_now(),))


def ensure_columns(connection: sqlite3.Connection) -> None:
    user_columns = {
        row['name']
        for row in connection.execute('PRAGMA table_info(users)').fetchall()
    }
    if 'updated_at' not in user_columns:
        connection.execute('ALTER TABLE users ADD COLUMN updated_at TEXT')
    if 'password_changed_at' not in user_columns:
        connection.execute('ALTER TABLE users ADD COLUMN password_changed_at TEXT')
