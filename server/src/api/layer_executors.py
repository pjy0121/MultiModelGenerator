"""
Layer별 실행 로직을 담당하는 모듈 - LangChain 기반 리팩토링
"""
import logging
from typing import List, Tuple, Dict, Any

# Chain 기반 실행기 import
from .chain_executors import ChainBasedLayerExecutors

# LangChain imports
from src.langchain_parsers.output_parsers import (
    LayerOutputParser, 
    LayerOutput, 
    NodeOutput as LangChainNodeOutput,
    get_layer_prompt_template
)
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

# Chain 기반 실행기 인스턴스
chain_executors = ChainBasedLayerExecutors()

# LangChain 기반 실행으로 완전 전환 (레거시 코드 제거)

def parse_structured_output_langchain(raw_output: str, layer_type: str = "requirement") -> Tuple[str, str]:
    """
    LangChain PydanticOutputParser를 사용한 구조화된 출력 파싱
    레거시 함수와의 호환성을 위해 (general_output_str, forward_data_str) 반환
    """
    try:
        # Layer 타입에 따른 적절한 파서 선택
        if layer_type == "requirement":
            parser = LayerOutputParser.get_requirements_parser()
        elif layer_type == "ensemble":
            parser = LayerOutputParser.get_ensemble_parser()
        elif layer_type == "validation":
            parser = LayerOutputParser.get_validation_parser()
        else:
            parser = LayerOutputParser.get_requirements_parser()  # 기본값
        
        # LangChain 파서로 구조화된 출력 파싱 시도
        try:
            parsed_output: LayerOutput = parser.parse(raw_output)
            
            # LayerOutput을 문자열로 변환 (레거시 호환성)
            general_output_str = parsed_output.content
            
            # forward_data 생성 (구조화된 데이터에서 추출)
            forward_data_parts = []
            
            if parsed_output.requirements:
                forward_data_parts.append(f"Requirements: {', '.join(parsed_output.requirements)}")
            
            if parsed_output.final_decision:
                forward_data_parts.append(f"Decision: {parsed_output.final_decision}")
            
            if parsed_output.overall_valid is not None:
                forward_data_parts.append(f"Validation: {'PASS' if parsed_output.overall_valid else 'FAIL'}")
            
            forward_data_str = " | ".join(forward_data_parts) if forward_data_parts else parsed_output.content
            
            logger.info(f"LangChain 구조화된 파싱 성공 - Layer: {layer_type}")
            return general_output_str, forward_data_str
            
        except OutputParserException as parse_error:
            logger.warning(f"LangChain 파싱 실패, 레거시 방식으로 fallback: {str(parse_error)}")
            return fallback_parse_structured_output(raw_output)
            
    except Exception as e:
        logger.error(f"LangChain 파서 초기화 실패: {str(e)}")
        return fallback_parse_structured_output(raw_output)


def fallback_parse_structured_output(text: str) -> Tuple[str, str]:
    """
    레거시 구조화된 출력 파싱 (LangChain 파싱 실패 시 사용)
    """
    logger.info("레거시 구조화된 출력 파싱 사용")
    
    if not text or not text.strip():
        return "파싱할 내용이 없습니다.", ""
    
    text = text.strip()
    
    # forward_data 패턴들 시도
    forward_patterns = [
        r'\*\*Forward Data:\*\*\s*(.*?)(?=\n\n|\Z)',
        r'\*\*다음 레이어 입력:\*\*\s*(.*?)(?=\n\n|\Z)',
        r'\*\*Next Layer Input:\*\*\s*(.*?)(?=\n\n|\Z)',
        r'Forward Data:\s*(.*?)(?=\n\n|\Z)',
    ]
    
    forward_data = ""
    for pattern in forward_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            forward_data = match.group(1).strip()
            break
    
    # forward_data가 없으면 전체 텍스트에서 요약 추출
    if not forward_data:
        lines = text.split('\n')
        content_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        if content_lines:
            forward_data = content_lines[0][:200]  # 첫 번째 의미있는 줄의 처음 200자
    
    # general_output은 전체 텍스트
    general_output = text
    
    return general_output, forward_data
def execute_generation_layer(nodes: List[Dict[str, Any]], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Generation Layer 실행 - LangChain Chain 기반
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 모든 노드의 forward_data를 append한 결과
    }
    """
    logger.info(f"LangChain Generation Layer 실행 시작: {len(nodes)}개 노드")
    
    try:
        # knowledge_base 추출 (context_chunks에서 유추 또는 기본값 사용)
        knowledge_base = "nvme-2_2"  # 기본값, 실제로는 API에서 전달받아야 함
        return chain_executors.execute_generation_layer_with_chains(nodes, layer_input, knowledge_base)
    except Exception as e:
        logger.error(f"Chain 기반 실행 실패: {e}")
        # 최소한의 오류 응답 반환
        return {
            "node1": f"실행 실패: {str(e)}",
            "forward_data": ""
        }


def execute_ensemble_layer(nodes: List[Dict[str, Any]], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Ensemble Layer 실행 - LangChain Chain 기반
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 모든 노드의 forward_data를 append한 결과
    }
    """
    logger.info(f"LangChain Ensemble Layer 실행 시작: {len(nodes)}개 노드")
    
    try:
        knowledge_base = "nvme-2_2"  # 기본값
        return chain_executors.execute_ensemble_layer_with_chains(nodes, layer_input, knowledge_base)
    except Exception as e:
        logger.error(f"Chain 기반 실행 실패: {e}")
        # 최소한의 오류 응답 반환
        return {
            "node1": f"실행 실패: {str(e)}",
            "forward_data": ""
        }


def execute_validation_layer(nodes: List[Dict[str, Any]], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Validation Layer 실행 - LangChain Chain 기반
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 마지막 노드의 forward_data (덮어쓰기 방식)
    }
    """
    logger.info(f"LangChain Validation Layer 실행 시작: {len(nodes)}개 노드")
    
    try:
        knowledge_base = "nvme-2_2"  # 기본값
        return chain_executors.execute_validation_layer_with_chains(nodes, layer_input, knowledge_base)
    except Exception as e:
        logger.error(f"Chain 기반 실행 실패: {e}")
        # 최소한의 오류 응답 반환
        return {
            "node1": f"실행 실패: {str(e)}",
            "forward_data": ""
        }
    print(f"🎯 Final result forward_data length: {len(final_forward_data)}")
    print(f"🎯 Final result keys: {list(result.keys())}")
    
    logger.info(f"Validation Layer 완료: 최종 forward_data 길이 {len(final_forward_data)}")
    return result


