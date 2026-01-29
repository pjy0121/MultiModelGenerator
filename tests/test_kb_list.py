"""KB list function test"""
import sys
import os

# Add server module path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from src.utils import get_kb_list_sync
import json

print("=" * 60)
print("KB List Test")
print("=" * 60)

kb_list = get_kb_list_sync()

print(f"\nFound {len(kb_list)} KBs:\n")
for kb in kb_list:
    print(f"  - {kb}")

print("\n" + "=" * 60)
