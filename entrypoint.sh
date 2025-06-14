#!/bin/bash
set -e

# Add common CUDA binary paths to the PATH
export PATH=/usr/local/cuda/bin:/usr/local/cuda-12.1/bin:${PATH}

echo "Current PATH: ${PATH}"
echo "Searching for nvidia-cuda-mps-control..."
if command -v nvidia-cuda-mps-control &> /dev/null; then
    echo "Found nvidia-cuda-mps-control at: $(command -v nvidia-cuda-mps-control)"
else
    echo "nvidia-cuda-mps-control not found in PATH. Searching common locations..."
    find /usr/local -name nvidia-cuda-mps-control -print -quit || echo "nvidia-cuda-mps-control still not found after search."
fi

# Start NVIDIA MPS control daemon in the background
echo "Attempting to start NVIDIA CUDA MPS control daemon..."
if nvidia-cuda-mps-control -d; then
    echo "NVIDIA CUDA MPS control daemon command executed."
    # Check if MPS daemon started successfully (optional, basic check)
    if pgrep nvidia-cuda-mps-control > /dev/null; then
        echo "NVIDIA CUDA MPS control daemon process found."
    else
        echo "NVIDIA CUDA MPS control daemon process NOT found after attempting to start."
    fi
else
    echo "Executing 'nvidia-cuda-mps-control -d' FAILED."
    # Depending on requirements, you might want to exit here if MPS is critical
    # exit 1
fi

# Execute the CMD passed to the entrypoint (your Gunicorn command)
echo "Executing command: $@"
exec "$@"
