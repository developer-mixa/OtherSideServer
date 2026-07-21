# Monitoring stack (Prometheus + Grafana + node-exporter + cAdvisor)

| Service       | Scrapes / serves                                   |
|---------------|-----------------------------------------------------|
| node-exporter | Host CPU, RAM, disk, network                         |
| cadvisor      | Per-container CPU/RAM/IO (api, db, prometheus, ...)  |
| prometheus    | Scrapes node-exporter + cadvisor, stores metrics     |
| grafana       | Dashboards, reads from Prometheus                    |

Same four services are defined in both compose files, but behave differently:

- **`docker-compose.prod.yml` (server): always on, no profile.** A plain
  `docker compose -f docker-compose.prod.yml up -d` brings monitoring up alongside
  `api`/`db` — prod should always be observable. Nothing is exposed on a public port:
  Grafana binds to `127.0.0.1:3001` and is reached only through an SSH tunnel.
- **`docker-compose.yml` (local dev): opt-in, behind the `monitoring` profile.**
  A plain `docker compose up` never starts these locally — you bring them up
  explicitly so day-to-day dev work doesn't pay for four extra containers.

## Testing locally

```bash
docker compose --profile monitoring up -d node-exporter cadvisor prometheus grafana
```

Open `http://localhost:3001`, log in as `admin` / `admin` (local default — see
`GRAFANA_ADMIN_PASSWORD` in `docker-compose.yml` if you want to override it).

Tear down: `docker compose --profile monitoring down` (add `-v` to also drop the
`prometheus-data`/`grafana-data` volumes).

node-exporter and cadvisor mount host paths read-only (`/`, `/sys`, `/var/lib/docker`,
...) to report on whatever machine runs them — locally that's *your* CPU/disk/
containers, not the server's. That's expected.

## First-time setup on the server

1. Set `GRAFANA_ADMIN_PASSWORD` in the server's `.env` (see `.env.example`) —
   a strong, unique value. Unlike local dev, there's no weak default here.
2. `docker compose -f docker-compose.prod.yml up -d --build` (as usual — monitoring
   comes up with everything else, no extra flag needed).
3. From your machine: `ssh -L 3001:localhost:3001 root@<server>` and open
   `http://localhost:3001`. Log in as `admin` / `GRAFANA_ADMIN_PASSWORD`.
4. The Prometheus datasource is pre-provisioned. Add dashboards via
   **Dashboards → New → Import** using these community IDs:
   - `1860` — Node Exporter Full (host CPU/RAM/disk/network)
   - `19792` — Docker / cAdvisor containers (or `193` for the older classic one)

## Day to day

- Tunnel: `ssh -L 3001:localhost:3001 root@<server>`, then browse `localhost:3001`.
- Data persists in the `prometheus-data` / `grafana-data` docker volumes — restarting
  containers doesn't lose history.
- To change what's scraped, edit `prometheus.yml` here and restart prometheus
  (`docker compose -f docker-compose.prod.yml restart prometheus` on the server,
  `docker compose --profile monitoring restart prometheus` locally).
