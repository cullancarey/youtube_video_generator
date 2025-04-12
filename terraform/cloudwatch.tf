#############################################
###### TWEET VIDEO LAMBDA CW TRIGGER ########
#############################################

resource "aws_cloudwatch_event_rule" "tweet_youtube_video_lambda_rule" {
  name                = "${local.tweet_video_lambda}_trigger"
  schedule_expression = "cron(10 5,9,13,17,21,1 ? * * *)"
}

resource "aws_cloudwatch_event_target" "invoke_tweet_youtube_video_lambda" {
  rule      = aws_cloudwatch_event_rule.tweet_youtube_video_lambda_rule.name
  target_id = "trigger_tweet_youtube_video_lambda"
  arn       = aws_lambda_function.tweet_youtube_video_lambda.arn
}

resource "aws_lambda_permission" "tweet_youtube_video_lambda_allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tweet_youtube_video_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.tweet_youtube_video_lambda_rule.arn
}


#############################################
####### YOUTUBE LAMBDA CW TRIGGER ###########
#############################################


resource "aws_cloudwatch_event_rule" "youtube_video_generator_lambda_rule" {
  name                = "${local.youtube_lambda}_trigger"
  schedule_expression = "cron(0 14 ? * * *)"
}

resource "aws_cloudwatch_event_target" "invoke_youtube_video_generator_lambda" {
  rule      = aws_cloudwatch_event_rule.youtube_video_generator_lambda_rule.name
  target_id = "trigger_youtube_video_generator_lambda"
  arn       = aws_lambda_function.youtube_video_generator_lambda.arn
}

resource "aws_lambda_permission" "youtube_video_generator_lambda_allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.youtube_video_generator_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.youtube_video_generator_lambda_rule.arn
}
