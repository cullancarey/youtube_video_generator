FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY lambdas/tweet/tweet_lambda_requirements.txt .
RUN pip install --no-cache-dir -r tweet_lambda_requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy the function code
COPY lambdas/tweet/ ${LAMBDA_TASK_ROOT}

# Set the handler
CMD ["tweet_youtube_video.lambda_handler"]