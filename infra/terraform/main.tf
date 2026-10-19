# Everything the app needs on AWS:
#   - 1 EC2 server running Docker (app + Airflow), with a fixed public IP
#   - 1 S3 bucket for raw data and trained models
#   - an IAM role so the server can use S3 and SSM without any access keys
#   - settings in SSM Parameter Store (secrets are added by deploy/set_secrets.sh)
#
#   cd infra/terraform
#   terraform init
#   terraform apply

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "outreach" } # Find everything this created in the AWS console / billing
  }
}

data "aws_caller_identity" "current" {}
data "aws_vpc" "default" { default = true }

# Latest Amazon Linux 2023 image
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  ssm_prefix = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/outreach"
}

# ---------------------------------------------------------------- S3

resource "aws_s3_bucket" "data" {
  bucket_prefix = "outreach-data-" # AWS adds a unique suffix
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Keeps old copies of overwritten files (e.g. a bad raw upload or models/latest.json)
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

# ---------------------------------------------------------------- IAM (no access keys)

resource "aws_iam_role" "server" {
  name_prefix = "outreach-server-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Only this bucket and only /outreach/* settings
resource "aws_iam_role_policy" "server" {
  name = "outreach-app"
  role = aws_iam_role.server.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.data.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"]
        Resource = ["${local.ssm_prefix}", "${local.ssm_prefix}/*"]
      },
    ]
  })
}

# Lets you open a terminal on the server from the AWS console/CLI, without SSH keys or port 22
resource "aws_iam_role_policy_attachment" "ssm_session" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "server" {
  name_prefix = "outreach-server-"
  role        = aws_iam_role.server.name
}

# ---------------------------------------------------------------- Network

# Only the website is open to the internet. Airflow (8080) is not; reach it through an SSM tunnel
resource "aws_security_group" "server" {
  name_prefix = "outreach-server-"
  description = "Outreach web traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description      = "HTTP"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  ingress {
    description      = "HTTPS"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  egress {
    description      = "All outbound (GitHub, Docker Hub, S3, Gemini, Qdrant)"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  lifecycle { create_before_destroy = true }
}

# ---------------------------------------------------------------- Server

resource "aws_instance" "server" {
  ami                    = nonsensitive(data.aws_ssm_parameter.al2023.value)
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.server.name
  vpc_security_group_ids = [aws_security_group.server.id]

  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", {
    region   = var.region
    repo_url = var.repo_url
    branch   = var.branch
  })

  metadata_options {
    http_tokens                 = "required" # IMDSv2 only (blocks a common credential-theft trick)
    http_put_response_hop_limit = 2          # Lets Docker containers reach the instance role
  }

  root_block_device {
    volume_size = var.disk_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "outreach-server" }

  lifecycle {
    # A newer Amazon Linux image or an edited bootstrap script should not replace a running server
    ignore_changes = [ami, user_data]
  }
}

# A public IP that stays the same when the server is stopped and started
resource "aws_eip" "server" {
  instance = aws_instance.server.id
  domain   = "vpc"
}

# ---------------------------------------------------------------- Settings (not secret)

resource "aws_ssm_parameter" "settings" {
  for_each = {
    S3_BUCKET    = aws_s3_bucket.data.bucket
    AWS_REGION   = var.region
    DBT_TARGET   = "aws"
    SITE_ADDRESS = var.site_address
  }
  name  = "/outreach/${each.key}"
  type  = "String"
  value = each.value
}
