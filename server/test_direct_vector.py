"""
VectorStore 직접 테스트 - 서버 없이 직접 VectorStore 클래스 테스트
"""

import sys
import os
sys.path.append('/src')

from src.services.vector_store import VectorStore

def test_vector_store_directly():
    """VectorStore 클래스를 직접 테스트"""
    print("=== VectorStore 직접 테스트 시작 ===")
    
    # 지식베이스 이름들
    kb_names = ['keyword_nvme_2-2', 'sentence_nvme_2-2', 'large_nvme_2-2']
    
    for kb_name in kb_names:
        print(f"\n--- {kb_name} 테스트 ---")
        try:
            # VectorStore 인스턴스 생성
            vector_store = VectorStore(kb_name)
            print(f"✅ VectorStore 인스턴스 생성 성공")
            
            # 상태 확인
            status = vector_store.get_status()
            print(f"상태: {status}")
            
            # 실제 ChromaDB에 접근해서 count 확인
            try:
                collection = vector_store.get_collection()
                actual_count = collection.count()
                print(f"실제 문서 수: {actual_count}")
                
                if actual_count > 0:
                    print("✅ 데이터가 있는 지식베이스 발견!")
                    # 간단한 검색 테스트
                    import asyncio
                    
                    async def test_search():
                        try:
                            results = await vector_store.search("NVMe", "medium")
                            print(f"검색 결과 수: {len(results)}")
                            if results:
                                print(f"첫 번째 결과 (미리보기): {results[0][:100]}...")
                                return True
                        except Exception as e:
                            print(f"❌ 검색 오류: {e}")
                            return False
                    
                    search_success = asyncio.run(test_search())
                    if search_success:
                        print("✅ 검색 성공!")
                        break
                else:
                    print("⚠️ 빈 지식베이스")
                    
            except Exception as e:
                print(f"❌ ChromaDB 접근 오류: {e}")
                
        except Exception as e:
            print(f"❌ VectorStore 생성 오류: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_vector_store_directly()