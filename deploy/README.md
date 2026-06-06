# SoftPortal deployment

Example layout:

```text
/srv/softportal/
  backend/
  frontend/
    dist/
```

Backend:

```bash
cd /srv/softportal/backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
sudo cp /srv/softportal/deploy/softportal-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now softportal-api
```

Frontend:

```bash
cd /srv/softportal/frontend
npm ci
npm run build
```

Nginx:

```bash
sudo cp /srv/softportal/deploy/nginx.portal.example.conf /etc/nginx/sites-available/softportal.conf
sudo ln -s /etc/nginx/sites-available/softportal.conf /etc/nginx/sites-enabled/softportal.conf
sudo nginx -t
sudo systemctl reload nginx
```

Production flags:

```text
PORTAL_COOKIE_SECURE=1
PORTAL_COOKIE_SAMESITE=lax
PORTAL_ADMIN_PASSWORD=<set-before-first-start>
```

`/pnl/` is protected by nginx `auth_request` against `/api/auth/proxy-check`.
The actual ProfitsNLosses service is expected on `127.0.0.1:8010` in the sample config.
