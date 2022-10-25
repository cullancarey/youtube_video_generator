#############################################
######### YOUTUBE LAMBDA ##########
#############################################


resource "null_resource" "create_youtube_video_generator_package" {
  provisioner "local-exec" {
    command = "../create_youtube_lambda_package.sh"
  }
}


resource "aws_s3_object" "youtube_lambda_file" {
  bucket     = "youtube-uploader-bucket"
  key        = "${local.youtube_lambda}_lambda"
  source     = "${local.youtube_lambda}.zip"
  depends_on = [null_resource.create_youtube_video_generator_package]

}

resource "aws_iam_role" "iam_for_youtube_video_generator_lambda" {
  name = "${local.youtube_lambda}-role"
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

resource "aws_lambda_function" "youtube_video_generator_lambda" {
  s3_bucket     = local.s3_bucket_for_lambda
  s3_key        = aws_s3_object.youtube_lambda_file.id
  function_name = local.youtube_lambda
  role          = aws_iam_role.iam_for_youtube_video_generator_lambda.arn
  handler       = "${local.youtube_lambda}.lambda_handler"
  description   = "Lambda function for creating and uploading a youtube video to my channel"

  source_code_hash = aws_s3_object.youtube_lambda_file.id

  runtime = "python3.9"
  timeout = 300
}

resource "aws_iam_policy" "youtube_video_generator_lambda_iam_policy" {
  name   = "${local.youtube_lambda}-role-policy"
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
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/reddit_client_secret",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/reddit_username",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/reddit_password",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/reddit_user_agent",
                "arn:aws:ssm:us-east-2:${local.account_id}:parameter/reddit_client_id"
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
            "Resource": ["arn:aws:logs:us-east-2:${local.account_id}:log-group:/aws/lambda/${local.youtube_lambda}:*",
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

resource "aws_iam_role_policy_attachment" "youtube_video_generator_lambda_attach" {
  role       = aws_iam_role.iam_for_youtube_video_generator_lambda.name
  policy_arn = aws_iam_policy.youtube_video_generator_lambda_iam_policy.arn
}