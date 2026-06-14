# AWS Deployment Notes

This repository is ready to run on AWS with an RDS Postgres backend.

Recommended production layout:

1. Store `OPENAI_API_KEY` and `DATABASE_URL` in AWS Secrets Manager.
2. Run Postgres in Amazon RDS with encryption at rest, TLS, private subnets, and automated backups.
3. Deploy the Docker image to ECS Fargate behind an Application Load Balancer.
4. Configure AWS WAF, access logs, CloudWatch metrics, and health checks on `/health`.
5. Use IAM task roles with least privilege. The app does not need broad AWS permissions unless you add S3 or Bedrock integrations.
6. Restrict CORS to the Streamlit or frontend domain.

The application never writes conversation memory to RDS. Only catalog, review, and policy CSV data are imported.
