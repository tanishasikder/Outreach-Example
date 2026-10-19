#!/usr/bin/env bash
# Run ON THE SERVER to deploy the latest code from GitHub:
#   cd /opt/outreach && bash deploy/deploy.sh
# Safe to run again: Docker only rebuilds and restarts what changed.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Pull latest code"
git pull --ff-only

echo "== Settings and secrets from SSM"
bash deploy/fetch_env.sh

echo "== App: web, api, worker, redis"
docker compose --env-file .env -f deploy/compose.yaml up -d --build --remove-orphans

echo "== Pipeline: Airflow"
mkdir -p artifacts
docker compose --env-file .env -f airflow/compose.yaml up -d --build --remove-orphans

echo "== Remove old images"
docker image prune -f >/dev/null

docker compose -f deploy/compose.yaml ps
docker compose -f airflow/compose.yaml ps
