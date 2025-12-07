"""
PathResolver - 지식 베이스 경로 관리 유틸리티

중복된 경로 계산 로직을 중앙화하여 유지보수성 향상
"""
import os
from typing import Optional


class PathResolver:
    """KB 및 폴더 경로 계산을 위한 유틸리티 클래스"""
    
    _kb_base_path: Optional[str] = None
    
    @classmethod
    def get_kb_base_path(cls) -> str:
        """
        KB base directory 절대 경로 반환
        
        Returns:
            knowledge_bases 디렉토리의 절대 경로
        """
        if cls._kb_base_path is None:
            # api_server.py 기준으로 상대 경로 계산
            current_file = os.path.dirname(__file__)
            kb_base = os.path.join(current_file, '..', '..', 'knowledge_bases')
            cls._kb_base_path = os.path.abspath(kb_base)
        
        return cls._kb_base_path
    
    @classmethod
    def resolve_kb_path(cls, kb_name: str) -> str:
        """
        KB 이름을 절대 경로로 변환 (폴더 구조 지원)
        
        Args:
            kb_name: KB 이름 (예: 'nvme_kb' 또는 'folder/nvme_kb')
        
        Returns:
            KB의 절대 경로
        """
        # 경로 구분자를 OS에 맞게 정규화
        kb_name_normalized = kb_name.replace('/', os.sep).replace('\\', os.sep)
        return os.path.join(cls.get_kb_base_path(), kb_name_normalized)
    
    @classmethod
    def resolve_folder_path(cls, folder_path: str) -> str:
        """
        폴더 상대 경로를 절대 경로로 변환
        
        Args:
            folder_path: 폴더 상대 경로 (예: 'folder1/subfolder')
        
        Returns:
            폴더의 절대 경로
        """
        if not folder_path:
            return cls.get_kb_base_path()
        
        # 경로 구분자를 OS에 맞게 정규화
        folder_normalized = folder_path.replace('/', os.sep).replace('\\', os.sep)
        return os.path.join(cls.get_kb_base_path(), folder_normalized)
    
    @classmethod
    def to_relative_path(cls, abs_path: str) -> str:
        """
        절대 경로를 KB base 기준 상대 경로로 변환
        
        Args:
            abs_path: 변환할 절대 경로
        
        Returns:
            KB base 기준 상대 경로 (슬래시 구분자 사용)
        """
        base_path = cls.get_kb_base_path()
        rel_path = os.path.relpath(abs_path, base_path)
        # Windows 백슬래시를 슬래시로 변환 (크로스 플랫폼 호환)
        return rel_path.replace('\\', '/')
    
    @classmethod
    def validate_path_exists(cls, path: str) -> bool:
        """
        경로가 존재하는지 확인
        
        Args:
            path: 확인할 경로
        
        Returns:
            경로 존재 여부
        """
        return os.path.exists(path)
    
    @classmethod
    def validate_is_directory(cls, path: str) -> bool:
        """
        경로가 디렉토리인지 확인
        
        Args:
            path: 확인할 경로
        
        Returns:
            디렉토리 여부
        """
        return os.path.isdir(path)
    
    @classmethod
    def normalize_path(cls, path: str) -> str:
        """
        경로를 정규화 (os.path.normpath + 절대 경로 변환)
        
        Args:
            path: 정규화할 경로
        
        Returns:
            정규화된 절대 경로
        """
        return os.path.abspath(os.path.normpath(path))
