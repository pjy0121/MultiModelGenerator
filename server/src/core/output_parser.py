"""
JSON 출력 파싱 모듈 - project_reference.md 기준
"""

import json
from typing import Dict, Any
from .models import ParsedNodeOutput

class ResultParser:
    """
    LLM 출력 결과를 파싱하는 클래스
    project_reference.md의 ResultParser 사양에 따라 구현
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
            # JSON 파싱 시도
            parsed_json = json.loads(raw_output)
            
            # 필수 필드 확인
            if not isinstance(parsed_json, dict):
                raise ValueError("Output must be a JSON object")
            
            if "description" not in parsed_json:
                raise ValueError("Missing 'description' field in output")
            
            if "output" not in parsed_json:
                raise ValueError("Missing 'output' field in output")
            
            description = str(parsed_json["description"])
            output = str(parsed_json["output"])
            
            return ParsedNodeOutput(
                description=description,
                output=output
            )
            
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 - 전체 텍스트를 description으로 사용
            return ParsedNodeOutput(
                description=f"Parse error: {str(e)}. Raw output: {raw_output[:200]}...",
                output=raw_output
            )
        
        except Exception as e:
            # 기타 에러
            raise ValueError(f"Result parsing failed: {str(e)}")
    
    def validate_output_format(self, raw_output: str) -> Dict[str, Any]:
        """
        출력 형식 유효성 검증
        
        Args:
            raw_output: 검증할 출력 문자열
            
        Returns:
            Dict: 검증 결과 {"valid": bool, "errors": List[str]}
        """
        
        errors = []
        
        try:
            parsed_json = json.loads(raw_output)
            
            if not isinstance(parsed_json, dict):
                errors.append("Output must be a JSON object")
            else:
                if "description" not in parsed_json:
                    errors.append("Missing 'description' field")
                elif not isinstance(parsed_json["description"], str):
                    errors.append("'description' field must be a string")
                
                if "output" not in parsed_json:
                    errors.append("Missing 'output' field")
                elif not isinstance(parsed_json["output"], str):
                    errors.append("'output' field must be a string")
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }