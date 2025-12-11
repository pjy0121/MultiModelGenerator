"""
Password-based protection utilities for folders and knowledge bases.

Uses bcrypt for secure password hashing and .secure_marker files for protection management.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Tuple, List
from fastapi import HTTPException

try:
    import bcrypt
except ImportError:
    raise ImportError("bcrypt is required for protection features. Install it with: pip install bcrypt")

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 12 salt rounds.
    
    Args:
        password: Plain text password
        
    Returns:
        Base64 encoded bcrypt hash
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Args:
        password: Plain text password to verify
        hashed: Bcrypt hash to check against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def create_secure_marker(path: str, password: str, reason: str = "") -> None:
    """
    Create a .secure_marker file with hashed password.
    
    Args:
        path: Directory path to protect
        password: Plain text password
        reason: Optional reason for protection
        
    Raises:
        HTTPException: If marker creation fails
    """
    try:
        marker_data = {
            "version": "1.0",
            "protected_at": datetime.now().isoformat(),
            "password_hash": hash_password(password),
            "salt_rounds": 12,
            "metadata": {
                "protected_by": "system",
                "reason": reason or "User-protected content"
            }
        }
        
        marker_path = os.path.join(path, '.secure_marker')
        with open(marker_path, 'w', encoding='utf-8') as f:
            json.dump(marker_data, f, indent=2)
        
        logger.info(f"🔒 Protection enabled for: {path}")
        
    except Exception as e:
        logger.error(f"Failed to create secure marker at {path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable protection: {str(e)}"
        )


def read_secure_marker(path: str) -> Optional[dict]:
    """
    Read .secure_marker file from a directory.
    
    Args:
        path: Directory path to check
        
    Returns:
        Marker data dict if exists, None otherwise
    """
    marker_path = os.path.join(path, '.secure_marker')
    
    if not os.path.exists(marker_path):
        return None
    
    try:
        with open(marker_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read secure marker at {path}: {e}")
        return None


def verify_protection_password(path: str, password: str) -> bool:
    """
    Verify password against .secure_marker file.
    
    Args:
        path: Directory path with .secure_marker
        password: Password to verify
        
    Returns:
        True if password is correct, False otherwise
    """
    marker_data = read_secure_marker(path)
    
    if not marker_data:
        return False
    
    password_hash = marker_data.get("password_hash", "")
    return verify_password(password, password_hash)


def is_protected(path: str) -> bool:
    """
    Check if a path is protected.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if .secure_marker exists, False otherwise
    """
    marker_path = os.path.join(path, '.secure_marker')
    return os.path.exists(marker_path)


def remove_secure_marker(path: str, password: str) -> None:
    """
    Remove .secure_marker file after password verification.
    
    Args:
        path: Directory path to unprotect
        password: Password for verification
        
    Raises:
        HTTPException: If password is invalid or removal fails
    """
    # Verify password first
    if not verify_protection_password(path, password):
        raise HTTPException(
            status_code=403,
            detail="Invalid password"
        )
    
    marker_path = os.path.join(path, '.secure_marker')
    
    try:
        if os.path.exists(marker_path):
            os.remove(marker_path)
            logger.info(f"🔓 Protection removed from: {path}")
        else:
            raise HTTPException(
                status_code=404,
                detail="Item is not protected"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove secure marker at {path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove protection: {str(e)}"
        )


def has_protected_content(folder_path: str) -> Tuple[bool, List[str]]:
    """
    Recursively check if folder or any child is protected.
    
    This prevents operations on parent folders when children are protected.
    
    Args:
        folder_path: Root folder path to check
        
    Returns:
        Tuple of (is_protected, list_of_protected_items)
    """
    from ..utils.path_resolver import PathResolver
    
    protected_items = []
    
    # Check current folder
    if is_protected(folder_path):
        protected_items.append(PathResolver.to_relative_path(folder_path))
    
    # Recursively check children
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            
            if not os.path.isdir(item_path):
                continue
            
            # Skip deleted items
            delete_marker = os.path.join(item_path, '.delete_marker')
            if os.path.exists(delete_marker):
                continue
            
            # Check child protection
            if is_protected(item_path):
                protected_items.append(PathResolver.to_relative_path(item_path))
            
            # Recursive check for folders (not KBs)
            folder_marker = os.path.join(item_path, '.folder_marker')
            if os.path.exists(folder_marker):
                child_protected, child_items = has_protected_content(item_path)
                if child_protected:
                    protected_items.extend(child_items)
    
    except Exception as e:
        logger.error(f"Error checking protection in {folder_path}: {e}")
    
    return (len(protected_items) > 0, protected_items)


def check_protection_before_operation(path: str, operation_name: str, is_folder: bool = False) -> None:
    """
    Check if item or any child is protected before allowing operations.
    
    This is the main validation function called by delete/rename/move operations.
    
    Args:
        path: Full path to check
        operation_name: Operation being attempted (for error messages)
        is_folder: True if checking a folder, False for KB
        
    Raises:
        HTTPException(403): If item is protected or contains protected children
    """
    # Check direct protection
    if is_protected(path):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot {operation_name}: Item is password-protected. Please unprotect it first."
        )
    
    # For folders: check children recursively
    if is_folder and os.path.isdir(path):
        folder_marker = os.path.join(path, '.folder_marker')
        if os.path.exists(folder_marker):
            child_protected, protected_items = has_protected_content(path)
            if child_protected:
                # Show first 3 protected items
                items_preview = ', '.join(protected_items[:3])
                if len(protected_items) > 3:
                    items_preview += f" (and {len(protected_items) - 3} more)"
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot {operation_name}: Folder contains protected items: {items_preview}"
                )
