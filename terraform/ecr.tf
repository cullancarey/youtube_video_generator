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
        description  = "Retain only last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
