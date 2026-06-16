output "youtube_lambda_name" {
  description = "Name of the YouTube Lambda function"
  value       = aws_lambda_function.youtube_video_generator_lambda.function_name
}

output "youtube_lambda_arn" {
  description = "ARN of the YouTube Lambda function"
  value       = aws_lambda_function.youtube_video_generator_lambda.arn
}

output "youtube_lambda_role_arn" {
  description = "IAM role ARN used by the YouTube Lambda function"
  value       = aws_iam_role.iam_for_youtube_video_generator_lambda.arn
}

output "youtube_lambda_log_group_name" {
  description = "CloudWatch log group name for the YouTube Lambda function"
  value       = aws_cloudwatch_log_group.youtube_video_generator_lambda.name
}

output "youtube_ecr_repository_name" {
  description = "ECR repository name for the YouTube Lambda image"
  value       = aws_ecr_repository.youtube_lambda.name
}

output "youtube_ecr_repository_url" {
  description = "ECR repository URL for the YouTube Lambda image"
  value       = aws_ecr_repository.youtube_lambda.repository_url
}

output "youtube_bucket_name" {
  description = "S3 bucket name used by the YouTube Lambda function"
  value       = aws_s3_bucket.youtube_uploader_bucket.bucket
}

output "youtube_event_rule_arn" {
  description = "EventBridge rule ARN that triggers the YouTube Lambda"
  value       = aws_cloudwatch_event_rule.youtube_video_generator_lambda_rule.arn
}

output "youtube_alerts_topic_arn" {
  description = "SNS topic ARN used for YouTube Lambda failure alerts"
  value       = aws_sns_topic.youtube_lambda_alerts.arn
}

output "youtube_lambda_errors_alarm_name" {
  description = "CloudWatch alarm name for YouTube Lambda error notifications"
  value       = aws_cloudwatch_metric_alarm.youtube_lambda_errors.alarm_name
}
