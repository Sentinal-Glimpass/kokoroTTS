#!/bin/bash
set -e

echo "Entrypoint script started. Attempting to initialize CUDA MPS."

# Common paths for nvidia-cuda-mps-control
MPS_CONTROL_PATHS=(
    "/usr/bin/nvidia-cuda-mps-control"
    "/usr/local/cuda/bin/nvidia-cuda-mps-control"
    "/usr/local/cuda-12.1/bin/nvidia-cuda-mps-control" # Specific to CUDA 12.1
    "/opt/nvidia/cuda/bin/nvidia-cuda-mps-control"
)

MPS_CONTROL_EXECUTABLE=""

for path_attempt in "${MPS_CONTROL_PATHS[@]}"; do
    echo "Checking for MPS control at: ${path_attempt}"
    if [ -x "${path_attempt}" ]; then
        MPS_CONTROL_EXECUTABLE="${path_attempt}"
        echo "Found MPS control executable at: ${MPS_CONTROL_EXECUTABLE}"
        break
    else
        echo "MPS control not found or not executable at: ${path_attempt}"
    fi
done

if [ -z "${MPS_CONTROL_EXECUTABLE}" ]; then
    echo "CRITICAL: nvidia-cuda-mps-control executable not found in any common paths. MPS cannot be started."
    echo "Please verify CUDA toolkit installation in the base image."
    # exit 1 # Optionally exit if MPS is absolutely critical
else
    echo "Attempting to start NVIDIA CUDA MPS control daemon using: ${MPS_CONTROL_EXECUTABLE}"
    if ${MPS_CONTROL_EXECUTABLE} -d; then
        echo "NVIDIA CUDA MPS control daemon command executed."
        # Give it a moment to start
        sleep 2
        if pgrep nvidia-cuda-mps-control > /dev/null; then
            echo "NVIDIA CUDA MPS control daemon process is running."
        else
            echo "WARNING: NVIDIA CUDA MPS control daemon process NOT found after attempting to start."
        fi
    else
        echo "ERROR: Executing '${MPS_CONTROL_EXECUTABLE} -d' FAILED."
        # exit 1 # Optionally exit
    fi
fi

echo "Proceeding to execute CMD: $@"
exec "$@"
