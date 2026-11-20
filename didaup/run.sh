#!/bin/sh
set -eu
cd /srv/didaup
exec uvicorn app.main:app --host 0.0.0.0 --port 8097 --no-proxy-headers --no-access-log
