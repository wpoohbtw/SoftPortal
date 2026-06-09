# SoftPortal deployment

Example layout for deploying SoftPortal together with ProfitsNLosses:

```text
/srv/SoftPortal/
  backend/
  frontend/
    dist/
/srv/ProfitsNLosses/
  backend/
  dist/
```

## SoftPortal backend

```bash
cd /srv/SoftPortal/backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.production.example .env
nano .env
sudo cp /srv/SoftPortal/deploy/softportal-api.http-ip.service /etc/systemd/system/softportal-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now softportal-api
```

For temporary HTTP-by-IP deployment keep:

```text
PORTAL_COOKIE_SECURE=0
```

After moving to HTTPS, change it to `1`, restart `softportal-api`, and use the HTTPS nginx example.

Set `PORTAL_ADMIN_PASSWORD` before the first backend start. If `backend/data/portal.db` already exists, changing this env variable will not change the existing admin password.

## SoftPortal frontend

```bash
cd /srv/SoftPortal/frontend
npm ci
npm run build
```

## Nginx for HTTP by IP

```bash
sudo cp /srv/SoftPortal/deploy/nginx.http-ip.example.conf /etc/nginx/sites-available/softportal.conf
sudo ln -s /etc/nginx/sites-available/softportal.conf /etc/nginx/sites-enabled/softportal.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Nginx after a domain and HTTPS are configured

Use `deploy/nginx.portal.example.conf`, set a real `server_name`, configure certificates, then set:

```text
PORTAL_COOKIE_SECURE=1
PORTAL_COOKIE_SAMESITE=lax
```

## ProfitsNLosses integration

`/pnl/` is protected by nginx `auth_request` against `/api/auth/proxy-check`.
Nginx sends `/pnl/` to the SoftPortal backend, not directly to ProfitsNLosses. SoftPortal then:

- checks the Portal session;
- serves the ProfitsNLosses frontend from `PORTAL_PNL_DIST_PATH`;
- proxies `/pnl/api/v1/*` to `PORTAL_PNL_API_URL`;
- passes `X-Portal-User-Id` and `X-Portal-Username`.

ProfitsNLosses backend should listen privately on `127.0.0.1:8001`.
