#!/bin/bash
set -e

# Start NVIDIA MPS control daemon in the background
# This allows multiple CUDA processes (e.g., Gunicorn workers) to share GPU resources more efficiently.
echo "Starting NVIDIA CUDA MPS control daemon..."
# The following command starts the MPS control daemon.
# It needs to be run with appropriate permissions, typically as root or a user in the docker group with GPU access.
nvidia-cuda-mps-control -d

# Check if MPS daemon started successfully (optional, basic check)
if pgrep nvidia-cuda-mps-control > /dev/null; then
    echo "NVIDIA CUDA MPS control daemon started successfully."
else
    echo "NVIDIA CUDA MPS control daemon FAILED to start. Proceeding without MPS..."
    # Depending on requirements, you might want to exit here if MPS is critical
    # exit 1 
fi

# Execute the CMD passed to the entrypoint (your Gunicorn command)
echo "Executing command: $@"
exec "$@"
