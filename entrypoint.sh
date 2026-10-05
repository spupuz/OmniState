#!/bin/sh
set -e
# Fix ownership of mounted /data when running as root before dropping privileges.
# The image USER is root by default; this script chowns /data to omnistate if needed
# and then execs as the unprivileged user.
if [ "$(id -u)" = "0" ]; then
  if [ -d /data ]; then
    chown -R omnistate:omnistate /data 2>/dev/null || chmod -R 775 /data 2>/dev/null || true
  fi
  exec su omnistate -c "exec $*"
fi
exec "$@"
