"""
LangChain Chain 기반 레이어 실행 로직
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.base import Runnable

from ..services.langchain_llm_factory import LangChainLLMFactory
from ..services.vector_store import VectorStore
from ..core.default_prompts import DEFAULT_LAYER_PROMPTS
from src.langchain_parsers.output_parsers import (
    LayerOutputParser, 
    LayerOutput,
    get_layer_prompt_template
)

logger = logging.getLogger(__name__)

# 상수 정의
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TOP_K = 15


class LayerChainExecutor:
    """LangChain Chain을 사용한 레이어 실행기"""
    
    def __init__(self):
        self.llm_factory = LangChainLLMFactory
        self.str_parser = StrOutputParser()
    
    def _create_context_retriever(self, knowledge_base: str, top_k: int = DEFAULT_TOP_K) -> RunnableLambda:
        """컨텍스트 검색을 위한 Runnable 생성"""
        def retrieve_context(input_data: Dict[str, Any]) -> Dict[str, Any]:
            """입력으로부터 관련 컨텍스트 검색"""
            query = input_data.get("layer_input", "")
            if not query:
                return {**input_data, "context": ""}
            
            try:
                vector_store = VectorStore(knowledge_base)
                chunks = vector_store.search_similar_chunks(query, top_k=top_k)
                context = "\n\n".join(chunks) if chunks else ""
                logger.info(f"컨텍스트 검색 완료: {len(chunks)}개 청크")
                return {**input_data, "context": context}
            except Exception as e:
                logger.error(f"컨텍스트 검색 실패: {e}")
                return {**input_data, "context": ""}
        
        return RunnableLambda(retrieve_context)
    
    def _create_chain(self, node: Dict[str, Any], knowledge_base: str, layer_type: str) -> Runnable:
        """레이어 타입에 따른 통합 체인 생성"""
        # 레이어 타입에 따른 프롬프트 선택
        prompt_mapping = {
            "requirement": "generation",
            "ensemble": "ensemble", 
            "validation": "validation"
        }
        
        prompt_key = prompt_mapping.get(layer_type)
        if not prompt_key:
            raise ValueError(f"지원하지 않는 레이어 타입: {layer_type}")
        
        # 프롬프트 템플릿 생성
        prompt_template = ChatPromptTemplate.from_template(DEFAULT_LAYER_PROMPTS[prompt_key])
        
        # LLM 선택
        try:
            llm = self.llm_factory.get_llm_by_model_id(node.get("model", DEFAULT_MODEL))
        except Exception as e:
            logger.error(f"LLM 초기화 실패 ({layer_type}): {e}")
            raise
        
        # 체인 구성
        context_retriever = self._create_context_retriever(knowledge_base)
        output_parser = self.str_parser
        
        chain = (
            context_retriever
            | prompt_template
            | llm
            | output_parser
        )
        
        return chain
    
    def execute_node_with_chain(
        self, 
        node: Dict[str, Any], 
        layer_input: str, 
        knowledge_base: str,
        layer_type: str = "requirement"
    ) -> str:
        """체인을 사용한 노드 실행 - 문자열 결과 반환"""
        
        try:
            # 통합된 체인 생성 함수 사용
            chain = self._create_chain(node, knowledge_base, layer_type)
            
            # 입력 데이터 준비
            input_data = {
                "input_data": layer_input,
                "layer_input": layer_input,  # 호환성
                "node_prompt": node.get("prompt", "")
            }
            
            # 체인 실행
            logger.info(f"체인 실행 시작: {layer_type} 레이어, 노드 {node.get('id', 'unknown')}")
            result = chain.invoke(input_data)
            
            logger.info(f"체인 실행 완료: {node.get('id', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"체인 실행 실패: {e}")
            # 기본 출력 반환
            return f"체인 실행 실패: {str(e)}"


class ChainBasedLayerExecutors:
    """Chain 기반 레이어 실행기들"""
    
    def __init__(self):
        self.chain_executor = LayerChainExecutor()
    
    def execute_generation_layer_with_chains(
        self, 
        nodes: List[Dict[str, Any]], 
        layer_input: str, 
        knowledge_base: str
    ) -> Dict[str, Any]:
        """Chain 기반 Generation Layer 실행"""
        logger.info(f"Chain 기반 Generation Layer 실행: {len(nodes)}개 노드")
        
        result = {}
        forward_data_list = []
        
        for node in nodes:
            try:
                # Chain으로 노드 실행
                chain_output = self.chain_executor.execute_node_with_chain(
                    node, layer_input, knowledge_base, "requirement"
                )
                
                # 결과 저장
                result[f"node{node.get('id', 'unknown')}"] = chain_output
                
                # forward_data 생성 (전체 텍스트 사용)
                try:
                    import json
                    parsed = json.loads(chain_output)
                    if "requirements" in parsed:
                        forward_data = f"Requirements: {', '.join(parsed['requirements'][:3])}"
                    else:
                        forward_data = parsed.get("content", chain_output)
                except:
                    forward_data = chain_output
                
                forward_data_list.append(forward_data)
                logger.info(f"노드 {node.get('id', 'unknown')} Chain 실행 완료")
                
            except Exception as e:
                logger.error(f"노드 {node.get('id', 'unknown')} Chain 실행 실패: {e}")
                result[f"node{node.get('id', 'unknown')}"] = f"실행 실패: {str(e)}"
        
        # forward_data 결합
        result["forward_data"] = "\n\n".join(forward_data_list)
        
        logger.info(f"Generation Layer Chain 실행 완료: {len(forward_data_list)}개 결과")
        return result
    
    def execute_ensemble_layer_with_chains(
        self, 
        nodes: List[Dict[str, Any]], 
        layer_input: str, 
        knowledge_base: str
    ) -> Dict[str, Any]:
        """Chain 기반 Ensemble Layer 실행"""
        logger.info(f"Chain 기반 Ensemble Layer 실행: {len(nodes)}개 노드")
        
        result = {}
        forward_data_list = []
        
        for node in nodes:
            try:
                # Chain으로 노드 실행
                chain_output = self.chain_executor.execute_node_with_chain(
                    node, layer_input, knowledge_base, "ensemble"
                )
                
                # 결과 저장
                result[f"node{node.get('id', 'unknown')}"] = chain_output
                
                # forward_data 생성
                try:
                    import json
                    parsed = json.loads(chain_output)
                    if "final_decision" in parsed:
                        forward_data = f"Decision: {parsed['final_decision']}"
                    else:
                        forward_data = parsed.get("content", chain_output)
                except:
                    forward_data = chain_output
                
                forward_data_list.append(forward_data)
                logger.info(f"노드 {node.get('id', 'unknown')} Chain 실행 완료")
                
            except Exception as e:
                logger.error(f"노드 {node.get('id', 'unknown')} Chain 실행 실패: {e}")
                result[f"node{node.get('id', 'unknown')}"] = f"실행 실패: {str(e)}"
        
        result["forward_data"] = "\n\n".join(forward_data_list)
        
        logger.info(f"Ensemble Layer Chain 실행 완료")
        return result
    
    def execute_validation_layer_with_chains(
        self, 
        nodes: List[Dict[str, Any]], 
        layer_input: str, 
        knowledge_base: str
    ) -> Dict[str, Any]:
        """Chain 기반 Validation Layer 실행"""
        logger.info(f"Chain 기반 Validation Layer 실행: {len(nodes)}개 노드")
        
        result = {}
        current_input = layer_input  # 현재 노드의 입력 (순차적으로 업데이트됨)
        
        # 순차 실행 (validation은 순서 중요)
        for i, node in enumerate(nodes):
            try:
                # Chain으로 노드 실행 (이전 노드의 결과를 다음 노드의 입력으로 사용)
                chain_output = self.chain_executor.execute_node_with_chain(
                    node, current_input, knowledge_base, "validation"
                )
                
                # 결과 저장
                result[f"node{node.get('id', 'unknown')}"] = chain_output
                
                # forward_data 추출 및 다음 노드의 입력으로 설정
                try:
                    import json
                    parsed = json.loads(chain_output)
                    forward_data = parsed.get("forward_data", chain_output)
                    
                    # 다음 노드를 위해 현재 결과를 입력으로 설정
                    current_input = forward_data
                    
                except:
                    # JSON 파싱 실패 시 전체 결과를 다음 입력으로 사용
                    current_input = chain_output
                
                logger.info(f"노드 {node.get('id', 'unknown')} Chain 실행 완료 (노드 {i+1}/{len(nodes)})")
                
            except Exception as e:
                logger.error(f"노드 {node.get('id', 'unknown')} Chain 실행 실패: {e}")
                result[f"node{node.get('id', 'unknown')}"] = f"실행 실패: {str(e)}"
        
        # 최종 결과는 마지막 노드의 forward_data
        result["forward_data"] = current_input
        
        logger.info(f"Validation Layer Chain 실행 완료")
        return result