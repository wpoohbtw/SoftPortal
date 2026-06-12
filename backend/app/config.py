import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
WORKSPACE_DIR = PROJECT_DIR.parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'portal.db'

SESSION_COOKIE = 'portal_session'
SESSION_TTL_DAYS = 7
COOKIE_SECURE = os.getenv('PORTAL_COOKIE_SECURE', '0').lower() in {'1', 'true', 'yes'}
COOKIE_SAMESITE = os.getenv('PORTAL_COOKIE_SAMESITE', 'lax')

DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_DISPLAY_NAME = 'Admin'
DEFAULT_ADMIN_PASSWORD = 'ChangeMe123!'

PNL_API_URL = os.getenv('PORTAL_PNL_API_URL', 'http://127.0.0.1:8001').rstrip('/')
PNL_WS_URL = os.getenv('PORTAL_PNL_WS_URL', 'ws://127.0.0.1:8001').rstrip('/')
PNL_DIST_PATH = Path(os.getenv('PORTAL_PNL_DIST_PATH', str(WORKSPACE_DIR / 'ProfitsNLosses' / 'dist')))

FNUP_API_URL = os.getenv('PORTAL_FNUP_API_URL', 'http://127.0.0.1:8002').rstrip('/')
FNUP_DIST_PATH = Path(os.getenv('PORTAL_FNUP_DIST_PATH', str(WORKSPACE_DIR / 'FoldersNUsersParser' / 'dist')))
