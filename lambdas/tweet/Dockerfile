FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY tweet_lambda_requirements.txt .
RUN pip install -r tweet_lambda_requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy the function code
COPY lambdas/tweet/ ${LAMBDA_TASK_ROOT}

# Set the handler
CMD ["tweet_youtube_video.lambda_handler"]