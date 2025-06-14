# kokoroTTS

kokoroTTS is a high-performance Text-to-Speech (TTS) service built with Python, using the `kokoro` library. It is designed for scalability and efficient GPU utilization, particularly for deployment on GKE with T4 GPU instances.

The service manages a pool of `KPipeline` objects to handle concurrent TTS requests, dynamically scaling the pool to ensure low latency and high throughput.

## Features

-   **High-Quality TTS**: Leverages the `kokoro` library for speech synthesis.
-   **Scalable Architecture**: Dynamically manages a pool of TTS pipelines.
-   **GPU Optimized**: Designed for efficient use of GPU resources.
-   **FastAPI Interface**: Exposes a simple REST API for TTS requests.

## Project Structure

```
kokoroTTS/
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── pipeline_manager.py
│   └── tts_service.py
└── scripts/ (optional, for utility scripts)
```

## Prerequisites

-   Python 3.8+
-   `espeak-ng` (system dependency)
    ```bash
    sudo apt-get update && sudo apt-get install -y espeak-ng
    ```

## Setup and Installation

1.  **Clone the repository (once created on GitHub):**
    ```bash
    git clone <repository-url>
    cd kokoroTTS
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install system dependencies:**
    Make sure `espeak-ng` is installed. The command might vary based on your OS. For Debian/Ubuntu:
    ```bash
    sudo apt-get update && sudo apt-get install -y espeak-ng
    ```

4.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Configuration parameters such as language code, initial pipeline pool size, and minimum spare pipelines are managed in `src/config.py`.

## Running the Service

To run the FastAPI application locally:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
The `--reload` flag is for development and automatically reloads the server on code changes.

## API Usage

### Synthesize Speech

-   **Endpoint**: `/synthesize`
-   **Method**: `POST`
-   **Request Body** (JSON):
    ```json
    {
        "text": "Your text to synthesize.",
        "voice": "hf_beta" // Optional, defaults to a pre-configured voice
    }
    ```
-   **Success Response** (`200 OK`):
    -   **Content-Type**: `audio/wav`
    -   The response body will be the raw WAV audio data.
-   **Error Response** (e.g., `400 Bad Request`, `500 Internal Server Error`):
    -   **Content-Type**: `application/json`
    ```json
    {
        "detail": "Error message"
    }
    ```

## Deployment (GKE with T4 GPU)

Detailed instructions for deploying to GKE will be added here. This will involve:
-   Building the Docker image.
-   Pushing the image to a container registry (e.g., Google Container Registry - GCR).
-   Configuring GKE deployments and services, ensuring GPU node pools are used.

## TODO

-   Implement `pipeline_manager.py`
-   Implement `tts_service.py`
-   Implement `main.py` (FastAPI app)
-   Create `Dockerfile`
-   Add detailed GKE deployment steps.
