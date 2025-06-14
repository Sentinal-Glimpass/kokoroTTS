# Dockerfile for kokoroTTS service

# 1. Base Image
# Using NVIDIA CUDA base image for T4 GPU compatibility on Google Cloud Run.
# This image includes CUDA 12.1.1 and cuDNN 8, suitable for recent PyTorch versions.
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# 2. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
ENV PORT=8000
ENV DEFAULT_LANG_CODE=h 

# 3. System Dependencies
# Install Python 3.10, pip, venv, and other necessary tools.
# Also install espeak-ng and libsndfile1.
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    # Add deadsnakes PPA for newer Python versions if needed, though Ubuntu 22.04 might have 3.10
    # Forcing Python 3.10 installation
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    # System dependencies for the application
    espeak-ng \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update alternatives to make python3.10 the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
# Ensure pip is for python3.10
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# 4. Set Working Directory
WORKDIR ${APP_HOME}

# 5. Install Python Dependencies
# Copy requirements first to leverage Docker cache
COPY requirements.txt .
# It's generally recommended to install torch separately with a specific CUDA version if issues arise,
# but pip should pick up the CUDA version from the environment.
# Example for specific torch version: RUN python3 -m pip install torch==2.1.0+cu121 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN python3 -m pip install --no-cache-dir -r requirements.txt

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
CMD ["gunicorn", "src.main:app", "--workers", "20", "--worker-class", "uvicorn.workers.UvicornWorker", "--worker-connections", "1", "--bind", "0.0.0.0:8000", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
