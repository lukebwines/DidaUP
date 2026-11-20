#!/bin/sh
set -eu
# The Supervisor mounts /data at runtime. Initialize permissions, then drop root.
chown -R didaup:didaup /data
chmod 700 /data
cd /srv/didaup
exec gosu didaup uvicorn app.main:app --host 0.0.0.0 --port 8097 --no-proxy-headers --no-access-log
