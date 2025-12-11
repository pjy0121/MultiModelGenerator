"""
마크다운 태그 기반 출력 파싱 모듈 - project_reference.md 기준
"""

import re
from typing import Dict, Any
from ..models import ParsedNodeOutput

class ResultParser:
    """
    LLM 출력 결과를 파싱하는 클래스
    마크다운 태그 기반으로 output 추출
    """
    
    def parse_node_output(self, raw_output: str) -> ParsedNodeOutput:
        """
        LLM 원시 출력을 파싱하여 description과 output 추출
        
        Args:
            raw_output: LLM의 원시 출력 문자열
            
        Returns:
            ParsedNodeOutput: 파싱된 description과 output
            
        Raises:
            ValueError: 파싱 실패시
        """
        
        try:
            # <output>...</output> 또는 <출력>...</출력> 태그 패턴 찾기
            # [\s\S]*? 사용으로 멀티라인 텍스트 안전하게 매칭
            output_patterns = [
                r'<output>([\s\S]*?)</output>',
                r'<출력>([\s\S]*?)</출력>'
            ]
            
            output_match = None
            for pattern in output_patterns:
                output_match = re.search(pattern, raw_output, re.IGNORECASE)
                if output_match:
                    break
            
            if output_match:
                # output 태그 내용 추출
                output = output_match.group(1).strip()

                # description은 전체 텍스트 (스트리밍에서는 사용되지 않음)
                description = raw_output.strip()
                
                return ParsedNodeOutput(
                    description=description,
                    output=output
                )
            else:
                # output 태그가 없으면 전체 텍스트를 output으로 사용
                return ParsedNodeOutput(
                    description=raw_output.strip(),
                    output=raw_output.strip()
                )
                
        except Exception as e:
            # 기타 에러
            raise ValueError(f"Result parsing failed: {str(e)}")
    
    def validate_output_format(self, raw_output: str) -> Dict[str, Any]:
        """
        출력 형식 유효성 검증 (마크다운 태그 기반)
        
        Args:
            raw_output: 검증할 출력 문자열
            
        Returns:
            Dict: 검증 결과 {"valid": bool, "errors": List[str]}
        """
        
        errors = []
        
        try:
            # <output>...</output> 또는 <출력>...</출력> 태그 패턴 확인
            output_patterns = [
                r'<output>([\s\S]*?)</output>',
                r'<출력>([\s\S]*?)</출력>'
            ]
            
            output_match = None
            for pattern in output_patterns:
                output_match = re.search(pattern, raw_output, re.IGNORECASE)
                if output_match:
                    break
            
            if not output_match:
                errors.append("Missing <output>...</output> or <출력>...</출력> tags")
            else:
                output_content = output_match.group(1).strip()
                if not output_content:
                    errors.append("Empty content in <output> tags")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }