"""
FileSystem Utilities - 파일 시스템 작업 유틸리티

ChromaDB 파일 잠금 문제를 해결하기 위한 안전한 파일 시스템 작업 함수들
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
    ChromaDB 안전 삭제 (재시도 로직 포함)
    
    Args:
        path: 삭제할 경로
        max_retries: 최대 재시도 횟수
        lock: 사용할 asyncio Lock (None이면 락 없이 실행)
        operation_name: 작업 이름 (로깅용)
    
    Raises:
        PermissionError: 최대 재시도 후에도 삭제 실패 시
    """
    async def _perform_delete():
        for attempt in range(max_retries):
            try:
                # 가비지 컬렉션 강제 실행 (ChromaDB 파일 핸들 해제)
                gc.collect()
                await asyncio.sleep(0.2 + attempt * 0.1)  # 첫 시도도 대기
                
                # readonly 속성 제거 함수
                def remove_readonly(func, file_path, excinfo):
                    try:
                        os.chmod(file_path, 0o777)
                        func(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove readonly for {file_path}: {e}")
                
                # 디렉토리 전체 삭제
                shutil.rmtree(path, onerror=remove_readonly)
                logger.info(f"Successfully deleted '{path}' on attempt {attempt + 1}")
                return
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error during {operation_name} '{path}', retrying... "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    # 추가 가비지 컬렉션
                    gc.collect()
                    await asyncio.sleep(0.5 + attempt * 0.3)  # 더 긴 점진적 백오프
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
    ChromaDB 안전 이름 변경 (재시도 로직 포함)
    
    Args:
        old_path: 기존 경로
        new_path: 새 경로
        max_retries: 최대 재시도 횟수
        lock: 사용할 asyncio Lock (None이면 락 없이 실행)
    
    Raises:
        PermissionError: 최대 재시도 후에도 이름 변경 실패 시
    """
    async def _perform_rename():
        for attempt in range(max_retries):
            try:
                # 가비지 컬렉션 강제 실행 (ChromaDB 파일 핸들 해제)
                gc.collect()
                await asyncio.sleep(0.2 + attempt * 0.1)  # 첫 시도도 대기
                
                # 이름 변경
                os.rename(old_path, new_path)
                logger.info(f"Successfully renamed '{old_path}' to '{new_path}' on attempt {attempt + 1}")
                return
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error renaming '{old_path}', retrying... "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    # 추가 가비지 컬렉션
                    gc.collect()
                    await asyncio.sleep(0.5 + attempt * 0.3)  # 더 긴 점진적 백오프
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
