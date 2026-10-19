#!/usr/bin/env bash
# Run on YOUR computer (Git Bash) once, after `terraform apply`, to store the secrets
# in AWS SSM Parameter Store (encrypted). The server reads them with its IAM role,
# so no secret is ever copied to the server by hand or committed to git.
#
#   ./deploy/set_secrets.sh            # asks for each value
#
# Re-run it any time to change a value, then run deploy.sh on the server.
set -euo pipefail
export MSYS_NO_PATHCONV=1 # Stop Git Bash turning "/outreach/..." into a Windows path

REGION=$(terraform -chdir=infra/terraform output -raw region)

put() { # name value
  aws ssm put-parameter --region "$REGION" --name "/outreach/$1" --value "$2" \
    --type SecureString --overwrite >/dev/null
  echo "  saved /outreach/$1"
}

ask() { # name description
  local value
  read -r -s -p "$1 ($2): " value; echo
  if [[ -z "$value" ]]; then echo "  skipped $1"; return; fi
  put "$1" "$value"
}

random() { python -c "import secrets; print(secrets.token_hex(32))"; }

echo "API keys (input is hidden, press Enter to skip one you already set):"
ask GOOGLE_API_KEY "Gemini key for the sales report"
ask QDRANT_URL "Qdrant Cloud cluster URL"
ask QDRANT_KEY "Qdrant Cloud API key"

echo "Generated secrets (only set the first time, so existing logins keep working):"
for name in JWT_SECRET_KEY AIRFLOW_JWT_SECRET AIRFLOW_DB_PASSWORD AIRFLOW_ADMIN_PASSWORD; do
  if aws ssm get-parameter --region "$REGION" --name "/outreach/$name" >/dev/null 2>&1; then
    echo "  /outreach/$name already exists, kept"
  else
    put "$name" "$(random)"
  fi
done
if ! aws ssm get-parameter --region "$REGION" --name "/outreach/AIRFLOW_FERNET_KEY" >/dev/null 2>&1; then
  put AIRFLOW_FERNET_KEY "$(python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")"
fi

echo
echo "Airflow login: user 'airflow', password:"
echo "  aws ssm get-parameter --region $REGION --name /outreach/AIRFLOW_ADMIN_PASSWORD --with-decryption --query Parameter.Value --output text"
