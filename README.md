# SoftPortal

Private project portal scaffold.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, SQLite
- Auth scaffold: users, sessions, project access
- Admin scaffold: create and remove portal users
- Deployment scaffold: static frontend, FastAPI API, protected future `/pnl/` reverse proxy route

## Development

Run everything through one launcher:

```bat
run-local.bat
```

Open:

```text
http://127.0.0.1:5173
```

ProfitsNLosses is available through the portal after login:

```text
http://127.0.0.1:5173/pnl/
```

The launcher also prepares the local PnLs integration:

- builds `../ProfitsNLosses/dist` with Vite base `/pnl/`;
- starts the PnLs backend on `http://127.0.0.1:8001`;
- starts the Portal backend on a free local port;
- proxies `/pnl/`, `/pnl/api/v1/*`, and `/pnl/api/v1/market/ws` through Portal auth.

If the default dev port is busy, the launcher tries `5174` and `5175` and prints
the selected URL in the same console.

Login image:

```text
C:\Soft\Projects\SoftPortal\login-art.jpg
```

The launcher copies this file into `frontend/public/login-art.jpg` before Vite starts.
Use a dark, wide image; `jpg` is expected.

Default seeded admin:

```text
login: admin
password: ChangeMe123!
```

Before first backend start, set `PORTAL_ADMIN_PASSWORD` if you want another initial
password. The seed is only created when the `admin` user does not exist yet.

## Layout

```text
SoftPortal/
  backend/
  frontend/
  deploy/
  vault/
  run-local.bat
```

## Notes

- Registration is intentionally absent.
- Unauthenticated API calls return `401`; the frontend returns to login when there is no session.
- The ProfitsNLosses project button opens `/pnl/`.
- Local `/pnl/` integration is served by the Portal backend; production can use the nginx `auth_request` example.
- Admin users can open `/admin` and manage portal users.
