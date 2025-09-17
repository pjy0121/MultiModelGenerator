"""
Node별 실행자 구현 - project_reference.md 기준
"""

import json
import asyncio
from typing import List, Optional, Dict, Any

from ..core.models import (
    WorkflowNode, NodeType, NodeExecutionResult, ParsedNodeOutput
)
from ..core.output_parser import ResultParser
from ..services.llm_factory import LLMFactory
from ..services.vector_store import VectorStoreService

class NodeExecutor:
    """노드별 실행 로직을 담당하는 클래스"""
    
    def __init__(self):
        self.llm_factory = LLMFactory()
        self.vector_store_service = VectorStoreService()
        self.result_parser = ResultParser()
    
    async def execute_node(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ) -> NodeExecutionResult:
        """노드 타입에 따른 실행 분기"""
        
        try:
            if node.type in ["input-node", "output-node"]:
                return await self._execute_text_node(node, pre_outputs)
            else:
                return await self._execute_llm_node(
                    node, pre_outputs, knowledge_base, search_intensity
                )
        
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Node execution failed: {str(e)}",
                execution_time=0.0
            )
    
    async def _execute_text_node(
        self, 
        node: WorkflowNode, 
        pre_outputs: List[str]
    ) -> NodeExecutionResult:
        """
        input-node, output-node 실행
        project_reference.md 1-1 ~ 1-5 기준
        """
        
        # input-node와 output-node 구분 처리
        if node.type == "input-node":
            # input-node: pre_outputs 무시하고 node.content 사용 (파싱 불필요)
            current_content = node.content or ""
            
            # input-node의 content가 비어있는 경우 처리
            if not current_content.strip():
                current_content = f"입력 데이터가 설정되지 않았습니다."
            
            # input-node는 파싱하지 않고 content를 그대로 사용
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=current_content,  # content를 description에 저장
                output=current_content,       # output도 동일하게 저장
                execution_time=0.0           # input-node는 즉시 실행되므로 0.0
            )
        else:
            # output-node: pre_outputs 결합하여 사용 (파싱 불필요)
            input_data = " ".join(pre_outputs) if pre_outputs else ""
            final_output = input_data if input_data else (node.content or "")
            
            # output-node는 파싱하지 않고 이전 노드의 output을 그대로 사용
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=final_output,  # 이전 노드의 output을 description에 저장
                output=final_output,       # output도 동일하게 저장
                execution_time=0.0         # output-node는 즉시 실행되므로 0.0
            )
    
    async def _execute_llm_node(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str],
        search_intensity: int
    ) -> NodeExecutionResult:
        """
        generation-node, ensemble-node, validation-node 실행
        project_reference.md 2-1 ~ 2-8 기준
        """
        import time
        start_time = time.time()
        
        try:
            # 2-2. inputs 연결하여 input_data 생성
            input_data = " ".join(pre_outputs) if pre_outputs else ""
            
            # 2-3. 프롬프트에서 {input_data} 치환
            prompt = node.prompt or ""
            prompt = prompt.replace('{input_data}', input_data)
            
            # 2-4. knowledge_base 검색 및 {context} 치환 (프롬프트에 {context}가 있을 때만)
            if knowledge_base and '{context}' in prompt:
                try:
                    # 2-4-1. intensity에 따른 top_k 결정
                    top_k = max(5, min(search_intensity, 50))  # 5~50 범위로 확장
                    
                    # 2-4-2. VectorDB 검색
                    search_results = await self._search_knowledge_base(
                        knowledge_base, input_data, top_k
                    )
                    
                    # 2-4-3. {context} 치환
                    context = "\n".join(search_results) if search_results else "No relevant context found."
                    prompt = prompt.replace('{context}', context)
                
                except Exception as e:
                    # 검색 실패시 빈 컨텍스트로 처리
                    prompt = prompt.replace('{context}', f"Context search failed: {str(e)}")
            elif '{context}' in prompt:
                # 지식베이스는 없지만 프롬프트에 {context}가 있는 경우 빈 컨텍스트로 처리
                prompt = prompt.replace('{context}', "No knowledge base selected.")
            
            # 2-5. {output_format} 치환
            output_format = '''마크다운으로 자유롭게 작성하되, 다음 노드로 전달할 핵심 내용은 <output> 태그 안에 작성하세요:

<output>
다음 노드로 전달될 내용
</output>'''
            prompt = prompt.replace('{output_format}', output_format)
            
            # 2-6. LLM API 호출
            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            llm_client = self.llm_factory.get_client(node.llm_provider)
            llm_response = await self._call_llm_async(
                llm_client, node.model_type, prompt
            )
            
            # 2-7, 2-8. ResultParser 실행
            parsed_result = self.result_parser.parse_node_output(llm_response)
            
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
    
    async def _search_knowledge_base(
        self, 
        kb_name: str, 
        query: str, 
        top_k: int
    ) -> List[str]:
        """지식베이스 검색 (비동기)"""
        
        try:
            # VectorStoreService 사용 (search 메서드는 동기)
            search_results = self.vector_store_service.search(
                query=query, 
                collection_name=kb_name, 
                top_k=top_k
            )
            
            # 검색 결과에서 content 추출
            return [result["content"] for result in search_results]
            
        except Exception as e:
            raise Exception(f"Knowledge base search failed: {str(e)}")
    
    async def _call_llm_async(
        self, 
        llm_client: Any, 
        model_type: str, 
        prompt: str
    ) -> str:
        """LLM 호출 (비동기)"""
        
        try:
            # 기존 LLM 팩토리의 호출 방식에 맞게 수정
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: llm_client.generate_response(prompt, model_type)
            )
            
            return response
                
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    async def execute_node_stream(
        self,
        node: WorkflowNode,
        workflow,
        node_outputs: Dict[str, str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ):
        """노드 스트리밍 실행"""
        
        try:
            # pre-node 출력들 수집
            pre_outputs = []
            for edge in workflow.edges:
                if edge.target == node.id and edge.source in node_outputs:
                    pre_outputs.append(node_outputs[edge.source])
            
            if node.type in ["input-node", "output-node"]:
                # 텍스트 노드는 즉시 결과 반환 (스트리밍 없음)
                import time
                start_time = time.time()
                result = await self._execute_text_node(node, pre_outputs)
                execution_time = time.time() - start_time
                
                if result.success:
                    yield {
                        "type": "result", 
                        "success": True, 
                        "output": result.output,
                        "description": result.description,
                        "execution_time": execution_time
                    }
                else:
                    raise Exception(result.error)
            else:
                # LLM 노드는 스트리밍 실행
                async for chunk in self._execute_llm_node_stream(
                    node, pre_outputs, knowledge_base, search_intensity
                ):
                    yield chunk
                    
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Node execution failed: {str(e)}"
            }
    
    async def _execute_llm_node_stream(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ):
        """LLM 노드 스트리밍 실행"""
        
        try:
            # 입력 데이터 준비
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            
            # 컨텍스트 검색 (필요한 경우)
            context = ""
            if knowledge_base and "{context}" in (node.prompt or ""):
                try:
                    context_results = self.vector_store_service.search(
                        query=input_data,
                        collection_name=knowledge_base,
                        top_k=search_intensity
                    )
                    context = "\n".join([result["content"] for result in context_results])
                except Exception as e:
                    print(f"Context search failed: {e}")
            
            # 프롬프트 준비
            prompt = node.prompt or ""
            formatted_prompt = prompt.replace("{input_data}", input_data).replace("{context}", context)
            
            if not formatted_prompt.strip():
                formatted_prompt = input_data  # 프롬프트가 없으면 입력 데이터를 그대로 사용
            
            # LLM 클라이언트 가져오기
            client = self.llm_factory.get_client(node.llm_provider)
            if not client or not client.is_available():
                raise Exception(f"LLM client not available: {node.llm_provider}")
            
            # 스트리밍 LLM 호출
            messages = [{"role": "user", "content": formatted_prompt}]
            full_response = ""
            
            # 스트리밍 채팅 완성 (클라이언트가 지원하는 경우)
            if hasattr(client, 'chat_completion_stream'):
                async for chunk in client.chat_completion_stream(
                    model=node.model_type,
                    messages=messages,
                    temperature=0.1
                ):
                    if chunk:
                        full_response += chunk
                        yield {
                            "type": "stream",
                            "content": chunk
                        }
            else:
                # 스트리밍을 지원하지 않는 경우 일반 호출
                response = client.chat_completion(
                    model=node.model_type,
                    messages=messages,
                    temperature=0.1
                )
                full_response = response
                
                # 응답을 청크 단위로 시뮬레이션
                chunk_size = 10
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i+chunk_size]
                    yield {
                        "type": "stream",
                        "content": chunk
                    }
                    await asyncio.sleep(0.1)  # 스트리밍 시뮬레이션
            
            # 결과 파싱
            try:
                if not full_response:
                    raise Exception("Empty LLM response")
                
                parsed_result = self.result_parser.parse_node_output(full_response)
                
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": parsed_result.description,
                    "output": parsed_result.output,  # <output> 태그 안의 내용만
                    "execution_time": 0.0
                }
            except Exception as e:
                yield {
                    "type": "parsed_result", 
                    "success": False,
                    "error": f"Parsing failed: {str(e)}",
                    "description": f"오류: {str(e)}",
                    "output": None,
                    "execution_time": 0.0
                }
            
        except Exception as e:
            error_msg = str(e)
            
            # API 할당량 오류인지 확인
            if "quota" in error_msg.lower() or "429" in error_msg:
                error_msg = f"API 할당량 초과: {error_msg}"
            
            yield {
                "type": "result",
                "success": False,
                "error": error_msg,
                "description": f"LLM 실행 오류: {error_msg}",
                "output": None
            }


