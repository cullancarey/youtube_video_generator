#############################################
####### YOUTUBE LAMBDA CW TRIGGER ###########
#############################################


resource "aws_cloudwatch_event_rule" "youtube_video_generator_lambda_rule" {
  name                = local.youtube_trigger_name
  schedule_expression = var.youtube_schedule_expression
}

resource "aws_cloudwatch_event_target" "invoke_youtube_video_generator_lambda" {
  rule      = aws_cloudwatch_event_rule.youtube_video_generator_lambda_rule.name
  target_id = local.youtube_target_id
  arn       = aws_lambda_function.youtube_video_generator_lambda.arn
}

resource "aws_lambda_permission" "youtube_video_generator_lambda_allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.youtube_video_generator_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.youtube_video_generator_lambda_rule.arn
}

resource "aws_sns_topic" "youtube_lambda_alerts" {
  name = local.youtube_alert_topic_name
}

resource "aws_sns_topic_subscription" "youtube_lambda_alerts_email" {
  topic_arn = aws_sns_topic.youtube_lambda_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "youtube_lambda_errors" {
  alarm_name          = local.youtube_error_alarm_name
  alarm_description   = "Alerts when the YouTube Lambda invocation fails"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.youtube_video_generator_lambda.function_name
  }

  alarm_actions = [aws_sns_topic.youtube_lambda_alerts.arn]
}
