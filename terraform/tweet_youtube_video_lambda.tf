#############################################
######### TWEET VIDEO LAMBDA ##########
#############################################


# resource "null_resource" "create_tweet_youtube_video_lambda_package" {
#   provisioner "local-exec" {
#     command = "../create_tweet_lambda_package.sh"
#   }
# }


resource "aws_s3_object" "tweet_youtube_video_lambda_file" {
  bucket      = "youtube-uploader-bucket"
  key         = "${local.tweet_video_lambda}_lambda"
  source      = "tweet_lambda_build/${local.tweet_video_lambda}.zip"
  source_hash = filemd5("tweet_lambda_build/${local.tweet_video_lambda}.zip")
}

resource "aws_iam_role" "iam_for_tweet_youtube_video_lambda_lambda" {
  name = "${local.tweet_video_lambda}-role"
  path = "/service-role/"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

POLICY
}

resource "aws_lambda_function" "tweet_youtube_video_lambda_lambda" {
  s3_bucket     = local.s3_bucket_for_lambda
  s3_key        = aws_s3_object.tweet_youtube_video_lambda_file.id
  function_name = local.tweet_video_lambda
  role          = aws_iam_role.iam_for_tweet_youtube_video_lambda_lambda.arn
  handler       = "${local.tweet_video_lambda}.lambda_handler"
  description   = "Lambda function for tweeting about the youtube video on my channel"

  source_code_hash = aws_s3_object.tweet_youtube_video_lambda_file.id

  runtime = "python3.9"
  timeout = 300
}

resource "aws_iam_policy" "tweet_youtube_video_lambda_lambda_iam_policy" {
  name   = "${local.tweet_video_lambda}-role-policy"
  path   = "/service-role/"
  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowGetParameter",
            "Effect": "Allow",
            "Action": "ssm:GetParameter",
            "Resource": [
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/twitter_api_key",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/twitter_access_token",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/twitter_access_token_secret",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/twitter_api_key_secret"
            ]
        },
        {
            "Sid": "AllowCloudwatch",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:CreateLogGroup"
            ],
            "Resource": ["arn:aws:logs:us-east-2:${local.account_id}:log-group:/aws/lambda/${local.tweet_video_lambda}:*",
                "arn:aws:logs:us-east-2:${local.account_id}:*"]
        },
        {
            "Sid": "AllowS3",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::youtube-uploader-bucket/*"
        }
    ]
}

POLICY
}

resource "aws_iam_role_policy_attachment" "tweet_youtube_video_lambda_lambda_attach" {
  role       = aws_iam_role.iam_for_tweet_youtube_video_lambda_lambda.name
  policy_arn = aws_iam_policy.tweet_youtube_video_lambda_lambda_iam_policy.arn
}