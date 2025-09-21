#!/usr/bin/env python3
"""
지식 베이스 검색 과정 스트리밍 테스트
"""

import asyncio
from src.core.models import WorkflowDefinition, WorkflowNode, WorkflowEdge
from src.api.node_executors import NodeExecutor

async def test_knowledge_base_streaming():
    """지식 베이스 검색 과정이 스트리밍으로 보이는지 테스트"""
    
    # 테스트용 generation-node 생성 (지식 베이스 포함)
    generation_node = WorkflowNode(
        id="test-generation",
        type="generation-node",
        prompt="다음 내용을 분석해서 요구사항을 추출해주세요.\n\n입력: {input_data}\n\n참고 문서: {context}",
        llm_provider="openai",
        model_type="gpt-4o-mini",
        knowledge_base="large_nvme_2-2",  # 존재하는 지식 베이스 사용
        search_intensity="medium"
    )
    
    # NodeExecutor 생성
    executor = NodeExecutor()
    
    print("=== 지식 베이스 검색 스트리밍 테스트 ===")
    print(f"Node ID: {generation_node.id}")
    print(f"Knowledge Base: {generation_node.knowledge_base}")
    print(f"Search Intensity: {generation_node.search_intensity}")
    print("-" * 60)
    
    try:
        # pre_outputs로 테스트 데이터 제공
        pre_outputs = ["NVMe SSD의 성능 요구사항에 대해 알려주세요."]
        
        print("🚀 스트리밍 실행 시작:")
        print()
        
        # execute_node_stream으로 스트리밍 실행
        chunk_count = 0
        knowledge_search_shown = False
        
        async for chunk in executor.execute_node_stream(generation_node, pre_outputs, False):
            chunk_count += 1
            
            if chunk.get("type") == "stream":
                content = chunk.get("content", "")
                print(f"[{chunk_count:03d}] {content}", end="")
                
                # 지식 베이스 검색 관련 메시지가 나왔는지 확인
                if "지식 베이스" in content or "검색" in content:
                    knowledge_search_shown = True
                    
            elif chunk.get("type") == "result":
                print(f"\n\n[최종 결과]")
                print(f"Success: {chunk.get('success')}")
                print(f"Output 길이: {len(chunk.get('output', ''))} 글자")
                
            elif chunk.get("type") == "parsed_result":
                print(f"\n\n[파싱 결과]")
                print(f"Success: {chunk.get('success')}")
                print(f"Output 길이: {len(chunk.get('output', ''))} 글자")
        
        print(f"\n\n✅ 총 {chunk_count}개 청크 수신")
        
        if knowledge_search_shown:
            print("✅ 지식 베이스 검색 과정이 스트리밍으로 표시됨")
        else:
            print("❌ 지식 베이스 검색 과정이 표시되지 않음")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_knowledge_base_streaming())