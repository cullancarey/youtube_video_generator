#!/bin/bash
set -e

REPO="tweet-lambda-repo"
IMAGE_TAG="latest"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-2" # or your region
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO"

# Authenticate to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Build and push
docker build -t $REPO -f lambdas/tweet/Dockerfile .
docker tag $REPO:latest $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$IMAGE_TAG