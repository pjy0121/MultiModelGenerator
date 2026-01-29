"""
Server utility functions - Common helper functions
"""

import os
import asyncio
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ..config import VECTOR_DB_CONFIG


def get_kb_path(kb_name: str) -> str:
    """Return path for knowledge base (supports folder structure)

    Args:
        kb_name: Knowledge base name (can include path, e.g., 'folder1/kb_name')

    Returns:
        Absolute path
    """
    # Use PathResolver for consistency
    from .path_resolver import PathResolver
    return PathResolver.resolve_kb_path(kb_name)


def _get_kb_list_sync() -> List[str]:
    """Return knowledge base list synchronously (internal use)

    Recursively scans all subdirectories to return only actual KBs.
    Excludes folders (.folder_marker exists), returns only KBs with chroma.sqlite3.
    Returned names are in relative path format (e.g., "folder1/kb_name").
    """
    root_dir = VECTOR_DB_CONFIG["root_dir"]
    if not os.path.exists(root_dir):
        return []
    
    kb_list = []
    
    def scan_directory(current_path: str, relative_path: str = ""):
        """Recursively scan directories to find KBs"""
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                # Ignore if delete marker exists
                delete_marker = os.path.join(item_path, '.delete_marker')
                if os.path.exists(delete_marker):
                    continue

                # Check folder marker
                folder_marker = os.path.join(item_path, '.folder_marker')
                chroma_file = os.path.join(item_path, 'chroma.sqlite3')

                is_folder = os.path.exists(folder_marker)

                # Relative path of current item
                current_relative = os.path.join(relative_path, item) if relative_path else item

                if is_folder:
                    # If folder, scan subdirectories
                    scan_directory(item_path, current_relative)
                elif os.path.exists(chroma_file) and os.path.getsize(chroma_file) > 0:
                    # If KB (chroma.sqlite3 exists and size > 0)
                    kb_list.append(current_relative)
        except Exception as e:
            print(f"⚠️ Error during directory scan ({current_path}): {e}")
    
    scan_directory(root_dir)
    return sorted(kb_list)


async def get_kb_list() -> List[str]:
    """Return list of existing knowledge bases (async)"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, _get_kb_list_sync)


def get_kb_list_sync() -> List[str]:
    """Return knowledge base list synchronously (for compatibility)"""
    return _get_kb_list_sync()


def format_sse_data(data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Events"""
    return f"data: {json.dumps(data)}\n\n"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safe JSON parsing (returns default on failure)"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def ensure_directory_exists(path: str) -> None:
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


def is_valid_kb_name(kb_name: str) -> bool:
    """Validate knowledge base name"""
    if not kb_name or not isinstance(kb_name, str):
        return False

    # Basic filesystem safety check
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    return not any(char in kb_name for char in invalid_chars)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length (with ellipsis)"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_file_size(size_bytes: int) -> str:
    """Format byte size to human-readable format"""
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
    Utility function to safely parse JSON from LLM output
    Handles various JSON formats including code blocks, markdown, etc.
    """
    if not content or not content.strip():
        return {}

    import re

    # 1. Try extracting JSON from code blocks
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

    # 2. Try extracting JSON object from entire content
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(0)
            # Basic cleanup
            json_str = json_str.replace('\\n', '\n').replace('\\"', '"')
            return safe_json_loads(json_str)
        except:
            pass
    
    return {}


def clean_string_escapes(text: str) -> str:
    """Clean escape characters in string"""
    if not text:
        return ""
    
    return text.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')