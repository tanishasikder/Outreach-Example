variable "region" {
  description = "AWS region for everything"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  # t3.large = 2 vCPU, 8 GB RAM, about $60/month if left running.
  # Airflow + the app need roughly 4-5 GB; t3.medium (4 GB) works but is tight.
  description = "EC2 size"
  type        = string
  default     = "t3.large"
}

variable "disk_gb" {
  description = "Server disk size (Docker images take ~10 GB)"
  type        = number
  default     = 30
}

variable "repo_url" {
  description = "Git repository the server clones and pulls"
  type        = string
  default     = "https://github.com/tanishasikder/Outreach-Example.git"
}

variable "branch" {
  description = "Branch the server deploys"
  type        = string
  default     = "main"
}

variable "site_address" {
  # ":80" serves plain HTTP on the server's IP. Set a domain (e.g. "deals.example.com")
  # after pointing its DNS A record at the server's IP, and Caddy turns on HTTPS by itself.
  description = "Address Caddy serves the site on"
  type        = string
  default     = ":80"
}
