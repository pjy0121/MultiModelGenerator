"""
Node execution engine - project_reference.md 기준 의존성 해결 및 병렬 실행
"""

import asyncio
import time
import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict, deque

from ..core.models import (
    WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType,
    NodeExecutionResult, WorkflowExecutionResponse
)
from ..api.node_executors import NodeExecutor

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
        
        # NodeExecutor 인스턴스 생성
        self.node_executor = NodeExecutor()
    
    async def execute_workflow(
        self, 
        workflow: WorkflowDefinition,
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ) -> WorkflowExecutionResponse:
        """워크플로우 전체 실행"""
        
        start_time = time.time()  # 실행 시간 측정 시작
        
        try:
            # 초기화
            self._reset_state()
            
            # 의존성 그래프 구축
            pre_nodes_map = self._build_dependency_graph(workflow)
            post_nodes_map = self._build_post_nodes_map(workflow)
            nodes_map = {node.id: node for node in workflow.nodes}
            
            # 1. 모든 input-node들을 실행 대기 목록에 추가
            input_nodes = [node for node in workflow.nodes if node.type == "input-node"]
            for node in input_nodes:
                self.execution_queue.add(node.id)
            
            # 2. 실행 루프
            while self.execution_queue:
                # 2-1. 실행 가능한 노드들 찾기 (pre-node가 모두 완료된 노드들)
                ready_nodes = self._find_ready_nodes(pre_nodes_map)
                
                if not ready_nodes:
                    # 더 이상 실행할 수 있는 노드가 없으면 순환 의존성 또는 오류
                    remaining_nodes = list(self.execution_queue)
                    return WorkflowExecutionResponse(
                        success=False,
                        results=self.execution_results,
                        error=f"Circular dependency or execution error. Remaining nodes: {remaining_nodes}"
                    )
                
                # 2-2. 실행 가능한 노드들을 병렬로 실행
                execution_tasks = []
                for node_id in ready_nodes:
                    node = nodes_map[node_id]
                    task = self._execute_single_node(
                        node, pre_nodes_map[node_id], 
                        knowledge_base, search_intensity
                    )
                    execution_tasks.append(task)
                
                # 2-3. 병렬 실행 완료 대기
                node_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
                
                # 2-4. 결과 처리 및 post-node들을 큐에 추가
                for i, result in enumerate(node_results):
                    node_id = ready_nodes[i]
                    
                    # 실행 순서 기록 (성공/실패 관계없이)
                    self.execution_order.append(node_id)
                    
                    if isinstance(result, Exception):
                        # 실행 중 에러 발생
                        error_result = NodeExecutionResult(
                            node_id=node_id,
                            success=False,
                            error=str(result)
                        )
                        self.execution_results.append(error_result)
                    else:
                        # 성공적 실행
                        self.execution_results.append(result)
                        if result.success and result.output:
                            self.node_outputs[node_id] = result.output
                    
                    # 완료된 노드 처리
                    self.completed_nodes.add(node_id)
                    self.execution_queue.remove(node_id)
                    
                    # post-node들을 실행 큐에 추가
                    for post_node_id in post_nodes_map.get(node_id, []):
                        if post_node_id not in self.completed_nodes:
                            self.execution_queue.add(post_node_id)
            
            # 최종 결과 조립
            final_output = self._get_final_output(workflow)
            execution_time = time.time() - start_time  # 실행 시간 계산
            
            return WorkflowExecutionResponse(
                success=True,
                results=self.execution_results,
                final_output=final_output,
                total_execution_time=execution_time,
                execution_order=self.execution_order
            )
            
        except Exception as e:
            execution_time = time.time() - start_time  # 오류 시에도 실행 시간 계산
            return WorkflowExecutionResponse(
                success=False,
                results=self.execution_results,
                error=f"Workflow execution failed: {str(e)}",
                total_execution_time=execution_time,
                execution_order=self.execution_order
            )
    
    def _reset_state(self):
        """실행 상태 초기화"""
        self.execution_queue.clear()
        self.completed_nodes.clear()
        self.node_outputs.clear()
        self.execution_results.clear()
        self.execution_order.clear()  # 실행 순서도 초기화
    
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
    
    async def _execute_single_node(
        self, 
        node: WorkflowNode, 
        pre_node_ids: List[str],
        knowledge_base: Optional[str],
        search_intensity: int
    ) -> NodeExecutionResult:
        """단일 노드 실행 - NodeExecutor 사용"""
        
        try:
            # pre-node들의 출력 수집
            pre_outputs = [self.node_outputs.get(pre_id, "") for pre_id in pre_node_ids]
            
            # NodeExecutor를 통한 실행
            result = await self.node_executor.execute_node(
                node, pre_outputs, knowledge_base, search_intensity
            )
            
            return result
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=str(e)
            )
    
    def _get_final_output(self, workflow: WorkflowDefinition) -> Optional[str]:
        """최종 출력 결과 (output-node의 결과)"""
        output_nodes = [node for node in workflow.nodes if node.type == "output-node"]
        
        if output_nodes:
            output_node_id = output_nodes[0].id
            return self.node_outputs.get(output_node_id)
        
        return None
    
    async def execute_workflow_stream(
        self, 
        workflow: WorkflowDefinition,
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ):
        """워크플로우 스트리밍 실행 - LLM 응답을 실시간으로 전송"""
        
        start_time = time.time()
        
        try:
            # 초기화
            self._reset_state()
            
            # 스트리밍 시작 알림
            yield {
                "type": "start",
                "message": "워크플로우 실행을 시작합니다.",
                "total_nodes": len(workflow.nodes)
            }
            
            # 의존성 그래프 구축
            pre_nodes_map = self._build_dependency_graph(workflow)
            
            # input-node들을 실행 대기 목록에 추가
            for node in workflow.nodes:
                if node.type == "input-node":
                    self.execution_queue.add(node.id)
            
            node_lookup = {node.id: node for node in workflow.nodes}
            
            # 메인 실행 루프
            while self.execution_queue:
                # 실행 가능한 노드들 찾기
                ready_nodes = []
                for node_id in list(self.execution_queue):
                    pre_nodes = set(pre_nodes_map.get(node_id, []))  # List를 set으로 변환
                    if pre_nodes.issubset(self.completed_nodes):
                        ready_nodes.append(node_id)
                        self.execution_queue.remove(node_id)
                
                # 노드 ID 순으로 정렬 (일관된 실행 순서를 위해)
                ready_nodes.sort()
                
                if not ready_nodes:
                    error_msg = "순환 의존성 또는 블록된 노드가 발견되었습니다."
                    logger.error(error_msg)
                    yield {
                        "type": "error",
                        "message": error_msg
                    }
                    return
                
                # project_reference.md 1-2-2, 1-2-3: 병렬 실행 후 완료 대기
                # 모든 ready_nodes를 먼저 실행하고, 모두 완료될 때까지 기다린 후 post-node 추가
                completed_in_this_round = []
                failed_nodes = []
                
                for node_id in ready_nodes:
                    node = node_lookup[node_id]
                    
                    # 실행 시작하므로 큐에서 제거 (중복 실행 방지)
                    self.execution_queue.discard(node_id)
                    
                    # 노드 실행 시작 알림
                    yield {
                        "type": "node_start",
                        "node_id": node_id,
                        "node_type": node.type,
                        "message": f"{node.type} 노드 실행 시작"
                    }
                    
                    accumulated_output = ""
                    final_result = None
                    
                    # 스트리밍 출력 처리
                    async for chunk in self._execute_node_stream(
                        node, workflow, knowledge_base, search_intensity
                    ):
                        if chunk["type"] == "stream":
                            accumulated_output += chunk["content"]
                            yield {
                                "type": "stream",
                                "node_id": node_id,
                                "content": chunk["content"]
                            }
                        elif chunk["type"] == "result":
                            final_result = chunk
                        elif chunk["type"] == "parsed_result":
                            final_result = chunk
                    
                    # 노드 실행 완료 처리
                    if final_result:
                        # 성공한 경우
                        if final_result.get("success") == True or (
                            final_result.get("success") != False and (
                                final_result.get("result") is not None or
                                final_result.get("output") is not None
                            )
                        ):
                            self.completed_nodes.add(node_id)
                            self.execution_order.append(node_id)
                            
                            # 결과 저장 (다양한 형식 지원)
                            if "output" in final_result:
                                output_value = final_result.get("output", accumulated_output)
                            elif "result" in final_result:
                                output_value = final_result.get("result", accumulated_output)
                            else:
                                output_value = accumulated_output
                                
                            # description 결정: 텍스트 노드는 final_result에서, LLM 노드는 accumulated_output에서
                            description_value = accumulated_output if accumulated_output else final_result.get("description", "")
                                
                            self.node_outputs[node_id] = output_value
                            self.execution_results.append(NodeExecutionResult(
                                node_id=node_id,
                                success=True,
                                output=output_value,
                                description=description_value,  # 올바른 description 사용
                                raw_response=accumulated_output or final_result.get("description", ""),
                                execution_time=final_result.get("execution_time", 0.0)
                            ))
                            
                            completed_in_this_round.append(node_id)
                            
                            yield {
                                "type": "node_complete",
                                "node_id": node_id,
                                "success": True,
                                "description": description_value,
                                "execution_time": final_result.get("execution_time", 0.0),
                                "message": f"{node.type} 노드 실행 완료"
                            }
                        else:
                            # 실패한 경우 (success == False)
                            error_msg = final_result.get("error", "Unknown error")
                            description = final_result.get("description", str(error_msg))
                            
                            # 실패한 노드도 execution_results에 추가
                            self.execution_results.append(NodeExecutionResult(
                                node_id=node_id,
                                success=False,
                                output=None,
                                description=description,
                                error=error_msg,
                                raw_response=accumulated_output,
                                execution_time=final_result.get("execution_time", 0.0)
                            ))
                            
                            failed_nodes.append(node_id)
                            yield {
                                "type": "node_complete", 
                                "node_id": node_id,
                                "success": False,
                                "error": error_msg,
                                "description": description,
                                "execution_time": final_result.get("execution_time", 0.0)
                            }
                    else:
                        # final_result가 없는 경우
                        error_msg = "No execution result"
                        failed_nodes.append(node_id)
                        yield {
                            "type": "node_complete", 
                            "node_id": node_id,
                            "success": False,
                            "error": error_msg,
                            "execution_time": 0.0
                        }
                
                # 실패한 노드가 있으면 전체 워크플로우 중단
                if failed_nodes:
                    yield {
                        "type": "error",
                        "message": f"노드 실행 실패: {', '.join(failed_nodes)}"
                    }
                    return
                
                # 모든 노드가 완료된 후에야 post-node들을 실행 대기 목록에 추가
                # project_reference.md 1-2-4: 실행이 끝난 노드의 post-node들을 목록에 등록
                for node_id in completed_in_this_round:
                    for edge in workflow.edges:
                        if edge.source == node_id:
                            self.execution_queue.add(edge.target)
            
            # 최종 결과
            total_time = time.time() - start_time
            final_output = self._get_final_output(workflow)
            
            yield {
                "type": "complete",
                "success": True,
                "final_output": final_output,
                "total_execution_time": total_time,
                "execution_order": self.execution_order,
                "results": [result.__dict__ for result in self.execution_results]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            yield {
                "type": "error", 
                "message": f"Workflow execution failed: {str(e)}"
            }
    
    async def _execute_node_stream(
        self,
        node: WorkflowNode,
        workflow: WorkflowDefinition,
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ):
        """개별 노드 스트리밍 실행"""
        
        start_time = time.time()
        
        try:
            # 스트리밍 실행
            accumulated_output = ""
            parsed_result = None
            
            final_result = None
            
            async for chunk in self.node_executor.execute_node_stream(
                node, workflow, self.node_outputs, knowledge_base, search_intensity
            ):
                if chunk["type"] == "stream":
                    accumulated_output += chunk["content"] 
                    yield chunk
                elif chunk["type"] == "result":
                    # 텍스트 노드나 LLM 노드의 최종 결과
                    final_result = chunk
                elif chunk["type"] == "parsed_result":
                    # parsed_result 타입에서는 전체 chunk를 final_result로 사용
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