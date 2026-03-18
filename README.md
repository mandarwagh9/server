# writesomething.fun

Personal self-hosted platform running on Ubuntu 24.04, exposed via Cloudflare Tunnel with zero port forwarding.

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Radio | radio.writesomething.fun | 24/7 music streaming via Icecast + Liquidsoap |
| Dump | dump.writesomething.fun | File uploads, pastebin, link bookmarks |
| Draw | draw.writesomething.fun | Collaborative whiteboard |
| Dashboard | server.writesomething.fun | Server monitoring via Grafana |
| Wiki | wiki.writesomething.fun | Offline Wikipedia mirror |

## Stack

- **Docker + docker-compose** — container orchestration
- **Cloudflare Tunnel** — public routing without opening ports
- **Icecast + Liquidsoap** — radio streaming server and source client
- **FastAPI** — dump-app backend (file storage, pastebin, links)
- **Grafana + Prometheus** — metrics, dashboards, alerting

## Service Details

### Radio

Music stations run 24/7 via Icecast (streaming) and Liquidsoap (source). Place MP3 files in the appropriate directories:

```
radio/music/[station-name]/
```

Stations: Daft Punk, Lifafa, Marathi, Hindi Old, Gazals, Road Trip, Rap, Retro Jazz, Pink Floyd, Radiohead, The Smiths, Classical, Fred Again, Chaardiwaari, Seedhe Maut, Dhanji, KK.

### Dump

FastAPI app running on port 4000. Data stored at `/data/dump/`.

**Sub-services:**
- `/` — Landing page with links to all dump features
- `/files` — Browse uploaded files with folder support
- `/paste` — Create code/text pastes with syntax highlighting
- `/p/{id}` — View a paste (supports passwords, expiration)
- `/links` — Bookmark manager with tags and click tracking
- `/suggest` — Feature suggestion board with upvoting

### Draw

Self-hosted Excalidraw instance for collaborative drawing. Frontend on port 5000, collab server on port 5001.

### Monitoring

Grafana + Prometheus stack for server and service metrics.

**Access:** https://server.writesomething.fun  
**Login:** admin / admin123  
**Prometheus:** port 9090

**Dashboards included:**
- Home — overview of all metrics
- System Overview — CPU, RAM, disk, network
- Nginx Traffic — requests, status codes, connections
- Docker Containers — per-container resource usage

```
cd monitoring
docker-compose up -d
```

## Deployment

1. Clone this repo
2. Set up Cloudflare Tunnel and add routes to `cloudflare/config.yml`
3. Place music files in `radio/music/[station]/`
4. `mkdir -p /data/dump` for file storage
5. Run `docker-compose up -d` per service
6. Start dump-app: `cd dump-app && uvicorn app:app --host 127.0.0.1 --port 4000`

## Cloudflare Tunnel

Each subdomain is routed in `/etc/cloudflared/config.yml`:

```yaml
tunnel: <id>
credentials-file: /etc/cloudflared/creds.json

ingress:
  - hostname: radio.writesomething.fun
    service: http://localhost:8090
  - hostname: dump.writesomething.fun
    service: http://localhost:4000
  # ...etc
```
