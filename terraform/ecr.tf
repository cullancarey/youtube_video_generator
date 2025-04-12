resource "aws_ecr_repository" "tweet_lambda" {
  name                 = "tweet-lambda-repo"
  image_tag_mutability = "MUTABLE"

  tags = {
    Name        = "Tweet Lambda ECR"
    Environment = "production"
  }
}

resource "aws_ecr_lifecycle_policy" "tweet_lambda" {
  repository = aws_ecr_repository.tweet_lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain only last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}


resource "aws_ecr_repository" "youtube_lambda" {
  name                 = "youtube-lambda-repo"
  image_tag_mutability = "MUTABLE"

  tags = {
    Name        = "YouTube Lambda ECR"
    Environment = "production"
  }
}

resource "aws_ecr_lifecycle_policy" "youtube_lambda" {
  repository = aws_ecr_repository.youtube_lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain only last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
