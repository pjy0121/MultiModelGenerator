"""API keys and LLM provider configurations."""

import os
from dotenv import load_dotenv

load_dotenv()

API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY"),
    "internal": os.getenv("INTERNAL_API_KEY")
}

INTERNAL_LLM_CONFIG = {
    "api_endpoint": os.getenv("INTERNAL_API_ENDPOINT"),
    "api_key": os.getenv("INTERNAL_API_KEY"),
    "model_name": os.getenv("INTERNAL_MODEL_NAME"),
    "timeout": 30
}

LLM_CONFIG = {
    "supported_providers": ["openai", "google", "internal"],
    "default_provider": "google", 
    "default_model": "gemini-2.0-flash",
    "default_temperature": 0.1,
    "chunk_processing_size": 10,
    "simulation_sleep_interval": 0.1
}
