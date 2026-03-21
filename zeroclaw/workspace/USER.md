# USER.md — Who You're Helping

## About You
- **Name:** Mandar
- **Timezone:** UTC
- **Languages:** English, Marathi

## Your Server
- **Domain:** writesomething.fun
- **Server:** Ubuntu, hosted somewhere with Cloudflare Tunnel
- **GitHub:** https://github.com/mandarwagh9/server
- **Git author:** mandarwagh9 <mandarwagh90@gmail.com>

## Services You Manage
| Service | URL | Port | Location |
|---------|-----|------|----------|
| Landing | writesomething.fun | 8000 | |
| Dump | dump.writesomething.fun | 4000 | /home/mandar/dump-app/ |
| Radio | radio.writesomething.fun | 8090 | /home/mandar/radio/ |
| Skribbl | skribbl.writesomething.fun | 5002 | /home/mandar/skribbl/ |
| Draw | draw.writesomething.fun | 5000 | /home/mandar/excalidraw/ |
| Collab | collab.writesomething.fun | 5001 | |
| ZeroClaw | claw.writesomething.fun | 42618 | /home/mandar/.zeroclaw/ |
| Monitoring | server.writesomething.fun | 3031 | /home/mandar/monitoring/ |
| Auth | auth.writesomething.fun | 8080 | |
| Wiki | wiki.writesomething.fun | 8090 | |

## Cloudflare Tunnel
- Config: /etc/cloudflared/config.yml
- Tunnel ID: 82377467-2594-41e3-a760-84c64a788819

## Your Workflow
1. Make changes on the server
2. Commit and push to https://github.com/mandarwagh9/server
3. Restart services via systemctl

## Preferences
- Minimal output, no emojis, professional tone
- Push to git after every meaningful change
