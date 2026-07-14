#!/bin/sh
set -e

case "$1" in
  api)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
    ;;
  worker)
    exec arq app.worker.WorkerSettings
    ;;
  *)
    exec "$@"
    ;;
esac
