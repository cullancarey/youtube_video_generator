#############################################
######### TWEET VIDEO LAMBDA ##########
#############################################


# resource "null_resource" "create_tweet_youtube_video_lambda_package" {
#   provisioner "local-exec" {
#     command = "../create_tweet_lambda_package.sh"
#   }
# }

data "aws_ecr_image" "tweet_lambda" {
  repository_name = aws_ecr_repository.tweet_lambda.name
  image_tag       = "latest"
}

resource "aws_lambda_function" "tweet_youtube_video_lambda" {
  function_name = local.tweet_video_lambda
  description   = "Lambda function for tweeting a youtube video"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.tweet_lambda.repository_url}@${data.aws_ecr_image.tweet_lambda.image_digest}"
  role          = aws_iam_role.iam_for_tweet_youtube_video_lambda.arn
  timeout       = 30
  memory_size   = 512
}

resource "aws_iam_role" "iam_for_tweet_youtube_video_lambda" {
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

resource "aws_iam_policy" "tweet_youtube_video_lambda_iam_policy" {
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
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": "arn:aws:s3:::youtube-uploader-bucket/*"
        }
    ]
}

POLICY
}

resource "aws_iam_role_policy_attachment" "tweet_youtube_video_lambda_attach" {
  role       = aws_iam_role.iam_for_tweet_youtube_video_lambda.name
  policy_arn = aws_iam_policy.tweet_youtube_video_lambda_iam_policy.arn
}
