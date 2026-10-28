#!/bin/sh
set -e
# Fix ownership of mounted /data when running as root before dropping privileges.
if [ "$(id -u)" = "0" ]; then
  if [ -d /data ]; then
    chown -R omnistate:omnistate /data 2>/dev/null || chmod -R 775 /data 2>/dev/null || true
  fi
  exec su omnistate -c "python /app/supermemory_server.py >/tmp/supermemory.log 2>&1 & for i in \$(seq 1 40); do curl -fsS http://localhost:6767/health >/dev/null 2>&1 && break; sleep 0.25; done; exec $*"
fi
python /app/supermemory_server.py >/tmp/supermemory.log 2>&1 &
for i in $(seq 1 40); do
  curl -fsS http://localhost:6767/health >/dev/null 2>&1 && break
  sleep 0.25
done
exec "$@"
