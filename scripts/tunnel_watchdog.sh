#!/bin/sh
# Keeps the web app reachable: run from cron every couple of minutes on the server.
# A quick tunnel gets a new address when it restarts; the bot reads the new one by itself.
cd "$(dirname "$0")/.." || exit 1
log() { echo "$(date '+%F %T') $*" >> backups/tunnel_watchdog.log; }

health=$(docker inspect -f '{{.State.Health.Status}}' aroma_web 2>/dev/null)
if [ "$health" != "healthy" ] && [ "$health" != "starting" ]; then
    log "web is '$health': restarting it"
    docker restart aroma_web >/dev/null 2>&1
    sleep 40
fi

url=$(docker logs aroma_quicktunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1)
ok=0
for try in 1 2 3; do
    if [ -n "$url" ] && [ "$(curl -s -o /dev/null -m 15 -w '%{http_code}' "$url/api/health")" = "200" ]; then ok=1; break; fi
    sleep 15
done
if [ "$ok" = 0 ]; then
    log "tunnel $url does not answer: restarting it"
    docker restart aroma_quicktunnel >/dev/null 2>&1
fi
