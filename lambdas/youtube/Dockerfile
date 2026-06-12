FROM public.ecr.aws/lambda/python:3.13

# Install Python dependencies from uv metadata into Lambda task root
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
 && uv export --format requirements.txt --frozen --no-dev --no-emit-project --no-hashes --output-file /tmp/requirements.txt \
 && pip install --no-cache-dir -r /tmp/requirements.txt --target "${LAMBDA_TASK_ROOT}" \
 && rm -f /tmp/requirements.txt

# Copy function code
COPY lambdas/youtube/ ${LAMBDA_TASK_ROOT}

# Copy ffmpeg binary into Lambda root
COPY ffmpeg ${LAMBDA_TASK_ROOT}

# Make sure ffmpeg is executable
RUN chmod +x ${LAMBDA_TASK_ROOT}/ffmpeg

# Set the handler
CMD ["youtube_video_generator.lambda_handler"]