# writesomething.fun

Personal self-hosted platform running on Ubuntu 24.04, exposed via Cloudflare Tunnel with zero port forwarding.

## Services

| Service | URL | Description |
|---------|-----|-------------|
| ZeroClaw | claw.writesomething.fun | Personal AI assistant (NVIDIA NIM / Moonshot) |
| Radio | radio.writesomething.fun | 24/7 music streaming via Icecast + Liquidsoap |
| Dump | dump.writesomething.fun | File uploads, pastebin, links, chat |
| Skribbl | skribbl.writesomething.fun | Multiplayer drawing and guessing game |
| Draw | draw.writesomething.fun | Collaborative whiteboard (Excalidraw) |
| Collab | collab.writesomething.fun | Real-time Excalidraw collaboration |
| Dashboard | server.writesomething.fun | Server monitoring via Grafana |
| Wiki | wiki.writesomething.fun | Offline Wikipedia mirror |
| Auth | auth.writesomething.fun | Authentication service |
| Auth Admin | authadmin.writesomething.fun | Auth service admin panel |

## Stack

- **Docker + docker-compose** — container orchestration
- **Cloudflare Tunnel** — public routing without opening ports
- **Icecast + Liquidsoap** — radio streaming server and source client
- **FastAPI** — dump-app backend (file storage, pastebin, links, chat)
- **Grafana + Prometheus** — metrics, dashboards, alerting
- **ZeroClaw (Rust)** — personal AI assistant on NVIDIA NIM (moonshotai/kimi-k2.5)
- **Node.js + Socket.IO** — skribbl multiplayer game

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
- `/chat` — Ephemeral WebSocket chat rooms (auto-delete when empty)
- `/suggest` — Feature suggestion board with upvoting

### Skribbl

Multiplayer drawing and guessing game running on port 5002. Node.js + Socket.IO.

```
cd skribbl
node server.js
```

Access at https://skribbl.writesomething.fun

### ZeroClaw

Personal AI assistant powered by Rust. Running on port 42618, exposed via Cloudflare Tunnel.

- **Provider:** NVIDIA NIM (moonshotai/kimi-k2.5)
- **Binary:** `/home/mandar/.cargo/bin/zeroclaw`
- **Config:** `/home/mandar/.zeroclaw/config.toml`
- **Workspace:** `/home/mandar/.zeroclaw/workspace/`
- **Service:** systemd unit at `/etc/systemd/system/zeroclaw.service`

```
zeroclaw gateway start -p 42618  # start gateway
zeroclaw agent -m "hello"         # test agent
zeroclaw status                   # check status
zeroclaw doctor                   # diagnostics
```

Access dashboard at https://claw.writesomething.fun (requires pairing code).

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
7. Start skribbl: `cd skribbl && node server.js`
8. Install zeroclaw: extract binary, configure `~/.zeroclaw/config.toml`, `zeroclaw gateway start -p 42618`

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
