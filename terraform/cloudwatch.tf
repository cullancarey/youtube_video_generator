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
