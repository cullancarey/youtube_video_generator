variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  default     = "us-east-2"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS region format, e.g. us-east-2."
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production."
  }
}

variable "project_name" {
  description = "Project name used for tagging and naming"
  type        = string
  default     = "youtube_video_generator"

  validation {
    condition     = can(regex("^[a-z0-9_-]{3,64}$", var.project_name))
    error_message = "project_name must be 3-64 chars and contain only lowercase letters, numbers, underscores, or hyphens."
  }
}

variable "youtube_lambda_name" {
  description = "YouTube Lambda function name"
  type        = string
  default     = "youtube_video_generator"

  validation {
    condition     = can(regex("^[a-zA-Z0-9-_]{1,64}$", var.youtube_lambda_name))
    error_message = "youtube_lambda_name must be 1-64 chars and contain only letters, numbers, hyphens, or underscores."
  }
}

variable "youtube_bucket_name" {
  description = "S3 bucket used by YouTube Lambda"
  type        = string
  default     = "youtube-uploader-bucket"

  validation {
    condition = can(
      regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.youtube_bucket_name)
    )
    error_message = "youtube_bucket_name must be a valid S3 bucket name."
  }
}

variable "youtube_ecr_repo_name" {
  description = "ECR repository name for YouTube Lambda"
  type        = string
  default     = "youtube-lambda-repo"

  validation {
    condition     = can(regex("^[a-z0-9]+(?:[._/-][a-z0-9]+)*$", var.youtube_ecr_repo_name))
    error_message = "youtube_ecr_repo_name must be a valid ECR repository name."
  }
}

variable "youtube_schedule_expression" {
  description = "EventBridge schedule for YouTube Lambda"
  type        = string
  default     = "cron(0 14 ? * * *)"

  validation {
    condition = startswith(var.youtube_schedule_expression, "cron(") || startswith(
      var.youtube_schedule_expression,
      "rate(",
    )
    error_message = "youtube_schedule_expression must start with cron( or rate(."
  }
}

variable "lambda_log_retention_days" {
  description = "CloudWatch log retention period for Lambda logs"
  type        = number
  default     = 30

  validation {
    condition = contains(
      [
        1,
        3,
        5,
        7,
        14,
        30,
        60,
        90,
        120,
        150,
        180,
        365,
        400,
        545,
        731,
        1096,
        1827,
        2192,
        2557,
        2922,
        3288,
        3653,
      ],
      var.lambda_log_retention_days,
    )
    error_message = "lambda_log_retention_days must be one of the AWS-supported retention values."
  }
}

variable "youtube_image_tag" {
  description = "Docker image tag for YouTube Lambda"
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]{1,128}$", var.youtube_image_tag))
    error_message = "youtube_image_tag must be 1-128 chars and contain only letters, numbers, dots, underscores, or hyphens."
  }
}

variable "alert_email" {
  description = "Email address to receive Lambda failure alerts via SNS"
  type        = string
  default     = "cullancarey@gmail.com"

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}
