#!/usr/bin/env python3
"""
input-node output 버그 테스트
"""

import asyncio
from src.core.models import WorkflowDefinition, WorkflowNode, WorkflowEdge
from src.api.node_executors import NodeExecutor

async def test_input_node():
    """input-node의 output 테스트"""
    
    # 테스트용 input-node 생성
    input_node = WorkflowNode(
        id="test-input",
        type="input-node",
        content="테스트 입력 데이터입니다."
    )
    
    # NodeExecutor 생성
    executor = NodeExecutor()
    
    print("=== Input Node Output 테스트 ===")
    print(f"Node ID: {input_node.id}")
    print(f"Node Type: {input_node.type}")
    print(f"Node Content: {input_node.content}")
    print("-" * 50)
    
    try:
        # 1. execute_node 테스트
        print("1. execute_node 테스트:")
        result = await executor.execute_node(input_node, [], False)
        print(f"   Success: {result.success}")
        print(f"   Output: {repr(result.output)}")
        print(f"   Description: {repr(result.description)}")
        print(f"   Error: {result.error}")
        print()
        
        # 2. execute_node_stream 테스트
        print("2. execute_node_stream 테스트:")
        chunks = []
        async for chunk in executor.execute_node_stream(input_node, [], False):
            chunks.append(chunk)
            print(f"   Chunk: {chunk}")
        
        print(f"   총 {len(chunks)}개 청크 수신")
        
        # 결과 검증
        if result.output is None:
            print("❌ BUG: input-node의 output이 None입니다!")
        else:
            print("✅ OK: input-node의 output이 정상입니다.")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_input_node())