"""
Centralized exception handling utilities for the application.

Provides decorators and factory functions for consistent error handling
across API endpoints and service layers.
"""

import logging
import traceback
from functools import wraps
from typing import Callable, Optional, Type
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Factory for creating standardized HTTPException responses."""
    
    @staticmethod
    def validation_error(detail: str) -> HTTPException:
        """Create a 400 validation error response."""
        return HTTPException(status_code=400, detail=detail)
    
    @staticmethod
    def not_found(resource: str) -> HTTPException:
        """Create a 404 not found error response."""
        return HTTPException(status_code=404, detail=f"{resource} not found")
    
    @staticmethod
    def conflict(detail: str) -> HTTPException:
        """Create a 409 conflict error response."""
        return HTTPException(status_code=409, detail=detail)
    
    @staticmethod
    def forbidden(detail: str) -> HTTPException:
        """Create a 403 forbidden error response."""
        return HTTPException(status_code=403, detail=detail)
    
    @staticmethod
    def internal_error(detail: str, include_traceback: bool = False) -> HTTPException:
        """Create a 500 internal server error response."""
        if include_traceback:
            detail = f"{detail}\n{traceback.format_exc()}"
        return HTTPException(status_code=500, detail=detail)


def handle_api_errors(
    default_status: int = 500,
    log_errors: bool = True,
    reraise_http: bool = True
):
    """
    Decorator for consistent error handling in API endpoints.
    
    Args:
        default_status: Default HTTP status code for unhandled exceptions
        log_errors: Whether to log errors
        reraise_http: Whether to re-raise HTTPException without modification
        
    Usage:
        @handle_api_errors(default_status=500)
        async def my_endpoint():
            # endpoint logic
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPException as-is if requested
                if reraise_http:
                    raise
                if log_errors:
                    logger.error(f"HTTP error in {func.__name__}: {traceback.format_exc()}")
                raise
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=default_status,
                    detail=f"Internal error: {str(e)}"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                if log_errors:
                    logger.error(f"HTTP error in {func.__name__}: {traceback.format_exc()}")
                raise
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=default_status,
                    detail=f"Internal error: {str(e)}"
                )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def handle_service_errors(
    operation_name: str,
    log_errors: bool = True,
    default_error_msg: Optional[str] = None
):
    """
    Decorator for error handling in service layer operations.
    
    Args:
        operation_name: Name of the operation for logging
        log_errors: Whether to log errors
        default_error_msg: Custom error message to return
        
    Usage:
        @handle_service_errors("vector search")
        async def search_vectors(query: str):
            # service logic
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {operation_name} ({func.__name__}): {str(e)}\n{traceback.format_exc()}")
                error_msg = default_error_msg or f"Failed to {operation_name}: {str(e)}"
                raise RuntimeError(error_msg) from e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {operation_name} ({func.__name__}): {str(e)}\n{traceback.format_exc()}")
                error_msg = default_error_msg or f"Failed to {operation_name}: {str(e)}"
                raise RuntimeError(error_msg) from e
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def handle_node_execution_error(
    node_id: str,
    node_type: str,
    error: Exception,
    log_error: bool = True
) -> dict:
    """
    Create standardized error response for node execution failures.
    
    Args:
        node_id: ID of the node that failed
        node_type: Type of the node
        error: The exception that occurred
        log_error: Whether to log the error
        
    Returns:
        Dictionary with error details for node execution result
    """
    if log_error:
        logger.error(f"Node execution error [{node_type}:{node_id}]: {str(error)}\n{traceback.format_exc()}")
    
    return {
        "node_id": node_id,
        "node_type": node_type,
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__
    }


def handle_llm_error(
    provider: str,
    model: str,
    error: Exception,
    log_error: bool = True
) -> str:
    """
    Create standardized error message for LLM failures.
    
    Args:
        provider: LLM provider name
        model: Model name
        error: The exception that occurred
        log_error: Whether to log the error
        
    Returns:
        Formatted error message string
    """
    if log_error:
        logger.error(f"LLM error [{provider}/{model}]: {str(error)}\n{traceback.format_exc()}")
    
    return f"LLM request failed [{provider}/{model}]: {str(error)}"
