#############################################
######### YOUTUBE LAMBDA ##########
#############################################

data "aws_ecr_image" "youtube_lambda" {
  repository_name = aws_ecr_repository.youtube_lambda.name
  image_tag       = var.youtube_image_tag
}


resource "aws_lambda_function" "youtube_video_generator_lambda" {
  function_name = local.youtube_lambda
  role          = aws_iam_role.iam_for_youtube_video_generator_lambda.arn
  description   = "Lambda function for creating and uploading a youtube video to my channel"

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.youtube_lambda.repository_url}@${data.aws_ecr_image.youtube_lambda.image_digest}"

  timeout     = 900
  memory_size = 512
}

resource "aws_cloudwatch_log_group" "youtube_video_generator_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.youtube_video_generator_lambda.function_name}"
  retention_in_days = var.lambda_log_retention_days
  skip_destroy      = true
}

resource "aws_iam_role" "iam_for_youtube_video_generator_lambda" {
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

data "aws_iam_policy_document" "youtube_video_generator_lambda" {
  statement {
    sid    = "AllowGetParameter"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${local.account_id}:parameter/reddit_client_secret",
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${local.account_id}:parameter/reddit_username",
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${local.account_id}:parameter/reddit_password",
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${local.account_id}:parameter/reddit_user_agent",
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${local.account_id}:parameter/reddit_client_id",
    ]
  }

  statement {
    sid    = "AllowCloudwatch"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.youtube_video_generator_lambda.arn}:*",
    ]
  }

  statement {
    sid    = "AllowCloudwatchCreateGroup"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${local.account_id}:*",
    ]
  }

  statement {
    sid    = "AllowS3ListBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.youtube_uploader_bucket.arn,
    ]
  }

  statement {
    sid    = "AllowS3GetObject"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${aws_s3_bucket.youtube_uploader_bucket.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "youtube_video_generator_lambda_iam_policy" {
  path   = "/service-role/"
  policy = data.aws_iam_policy_document.youtube_video_generator_lambda.json
}

resource "aws_iam_role_policy_attachment" "youtube_video_generator_lambda_attach" {
  role       = aws_iam_role.iam_for_youtube_video_generator_lambda.name
  policy_arn = aws_iam_policy.youtube_video_generator_lambda_iam_policy.arn
}
