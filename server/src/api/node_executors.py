"""
Node별 실행자 구현 - 간소화된 버전
핵심 기능만 유지하고 불필요한 복잡성 제거
"""

import asyncio
import time
from typing import List, Any, AsyncGenerator

from ..core.models import WorkflowNode, NodeExecutionResult, SearchIntensity
from ..core.output_parser import ResultParser
from ..core.config import LLM_CONFIG
from ..services.llm_factory import LLMFactory
from ..services.vector_store_service import VectorStoreService


class NodeExecutor:
    """노드 실행자 - 모든 노드 타입을 처리"""
    
    def __init__(self):
        self.llm_factory = LLMFactory()
        self.result_parser = ResultParser()
        # VectorStoreService는 필요할 때마다 새로 생성하여 블로킹 방지

    async def execute_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """노드 실행 (레거시 인터페이스)"""
        return await self.execute_node_with_context(node, pre_outputs, [])

    async def execute_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
        """노드 실행 - context-node 출력과 일반 pre-node 출력을 분리해서 처리"""
        try:
            if self._is_text_node(node.type):
                # Text 노드는 일반 pre_outputs만 사용
                return self._execute_text_node(node, pre_outputs)
            elif node.type == "context-node":
                return await self._execute_context_node(node, pre_outputs)
            else:
                # LLM 노드는 context와 input_data를 분리해서 처리
                return await self._execute_llm_node_with_context(node, pre_outputs, context_outputs)
        except Exception as e:
            import traceback
            error_msg = f"Node execution failed: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"[NodeExecutor] Error in node {node.id}: {error_msg}")  # Debug log
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=error_msg,
                execution_time=0.0
            )
    
    async def execute_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """노드 스트리밍 실행 (레거시 인터페이스)"""
        async for chunk in self.execute_node_stream_with_context(node, pre_outputs, []):
            yield chunk

    async def execute_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]):
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
                result = await self._execute_context_node(node, pre_outputs)
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
                async for chunk in self._execute_llm_node_stream_with_context(node, pre_outputs, context_outputs):
                    yield chunk
        except Exception as e:
            import traceback
            error_msg = f"Node execution failed: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"[NodeExecutor Stream] Error in node {node.id}: {error_msg}")  # Debug log
            yield {
                "type": "error",
                "message": error_msg
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
    
    async def _execute_llm_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """LLM 노드 실행 (Generation/Ensemble/Validation)"""
        start_time = time.time()
        
        try:
            prompt = await self._prepare_prompt(node, pre_outputs)
            
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

    async def _execute_llm_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
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
    
    async def _execute_llm_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """LLM 노드 스트리밍 실행"""
        try:
            # LLM 노드에서는 지식베이스 검색을 하지 않음 (context-node에서 처리)
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            prompt_template = node.prompt or ""
            
            # context는 빈 문자열로 처리 (context-node에서 제공받음)
            context = ""
            
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
            
            full_response = ""
            
            # 통합된 스트리밍 인터페이스 사용
            async for chunk in client.generate_stream(
                prompt=prompt,
                model=node.model_type,
                temperature=LLM_CONFIG["default_temperature"]
            ):
                if chunk:
                    full_response += chunk
                    yield {"type": "stream", "content": chunk}
            
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
    
    async def _prepare_prompt(self, node: WorkflowNode, pre_outputs: List[str]) -> str:
        """프롬프트 준비 (비스트리밍) - LLM 노드용, 지식베이스 검색 제거"""
        input_data = "\n".join(pre_outputs) if pre_outputs else ""
        prompt_template = node.prompt or ""
        
        # context는 빈 문자열로 처리 (context-node에서 제공받음)
        context = ""
        
        # 프롬프트 변수 치환
        formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
        return formatted_prompt if formatted_prompt.strip() else input_data

    async def _execute_context_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """
        Context 노드 실행 - 벡터 DB에서 컨텍스트 검색 + 사용자 정의 컨텍스트 추가
        지식베이스가 없을 경우 additional_context만 사용 가능
        """
        start_time = time.time()
        
        try:
            # 입력 데이터 준비 (pre_outputs 결합)
            input_data = " ".join(pre_outputs) if pre_outputs else ""
            
            # 지식베이스 및 검색 강도 확인
            knowledge_base = node.knowledge_base
            search_intensity = node.search_intensity or SearchIntensity.get_default()
            additional_context = node.additional_context or ""
            
            context_parts = []
            total_chunks = 0
            found_chunks = 0
            kb_searched = False  # 지식베이스 검색 수행 여부
            
            # 지식베이스가 설정되어 있고 "none"이 아니면 검색 수행
            if knowledge_base and knowledge_base.lower() != "none":
                kb_searched = True
                if not input_data.strip():
                    return NodeExecutionResult(
                        node_id=node.id,
                        success=False,
                        error="Context search requires input data from pre-nodes",
                        execution_time=time.time() - start_time
                    )
                
                # context-node 자체의 rerank 설정 사용
                rerank_info = None
                if (node.rerank_provider and node.rerank_provider != "none" and node.rerank_model):
                    rerank_info = {
                        "provider": node.rerank_provider,
                        "model": node.rerank_model
                    }
                
                # 벡터 DB 검색 실행
                vector_store_service = VectorStoreService()
                search_result = await vector_store_service.search(
                    kb_name=knowledge_base,
                    query=input_data,
                    search_intensity=search_intensity,
                    rerank_info=rerank_info
                )
                
                context_results = search_result["chunks"]
                total_chunks = search_result["total_chunks"]
                found_chunks = search_result["found_chunks"]
                
                if context_results:
                    # 지식베이스 이름만 출력 앞에 추가 (청크 수 정보는 description에 포함)
                    kb_header = f"=== Knowledge Base: {knowledge_base} ==="
                    kb_content = "\n".join(context_results)
                    context_parts.append(f"{kb_header}\n{kb_content}")
            
            # 추가 컨텍스트가 있으면 추가
            if additional_context.strip():
                context_parts.append(additional_context.strip())
            
            # 최종 컨텍스트 결합
            if not context_parts:
                context_content = "No context available."
                if kb_searched:
                    # 검색은 했지만 결과가 없는 경우
                    description = f"No context found from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    description = "No knowledge base search performed and no additional context provided."
            else:
                context_content = "\n\n".join(context_parts)
                # description에 청크 수 정보 포함
                if kb_searched:
                    kb_info = f" from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    kb_info = ""
                additional_info = " + user-defined context" if additional_context.strip() else ""
                description = f"Context prepared{kb_info}{additional_info}"
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=description,
                output=context_content,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Context preparation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _execute_context_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """
        Context 노드 스트리밍 실행
        지식베이스가 없을 경우 additional_context만 사용 가능
        """
        try:
            # 입력 데이터 준비
            query = "\n".join(pre_outputs) if pre_outputs else ""
            knowledge_base = node.knowledge_base
            additional_context = node.additional_context or ""
            
            context_parts = []
            total_chunks = 0
            found_chunks = 0
            kb_searched = False  # 지식베이스 검색 수행 여부
            
            # 지식베이스가 설정되어 있고 "none"이 아니면 검색 수행
            if knowledge_base and knowledge_base.lower() != "none":
                kb_searched = True
                if not query.strip():
                    yield {"type": "result", "success": False, "error": "No input data for context search"}
                    return
                
                # 검색 시작 알림
                yield {"type": "stream", "content": f"🔍 [{node.id}] 지식 베이스 '{knowledge_base}' 검색 중...\n"}
            
            # rerank 정보 설정
            rerank_info = None
            if (node.rerank_provider and node.rerank_provider != "none" and node.rerank_model):
                rerank_info = {
                    "provider": node.rerank_provider,
                    "model": node.rerank_model
                }
                yield {"type": "stream", "content": f"🔄 [{node.id}] 재정렬 설정됨: {node.rerank_provider}/{node.rerank_model}\n"}
            
            # 지식베이스 검색 수행 (설정되어 있고 "none"이 아닐 경우)
            if kb_searched:
                # 벡터 스토어에서 관련 컨텍스트 검색
                vector_store_service = VectorStoreService()
                search_result = await vector_store_service.search(
                    kb_name=knowledge_base,
                    query=query,
                    search_intensity=node.search_intensity or SearchIntensity.get_default(),
                    rerank_info=rerank_info
                )
                
                context_results = search_result["chunks"]
                total_chunks = search_result["total_chunks"]
                found_chunks = search_result["found_chunks"]
                
                if context_results:
                    # 지식베이스 이름만 출력 앞에 추가 (청크 수 정보는 description과 스트림 메시지에 포함)
                    kb_header = f"=== Knowledge Base: {knowledge_base} ==="
                    kb_content = "\n".join(context_results)
                    context_parts.append(f"{kb_header}\n{kb_content}")
                    yield {"type": "stream", "content": f"✅ [{node.id}] 전체 {total_chunks}개 청크 중 {found_chunks}개의 관련 컨텍스트를 찾았습니다.\n"}
                else:
                    yield {"type": "stream", "content": f"⚠️ [{node.id}] 지식베이스 (전체 {total_chunks}개 청크)에서 관련 컨텍스트를 찾지 못했습니다.\n"}
            
            # 추가 컨텍스트가 있으면 추가
            if additional_context.strip():
                additional_header = "=== Additional Context ==="
                context_parts.append(f"{additional_header}\n{additional_context.strip()}")
                yield {"type": "stream", "content": f"📝 [{node.id}] 사용자 정의 컨텍스트가 추가되었습니다.\n"}
            
            # 최종 컨텍스트 결합
            if not context_parts:
                yield {"type": "stream", "content": f"⚠️ [{node.id}] 사용 가능한 컨텍스트가 없습니다.\n"}
                if kb_searched:
                    description = f"No context found from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    description = "No context available"
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": description,
                    "output": "No context available.",
                    "execution_time": 0.0
                }
            else:
                context_content = "\n\n".join(context_parts)
                # description에 청크 수 정보 포함
                if kb_searched:
                    kb_info = f" from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks)"
                else:
                    kb_info = ""
                additional_info = " + user-defined" if additional_context.strip() else ""
                description = f"Context prepared{kb_info}{additional_info}"
                
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": description,
                    "output": context_content,
                    "execution_time": 0.0
                }
        except Exception as e:
            yield {"type": "result", "success": False, "error": f"Context search failed: {str(e)}"}
    
    async def _call_llm(self, llm_client: Any, model_type: str, prompt: str) -> str:
        """LLM 호출 - 스트리밍 인터페이스를 사용하여 전체 응답 수집"""
        try:
            # 스트리밍으로 전체 응답 수집
            full_response = ""
            async for chunk in llm_client.generate_stream(
                prompt=prompt,
                model=model_type,
                temperature=0.3
            ):
                if chunk:
                    full_response += chunk
            
            if not full_response.strip():
                raise Exception("Empty response from LLM")
                
            return full_response
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    async def _execute_llm_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]):
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
            
            full_response = ""
            
            # 통합된 스트리밍 인터페이스 사용
            async for chunk in client.generate_stream(
                prompt=prompt,
                model=node.model_type,
                temperature=LLM_CONFIG["default_temperature"]
            ):
                if chunk:
                    full_response += chunk
                    yield {"type": "stream", "content": chunk}
            
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