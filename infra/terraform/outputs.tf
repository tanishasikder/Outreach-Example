output "region" {
  value = var.region
}

output "url" {
  description = "The website"
  value       = "http://${aws_eip.server.public_ip}"
}

output "public_ip" {
  description = "Point your domain's DNS A record here"
  value       = aws_eip.server.public_ip
}

output "bucket_name" {
  value = aws_s3_bucket.data.bucket
}

output "instance_id" {
  value = aws_instance.server.id
}

output "shell_command" {
  description = "Open a terminal on the server (needs the AWS Session Manager plugin)"
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.server.id}"
}

output "airflow_tunnel_command" {
  description = "Then open http://localhost:8080"
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.server.id} --document-name AWS-StartPortForwardingSession --parameters portNumber=8080,localPortNumber=8080"
}
