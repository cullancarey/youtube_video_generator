data "aws_caller_identity" "current" {}

locals {
  youtube_lambda       = "youtube_video_generator"
  s3_bucket_for_lambda = "youtube-uploader-bucket"
  account_id           = data.aws_caller_identity.current.account_id
}
