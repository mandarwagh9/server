# writesomething.fun

Self-hosted multi-service platform on Ubuntu 24.04 via Cloudflare Tunnel.

## Services

- **Radio** - 24/7 music streaming at radio.writesomething.fun
- **Dump** - File uploads, pastebin, and link bookmarks at dump.writesomething.fun
- **Draw** - Collaborative whiteboard at draw.writesomething.fun
- **Dashboard** - Server monitoring at server.writesomething.fun

## Architecture

- Docker + docker-compose for containers
- Cloudflare Tunnel for public routing (no port forwarding)
- Icecast + Liquidsoap for radio
- FastAPI for dump service
- Grafana + Prometheus for monitoring

## Setup

### Radio
Music files not included. Place MP3s in `radio/music/[station]/` directories.

### Dump
FastAPI on port 4000. File storage at `/data/dump/`.
Dumps: `/` - Paste: `/paste` - Links: `/links` - Files: `/files`

### Monitoring
```
cd monitoring
docker-compose up -d
```
Grafana: https://server.writesomething.fun (admin / admin123)
