"""
서버 유틸리티 함수들 - 공통으로 사용되는 헬퍼 함수들
"""

import os
import asyncio
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ..config import VECTOR_DB_CONFIG


def get_kb_path(kb_name: str) -> str:
    """지식 베이스별 경로 반환 (폴더 구조 지원)
    
    Args:
        kb_name: 지식 베이스 이름 (경로 포함 가능, 예: 'folder1/kb_name')
    
    Returns:
        절대 경로
    """
    # PathResolver 사용으로 일관성 유지
    from .path_resolver import PathResolver
    return PathResolver.resolve_kb_path(kb_name)


def _get_kb_list_sync() -> List[str]:
    """동기 방식으로 지식 베이스 목록 반환 (내부 사용)
    
    재귀적으로 모든 하위 폴더를 탐색하여 실제 KB만 반환합니다.
    폴더(.folder_marker 존재)는 제외하고, chroma.sqlite3가 있는 KB만 반환합니다.
    반환되는 이름은 상대 경로 형태입니다 (예: "folder1/kb_name").
    """
    root_dir = VECTOR_DB_CONFIG["root_dir"]
    if not os.path.exists(root_dir):
        return []
    
    kb_list = []
    
    def scan_directory(current_path: str, relative_path: str = ""):
        """재귀적으로 디렉토리 탐색하여 KB 찾기"""
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                # 삭제 마커가 있으면 무시
                delete_marker = os.path.join(item_path, '.delete_marker')
                if os.path.exists(delete_marker):
                    continue
                
                # 폴더 마커 확인
                folder_marker = os.path.join(item_path, '.folder_marker')
                chroma_file = os.path.join(item_path, 'chroma.sqlite3')
                
                is_folder = os.path.exists(folder_marker)
                
                # 현재 항목의 상대 경로
                current_relative = os.path.join(relative_path, item) if relative_path else item
                
                if is_folder:
                    # 폴더인 경우 하위 탐색
                    scan_directory(item_path, current_relative)
                elif os.path.exists(chroma_file) and os.path.getsize(chroma_file) > 0:
                    # KB인 경우 (chroma.sqlite3가 있고 크기가 0보다 큼)
                    kb_list.append(current_relative)
        except Exception as e:
            print(f"⚠️ 디렉토리 스캔 중 오류 ({current_path}): {e}")
    
    scan_directory(root_dir)
    return sorted(kb_list)


async def get_kb_list() -> List[str]:
    """존재하는 지식 베이스 목록 반환 (비동기)"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, _get_kb_list_sync)


def get_kb_list_sync() -> List[str]:
    """동기 방식으로 지식 베이스 목록 반환 (호환성 유지)"""
    return _get_kb_list_sync()


def format_sse_data(data: Dict[str, Any]) -> str:
    """Server-Sent Events 형식으로 데이터 포맷팅"""
    return f"data: {json.dumps(data)}\n\n"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """안전한 JSON 파싱 (실패 시 기본값 반환)"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def ensure_directory_exists(path: str) -> None:
    """디렉토리가 존재하지 않으면 생성"""
    os.makedirs(path, exist_ok=True)


def is_valid_kb_name(kb_name: str) -> bool:
    """지식 베이스 이름 유효성 검사"""
    if not kb_name or not isinstance(kb_name, str):
        return False
    
    # 기본적인 파일시스템 안전성 검사
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    return not any(char in kb_name for char in invalid_chars)


def truncate_text(text: str, max_length: int = 100) -> str:
    """텍스트를 지정된 길이로 자르기 (생략 표시 포함)"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_file_size(size_bytes: int) -> str:
    """바이트 크기를 읽기 쉬운 형태로 포맷팅"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def parse_json_from_llm_output(content: str) -> Dict[str, Any]:
    """
    LLM 출력에서 JSON을 안전하게 파싱하는 유틸리티 함수
    코드 블록, 마크다운 등 다양한 형태의 JSON을 처리
    """
    if not content or not content.strip():
        return {}
    
    import re
    
    # 1. 코드 블록에서 JSON 추출 시도
    code_block_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```JSON\s*(.*?)\s*```', 
        r'```\s*(.*?)\s*```',
        r'`([^`]*?)`'
    ]
    
    for pattern in code_block_patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                return safe_json_loads(match.strip())
            except:
                continue
    
    # 2. 전체 내용에서 JSON 객체 추출 시도
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(0)
            # 기본적인 정리
            json_str = json_str.replace('\\n', '\n').replace('\\"', '"')
            return safe_json_loads(json_str)
        except:
            pass
    
    return {}


def clean_string_escapes(text: str) -> str:
    """문자열의 이스케이프 문자들을 정리"""
    if not text:
        return ""
    
    return text.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')