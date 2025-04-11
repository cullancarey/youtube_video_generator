#!/bin/bash
set -e
# This script creates a deployment package for the AWS Lambda function
# that uploads videos to YouTube. It includes the necessary dependencies
# and the main script. The package is zipped and ready for deployment.

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir -p package

echo "Copying main script to package directory"
cp ./lambdas/youtube_video_generator.py package/

echo "Copying upload script to package directory"
cp ./lambdas/upload_video.py package/

echo "Copying ffmpeg to package directory"
cp ./ffmpeg package/

echo "Installing requirements"
python -m pip install --target ./package/ -r ./youtube_lambda_requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -rq youtube_video_generator.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/youtube_video_generator.zip .
echo $PWD

echo "Removing package directory"
rm -rf package/