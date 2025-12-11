"""Utility functions and helper classes."""

from .exceptions import (
    ErrorResponse,
    handle_api_errors,
    handle_service_errors,
    handle_node_execution_error,
    handle_llm_error
)

from .general import (
    format_sse_data,
    get_kb_path,
    get_kb_list,
    get_kb_list_sync,
    safe_json_loads,
    ensure_directory_exists,
    is_valid_kb_name,
    truncate_text,
    format_file_size,
    parse_json_from_llm_output,
    clean_string_escapes
)

from .path_resolver import PathResolver
from .filesystem import safe_delete_with_retry, safe_rename_with_retry
from .protection import (
    hash_password,
    verify_password,
    create_secure_marker,
    read_secure_marker,
    verify_protection_password,
    is_protected,
    remove_secure_marker,
    has_protected_content,
    check_protection_before_operation
)
from .parser import ResultParser

__all__ = [
    # Exception handling
    'ErrorResponse',
    'handle_api_errors',
    'handle_service_errors',
    'handle_node_execution_error',
    'handle_llm_error',
    # General utilities
    'format_sse_data',
    'get_kb_path',
    'get_kb_list',
    'get_kb_list_sync',
    'safe_json_loads',
    'ensure_directory_exists',
    'is_valid_kb_name',
    'truncate_text',
    'format_file_size',
    'parse_json_from_llm_output',
    'clean_string_escapes',
    # Path utilities
    'PathResolver',
    # Filesystem utilities
    'safe_delete_with_retry',
    'safe_rename_with_retry',
    # Protection utilities
    'hash_password',
    'verify_password',
    'create_secure_marker',
    'read_secure_marker',
    'verify_protection_password',
    'is_protected',
    'remove_secure_marker',
    'has_protected_content',
    'check_protection_before_operation',
    # Parser
    'ResultParser'
]
