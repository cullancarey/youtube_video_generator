data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  youtube_lambda          = var.youtube_lambda_name
  s3_bucket_for_lambda    = var.youtube_bucket_name
  account_id              = data.aws_caller_identity.current.account_id
  normalized_project_name = lower(replace(var.project_name, "_", "-"))
  youtube_trigger_name    = "${replace(local.youtube_lambda, "_", "-")}-trigger"
  youtube_target_id       = "trigger-${replace(local.youtube_lambda, "_", "-")}"
  common_tags = {
    Project     = local.normalized_project_name
    Environment = var.environment
    Terraform   = "true"
    ManagedBy   = "Terraform"
  }
}
