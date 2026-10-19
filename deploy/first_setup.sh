#!/usr/bin/env bash
# First-time setup ON THE SERVER, without SSM Parameter Store. One command:
#   cd /opt/outreach && git pull && bash deploy/first_setup.sh
# It uploads the raw CSVs to S3, writes .env (asks for your API keys), deploys
# everything, loads the PDFs into Qdrant and prints a login token for the site.
set -euo pipefail
cd "$(dirname "$0")/.."

read -r -p "S3 bucket name: " BUCKET
REGION=$(aws s3api get-bucket-location --bucket "$BUCKET" --query LocationConstraint --output text 2>/dev/null || true)
if [[ -z "$REGION" || "$REGION" == "None" || "$REGION" == "null" ]]; then
  read -r -p "Bucket region (e.g. us-east-2): " REGION
fi
read -r -p "Domain(s), comma separated [salesoutreach.xyz, www.salesoutreach.xyz]: " SITE
SITE=${SITE:-salesoutreach.xyz, www.salesoutreach.xyz}
read -r -s -p "GROQ_API_KEY (hidden): " GROQ; echo
read -r -p "QDRANT_URL: " QURL
read -r -s -p "QDRANT_KEY (hidden): " QKEY; echo

echo "== Upload raw CSVs to s3://$BUCKET/raw/"
for f in accounts deals events; do
  aws s3 cp "data/$f.csv" "s3://$BUCKET/raw/$f.csv" --region "$REGION" --only-show-errors
done

echo "== Write .env"
umask 077
cat > .env <<EOF
S3_BUCKET='$BUCKET'
DBT_TARGET='aws'
AWS_REGION='$REGION'
SITE_ADDRESS='$SITE'
GROQ_API_KEY='$GROQ'
QDRANT_URL='$QURL'
QDRANT_KEY='$QKEY'
JWT_SECRET_KEY='$(openssl rand -hex 32)'
AIRFLOW_JWT_SECRET='$(openssl rand -hex 32)'
AIRFLOW_DB_PASSWORD='$(openssl rand -hex 16)'
AIRFLOW_ADMIN_PASSWORD='$(openssl rand -hex 12)'
AIRFLOW_FERNET_KEY='$(python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")'
EOF

echo "== Deploy (about 10 minutes the first time)"
SKIP_SSM=1 bash deploy/deploy.sh

echo "== Wait for the containers to be ready"
for i in $(seq 1 60); do
  docker compose -f deploy/compose.yaml exec -T api python -c "print()" >/dev/null 2>&1 \
    && docker compose -f airflow/compose.yaml exec -T airflow-scheduler true >/dev/null 2>&1 && break
  sleep 5
done

echo "== Load the sales PDFs into Qdrant"
docker compose -f airflow/compose.yaml exec -T airflow-scheduler \
  bash -c "cd /opt/app && /opt/pipeline/bin/python -m src.models.vector" \
  || echo "!! Qdrant load failed (check QDRANT_URL / QDRANT_KEY). Predictions still work; reports won't."

echo
echo "== Done. Open https://${SITE%%,*}"
echo "Login token for the site (valid 7 days):"
docker compose -f deploy/compose.yaml exec -T api python -m src.schemas.jwt demo 10080
echo
echo "Airflow password (user 'airflow'): $(grep AIRFLOW_ADMIN_PASSWORD .env | cut -d"'" -f2)"
