# writesomething.fun

Self-hosted multi-service platform running on Ubuntu 24.04 with Cloudflare Tunnel.

## Services

- **Excalidraw** - Collaborative whiteboard at draw.writesomething.fun
- **24/7 Radio** - Music stations at radio.writesomething.fun
- **File Dump** - Pastebin/file sharing at dump.writesomething.fun
- **Grafana** - Metrics dashboards at server.writesomething.fun
- **MachineAuth** - OAuth for AI agents at auth.writesomething.fun

## Architecture

- Docker + docker-compose for containerization
- Cloudflare Tunnel for zero-config public routing (no port forwarding)
- Icecast + Liquidsoap for radio streaming
- FastAPI for dump service
- Grafana + Prometheus for metrics & monitoring

## Quick Start

1. Clone this repo
2. Copy example configs
3. Set up Cloudflare Tunnel
4. Run `docker-compose up -d` in each service directory

## Services Setup

### Radio
- Music stations: Daft Punk, Lifafa, Marathi, Hindi Old, Gazals, Road Trip, Rap
- Music files not included
- Place MP3s in `radio/music/[station-name]/` directories

### Dump App
- FastAPI backend on port 4000
- File storage in `/data/dump/`

### Excalidraw
- Frontend: port 5000
- Collab server: port 5001

### Monitoring (Grafana + Prometheus)
- Grafana: https://server.writesomething.fun
- Login: admin / admin123
- Prometheus: port 9090
- Includes dashboards:
  - Home (overview)
  - System Overview (CPU, RAM, Disk, Network)
  - Nginx Traffic (requests, status codes, connections)
  - Docker Containers (per-container metrics)

Setup:
```bash
cd monitoring
docker-compose up -d
```

### MachineAuth (OAuth)
- OAuth 2.0 server for AI agents
- Admin dashboard: https://authadmin.writesomething.fun
- Login: admin@example.com / changeme
