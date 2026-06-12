#############################################
######### YOUTUBE UPLOADER BUCKET ###########
#############################################


resource "aws_s3_bucket" "youtube_uploader_bucket" {
  bucket = local.s3_bucket_for_lambda
  tags = {
    Name = local.s3_bucket_for_lambda
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "youtube_uploader_bucket_sse" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "youtube_uploader_bucket_ownership" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

data "aws_iam_policy_document" "youtube_uploader_bucket_policy" {
  statement {
    sid    = "AllowLambdaListBucket"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.iam_for_youtube_video_generator_lambda.arn]
    }

    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.youtube_uploader_bucket.arn,
    ]
  }

  statement {
    sid    = "AllowLambdaGetObject"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.iam_for_youtube_video_generator_lambda.arn]
    }

    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.youtube_uploader_bucket.arn}/*",
    ]
  }
}


resource "aws_s3_bucket_policy" "allow_access_from_lambda_user" {
  bucket = aws_s3_bucket.youtube_uploader_bucket.id
  policy = data.aws_iam_policy_document.youtube_uploader_bucket_policy.json
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
