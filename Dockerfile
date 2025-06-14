# Dockerfile for kokoroTTS service

# 1. Base Image
# Using a Python 3.10 slim image as a base. 
# For GPU support with PyTorch, a specific CUDA-enabled base image might be needed
# (e.g., nvidia/cuda:X.Y-cudnnA-runtime-ubuntuZ.W or a PyTorch official image).
# However, kokoro might rely on torch to handle this. Start with a general image.
FROM python:3.10-slim

# 2. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
ENV PORT=8000
ENV DEFAULT_LANG_CODE=hi # Can be overridden at runtime

# 3. System Dependencies
# Install espeak-ng and other common utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    # Add any other system dependencies here, e.g., build-essential for some packages
    # libsndfile1 for soundfile, though often handled by wheels
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Set Working Directory
WORKDIR ${APP_HOME}

# 5. Install Python Dependencies
# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Application Code
COPY ./src ./src

# 7. Expose Port
EXPOSE ${PORT}

# 8. Healthcheck (Optional but good practice for GKE/Kubernetes)
# This checks if the /health endpoint is responsive.
# Adjust interval, timeout, retries as needed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# 9. Command to Run Application
# Use uvicorn to run the FastAPI application.
# The host 0.0.0.0 makes it accessible from outside the container.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
