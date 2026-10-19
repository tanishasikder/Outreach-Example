#!/usr/bin/env bash
# Run ON THE SERVER to deploy the latest code from GitHub:
#   cd /opt/outreach && bash deploy/deploy.sh
#   SKIP_SSM=1 bash deploy/deploy.sh    # use the existing .env instead of SSM Parameter Store
#                                       # (e.g. when an AWS Organization policy blocks SSM)
# Safe to run again: Docker only rebuilds and restarts what changed.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Pull latest code"
git pull --ff-only

if [[ "${SKIP_SSM:-}" == "1" ]]; then
  echo "== Using the existing .env (SKIP_SSM=1)"
  [[ -f .env ]] || { echo "No .env file. Create it first (see deploy/README.md)"; exit 1; }
else
  echo "== Settings and secrets from SSM"
  bash deploy/fetch_env.sh
fi

# Trained models when S3_BUCKET is empty. Airflow (user 50000) writes, the worker reads
mkdir -p artifacts
chmod 777 artifacts

echo "== App: web, api, worker, redis"
docker compose --env-file .env -f deploy/compose.yaml up -d --build --remove-orphans

echo "== Pipeline: Airflow"
docker compose --env-file .env -f airflow/compose.yaml up -d --build --remove-orphans

echo "== Remove old images"
docker image prune -f >/dev/null

docker compose -f deploy/compose.yaml ps
docker compose -f airflow/compose.yaml ps
