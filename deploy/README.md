# Deploying to AWS

```
                     ┌──────────────────── EC2 server (Docker) ─────────────────────┐
 Browser ── :80/443 ─▶ web (Caddy) ─/api─▶ api (FastAPI) ─▶ redis ─▶ worker (Celery) │
                     │   serves frontend/                        loads model ▲      │
                     │                                                       │      │
                     │ Airflow (daily): dbt build ─▶ train ─▶ promote ───────┤      │
                     └───────────────────────────────────────────────────────┼──────┘
                                                                             │
                     S3 bucket:  raw/*.csv  (you upload)   models/<version>/, models/latest.json
                     SSM Parameter Store: /outreach/*  (settings + secrets, read with the server's IAM role)
```

Everything runs on one EC2 server to keep it simple and cheap. Nothing on the
server uses AWS access keys: it gets permissions from its IAM role.

## 1. On your computer (once)

1. **Install the tools** (PowerShell):
   ```
   winget install Amazon.AWSCLI Amazon.SessionManagerPlugin Hashicorp.Terraform
   ```
2. **Sign in to AWS** with your own IAM user or SSO (not the root account), then check it works:
   ```
   aws configure          # or: aws configure sso
   aws sts get-caller-identity
   ```
3. **Set a budget alert**: AWS console → Billing → Budgets → create a monthly budget (e.g. $20) with an email alert.
4. **Push your code to GitHub.** The server deploys whatever is on `main`.

## 2. Create the AWS resources

```
cd infra/terraform
terraform init
terraform apply        # review the plan, type "yes"
```

This creates the server, S3 bucket, IAM role, security group, public IP and
non-secret settings. It prints the URL, bucket name and commands used below
(`terraform output` shows them again). Give the server about 3 minutes to install Docker.

## 3. Store the secrets (from the project root, in Git Bash)

```
bash deploy/set_secrets.sh
```

Asks for your Gemini and Qdrant keys and generates the JWT and Airflow secrets.
They're stored encrypted in SSM, never in git or Terraform.

## 4. Upload the raw data

```
bash deploy/upload_data.sh
```

## 5. Deploy

Open a terminal on the server (no SSH keys needed):

```
terraform -chdir=infra/terraform output -raw shell_command    # copy and run what it prints
```

Then on the server:

```
sudo su - ec2-user
cd /opt/outreach && bash deploy/deploy.sh
```

The first deploy builds the images (about 10 minutes). Afterwards:

- The site is at the `url` output.
- Airflow runs `deal_pipeline` right away and then daily. Until a model is promoted,
  the worker uses the model committed in `src/models/`.

## 6. Load the sales PDFs into Qdrant (once)

Open Airflow (step 7) and trigger the `rag_ingest` DAG. Until then, predictions work
but the sales report says it could not be generated.

## 7. Airflow UI

Airflow isn't open to the internet. Open a tunnel from your computer and leave it running:

```
terraform -chdir=infra/terraform output -raw airflow_tunnel_command   # run what it prints
```

Go to http://localhost:8080, user `airflow`. The password is:

```
aws ssm get-parameter --name /outreach/AIRFLOW_ADMIN_PASSWORD --with-decryption --query Parameter.Value --output text
```

## Day to day

| To... | Do this |
|---|---|
| Add new data | `bash deploy/upload_data.sh`, then wait for the daily run or trigger `deal_pipeline` |
| Deploy a code change | `git push`, then on the server: `cd /opt/outreach && bash deploy/deploy.sh` |
| Make a login token (there's no login page yet) | On the server: `docker compose -f deploy/compose.yaml exec api python -m src.schemas.jwt alice 1440` |
| See logs | On the server: `docker compose -f deploy/compose.yaml logs -f worker` (or `api`, `web`) |
| See model versions | `aws s3 ls s3://<bucket>/models/` and `aws s3 cp s3://<bucket>/models/latest.json -` |
| Roll back the model | On the server: `docker compose -f airflow/compose.yaml exec airflow-scheduler bash -c "cd /opt/app && /opt/pipeline/bin/python -m src.pipeline.promote <version> --force"`. The worker switches within 5 minutes |
| Change a secret | `bash deploy/set_secrets.sh` (or `aws ssm put-parameter ... --overwrite`), then `deploy.sh` |

## HTTPS with your own domain

1. At your domain registrar, add an **A record** pointing to the `public_ip` output.
2. `terraform apply -var site_address=deals.example.com`
3. On the server: `bash deploy/deploy.sh`. Caddy gets the certificate automatically.

## Cost and shutting down

Roughly **$65/month** if left running: t3.large ~$61, 30 GB disk ~$2.40, public IP ~$3.60, S3 a few cents.

- **Pause**: `aws ec2 stop-instances --instance-ids <instance_id>` (disk and IP still cost ~$6/month).
  Start it again with `start-instances`; everything comes back up by itself.
- **Delete everything**: empty the bucket (S3 console → bucket → *Empty*), then `terraform destroy`.

## Troubleshooting

- **Setup on first boot**: `sudo cat /var/log/cloud-init-output.log`
- **A pipeline step failed**: Airflow UI → `deal_pipeline` → the red task → *Logs*. Each step is a plain
  command you can run yourself, e.g. `docker compose -f airflow/compose.yaml exec airflow-scheduler bash -c "cd /opt/app && /opt/pipeline/bin/dbt build --project-dir dbt --profiles-dir dbt"`
- **`promote_model` is skipped**: not an error. The new model wasn't better than the live one; the log says why.
- **Server is slow or containers restart**: probably out of memory. Use a bigger `instance_type`.
