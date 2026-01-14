# writesomething.fun

Self-hosted multi-service platform running on Ubuntu 24.04 with Cloudflare Tunnel.

## Services

- **Excalidraw** - Collaborative whiteboard at draw.writesomething.fun
- **24/7 Radio** - 7 music stations at radio.writesomething.fun
- **File Dump** - Pastebin/file sharing at dump.writesomething.fun
- **Netdata** - Server monitoring at server.writesomething.fun

## Architecture

- Docker + docker-compose for containerization
- Cloudflare Tunnel for zero-config public routing (no port forwarding)
- Icecast + Liquidsoap for radio streaming
- FastAPI for dump service
- Netdata for monitoring

## Quick Start

1. Clone this repo
2. Copy example configs
3. Set up Cloudflare Tunnel
4. Run `docker-compose up -d` in each service directory

## Services Setup

### Radio
- 7 stations: Daft Punk, Lifafa, Marathi, Hindi Old, Gazals, Road Trip, Rap
- Music files not included (115+ tracks total)
- Place MP3s in `radio/music/[station-name]/` directories

### Dump App
- FastAPI backend on port 4000
- 4 Uvicorn workers
- File storage in `/data/dump/`

### Excalidraw
- Frontend: port 5000
- Collab server: port 5001

### Netdata
- Port 3000
- Real-time system monitoring
