provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0.0, < 7.0"
    }
  }

  backend "s3" {
  }
}
