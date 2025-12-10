"""KB 목록 함수 테스트"""
import sys
import os

# 서버 모듈을 import 가능하도록 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from src.core.utils import get_kb_list_sync
import json

print("=" * 60)
print("KB 목록 테스트")
print("=" * 60)

kb_list = get_kb_list_sync()

print(f"\n총 {len(kb_list)}개의 KB 발견:\n")
for kb in kb_list:
    print(f"  - {kb}")

print("\n" + "=" * 60)
