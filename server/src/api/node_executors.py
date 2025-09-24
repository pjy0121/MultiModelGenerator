"""
Node별 실행자 구현 - 간소화된 버전
핵심 기능만 유지하고 불필요한 복잡성 제거
"""

import asyncio
import time
from typing import List, Any, AsyncGenerator

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
        """노드 실행 (레거시 인터페이스)"""
        return await self.execute_node_with_context(node, pre_outputs, [], rerank_enabled)

    async def execute_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str], rerank_enabled: bool) -> NodeExecutionResult:
        """노드 실행 - context-node 출력과 일반 pre-node 출력을 분리해서 처리"""
        try:
            if self._is_text_node(node.type):
                # Text 노드는 일반 pre_outputs만 사용
                return self._execute_text_node(node, pre_outputs)
            elif node.type == "context-node":
                return await self._execute_context_node(node, pre_outputs, rerank_enabled)
            else:
                # LLM 노드는 context와 input_data를 분리해서 처리
                return await self._execute_llm_node_with_context(node, pre_outputs, context_outputs, rerank_enabled)
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Node execution failed: {str(e)}",
                execution_time=0.0
            )
    
    async def execute_node_stream(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool):
        """노드 스트리밍 실행 (레거시 인터페이스)"""
        async for chunk in self.execute_node_stream_with_context(node, pre_outputs, [], rerank_enabled):
            yield chunk

    async def execute_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str], rerank_enabled: bool):
        """노드 스트리밍 실행 - context-node 출력과 일반 pre-node 출력을 분리해서 처리"""
        try:
            if self._is_text_node(node.type):
                # 텍스트 노드는 즉시 결과 반환
                result = self._execute_text_node(node, pre_outputs)
                yield {
                    "type": "result",
                    "success": result.success,
                    "output": result.output,
                    "description": result.description,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
            elif node.type == "context-node":
                # 컨텍스트 노드는 즉시 결과 반환
                result = await self._execute_context_node(node, pre_outputs, rerank_enabled)
                yield {
                    "type": "result", 
                    "success": result.success,
                    "output": result.output,
                    "description": result.description,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
            else:
                # LLM 노드는 context와 input_data를 분리해서 처리
                async for chunk in self._execute_llm_node_stream_with_context(node, pre_outputs, context_outputs, rerank_enabled):
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
            if pre_outputs:
                # pre_outputs에서 <output> 태그가 있는지 확인하고 파싱 시도
                combined_content = "\n".join(pre_outputs)
                try:
                    # output parsing 시도
                    parsed_result = self.result_parser.parse_node_output(combined_content)
                    content = parsed_result.output
                except:
                    # 파싱 실패 시 원본 사용
                    content = combined_content
            else:
                content = node.content or ""

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

    async def _execute_llm_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str], rerank_enabled: bool) -> NodeExecutionResult:
        """LLM 노드 실행 - context와 input_data를 분리해서 처리"""
        start_time = time.time()
        
        try:
            # input_data는 일반 pre-node 출력들만 사용
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            # context는 context-node 출력들 사용
            context = "\n".join(context_outputs) if context_outputs else ""
            
            prompt_template = node.prompt or ""
            
            # 프롬프트 변수 치환
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data
            
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
            # 지식 베이스 검색 과정 스트리밍
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            prompt_template = node.prompt or ""
            
            # 컨텍스트 검색 과정을 스트리밍으로 보여주기
            context = ""
            if node.knowledge_base and "{context}" in prompt_template:
                import time
                search_start = time.time()
                yield {"type": "stream", "content": f"🔍 [{node.id}] 지식 베이스 '{node.knowledge_base}' 검색 시작...\n"}
                
                try:
                    rerank_info = None
                    if rerank_enabled and node.llm_provider and node.model_type:
                        rerank_info = {"provider": node.llm_provider, "model": node.model_type}
                        yield {"type": "stream", "content": f"🔄 [{node.id}] 리랭킹 활성화됨 ({node.llm_provider}/{node.model_type})\n"}
                    
                    # 검색을 별도 태스크로 실행하여 병렬 처리 보장
                    search_task = asyncio.create_task(
                        self.vector_store_service.search(
                            kb_name=node.knowledge_base,
                            query=input_data,
                            search_intensity=node.search_intensity or "medium",
                            rerank_info=rerank_info
                        )
                    )
                    context_results = await search_task
                    
                    search_time = time.time() - search_start
                    
                    if context_results:
                        context = "\n".join(context_results)
                        yield {"type": "stream", "content": f"✅ [{node.id}] {len(context_results)}개 문서 찾음 ({search_time:.2f}초)\n"}
                    else:
                        context = "No relevant context found."
                        yield {"type": "stream", "content": f"⚠️ [{node.id}] 관련 문서 없음 ({search_time:.2f}초)\n"}
                        
                except Exception as e:
                    search_time = time.time() - search_start
                    context = f"Context search failed: {str(e)}"
                    yield {"type": "stream", "content": f"❌ [{node.id}] 검색 실패: {str(e)} ({search_time:.2f}초)\n"}
                    
            elif "{context}" in prompt_template:
                context = "No knowledge base selected."
                yield {"type": "stream", "content": f"⚠️ [{node.id}] 지식 베이스가 선택되지 않았습니다.\n"}
            
            # LLM 실행 시작 알림
            yield {"type": "stream", "content": f"🤖 [{node.id}] {node.llm_provider}/{node.model_type} 모델 실행 중...\n\n"}
            
            # 프롬프트 변수 치환
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data

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
        """프롬프트 준비 (비스트리밍)"""
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

    async def _execute_context_node(self, node: WorkflowNode, pre_outputs: List[str], rerank_enabled: bool) -> NodeExecutionResult:
        """Context 노드 실행 - 벡터 DB에서 컨텍스트 검색"""
        start_time = time.time()
        
        try:
            # 입력 데이터 준비 (pre_outputs 결합)
            input_data = " ".join(pre_outputs) if pre_outputs else ""
            if not input_data.strip():
                return NodeExecutionResult(
                    node_id=node.id,
                    success=False,
                    error="Context search requires input data from pre-nodes",
                    execution_time=time.time() - start_time
                )
            
            # 지식베이스 및 검색 강도 확인
            knowledge_base = node.knowledge_base
            search_intensity = node.search_intensity or "medium"
            
            if not knowledge_base:
                return NodeExecutionResult(
                    node_id=node.id,
                    success=False,
                    error="Knowledge base not specified for context node",
                    execution_time=time.time() - start_time
                )
            
            # 리랭크 설정
            rerank_info = None
            if rerank_enabled:
                rerank_info = {
                    "provider": LLM_CONFIG.get("default_provider", "google"),
                    "model": LLM_CONFIG.get("default_model", "gemini-2.0-flash")
                }
            
            # 벡터 DB 검색 실행
            context_results = await self.vector_store_service.search(
                kb_name=knowledge_base,
                query=input_data,
                search_intensity=search_intensity,
                rerank_info=rerank_info
            )
            
            context_content = "\n".join(context_results) if context_results else "No relevant context found."
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=f"Found {len(context_results)} relevant context chunks from knowledge base '{knowledge_base}'",
                output=context_content,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Context search failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _execute_context_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """Context 노드 스트리밍 실행"""
        try:
            # 입력 데이터 준비
            query = "\n".join(pre_outputs) if pre_outputs else ""
            
            if not query.strip():
                yield {"type": "result", "success": False, "error": "No input data for context search"}
                return
            
            if not node.knowledge_base:
                yield {"type": "result", "success": False, "error": "No knowledge base selected"}
                return
            
            # 검색 시작 알림
            yield {"type": "stream", "content": f"🔍 [{node.id}] 지식 베이스 '{node.knowledge_base}' 검색 중...\n"}
            
            # 벡터 스토어에서 관련 컨텍스트 검색
            context_results = await self.vector_store_service.search(
                kb_name=node.knowledge_base,
                query=query,
                search_intensity=node.search_intensity or "medium",
                rerank_info=None
            )
            
            if context_results:
                context_content = "\n".join(context_results)
                yield {"type": "stream", "content": f"✅ [{node.id}] {len(context_results)}개의 관련 컨텍스트를 찾았습니다.\n"}
                
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": f"Found {len(context_results)} relevant context chunks from knowledge base '{node.knowledge_base}'",
                    "output": context_content,
                    "execution_time": 0.0
                }
            else:
                yield {"type": "stream", "content": f"⚠️ [{node.id}] 관련 컨텍스트를 찾지 못했습니다.\n"}
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": "No relevant context found",
                    "output": "",
                    "execution_time": 0.0
                }
        except Exception as e:
            yield {"type": "result", "success": False, "error": f"Context search failed: {str(e)}"}
    
    async def _call_llm(self, llm_client: Any, model_type: str, prompt: str) -> str:
        """LLM 호출"""
        try:
            # generate_response가 async 메서드인 경우 직접 호출
            if hasattr(llm_client, 'generate_response'):
                response = await llm_client.generate_response(prompt, model_type)
                return response
            else:
                # 동기 클라이언트의 경우 executor 사용
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: llm_client.generate_response(prompt, model_type)
                )
                return response
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    async def _execute_llm_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str], rerank_enabled: bool):
        """LLM 노드 스트리밍 실행 - context와 input_data를 분리해서 처리"""
        try:
            # input_data는 일반 pre-node 출력들만 사용
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            # context는 context-node 출력들 사용
            context = "\n".join(context_outputs) if context_outputs else ""
            
            prompt_template = node.prompt or ""
            
            # 스트리밍 시작 알림
            yield {"type": "stream", "content": f"🤖 [{node.id}] Context-aware 실행: {node.llm_provider}/{node.model_type}\n"}
            
            # 프롬프트 변수 치환
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data

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
                yield {"type": "result", "success": False, "error": "No response received"}
                
        except Exception as e:
            yield {"type": "result", "success": False, "error": str(e)}