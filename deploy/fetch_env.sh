#!/usr/bin/env bash
# Run ON THE SERVER (deploy.sh calls it). Writes .env from SSM Parameter Store
# (/outreach/*) using the instance's IAM role. .env is readable by ec2-user only.
set -euo pipefail
cd "$(dirname "$0")/.."
source /etc/outreach.env # AWS_REGION, written when Terraform created the server

aws ssm get-parameters-by-path --region "$AWS_REGION" --path /outreach/ --recursive \
  --with-decryption --query 'Parameters[].[Name,Value]' --output text > /tmp/outreach-params
trap 'rm -f /tmp/outreach-params' EXIT

umask 077
{
  echo "# Written by deploy/fetch_env.sh from SSM /outreach/*. Edit values in SSM, not here."
  while IFS=$'\t' read -r name value; do
    # Single quotes: Docker Compose and python-dotenv both take the value literally
    printf "%s='%s'\n" "${name##*/}" "${value//\'/}"
  done < /tmp/outreach-params
} > .env.tmp
mv .env.tmp .env
echo "Wrote .env with $(grep -c "=" .env) settings"
