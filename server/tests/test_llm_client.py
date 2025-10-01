#!/usr/bin/env python3
"""
Test OpenAI client initialization
"""
import sys
import os

# Add server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.llm_factory import LLMFactory

def test_llm_clients():
    """Test LLM client initialization"""
    print("Testing LLM clients...")
    
    try:
        # Test getting available providers
        providers = LLMFactory.get_available_providers()
        print(f"Available providers: {providers}")
        
        # Test getting Google client
        if "google" in providers:
            client = LLMFactory.get_client("google")
            print(f"Google client: {client}")
            print(f"Google available: {client.is_available()}")
        else:
            print("Google client not available")
            
        # Test getting OpenAI client
        if "openai" in providers:
            client = LLMFactory.get_client("openai")
            print(f"OpenAI client: {client}")
            print(f"OpenAI available: {client.is_available()}")
        else:
            print("OpenAI client not available")
            
    except Exception as e:
        print(f"Error testing LLM clients: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_clients()