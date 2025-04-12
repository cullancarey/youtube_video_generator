#!/bin/bash
set -e

REPO="youtube-lambda-repo"
IMAGE_TAG="latest"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-2"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

docker build -t $REPO -f lambdas/youtube/Dockerfile .
docker tag $REPO:latest $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$IMAGE_TAG