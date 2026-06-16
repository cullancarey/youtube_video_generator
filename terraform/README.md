# Terraform Infrastructure

This directory defines AWS infrastructure for the YouTube generator Lambda.

## Managed Resources

- ECR repository and lifecycle policy for the YouTube Lambda image.
- Lambda function configured as container-image package type.
- IAM role and policy for logs, SSM parameter reads, and S3 access.
- EventBridge schedule and invoke permission.
- S3 bucket and lifecycle/versioning configuration for OAuth and runtime support files.

## Key Files

- main.tf: provider and backend block.
- backend.main.conf: production backend config values.
- ecr.tf: ECR repository and lifecycle rule.
- youtube_video_generator_lambda.tf: YouTube Lambda and IAM policy.
- cloudwatch.tf: schedule and permission.
- s3.tf: bucket, policy, public access block, lifecycle.
- variables.tf: validated input variables for region, naming, schedule, retention, and image tag.
- locals.tf: normalized naming and shared tagging conventions.
- outputs.tf: key resource identifiers for integrations and automation.

## Apply Strategy In CI

Workflow .github/workflows/deploy-docker.yml runs:

1. terraform init with backend.$GITHUB_REF_NAME.conf
2. terraform fmt -check
3. terraform validate
4. terraform plan with image tag from build job
5. terraform apply only if commit message includes [tf-apply]

## Local Commands

From the terraform directory:

```bash
terraform init -backend-config=backend.main.conf
terraform fmt -check
terraform validate
terraform plan \
	-var="youtube_image_tag=<tag>" \
	-var="environment=production" \
	-var="aws_region=us-east-2" \
	-out=tfplan
terraform apply tfplan
```

## Variables

- youtube_image_tag (required): Docker tag to deploy.
- environment: one of dev, staging, production.
- aws_region: AWS region in standard format (for example us-east-2).
- project_name: normalized for tagging and naming consistency.
- youtube_lambda_name, youtube_bucket_name, youtube_ecr_repo_name: resource naming inputs.
- youtube_schedule_expression: must start with cron( or rate(.
- lambda_log_retention_days: must be an AWS-supported retention value.

## Outputs

- youtube_lambda_name
- youtube_lambda_arn
- youtube_lambda_role_arn
- youtube_lambda_log_group_name
- youtube_ecr_repository_name
- youtube_ecr_repository_url
- youtube_bucket_name
- youtube_event_rule_arn

## Notes

- Provider region defaults to us-east-2 and can be overridden via var.aws_region.
- Naming normalization and common tags are defined in locals.tf.
- If new SSM parameters are introduced in code, IAM policy resources must be updated.
- The CloudWatch log group has `skip_destroy = true` to prevent accidental deletion on terraform destroy. If the log group already exists in AWS, Terraform will adopt it without recreating; use `terraform import aws_cloudwatch_log_group.youtube_video_generator_lambda /aws/lambda/youtube_video_generator` to bring pre-existing log groups under management.
