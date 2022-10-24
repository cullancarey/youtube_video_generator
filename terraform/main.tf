provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = {
      Project = "youtube_video_generator"
    }
  }
}

terraform {
  backend "s3" {
  }
}