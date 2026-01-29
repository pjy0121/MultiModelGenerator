"""
PathResolver - Knowledge base path management utility

Centralizes duplicate path calculation logic for improved maintainability
"""
import os
from typing import Optional


class PathResolver:
    """Utility class for calculating KB and folder paths"""

    _kb_base_path: Optional[str] = None

    @classmethod
    def get_kb_base_path(cls) -> str:
        """
        Return absolute path of KB base directory

        Returns:
            Absolute path of knowledge_bases directory
        """
        if cls._kb_base_path is None:
            # Calculate relative path based on api_server.py
            current_file = os.path.dirname(__file__)
            kb_base = os.path.join(current_file, '..', '..', 'knowledge_bases')
            cls._kb_base_path = os.path.abspath(kb_base)

        return cls._kb_base_path
    
    @classmethod
    def resolve_kb_path(cls, kb_name: str) -> str:
        """
        Convert KB name to absolute path (supports folder structure)

        Args:
            kb_name: KB name (e.g., 'nvme_kb' or 'folder/nvme_kb')

        Returns:
            Absolute path of KB
        """
        # Normalize path separator for OS
        kb_name_normalized = kb_name.replace('/', os.sep).replace('\\', os.sep)
        return os.path.join(cls.get_kb_base_path(), kb_name_normalized)
    
    @classmethod
    def resolve_folder_path(cls, folder_path: str) -> str:
        """
        Convert folder relative path to absolute path

        Args:
            folder_path: Folder relative path (e.g., 'folder1/subfolder')

        Returns:
            Absolute path of folder
        """
        if not folder_path:
            return cls.get_kb_base_path()

        # Normalize path separator for OS
        folder_normalized = folder_path.replace('/', os.sep).replace('\\', os.sep)
        return os.path.join(cls.get_kb_base_path(), folder_normalized)
    
    @classmethod
    def to_relative_path(cls, abs_path: str) -> str:
        """
        Convert absolute path to relative path based on KB base

        Args:
            abs_path: Absolute path to convert

        Returns:
            Relative path based on KB base (uses forward slash separator)
        """
        base_path = cls.get_kb_base_path()
        rel_path = os.path.relpath(abs_path, base_path)
        # Convert Windows backslash to forward slash (cross-platform compatibility)
        return rel_path.replace('\\', '/')
    
    @classmethod
    def validate_path_exists(cls, path: str) -> bool:
        """
        Check if path exists

        Args:
            path: Path to check

        Returns:
            Whether path exists
        """
        return os.path.exists(path)
    
    @classmethod
    def validate_is_directory(cls, path: str) -> bool:
        """
        Check if path is a directory

        Args:
            path: Path to check

        Returns:
            Whether path is a directory
        """
        return os.path.isdir(path)
    
    @classmethod
    def normalize_path(cls, path: str) -> str:
        """
        Normalize path (os.path.normpath + convert to absolute path)

        Args:
            path: Path to normalize

        Returns:
            Normalized absolute path
        """
        return os.path.abspath(os.path.normpath(path))
