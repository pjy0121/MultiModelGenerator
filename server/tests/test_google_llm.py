#!/usr/bin/env python3
"""
Test Google LLM client functionality using pytest
"""
import pytest
import asyncio
import sys
import os

# Add server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.llm_factory import LLMFactory

class TestGoogleLLMClient:
    """Google LLM 클라이언트 테스트"""
    
    def test_google_client_availability(self):
        """Google 클라이언트 사용 가능 여부 테스트"""
        try:
            # Test getting available providers with instance-based factory
            llm_factory = LLMFactory()
            providers = llm_factory.get_available_providers()
            print(f"Available providers: {providers}")
            
            assert "google" in providers, "Google provider should be available"
            
            client = llm_factory.get_client("google")
            assert client is not None, "Google client should not be None"
            assert client.is_available(), "Google client should be available"
            
            print("✅ Google client is available")
            
        except Exception as e:
            print(f"❌ Google client test failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @pytest.mark.asyncio
    async def test_google_simple_generation(self):
        """Google 모델 간단한 텍스트 생성 테스트"""
        try:
            llm_factory = LLMFactory()
            client = llm_factory.get_client("google")
            
            # 간단한 텍스트 생성 테스트 (스트리밍 사용)
            prompt = "Hello, how are you?"
            response = ""
            async for chunk in client.generate_stream(prompt, "gemini-2.0-flash"):
                response += chunk
            
            print(f"Google response: {response}")
            
            assert response is not None, "Response should not be None"
            assert len(response.strip()) > 0, "Response should not be empty"
            
            print("✅ Google simple generation test passed")
            
        except Exception as e:
            print(f"❌ Google generation test failed: {e}")
            import traceback
            traceback.print_exc()
            raise