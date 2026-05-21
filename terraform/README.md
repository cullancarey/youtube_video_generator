# Terraform Infrastructure

This directory defines AWS infrastructure for the YouTube generator and tweet bot Lambdas.

## Managed Resources

- ECR repositories and lifecycle policies for both Lambda images.
- Lambda functions configured as container-image package type.
- IAM roles and policies for logs, SSM parameter reads, and S3 access.
- EventBridge schedules and invoke permissions.
- S3 bucket and lifecycle/versioning configuration for OAuth and runtime support files.

## Key Files

- main.tf: provider and backend block.
- backend.main.conf: production backend config values.
- ecr.tf: ECR repositories and lifecycle rules.
- youtube_video_generator_lambda.tf: YouTube Lambda and IAM policy.
- tweet_youtube_video_lambda.tf: Tweet Lambda and IAM policy.
- cloudwatch.tf: schedules and permissions.
- s3.tf: bucket, policy, public access block, lifecycle.
- variables.tf: image tag variables used during plan/apply.

## Apply Strategy In CI

Workflow .github/workflows/deploy-docker.yml runs:

1. terraform init with backend.$GITHUB_REF_NAME.conf
2. terraform fmt -check
3. terraform validate
4. terraform plan with image tags from build jobs
5. terraform apply only if commit message includes [tf-apply]

## Local Commands

From the terraform directory:

```bash
terraform init -backend-config=backend.main.conf
terraform fmt -check
terraform validate
terraform plan -var="tweet_image_tag=<tag>" -var="youtube_image_tag=<tag>" -out=tfplan
terraform apply tfplan
```

## Notes

- Current provider region is set to us-east-2.
- Lambda names and common locals are defined in locals.tf.
- If new SSM parameters are introduced in code, IAM policy resources must be updated.
