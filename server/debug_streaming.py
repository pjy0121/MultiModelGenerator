"""
간단한 스트리밍 테스트 스크립트 - 디버깅용
"""

import asyncio
import aiohttp
import json
import time

async def simple_streaming_test():
    """간단한 스트리밍 테스트"""
    workflow_data = {
        "workflow": {
            "nodes": [
                {
                    "id": "input-1",
                    "type": "input-node",
                    "position": {"x": 100, "y": 100},
                    "content": "테스트 입력",
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
                    "id": "output-1",
                    "type": "output-node",
                    "position": {"x": 300, "y": 100},
                    "content": "최종 결과",
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
                {"id": "edge-1", "source": "input-1", "target": "output-1"}
            ]
        }
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("🚀 스트리밍 테스트 시작...")
        
        try:
            async with session.post(
                "http://localhost:5001/execute-workflow-stream",
                json=workflow_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"HTTP 상태: {response.status}")
                print(f"Content-Type: {response.headers.get('Content-Type')}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"오류 응답: {error_text}")
                    return
                
                buffer = ""
                chunk_count = 0
                
                async for chunk in response.content.iter_chunked(1024):
                    chunk_text = chunk.decode('utf-8')
                    buffer += chunk_text
                    print(f"청크 받음 ({len(chunk_text)} bytes): {repr(chunk_text)}")
                    
                    # 라인 단위로 처리
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # 마지막 불완전한 라인은 버퍼에 유지
                    
                    for line in lines[:-1]:
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                chunk_count += 1
                                print(f"[{chunk_count}] {data.get('type')}: {data.get('message', data.get('content', ''))}")
                                
                                if data.get('type') in ['complete', 'error']:
                                    print(f"✅ 완료! 총 {chunk_count}개 청크 수신")
                                    return
                                    
                            except json.JSONDecodeError as e:
                                print(f"JSON 파싱 실패: {line[6:]} - {e}")
                
                print(f"스트림 종료. 총 {chunk_count}개 청크 수신")
                
        except Exception as e:
            print(f"예외 발생: {e}")

if __name__ == "__main__":
    asyncio.run(simple_streaming_test())