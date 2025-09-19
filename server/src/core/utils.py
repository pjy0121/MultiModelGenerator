"""
공통 유틸리티 함수들
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ErrorMessages:
    """에러 메시지 상수"""
    
    # 일반적인 에러
    WORKFLOW_EXECUTION_FAILED = "워크플로우 실행 실패"
    NODE_EXECUTION_FAILED = "노드 실행 실패"
    
    # LLM 관련 에러
    LLM_CLIENT_NOT_AVAILABLE = "LLM 클라이언트를 사용할 수 없습니다"
    LLM_CLIENT_NOT_INITIALIZED = "LLM 클라이언트가 초기화되지 않았습니다"
    LLM_API_AUTH_FAILED = "LLM API 인증 실패"
    LLM_API_REQUEST_FAILED = "LLM API 요청 실패"
    
    # 지식베이스 관련 에러
    KNOWLEDGE_BASE_SEARCH_FAILED = "지식베이스 검색 실패"
    KNOWLEDGE_BASE_NOT_FOUND = "지식베이스를 찾을 수 없습니다"
    
    # 검증 관련 에러
    UNSUPPORTED_PROVIDER = "지원하지 않는 제공자입니다"
    MISSING_REQUIRED_FIELD = "필수 필드가 누락되었습니다"
    INVALID_NODE_CONFIGURATION = "노드 설정이 올바르지 않습니다"


class ResponseFormatter:
    """응답 포맷터"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = "성공") -> Dict[str, Any]:
        """성공 응답 생성"""
        response = {
            "success": True,
            "message": message
        }
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error_response(error: str, details: Optional[str] = None) -> Dict[str, Any]:
        """에러 응답 생성"""
        response = {
            "success": False,
            "error": error
        }
        if details:
            response["details"] = details
        return response
    
    @staticmethod
    def stream_chunk(chunk_type: str, **kwargs) -> Dict[str, Any]:
        """스트리밍 청크 생성"""
        chunk = {"type": chunk_type}
        chunk.update(kwargs)
        return chunk


class ValidationUtils:
    """검증 유틸리티"""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
        """필수 필드 검증"""
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
        return None
    
    @staticmethod
    def validate_provider(provider: str, supported_providers: List[str]) -> Optional[str]:
        """제공자 검증"""
        if provider not in supported_providers:
            return f"지원하지 않는 제공자입니다. 지원되는 제공자: {', '.join(supported_providers)}"
        return None


class LoggerUtils:
    """로깅 유틸리티"""
    
    @staticmethod
    def log_execution_start(logger: logging.Logger, node_id: str, node_type: str):
        """노드 실행 시작 로그"""
        logger.info(f"노드 실행 시작 - ID: {node_id}, Type: {node_type}")
    
    @staticmethod
    def log_execution_complete(logger: logging.Logger, node_id: str, success: bool, execution_time: float):
        """노드 실행 완료 로그"""
        status = "성공" if success else "실패"
        logger.info(f"노드 실행 완료 - ID: {node_id}, 상태: {status}, 실행시간: {execution_time:.2f}초")
    
    @staticmethod
    def log_error(logger: logging.Logger, operation: str, error: str, node_id: Optional[str] = None):
        """에러 로그"""
        if node_id:
            logger.error(f"{operation} 오류 (노드: {node_id}): {error}")
        else:
            logger.error(f"{operation} 오류: {error}")


class TextUtils:
    """텍스트 처리 유틸리티"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """텍스트 자르기"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """불필요한 공백 제거"""
        return " ".join(text.split())
    
    @staticmethod
    def safe_json_loads(text: str, default: Any = None) -> Any:
        """안전한 JSON 파싱"""
        try:
            import json
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return default