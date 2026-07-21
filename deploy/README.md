# Deploy configs (nginx, fail2ban, monitoring)

These files mirror what's actually applied on the prod server. Nginx and fail2ban run
directly on the host, outside docker-compose, so there's no automated sync — when you
change one of these files, copy it to the server by hand and reload the relevant
service. See `../DEPLOY-SELECTEL.md` (Часть 5 и Часть 7) for the full setup walkthrough.

`monitoring/` is different: it runs *inside* `docker-compose.prod.yml` (Prometheus,
Grafana, node-exporter, cAdvisor), so it comes up automatically with `docker compose up`.
See `monitoring/README.md` for access (SSH tunnel only, nothing public).

## nginx/otherside-api.conf

Reverse proxy for the FastAPI container. Restricts proxying to `/api/*` and `/health`;
every other path gets a flat 404 from nginx itself, so scanner noise (`.env`,
`wp-login.php`, firebase keys, `/owa/`, ...) never reaches uvicorn. Certbot manages the
SSL directives — only re-run `certbot --nginx` if you actually need to touch the SSL
block, otherwise a plain copy + reload is enough.

Apply:

```bash
scp deploy/nginx/otherside-api.conf root@<server>:/etc/nginx/sites-available/otherside-api
ssh root@<server> 'nginx -t && systemctl reload nginx'
```

## fail2ban/

Bans IPs hammering nginx with repeated 404s (the scanner background noise everyone gets
on a public IP). Default threshold: 15 hits in 5 minutes -> 1 hour ban.

Apply:

```bash
scp deploy/fail2ban/filter.d/otherside-nginx-404.conf root@<server>:/etc/fail2ban/filter.d/
scp deploy/fail2ban/jail.d/otherside-nginx-404.conf root@<server>:/etc/fail2ban/jail.d/
ssh root@<server> 'systemctl restart fail2ban && fail2ban-client status otherside-nginx-404'
```
