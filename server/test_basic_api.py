#!/usr/bin/env python3
"""
Simple test to verify API endpoints are working
"""
import asyncio
import aiohttp
import json

async def test_simple_endpoints():
    """Test basic API endpoints"""
    base_url = "http://localhost:5001"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test health endpoint
            print("Testing health endpoint...")
            async with session.get(f"{base_url}/health") as response:
                print(f"Health status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"Health response: {result}")
            
            # Test models endpoint  
            print("\nTesting models endpoint...")
            async with session.get(f"{base_url}/models") as response:
                print(f"Models status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"Models count: {len(result)}")
                else:
                    text = await response.text()
                    print(f"Models error: {text}")
            
            # Test knowledge bases
            print("\nTesting knowledge bases endpoint...")
            async with session.get(f"{base_url}/knowledge-bases") as response:
                print(f"KB status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"Knowledge bases count: {len(result)}")
                else:
                    text = await response.text()
                    print(f"KB error: {text}")
                    
        except Exception as e:
            print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_endpoints())