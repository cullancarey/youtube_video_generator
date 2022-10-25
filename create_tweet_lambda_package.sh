#!/bin/bash

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir package

echo "Copying python script to package directory"
cp ./lambdas/tweet_video.py package/

echo "Installing requirements"
pip install --target ./package/ -r ./tweet_lambda_requirements.txt

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

# echo "Uploading zip file to S3..."
# aws s3 cp tweet_youtube_video.zip s3://youtube-uploader-bucket/

# echo "Updating lambda function...!"
# aws lambda update-function-code \
#     --function-name  tweet_video \
#     --zip-file fileb://lambda_function.zip