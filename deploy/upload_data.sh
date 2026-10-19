#!/usr/bin/env bash
# Run on YOUR computer (Git Bash) to send new raw data to the pipeline:
#   ./deploy/upload_data.sh                 # uploads data/accounts.csv, deals.csv, events.csv
#   ./deploy/upload_data.sh path/to/folder  # or CSVs with those names from another folder
# The next deal_pipeline run (daily, or trigger it in Airflow) cleans them and retrains.
set -euo pipefail
SRC=${1:-data}
BUCKET=$(terraform -chdir=infra/terraform output -raw bucket_name)
for name in accounts deals events; do
  aws s3 cp "$SRC/$name.csv" "s3://$BUCKET/raw/$name.csv"
done
