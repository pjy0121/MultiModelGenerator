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
                error=f"Node execution failed: {str(e)}"
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
            # input-node: pre_outputs 무시하고 node.content 사용
            current_content = node.content or ""
            print(f"DEBUG: input-node {node.id}, content: '{current_content}'")
        else:
            # output-node: pre_outputs 결합하여 사용
            input_data = " ".join(pre_outputs) if pre_outputs else ""
            current_content = input_data if input_data else (node.content or "")
            print(f"DEBUG: output-node {node.id}, pre_outputs: {pre_outputs}, input_data: '{input_data}', current_content: '{current_content}'")
        
        # 1-3. json 데이터 생성
        json_data = {
            "description": current_content,
            "output": current_content
        }
        
        # 1-4, 1-5. ResultParser 실행
        try:
            parsed_result = self.result_parser.parse_node_output(json.dumps(json_data))
            print(f"DEBUG: 노드 {node.id} 파싱 결과 - description: '{parsed_result.description}', output: '{parsed_result.output}'")
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=parsed_result.description,
                output=parsed_result.output
            )
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Result parsing failed: {str(e)}"
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
            output_format = '{"description": "[UI display content]", "output": "[data for next node]"}'
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
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=parsed_result.description,
                output=parsed_result.output
            )
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"LLM node execution failed: {str(e)}"
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
            search_results = self.vector_store_service.search(query, kb_name, top_k)
            
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