#!/usr/bin/env python3
"""
Simple workflow test to debug the generation node issue
"""
import asyncio
import aiohttp
import json
import time

async def test_simple_workflow():
    """Test simple workflow with generation node"""
    
    workflow_data = {
        "workflow": {
            "nodes": [
                {
                    "id": "input-1",
                    "type": "input-node",
                    "position": {"x": 100, "y": 100},
                    "content": "간단한 테스트 입력입니다.",
                    "model_type": None,
                    "llm_provider": None,
                    "prompt": None,
                    "knowledge_base": None,
                    "search_intensity": None,
                    "rerank_provider": None,
                    "rerank_model": None,
                    "output": None,
                    "executed": False,
                    "error": None
                },
                {
                    "id": "generation-1",
                    "type": "generation-node",
                    "position": {"x": 300, "y": 100},
                    "content": None,
                    "model_type": "gemini-1.5-flash",
                    "llm_provider": "google",
                    "prompt": "다음 텍스트를 요약해주세요: {input_data}",
                    "knowledge_base": None,
                    "search_intensity": None,
                    "rerank_provider": None,
                    "rerank_model": None,
                    "output": None,
                    "executed": False,
                    "error": None
                },
                {
                    "id": "output-1",
                    "type": "output-node",
                    "position": {"x": 500, "y": 100},
                    "content": "결과",
                    "model_type": None,
                    "llm_provider": None,
                    "prompt": None,
                    "knowledge_base": None,
                    "search_intensity": None,
                    "rerank_provider": None,
                    "rerank_model": None,
                    "output": None,
                    "executed": False,
                    "error": None
                }
            ],
            "edges": [
                {"id": "edge-1", "source": "input-1", "target": "generation-1"},
                {"id": "edge-2", "source": "generation-1", "target": "output-1"}
            ]
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            print("Testing simple workflow...")
            async with session.post(
                "http://localhost:5001/execute-workflow-stream",
                json=workflow_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"Response status: {response.status}")
                if response.status != 200:
                    text = await response.text()
                    print(f"Error response: {text}")
                    return
                
                # SSE 스트림 읽기
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    lines = buffer.split('\n')
                    buffer = lines[-1]
                    
                    for line in lines[:-1]:
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                print(f"Received: {data.get('type')} - {data.get('message', '')}")
                                
                                if data.get('type') == 'error':
                                    print(f"ERROR DETAILS: {data}")
                                    return
                                elif data.get('type') == 'complete':
                                    print("Workflow completed successfully!")
                                    return
                                    
                            except json.JSONDecodeError as e:
                                print(f"JSON parse error: {line[6:]} - {e}")
                                continue
                
        except Exception as e:
            print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_workflow())