#!/bin/bash

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir package

echo "Copying main script to package directory"
cp lambdas/main.py package/

echo "Copying upload script to package directory"
cp lambdas/upload_video.py package/

echo "Copying ffmpeg to package directory"
cp ffmpeg package/

echo "Installing requirements"
pip install --target ./package/ -r youtube_lambda_requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -r youtube_video_generator.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/youtube_video_generator.zip .

echo "Removing package directory"
rm -rf package/

echo "Uploading zip file to S3..."
aws s3 cp youtube_video_generator.zip s3://youtube-uploader-bucket/

# echo "Updating lambda function...!"
# aws lambda update-function-code \
#     --function-name  youtube_video_uploader \
#     --s3-bucket youtube-uploader-bucket \
#     --s3-key lambda_function.zip