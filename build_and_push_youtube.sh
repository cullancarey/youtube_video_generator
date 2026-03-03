#!/bin/bash
set -e

REPO="youtube-lambda-repo"
IMAGE_TAG="${GITHUB_SHA:0:7}"  # Use first 7 chars of commit SHA
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-east-2}"  # Use AWS_REGION env var or default
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

docker build -t $REPO -f lambdas/youtube/Dockerfile .
docker tag $REPO:latest $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$IMAGE_TAG

# Output the image tag for GitHub Actions
echo "image-tag=$IMAGE_TAG" >> $GITHUB_OUTPUT