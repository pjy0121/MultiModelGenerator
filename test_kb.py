#!/usr/bin/env python3
"""
Knowledge Base 목록 테스트
"""

import sys
import os
sys.path.append('c:/Users/SpringFrog/projects/MultiModelGenerator/server')

from src.services.vector_store import VectorStoreService

def test_kb_list():
    service = VectorStoreService()
    kb_list = service.list_knowledge_bases()
    print(f"Knowledge bases found: {kb_list}")
    
    # 직접 경로 확인
    kb_base_path = os.path.join(os.path.dirname(__file__), 'server', 'knowledge_bases')
    print(f"KB base path: {kb_base_path}")
    print(f"Path exists: {os.path.exists(kb_base_path)}")
    
    if os.path.exists(kb_base_path):
        items = os.listdir(kb_base_path)
        print(f"Items in path: {items}")

if __name__ == "__main__":
    test_kb_list()