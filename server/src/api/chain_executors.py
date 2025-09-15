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
from src.langchain_parsers.output_parsers import (
    LayerOutputParser, 
    LayerOutput,
    get_layer_prompt_template
)

logger = logging.getLogger(__name__)

# 상수 정의
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TOP_K = 15
DEFAULT_MAX_EXCERPT_LENGTH = 100


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
    
    def _create_requirements_chain(self, node: Dict[str, Any], knowledge_base: str) -> Runnable:
        """요구사항 생성 체인 생성"""
        # 프롬프트 템플릿 (직접 문자열 사용)
        prompt_template = ChatPromptTemplate.from_template("""
다음 컨텍스트와 입력을 기반으로 요구사항을 생성하세요.

컨텍스트:
{context}

입력 데이터:
{input_data}

노드 프롬프트:
{node_prompt}

응답은 다음 JSON 형식으로 제공하세요:
{{
    "content": "요구사항 분석에 대한 상세한 설명",
    "requirements": ["요구사항1", "요구사항2", "요구사항3"],
    "confidence_score": 0.85
}}
""")
        
        # LLM 선택
        try:
            llm = self.llm_factory.get_llm_by_model_id(node.get("model", DEFAULT_MODEL))
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            raise
        
        # 출력 파서 (문자열만 반환)
        output_parser = self.str_parser
        
        # 체인 구성
        context_retriever = self._create_context_retriever(knowledge_base)
        
        chain = (
            context_retriever
            | prompt_template
            | llm
            | output_parser
        )
        
        return chain
    
    def _create_ensemble_chain(self, node: Dict[str, Any], knowledge_base: str) -> Runnable:
        """앙상블 레이어 체인 생성"""
        prompt_template = ChatPromptTemplate.from_template("""
여러 관점을 고려하여 최종 의사결정을 내리세요.

컨텍스트:
{context}

입력 데이터 (이전 결정들):
{input_data}

노드 프롬프트:
{node_prompt}

응답은 다음 JSON 형식으로 제공하세요:
{{
    "content": "의사결정 과정에 대한 상세한 설명",
    "decisions": [
        {{"perspective": "관점1", "decision": "결정1", "reasoning": "근거1"}},
        {{"perspective": "관점2", "decision": "결정2", "reasoning": "근거2"}}
    ],
    "final_decision": "최종 합의된 결정",
    "confidence_score": 0.9
}}
""")
        
        try:
            llm = self.llm_factory.get_llm_by_model_id(node.get("model", DEFAULT_MODEL))
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            raise
        
        output_parser = self.str_parser
        context_retriever = self._create_context_retriever(knowledge_base)
        
        chain = (
            context_retriever
            | prompt_template
            | llm
            | output_parser
        )
        
        return chain
    
    def _create_validation_chain(self, node: Dict[str, Any], knowledge_base: str) -> Runnable:
        """검증 레이어 체인 생성"""
        prompt_template = ChatPromptTemplate.from_template("""
주어진 요구사항이나 결정을 검증하세요.

컨텍스트:
{context}

검증할 항목들:
{input_data}

노드 프롬프트:
{node_prompt}

응답은 다음 JSON 형식으로 제공하세요:
{{
    "content": "검증 과정에 대한 상세한 설명",
    "validation_results": [
        {{"criterion": "기준1", "status": "pass", "reason": "통과 이유"}},
        {{"criterion": "기준2", "status": "fail", "reason": "실패 이유"}}
    ],
    "overall_valid": true,
    "confidence_score": 0.8
}}
""")
        
        try:
            llm = self.llm_factory.get_llm_by_model_id(node.get("model", DEFAULT_MODEL))
        except Exception as e:
            logger.error(f"LLM 초기화 실패: {e}")
            raise
        
        output_parser = self.str_parser
        context_retriever = self._create_context_retriever(knowledge_base)
        
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
            # 레이어 타입에 따른 체인 선택
            if layer_type == "requirement":
                chain = self._create_requirements_chain(node, knowledge_base)
            elif layer_type == "ensemble":
                chain = self._create_ensemble_chain(node, knowledge_base)
            elif layer_type == "validation":
                chain = self._create_validation_chain(node, knowledge_base)
            else:
                raise ValueError(f"지원하지 않는 레이어 타입: {layer_type}")
            
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
                
                # forward_data 생성 (JSON에서 추출하거나 첫 100자 사용)
                try:
                    import json
                    parsed = json.loads(chain_output)
                    if "requirements" in parsed:
                        forward_data = f"Requirements: {', '.join(parsed['requirements'][:3])}"
                    else:
                        forward_data = parsed.get("content", chain_output)[:DEFAULT_MAX_EXCERPT_LENGTH]
                except:
                    forward_data = chain_output[:DEFAULT_MAX_EXCERPT_LENGTH]
                
                forward_data_list.append(forward_data)
                logger.info(f"노드 {node.id} Chain 실행 완료")
                
            except Exception as e:
                logger.error(f"노드 {node.id} Chain 실행 실패: {e}")
                result[f"node{node.id}"] = f"실행 실패: {str(e)}"
        
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
                        forward_data = parsed.get("content", chain_output)[:DEFAULT_MAX_EXCERPT_LENGTH]
                except:
                    forward_data = chain_output[:DEFAULT_MAX_EXCERPT_LENGTH]
                
                forward_data_list.append(forward_data)
                logger.info(f"노드 {node.id} Chain 실행 완료")
                
            except Exception as e:
                logger.error(f"노드 {node.id} Chain 실행 실패: {e}")
                result[f"node{node.id}"] = f"실행 실패: {str(e)}"
        
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
        final_forward_data = ""
        
        # 순차 실행 (validation은 순서 중요)
        for node in nodes:
            try:
                # Chain으로 노드 실행
                chain_output = self.chain_executor.execute_node_with_chain(
                    node, layer_input, knowledge_base, "validation"
                )
                
                # 결과 저장
                result[f"node{node.get('id', 'unknown')}"] = chain_output
                
                # forward_data 업데이트 (덮어쓰기)
                try:
                    import json
                    parsed = json.loads(chain_output)
                    if "overall_valid" in parsed:
                        status = "PASS" if parsed["overall_valid"] else "FAIL"
                        final_forward_data = f"Validation: {status} - {parsed.get('content', '')[:DEFAULT_MAX_EXCERPT_LENGTH]}"
                    else:
                        final_forward_data = parsed.get("content", chain_output)[:DEFAULT_MAX_EXCERPT_LENGTH]
                except:
                    final_forward_data = chain_output[:DEFAULT_MAX_EXCERPT_LENGTH]
                
                logger.info(f"노드 {node.get('id', 'unknown')} Chain 실행 완료")
                
            except Exception as e:
                logger.error(f"노드 {node.get('id', 'unknown')} Chain 실행 실패: {e}")
                result[f"node{node.get('id', 'unknown')}"] = f"실행 실패: {str(e)}"
        
        result["forward_data"] = final_forward_data
        
        logger.info(f"Validation Layer Chain 실행 완료")
        return result