class InputNodeExecutor(NodeExecutor):
    """input-node 전용 실행자"""
    
    async def execute(
        self, 
        node: WorkflowNode, 
        pre_outputs: List[str] = None
    ) -> NodeExecutionResult:
        return await self._execute_text_node(node, pre_outputs or [])


class OutputNodeExecutor(NodeExecutor):
    """output-node 전용 실행자"""
    
    async def execute(
        self, 
        node: WorkflowNode, 
        pre_outputs: List[str]
    ) -> NodeExecutionResult:
        return await self._execute_text_node(node, pre_outputs)


class GenerationNodeExecutor(NodeExecutor):
    """generation-node 전용 실행자"""
    
    async def execute(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ) -> NodeExecutionResult:
        return await self._execute_llm_node(
            node, pre_outputs, knowledge_base, search_intensity
        )


class EnsembleNodeExecutor(NodeExecutor):
    """ensemble-node 전용 실행자"""
    
    async def execute(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ) -> NodeExecutionResult:
        return await self._execute_llm_node(
            node, pre_outputs, knowledge_base, search_intensity
        )


class ValidationNodeExecutor(NodeExecutor):
    """validation-node 전용 실행자"""
    
    async def execute(
        self,
        node: WorkflowNode,
        pre_outputs: List[str],
        knowledge_base: Optional[str] = None,
        search_intensity: int = 5
    ) -> NodeExecutionResult:
        return await self._execute_llm_node(
            node, pre_outputs, knowledge_base, search_intensity
        )
    
