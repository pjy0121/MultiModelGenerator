#!/usr/bin/env python3
"""
지식베이스 검색 API 테스트
"""

import requests
import json

def test_search_api():
    base_url = "http://localhost:5001"
    
    print("🔍 지식베이스 검색 API 테스트")
    print("=" * 40)
    
    try:
        # 지식베이스 목록 확인
        response = requests.get(f"{base_url}/knowledge-bases")
        kb_response = response.json()
        knowledge_bases = kb_response.get('knowledge_bases', [])
        
        if not knowledge_bases:
            print("❌ 사용 가능한 지식베이스가 없습니다.")
            return
        
        kb_name = knowledge_bases[0]['name']
        print(f"📚 테스트 대상 지식베이스: {kb_name}")
        
        # 검색 요청
        search_request = {
            "query": "specification",
            "knowledge_base": kb_name,
            "top_k": 3
        }
        
        print(f"\n🔍 검색 요청:")
        print(json.dumps(search_request, indent=2))
        
        response = requests.post(
            f"{base_url}/search-knowledge-base",
            json=search_request,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 응답 상태: {response.status_code}")
        print(f"📄 응답 내용:")
        
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 오류: {response.text}")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_search_api()