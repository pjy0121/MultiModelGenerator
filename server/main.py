#!/usr/bin/env python3
"""
MultiModelGenerator Server
Main entry point for the server application
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.api_server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
        reload=False  # Windows multiprocessing 문제 방지
    )
