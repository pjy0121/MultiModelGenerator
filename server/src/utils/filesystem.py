"""
FileSystem Utilities - File system operation utilities

Safe file system operation functions to resolve ChromaDB file locking issues
"""
import os
import shutil
import asyncio
import gc
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def safe_delete_with_retry(
    path: str,
    max_retries: int = 5,
    lock: Optional[asyncio.Lock] = None,
    operation_name: str = "delete"
) -> None:
    """
    Safe ChromaDB deletion (with retry logic)

    Args:
        path: Path to delete
        max_retries: Maximum retry count
        lock: asyncio Lock to use (None runs without lock)
        operation_name: Operation name (for logging)

    Raises:
        PermissionError: When deletion fails after max retries
    """
    async def _perform_delete():
        for attempt in range(max_retries):
            try:
                # Force garbage collection (release ChromaDB file handles)
                gc.collect()
                await asyncio.sleep(0.2 + attempt * 0.1)  # Wait even on first attempt

                # Function to remove readonly attribute
                def remove_readonly(func, file_path, excinfo):
                    try:
                        os.chmod(file_path, 0o777)
                        func(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove readonly for {file_path}: {e}")

                # Delete entire directory
                shutil.rmtree(path, onerror=remove_readonly)
                logger.info(f"Successfully deleted '{path}' on attempt {attempt + 1}")
                return
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error during {operation_name} '{path}', retrying... "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    # Additional garbage collection
                    gc.collect()
                    await asyncio.sleep(0.5 + attempt * 0.3)  # Longer progressive backoff
                else:
                    logger.error(
                        f"Failed to {operation_name} '{path}' after {max_retries} attempts: {e}"
                    )
                    raise PermissionError(
                        f"Cannot {operation_name}: files are in use. "
                        f"Please close any applications using them and try again. "
                        f"Error: {str(e)}"
                    )
    
    if lock:
        async with lock:
            await _perform_delete()
    else:
        await _perform_delete()


async def safe_rename_with_retry(
    old_path: str,
    new_path: str,
    max_retries: int = 5,
    lock: Optional[asyncio.Lock] = None
) -> None:
    """
    Safe ChromaDB rename (with retry logic)

    Args:
        old_path: Old path
        new_path: New path
        max_retries: Maximum retry count
        lock: asyncio Lock to use (None runs without lock)

    Raises:
        PermissionError: When rename fails after max retries
    """
    async def _perform_rename():
        for attempt in range(max_retries):
            try:
                # Force garbage collection (release ChromaDB file handles)
                gc.collect()
                await asyncio.sleep(0.2 + attempt * 0.1)  # Wait even on first attempt

                # Rename
                os.rename(old_path, new_path)
                logger.info(f"Successfully renamed '{old_path}' to '{new_path}' on attempt {attempt + 1}")
                return
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error renaming '{old_path}', retrying... "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    # Additional garbage collection
                    gc.collect()
                    await asyncio.sleep(0.5 + attempt * 0.3)  # Longer progressive backoff
                else:
                    logger.error(
                        f"Failed to rename '{old_path}' after {max_retries} attempts: {e}"
                    )
                    raise PermissionError(
                        f"Cannot rename: files are in use. "
                        f"Please close any applications using them and try again. "
                        f"Error: {str(e)}"
                    )
    
    if lock:
        async with lock:
            await _perform_rename()
    else:
        await _perform_rename()
