"""
Pytest configuration and fixtures
"""
import pytest
import requests
import os
import time
from typing import Generator


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """API base URL fixture"""
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "5001")
    return f"http://{api_host}:{api_port}"


@pytest.fixture(scope="session")
def api_client(api_base_url: str) -> Generator[requests.Session, None, None]:
    """HTTP client fixture with server health check"""
    session = requests.Session()
    session.timeout = 30
    
    # Wait for server to be ready
    max_retries = 10
    for i in range(max_retries):
        try:
            response = session.get(f"{api_base_url}/")
            if response.status_code == 200:
                print(f"✅ Server is ready at {api_base_url}")
                break
        except requests.exceptions.ConnectionError:
            if i == max_retries - 1:
                pytest.skip(f"❌ Server not available at {api_base_url}")
            time.sleep(1)
    
    yield session
    session.close()


@pytest.fixture
def sample_workflow():
    """Sample workflow fixture"""
    return {
        "nodes": [
            {
                "id": "input_1",
                "type": "input-node",
                "position": {"x": 100, "y": 100},
                "content": "Test input content"
            },
            {
                "id": "gen_1", 
                "type": "generation-node",
                "position": {"x": 300, "y": 100},
                "model_type": "gemini-1.5-flash",
                "llm_provider": "google",
                "prompt": "Process this: {input_data}"
            },
            {
                "id": "output_1",
                "type": "output-node", 
                "position": {"x": 500, "y": 100}
            }
        ],
        "edges": [
            {
                "id": "e1",
                "source": "input_1",
                "target": "gen_1"
            },
            {
                "id": "e2", 
                "source": "gen_1",
                "target": "output_1"
            }
        ]
    }