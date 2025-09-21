"""
Node별 실행자 구현 - 간소화된 버전
핵심 기능만 유지하고 불필요한 복잡성 제거
"""

import asyncio
import time
from typing import List, Optional, Dict, Any

from ..core.models import WorkflowNode, NodeExecutionResult
from ..core.output_parser import ResultParser
from ..core.config import LLM_CONFIG
from ..services.llm_factory import LLMFactory
from ..services.vector_store_service import VectorStoreService


class NodeExecutor:
    """노드 실행자 - 모든 노드 타입을 처리"""
    
    def __init__(self):
        self.llm_factory = LLMFactory()
        self.vector_store_service = VectorStoreService()
        self.result_parser = ResultParser()

    async def execute_node(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool) -> NodeExecutionResult:
        """노드 실행"""
        try:
            if self._is_text_node(node.type):
                return self._execute_text_node(node, pre_outputs, rerank_enabled)
            else:
                return await self._execute_llm_node(node, pre_outputs, rerank_enabled)
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Node execution failed: {str(e)}",
                execution_time=0.0
            )
    
    async def execute_node_stream(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool):
        """노드 스트리밍 실행"""
        try:
            if self._is_text_node(node.type):
                # 텍스트 노드는 즉시 결과 반환
                result = self._execute_text_node(node, pre_outputs, rerank_enabled)
                yield {
                    "type": "result",
                    "success": result.success,
                    "output": result.output,
                    "description": result.description,
                    "execution_time": result.execution_time
                }
            else:
                # LLM 노드는 스트리밍 실행
                async for chunk in self._execute_llm_node_stream(node, pre_outputs, rerank_enabled):
                    yield chunk
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Node execution failed: {str(e)}"
            }
    
    def _is_text_node(self, node_type: str) -> bool:
        """텍스트 노드 여부 확인"""
        return node_type in ["input-node", "output-node"]
    
    def _execute_text_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """텍스트 노드 실행 (Input/Output)"""
        if node.type == "input-node":
            content = node.content or "입력 데이터가 설정되지 않았습니다."
        else:  # Output node
            content = " ".join(pre_outputs) if pre_outputs else (node.content or "")
        
        return NodeExecutionResult(
            node_id=node.id,
            success=True,
            description=content,
            output=content,
            execution_time=0.0
        )
    
    async def _execute_llm_node(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool) -> NodeExecutionResult:
        """LLM 노드 실행 (Generation/Ensemble/Validation)"""
        start_time = time.time()
        
        try:
            prompt = await self._prepare_prompt(node, pre_outputs, rerank_enabled)
            
            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            llm_client = self.llm_factory.get_client(node.llm_provider)
            response = await self._call_llm(llm_client, node.model_type, prompt)
            
            parsed_result = self.result_parser.parse_node_output(response)
            execution_time = time.time() - start_time
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=parsed_result.description,
                output=parsed_result.output,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"LLM node execution failed: {str(e)}",
                execution_time=execution_time
            )
    
    async def _execute_llm_node_stream(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool):
        """LLM 노드 스트리밍 실행"""
        try:
            prompt = await self._prepare_prompt(node, pre_outputs, rerank_enabled)

            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            client = self.llm_factory.get_client(node.llm_provider)
            if not client or not client.is_available():
                raise Exception(f"LLM client not available: {node.llm_provider}")
            
            messages = [{"role": "user", "content": prompt}]
            full_response = ""
            
            # 스트리밍 실행
            if hasattr(client, 'chat_completion_stream'):
                async for chunk in client.chat_completion_stream(
                    model=node.model_type,
                    messages=messages,
                    temperature=LLM_CONFIG["default_temperature"]
                ):
                    if chunk:
                        full_response += chunk
                        yield {"type": "stream", "content": chunk}
            else:
                # 비스트리밍 클라이언트의 경우 시뮬레이션
                response = client.chat_completion(
                    model=node.model_type,
                    messages=messages,
                    temperature=LLM_CONFIG["default_temperature"]
                )
                full_response = response
                
                chunk_size = LLM_CONFIG["chunk_processing_size"]
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i+chunk_size]
                    yield {"type": "stream", "content": chunk}
                    await asyncio.sleep(LLM_CONFIG["simulation_sleep_interval"])
            
            # 결과 파싱
            if full_response:
                parsed_result = self.result_parser.parse_node_output(full_response)
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": parsed_result.description,
                    "output": parsed_result.output,
                    "execution_time": 0.0
                }
            else:
                raise Exception("Empty LLM response")
                
        except Exception as e:
            yield {
                "type": "result",
                "success": False,
                "error": str(e),
                "description": f"LLM 실행 오류: {str(e)}",
                "output": None
            }
    
    async def _prepare_prompt(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool) -> str:
        """프롬프트 준비"""
        input_data = "\n".join(pre_outputs) if pre_outputs else ""
        prompt_template = node.prompt or ""
        
        # 컨텍스트 검색
        context = ""
        if node.knowledge_base and "{context}" in prompt_template:
            try:
                rerank_info = None
                if rerank_enabled and node.llm_provider and node.model_type:
                    rerank_info = {
                        "provider": node.llm_provider,
                        "model": node.model_type
                    }
                
                context_results = await self.vector_store_service.search(
                    kb_name=node.knowledge_base,
                    query=input_data,
                    search_intensity=node.search_intensity or "medium",
                    rerank_info=rerank_info
                )
                context = "\n".join(context_results) if context_results else "No relevant context found."
            except Exception as e:
                context = f"Context search failed: {str(e)}"
        elif "{context}" in prompt_template:
            context = "No knowledge base selected."
        
        # 프롬프트 변수 치환
        formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
        return formatted_prompt if formatted_prompt.strip() else input_data
    
    async def _call_llm(self, llm_client: Any, model_type: str, prompt: str) -> str:
        """LLM 호출"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: llm_client.generate_response(prompt, model_type)
            )
            return response
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")