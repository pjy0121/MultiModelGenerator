#!/usr/bin/env python3
"""
병렬 지식 베이스 검색 테스트
"""

import asyncio
import time
from src.core.models import WorkflowDefinition, WorkflowNode, WorkflowEdge
from src.core.node_execution_engine import NodeExecutionEngine

async def test_parallel_knowledge_base_search():
    """여러 노드가 병렬로 지식 베이스를 검색할 때의 동작 테스트"""
    
    # 테스트용 워크플로우 생성: input -> 3개의 generation 노드 (병렬)
    nodes = [
        # Input node
        WorkflowNode(
            id="input-1",
            type="input-node",
            content="NVMe SSD의 성능 요구사항과 보안 요구사항을 분석해주세요."
        ),
        # 3개의 Generation 노드 (병렬 실행)
        WorkflowNode(
            id="gen-1", 
            type="generation-node",
            prompt="성능 관련 요구사항을 추출해주세요: {input_data}\n참고: {context}",
            llm_provider="openai",
            model_type="gpt-4o-mini",
            knowledge_base="large_nvme_2-2",
            search_intensity="medium"
        ),
        WorkflowNode(
            id="gen-2",
            type="generation-node", 
            prompt="보안 관련 요구사항을 추출해주세요: {input_data}\n참고: {context}",
            llm_provider="openai",
            model_type="gpt-4o-mini",
            knowledge_base="large_nvme_2-2",
            search_intensity="medium"
        ),
        WorkflowNode(
            id="gen-3",
            type="generation-node",
            prompt="호환성 관련 요구사항을 추출해주세요: {input_data}\n참고: {context}",
            llm_provider="openai", 
            model_type="gpt-4o-mini",
            knowledge_base="large_nvme_2-2",
            search_intensity="medium"
        )
    ]
    
    # 에지: input -> 3개 generation 노드들
    edges = [
        WorkflowEdge(source="input-1", target="gen-1"),
        WorkflowEdge(source="input-1", target="gen-2"), 
        WorkflowEdge(source="input-1", target="gen-3")
    ]
    
    workflow = WorkflowDefinition(nodes=nodes, edges=edges)
    
    print("=== 병렬 지식 베이스 검색 테스트 ===")
    print("3개의 Generation 노드가 동시에 같은 지식 베이스를 검색합니다.")
    print("-" * 60)
    
    engine = NodeExecutionEngine()
    
    try:
        start_time = time.time()
        search_start_times = {}
        search_end_times = {}
        
        print("🚀 워크플로우 스트리밍 실행 시작\n")
        
        async for chunk in engine.execute_workflow_stream(workflow, False):
            if chunk.get("type") == "stream":
                content = chunk.get("content", "")
                node_id = chunk.get("node_id", "unknown")
                timestamp = time.time() - start_time
                
                print(f"[{timestamp:6.2f}s] {content}", end="")
                
                # 검색 시작/종료 시간 추적
                if "검색 시작" in content:
                    search_start_times[node_id] = timestamp
                elif ("문서 찾음" in content or "관련 문서 없음" in content or "검색 실패" in content):
                    search_end_times[node_id] = timestamp
                    
            elif chunk.get("type") == "complete":
                total_time = time.time() - start_time
                print(f"\n✅ 워크플로우 완료 (총 {total_time:.2f}초)\n")
                
                # 검색 시간 분석
                print("=== 검색 시간 분석 ===")
                for node_id in ["gen-1", "gen-2", "gen-3"]:
                    if node_id in search_start_times and node_id in search_end_times:
                        duration = search_end_times[node_id] - search_start_times[node_id]
                        print(f"{node_id}: {search_start_times[node_id]:.2f}s ~ {search_end_times[node_id]:.2f}s (소요: {duration:.2f}s)")
                
                # 병렬성 분석
                if len(search_start_times) >= 2:
                    start_times = list(search_start_times.values())
                    start_times.sort()
                    if (start_times[1] - start_times[0]) < 0.5:  # 0.5초 이내 시작
                        print("\n✅ 병렬 검색이 정상적으로 작동하고 있습니다!")
                    else:
                        print(f"\n⚠️ 검색이 순차적으로 실행되고 있습니다 (시차: {start_times[1] - start_times[0]:.2f}초)")
                
                break
                
            elif chunk.get("type") == "error":
                print(f"\n❌ 오류: {chunk.get('message')}")
                break
                
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parallel_knowledge_base_search())