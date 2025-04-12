#############################################
######### YOUTUBE UPLOADER BUCKET ###########
#############################################


resource "aws_s3_bucket" "youtube_uploader_bucket" {
  bucket = "youtube-uploader-bucket"
  tags = {
    "Name" = "youtube-uploader-bucket"
  }
}


resource "aws_s3_bucket_policy" "allow_access_from_lambda_user" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id
  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambda",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::045107234435:role/service-role/youtube_video_generator-role"
            },
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": ["arn:aws:s3:::youtube-uploader-bucket/*", "arn:aws:s3:::youtube-uploader-bucket"]
        }
    ]
}
POLICY
}



resource "aws_s3_bucket_public_access_block" "youtube_uploader_bucket_access_block" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket_versioning" "youtube_uploader_bucket_versioning" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}


resource "aws_s3_bucket_lifecycle_configuration" "youtube_uploader_bucket_lifecycle_config" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id

  rule {
    id     = "ExpireAllAfter2Month"
    status = "Enabled"

    filter {
      prefix = "" # Explicitly apply to all objects
    }

    noncurrent_version_expiration {
      noncurrent_days = 60
    }
  }
}
