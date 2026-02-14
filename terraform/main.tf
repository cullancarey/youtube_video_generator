provider "aws" {
  region = "us-east-2"
  default_tags {
    tags = {
      Project   = "youtube_video_generator"
      Terraform = "true"
    }
  }
}

terraform {
  backend "s3" {
  }
}
