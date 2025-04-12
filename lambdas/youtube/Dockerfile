FROM public.ecr.aws/lambda/python:3.11

# Install Python dependencies into Lambda task root
COPY lambdas/youtube/youtube_lambda_requirements.txt .
RUN pip install --no-cache-dir -r youtube_lambda_requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY lambdas/youtube/ ${LAMBDA_TASK_ROOT}

# Copy ffmpeg binary into Lambda root
COPY ffmpeg ${LAMBDA_TASK_ROOT}

# Make sure ffmpeg is executable
RUN chmod +x ${LAMBDA_TASK_ROOT}/ffmpeg

# Set the handler
CMD ["youtube_video_generator.lambda_handler"]