"""
LangChain 기반 출력 파서 유틸리티
기존의 parse_structured_output 함수를 LangChain의 PydanticOutputParser로 대체
"""
import logging
import json
from typing import Tuple, Any
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from .output_models import LayerOutput

logger = logging.getLogger(__name__)


class LayerOutputParser:
    """Layer 출력을 파싱하기 위한 LangChain 기반 파서"""
    
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=LayerOutput)
    
    def parse(self, content: str) -> Tuple[str, str]:
        """
        LLM 출력에서 구조화된 데이터를 파싱
        
        Args:
            content: LLM 출력 텍스트
            
        Returns:
            Tuple[str, str]: (general_output, forward_data)
        """
        if not content or not content.strip():
            logger.warning("Content is empty or None")
            return "", ""
        
        logger.info(f"Starting to parse content (length: {len(content)})")
        
        try:
            # LangChain PydanticOutputParser를 사용하여 파싱
            parsed_result = self.parser.parse(content)
            
            general_output = parsed_result.general_output or ""
            forward_data = parsed_result.forward_data or ""
            
            logger.info(f"LangChain 파싱 성공 - general_output: {len(general_output)}자, forward_data: {len(forward_data)}자")
            return general_output, forward_data
            
        except OutputParserException as e:
            logger.warning(f"LangChain 파싱 실패, 기존 로직으로 폴백: {str(e)}")
            return self._fallback_parse(content)
        except Exception as e:
            logger.error(f"파싱 중 예외 발생: {str(e)}")
            return self._fallback_parse(content)
    
    def _fallback_parse(self, content: str) -> Tuple[str, str]:
        """
        LangChain 파싱이 실패했을 때 사용하는 기존 파싱 로직
        기존 parse_structured_output 함수의 핵심 로직을 간소화
        """
        import re
        import json
        
        logger.info("Using fallback parsing logic")
        
        try:
            # 1. 코드 블록에서 JSON 추출
            code_block_patterns = [
                r'```json\s*(.*?)\s*```',
                r'```JSON\s*(.*?)\s*```',
                r'```\s*(.*?)\s*```'
            ]
            
            for pattern in code_block_patterns:
                matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    json_str = match.group(1).strip()
                    if json_str and self._try_parse_json(json_str):
                        return self._try_parse_json(json_str)
            
            # 2. 전체 내용에서 JSON 객체 찾기
            json_patterns = [
                r'\{\s*"general_output".*?"forward_data".*?\}',
                r'\{\s*"forward_data".*?"general_output".*?\}',
                r'\{.*?\}'
            ]
            
            for pattern in json_patterns:
                matches = re.finditer(pattern, content, re.DOTALL)
                for match in matches:
                    json_str = match.group(0).strip()
                    result = self._try_parse_json(json_str)
                    if result:
                        return result
            
            # 3. 정규식으로 키-값 쌍 직접 추출
            general_output_match = re.search(r'"general_output"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"', content, re.DOTALL)
            forward_data_match = re.search(r'"forward_data"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"', content, re.DOTALL)
            
            if general_output_match or forward_data_match:
                general_output = general_output_match.group(1) if general_output_match else ""
                forward_data = forward_data_match.group(1) if forward_data_match else ""
                
                # 문자열 정리
                general_output = self._clean_string(general_output)
                forward_data = self._clean_string(forward_data)
                
                logger.info("정규식 추출 성공")
                return general_output, forward_data
            
            # 4. 마지막 시도: 전체 내용이 JSON인지 확인
            trimmed_content = content.strip()
            trimmed_content = re.sub(r'^\s*json\s*', '', trimmed_content, flags=re.IGNORECASE)
            trimmed_content = re.sub(r'\s*json\s*$', '', trimmed_content, flags=re.IGNORECASE)
            
            if trimmed_content.startswith('{') and trimmed_content.endswith('}'):
                result = self._try_parse_json(trimmed_content)
                if result:
                    return result
            
            # 5. 최종 폴백: 전체 내용을 general_output으로 처리
            logger.warning("JSON 블록을 찾을 수 없음. 전체 내용을 general_output으로 처리")
            return content, ""
            
        except Exception as e:
            logger.error(f"폴백 파싱 중 예외 발생: {e}")
            return content, ""
    
    def _try_parse_json(self, json_str: str) -> Tuple[str, str] | None:
        """JSON 문자열 파싱 시도"""
        try:
            # JSON 문자열 정리
            json_str = json_str.replace('\\\\\\', '\\').replace('\\\\', '\\')
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            parsed_json = json.loads(json_str)
            general_output = parsed_json.get("general_output", "")
            forward_data = parsed_json.get("forward_data", "")
            
            # 문자열 정리
            general_output = self._clean_string(general_output)
            forward_data = self._clean_string(forward_data)
            
            logger.info("JSON 파싱 성공")
            return general_output, forward_data
            
        except (json.JSONDecodeError, AttributeError, TypeError):
            return None
    
    def _clean_string(self, text: str) -> str:
        """문자열 정리"""
        if not text:
            return ""
        return text.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
    
    def get_format_instructions(self) -> str:
        """LLM 프롬프트에 추가할 형식 지침 반환"""
        return self.parser.get_format_instructions()


# 전역 파서 인스턴스
_parser = LayerOutputParser()


def parse_structured_output(content: str) -> Tuple[str, str]:
    """
    기존 함수와의 호환성을 위한 래퍼 함수
    """
    return _parser.parse(content)


def get_output_format_instructions() -> str:
    """
    LLM 프롬프트에 추가할 출력 형식 지침
    """
    return _parser.get_format_instructions()