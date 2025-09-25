"""
Node execution engine - project_reference.md 기준 의존성 해결 및 병렬 실행
"""

import asyncio
import time
import logging
from typing import Dict, List, Set, Optional, AsyncGenerator
from collections import defaultdict, deque

from ..core.models import (
    WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType,
    NodeExecutionResult, WorkflowExecutionResponse
)
from ..api.node_executors import NodeExecutor
from .config import NODE_EXECUTION_CONFIG


# 로거 설정
logger = logging.getLogger(__name__)

class NodeExecutionEngine:
    """
    노드 기반 워크플로우 실행 엔진
    
    project_reference.md의 실행 알고리즘:
    1. 모든 input-node들을 찾아 실행 대기 목록에 추가
    2. pre-node가 없거나 모든 pre-node 실행 완료된 노드들을 병렬 실행
    3. 실행 완료된 노드의 post-node들을 목록에 등록
    4. 목록이 빌 때까지 반복
    """
    
    def __init__(self):
        self.execution_queue: Set[str] = set()
        self.completed_nodes: Set[str] = set()
        self.node_outputs: Dict[str, str] = {}
        self.execution_results: List[NodeExecutionResult] = []
        self.execution_order: List[str] = []  # 실행 순서 추적
        self.is_stopping: bool = False  # 중단 플래그 추가
        self.stop_logged: bool = False  # 중단 로그 중복 방지용 플래그
        
        # 노드 실행자 생성
        self.node_executor = NodeExecutor()
    
    async def _collect_stream_output(self, stream_queue: asyncio.Queue, expected_completions: int) -> List[Dict]:
        """스트리밍 출력을 수집하는 헬퍼 메서드"""
        outputs = []
        completed_count = 0
        
        while completed_count < expected_completions:
            try:
                chunk = await asyncio.wait_for(
                    stream_queue.get(), 
                    timeout=NODE_EXECUTION_CONFIG["stream_timeout"]
                )
                
                if chunk["type"] == "_stream_complete":
                    break
                    
                outputs.append(chunk)
                
                if chunk["type"] == "node_complete":
                    completed_count += 1
                    
            except asyncio.TimeoutError:
                # 타임아웃 발생 시 로그 남기고 계속
                logger.warning(f"Stream timeout waiting for completion ({completed_count}/{expected_completions})")
                break
        
        return outputs
    
    async def _execute_single_node_stream(
        self, 
        node: WorkflowNode, 
        workflow: WorkflowDefinition, 
        stream_queue: asyncio.Queue
    ):
        """단일 노드를 실행하고 스트리밍 출력을 실시간으로 큐에 전송"""
        
        accumulated_output = ""
        final_result = None
        try:
            # 스트리밍 출력 처리
            async for chunk in self._execute_node_stream(node, workflow):
                if chunk["type"] == "stream":
                    accumulated_output += chunk["content"]
                    # 즉시 스트리밍 출력 전송
                    await stream_queue.put({
                        "type": "stream",
                        "node_id": node.id,
                        "content": chunk["content"]
                    })
                elif chunk["type"] == "result":
                    final_result = chunk
                elif chunk["type"] == "parsed_result":
                    final_result = chunk

            # 노드 실행 결과 처리
            if final_result and final_result.get("success") != False:
                # 성공한 경우
                if "output" in final_result:
                    output_value = final_result.get("output")
                elif "result" in final_result:
                    output_value = final_result.get("result")
                else:
                    output_value = accumulated_output
                    
                # output_value가 None이면 accumulated_output 사용
                if output_value is None:
                    output_value = accumulated_output
                    
                description_value = final_result.get("description", "") or accumulated_output
                    
                self.node_outputs[node.id] = output_value
                self.execution_results.append(NodeExecutionResult(
                    node_id=node.id,
                    success=True,
                    output=output_value,
                    description=description_value,
                    raw_response=accumulated_output or final_result.get("description", ""),
                    execution_time=final_result.get("execution_time", 0.0)
                ))
                
                # 즉시 완료 알림 전송
                await stream_queue.put({
                    "type": "node_complete",
                    "node_id": node.id,
                    "success": True,
                    "description": description_value,
                    "execution_time": final_result.get("execution_time", 0.0),
                    "message": f"{node.type} 노드 실행 완료"
                })
            else:
                # 실패한 경우
                error_msg = final_result.get("error", "Unknown error") if final_result else "No result"
                description = final_result.get("description", str(error_msg)) if final_result else str(error_msg)
                
                self.execution_results.append(NodeExecutionResult(
                    node_id=node.id,
                    success=False,
                    output=None,
                    description=description,
                    error=error_msg,
                    raw_response=accumulated_output,
                    execution_time=final_result.get("execution_time", 0.0) if final_result else 0.0
                ))
                
                # 즉시 실패 알림 전송
                await stream_queue.put({
                    "type": "node_complete",
                    "node_id": node.id,
                    "success": False,
                    "error": error_msg,
                    "description": description,
                    "execution_time": final_result.get("execution_time", 0.0) if final_result else 0.0
                })
 
        except Exception as e:
            # 예외 발생 시 처리
            await stream_queue.put({
                "type": "node_complete",
                "node_id": node.id,
                "success": False,
                "error": str(e),
                "execution_time": 0.0
            })
    
    async def execute_workflow(
        self, 
        workflow: WorkflowDefinition
    ) -> WorkflowExecutionResponse:
        """워크플로우 전체 실행 (비스트리밍)"""
        
        # 스트리밍 실행을 사용하되 결과만 수집
        results = []
        async for event in self.execute_workflow_stream(workflow):
            if event["type"] == "final_result":
                return event["result"]
        
        # fallback (정상적으로는 도달하지 않음)
        return WorkflowExecutionResponse(
            success=False,
            results=[],
            error="Workflow execution completed without final result"
        )
    
    def _reset_state(self):
        """실행 상태 초기화"""
        self.execution_queue.clear()
        self.completed_nodes.clear()
        self.node_outputs.clear()
        self.execution_results.clear()
        self.execution_order.clear()  # 실행 순서도 초기화
        self.workflow_nodes = []  # workflow nodes 초기화
    
    def _build_dependency_graph(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """의존성 그래프 구축 (각 노드의 pre-nodes 맵핑)"""
        pre_nodes_map = defaultdict(list)
        
        for edge in workflow.edges:
            pre_nodes_map[edge.target].append(edge.source)
        
        # 모든 노드에 대해 빈 리스트라도 생성
        for node in workflow.nodes:
            if node.id not in pre_nodes_map:
                pre_nodes_map[node.id] = []
        return dict(pre_nodes_map)
    
    def _build_post_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """각 노드의 post-nodes 맵핑"""
        post_nodes_map = defaultdict(list)
        
        for edge in workflow.edges:
            post_nodes_map[edge.source].append(edge.target)
        
        return dict(post_nodes_map)
    
    def _find_ready_nodes(self, pre_nodes_map: Dict[str, List[str]]) -> List[str]:
        """실행 가능한 노드들 찾기 (모든 pre-node가 완료된 노드들)"""
        ready_nodes = []
        
        logger.info(f"Finding ready nodes from queue: {list(self.execution_queue)}")
        logger.info(f"Completed nodes: {list(self.completed_nodes)}")
        
        for node_id in self.execution_queue:
            pre_nodes = pre_nodes_map.get(node_id, [])
            logger.info(f"Node {node_id} has pre_nodes: {pre_nodes}")
            
            # pre-node가 없거나 모든 pre-node가 완료되었으면 실행 가능
            if not pre_nodes or all(pre_id in self.completed_nodes for pre_id in pre_nodes):
                ready_nodes.append(node_id)
                logger.info(f"Node {node_id} is ready for execution")
            else:
                missing_pre_nodes = [pre_id for pre_id in pre_nodes if pre_id not in self.completed_nodes]
                logger.info(f"Node {node_id} waiting for pre_nodes: {missing_pre_nodes}")
        
        return ready_nodes
    
    def _get_final_output(self, workflow: WorkflowDefinition) -> Optional[str]:
        """최종 출력 결과 (output-node의 결과)"""
        output_nodes = [node for node in workflow.nodes if node.type == "output-node"]
        
        if output_nodes:
            output_node_id = output_nodes[0].id
            return self.node_outputs.get(output_node_id)
        
        return None
    
    async def execute_workflow_stream(
        self, 
        workflow: WorkflowDefinition
    ):
        """워크플로우 이벤트 기반 병렬 스트리밍 실행 - 각 노드가 완료되는 즉시 다음 단계 진행"""

        start_time = time.time()

        try:
            # 초기화
            self._reset_state()
            
            # workflow nodes 저장 (context-node 구분을 위해)
            self.workflow_nodes = workflow.nodes
            
            # 스트리밍 시작 알림
            yield {
                "type": "start",
                "message": "워크플로우 이벤트 기반 실행을 시작합니다.",
                "total_nodes": len(workflow.nodes)
            }
            
            # 의존성 그래프 구축
            pre_nodes_map = self._build_dependency_graph(workflow)
            node_lookup = {node.id: node for node in workflow.nodes}

            # 전체 스트리밍 출력을 위한 큐
            global_stream_queue = asyncio.Queue()
            
            # 활성 노드 태스크들을 추적
            active_tasks = {}
            
            # input-node들을 먼저 시작
            for node in workflow.nodes:
                if node.type == "input-node":
                    # 노드 실행 시작 알림을 먼저 발생시킴
                    yield {
                        "type": "node_start",
                        "node_id": node.id,
                        "node_type": node.type,
                        "message": f"{node.type} 노드 실행 시작"
                    }
                    
                    task = asyncio.create_task(
                        self._execute_single_node_stream(
                            node, workflow, global_stream_queue
                        )
                    )
                    active_tasks[node.id] = task
            
            # 전체 노드 완료 추적
            total_completed = 0
            total_nodes = len(workflow.nodes)

            # 이벤트 기반 실행 루프
            while total_completed < total_nodes:
                # 중단 요청 체크 (한 번만 로그)
                if self.is_stopping and not self.stop_logged:
                    logger.info("Workflow execution stopped by user request")
                    self.stop_logged = True
                    # 현재 실행 중인 태스크들을 취소하지 않고 완료되기를 기다림
                    yield {
                        "type": "stop_requested",
                        "message": "워크플로우 중단이 요청되었습니다. 현재 실행 중인 노드들이 완료되면 중단됩니다."
                    }
                
                # 스트리밍 출력 처리
                try:
                    chunk = await asyncio.wait_for(global_stream_queue.get(), timeout=0.1)
                    yield chunk
                    
                    # 노드 완료 이벤트 처리
                    if chunk["type"] == "node_complete" and chunk["success"]:
                        completed_node_id = chunk["node_id"]
                        total_completed += 1
                        
                        # 완료된 노드를 completed_nodes에 추가
                        self.completed_nodes.add(completed_node_id)
                        self.execution_order.append(completed_node_id)
                        
                        # 완료된 노드를 active_tasks에서 제거
                        if completed_node_id in active_tasks:
                            del active_tasks[completed_node_id]
                        
                        # 중단 요청이 있고 더 이상 활성 태스크가 없다면 루프 종료
                        if self.is_stopping and not active_tasks:
                            logger.info("Workflow execution stopping - all active tasks completed")
                            break
                        
                        # 즉시 post-node들 확인하고 실행 가능한 노드 시작
                        for edge in workflow.edges:
                            if edge.source == completed_node_id:
                                target_node_id = edge.target
                                
                                # 이미 실행 중이거나 완료된 노드는 스킵
                                if (target_node_id in active_tasks or 
                                    target_node_id in self.completed_nodes):
                                    continue
                                
                                # 의존성 체크: 모든 pre-node가 완료되었는지 확인
                                pre_nodes = set(pre_nodes_map.get(target_node_id, []))
                                if pre_nodes.issubset(self.completed_nodes):
                                    # 중단 요청이 있으면 새로운 노드 시작 안함
                                    if self.is_stopping:
                                        continue
                                        
                                    target_node = node_lookup[target_node_id]
                                    
                                    # 노드 실행 시작 알림을 먼저 발생시킴 (딜레이 최소화)
                                    yield {
                                        "type": "node_start",
                                        "node_id": target_node_id,
                                        "node_type": target_node.type,
                                        "message": f"{target_node.type} 노드 실행 시작"
                                    }
                                    
                                    # 즉시 노드 실행 시작
                                    task = asyncio.create_task(
                                        self._execute_single_node_stream(
                                            target_node, workflow, global_stream_queue
                                        )
                                    )
                                    active_tasks[target_node_id] = task
                    
                    elif chunk["type"] == "node_complete" and not chunk["success"]:
                        # 실패한 노드도 active_tasks에서 제거
                        failed_node_id = chunk.get("node_id")
                        if failed_node_id and failed_node_id in active_tasks:
                            del active_tasks[failed_node_id]
                        
                        # 실패한 노드가 있으면 전체 워크플로우 중단
                        yield {
                            "type": "error",
                            "message": f"노드 실행 실패: {chunk['node_id']}"
                        }
                        # 모든 활성 태스크 취소
                        for task in active_tasks.values():
                            task.cancel()
                        return
                        
                except asyncio.TimeoutError:
                    # 타임아웃은 정상 - 계속 진행
                    continue
 
            # 모든 활성 태스크 완료 대기
            if active_tasks:
                await asyncio.gather(*active_tasks.values(), return_exceptions=True)
            
            # 최종 결과
            total_time = time.time() - start_time
            final_output = self._get_final_output(workflow)
            
            # 중단된 경우와 정상 완료 구분
            was_stopped = self.is_stopping
            success_status = True  # 기본적으로 성공으로 처리 (중단도 성공적인 종료로 간주)
            
            # 스트리밍용 완료 이벤트
            yield {
                "type": "complete",
                "success": success_status,
                "final_output": final_output,
                "total_execution_time": total_time,
                "execution_order": self.execution_order,
                "results": [result.__dict__ for result in self.execution_results],
                "was_stopped": was_stopped  # 중단 여부 정보 추가
            }
            
            # 비스트리밍용 최종 결과 이벤트
            yield {
                "type": "final_result",
                "result": WorkflowExecutionResponse(
                    success=True,
                    results=self.execution_results,
                    final_output=final_output,
                    total_execution_time=total_time,
                    execution_order=self.execution_order
                )
            }
            
        except Exception as e:
            logger.error(f"워크플로우 실행 중 오류 발생: {str(e)}")
            total_time = time.time() - start_time
            
            # 스트리밍용 에러 이벤트
            yield {
                "type": "error",
                "message": f"워크플로우 실행 오류: {str(e)}"
            }
            
            # 비스트리밍용 최종 결과 이벤트
            yield {
                "type": "final_result",
                "result": WorkflowExecutionResponse(
                    success=False,
                    results=self.execution_results,
                    error=f"Workflow execution failed: {str(e)}",
                    total_execution_time=total_time,
                    execution_order=self.execution_order
                )
            }
    
    async def _execute_node_stream(
        self,
        node: WorkflowNode,
        workflow: WorkflowDefinition
    ):
        """개별 노드 스트리밍 실행"""
        
        start_time = time.time()
        
        try:
            # 스트리밍 실행
            accumulated_output = ""
            parsed_result = None
            
            final_result = None
            
            # pre-node들을 context-node와 일반 노드로 분리
            context_node_ids = []
            regular_pre_node_ids = []
            
            for edge in workflow.edges:
                if edge.target == node.id and edge.source in self.node_outputs:
                    # workflow nodes에서 source node 찾기
                    source_node = None
                    for wf_node in workflow.nodes:
                        if wf_node.id == edge.source:
                            source_node = wf_node
                            break
                    
                    if source_node and source_node.type == "context-node":
                        context_node_ids.append(edge.source)
                    else:
                        regular_pre_node_ids.append(edge.source)
            
            # 각각의 출력 수집
            context_outputs = [self.node_outputs[ctx_id] for ctx_id in context_node_ids]
            pre_outputs = [self.node_outputs[pre_id] for pre_id in regular_pre_node_ids]

            # context가 있는 LLM 노드인지 확인하고 적절한 스트리밍 메서드 호출
            if (node.type in ["generation-node", "ensemble-node", "validation-node"] 
                and context_outputs and hasattr(self.node_executor, 'execute_node_stream_with_context')):
                # context-aware 스트리밍 실행
                async for chunk in self.node_executor.execute_node_stream_with_context(node, pre_outputs, context_outputs):
                    if chunk["type"] == "stream":
                        accumulated_output += chunk["content"] 
                        yield chunk
                    elif chunk["type"] == "result":
                        final_result = chunk
                    elif chunk["type"] == "parsed_result":
                        final_result = chunk
                        parsed_result = chunk.get("output")
            else:
                # 기존 방식으로 스트리밍 실행 (모든 pre_outputs 합쳐서)
                all_pre_outputs = pre_outputs + context_outputs
                async for chunk in self.node_executor.execute_node_stream(node, all_pre_outputs):
                    if chunk["type"] == "stream":
                        accumulated_output += chunk["content"] 
                        yield chunk
                    elif chunk["type"] == "result":
                        final_result = chunk
                    elif chunk["type"] == "parsed_result":
                        final_result = chunk
                        parsed_result = chunk.get("output")
            
            # 최종 결과 반환 (execute_node_stream에서 이미 받은 결과 사용)
            if final_result:
                yield final_result
            else:
                # 실행 시간 계산
                execution_time = time.time() - start_time
                yield {
                    "type": "result",
                    "success": True,
                    "output": parsed_result,
                    "raw_response": accumulated_output,
                    "execution_time": execution_time
                }
            
        except Exception as e:
            logger.error(f"Node stream execution failed: {str(e)}")
            yield {
                "type": "result",
                "success": False,
                "error": str(e)
            }
    
    def stop_execution(self):
        """워크플로우 실행 중단 요청"""
        self.is_stopping = True
        logger.info("Workflow execution stop requested")
    
    def reset_execution_state(self):
        """실행 상태 초기화"""
        self.execution_queue.clear()
        self.completed_nodes.clear()
        self.node_outputs.clear()
        self.execution_results.clear()
        self.execution_order.clear()
        self.is_stopping = False
        self.stop_logged = False  # 중단 로그 플래그도 초기화