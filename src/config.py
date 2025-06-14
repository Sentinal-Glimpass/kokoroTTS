# src/config.py

# TTS Engine Configuration
DEFAULT_LANG_CODE = "hi"  # Default language code for KPipeline, e.g., 'en', 'hi'
DEFAULT_VOICE = "hf_beta" # Default voice for synthesis

# Pipeline Pool Management
INITIAL_PIPELINE_POOL_SIZE = 20
MIN_SPARE_PIPELINES = 2
MAX_PIPELINE_POOL_SIZE = 50 # A sensible upper limit to prevent runaway scaling

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Other settings
LOG_LEVEL = "INFO" # Logging level for the application
