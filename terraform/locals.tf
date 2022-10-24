data "aws_caller_identity" "current" {}

locals {
  youtube_lambda       = "youtube_video_generator"
  tweet_video_lambda   = "tweet_youtube_video"
  s3_bucket_for_lambda = "youtube-uploader-bucket"
  account_id           = data.aws_caller_identity.current.account_id
}