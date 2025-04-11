#!/bin/bash
set -e
# This script creates a deployment package for the AWS Lambda function
# that tweets YouTube videos. It includes the necessary dependencies
# and the main script. The package is zipped and ready for deployment.
# This script is specifically for the tweet_youtube_video.py script.

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir -p package

echo "Copying python script to package directory"
cp ./lambdas/tweet_youtube_video.py package/

echo "Installing requirements"
python -m pip install --target ./package/ -r ./tweet_lambda_requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -rq tweet_youtube_video.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/tweet_youtube_video.zip .
echo $PWD

echo "Removing package directory"
rm -rf package/