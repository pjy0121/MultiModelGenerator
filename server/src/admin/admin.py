import os
import sys
import shutil
from typing import Dict, Any
from ..core.config import Config
from ..services.document_processor import DocumentProcessor
from ..services.vector_store import VectorStore

class KnowledgeBaseAdmin:
    def __init__(self):
        # 루트 디렉토리 생성
        os.makedirs(Config.VECTOR_DB_ROOT, exist_ok=True)
    
    def build_knowledge_base(self, kb_name: str, pdf_path: str, chunk_size: int = 8000, chunk_overlap: int = 200) -> bool:
        """지식 베이스 구축"""
        print("=" * 60)
        print(f"📚 지식 베이스 '{kb_name}' 구축 중...")
        print(f"📏 청크 크기: {chunk_size:,} 문자")
        print(f"🔄 청크 오버랩: {chunk_overlap} 문자")
        print("=" * 60)
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
            return False
        
        print(f"📄 처리할 PDF: {pdf_path}")
        print(f"🏷️ 지식 베이스 이름: {kb_name}")
        
        # 사용자 지정 청크 크기로 DocumentProcessor 초기화
        doc_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # VectorStore 초기화
        vector_store = VectorStore(kb_name)
        
        # 1. PDF 텍스트 추출
        print("\n🔍 1단계: PDF 텍스트 추출 중...")
        text = doc_processor.extract_text_from_pdf(pdf_path)
        if not text.strip():
            print("❌ PDF에서 텍스트를 추출할 수 없습니다.")
            return False
        
        print(f"✅ 총 텍스트 길이: {len(text):,} 문자")
        
        # 2. 청킹
        print("\n📝 2단계: 문서 청킹 중...")
        chunks = doc_processor.semantic_chunking(text)
        print(f"✅ 총 {len(chunks)}개 청크 생성")
        
        # 청크 정보 출력
        total_chars = sum(len(chunk['content']) for chunk in chunks)
        avg_chunk_size = total_chars // len(chunks) if chunks else 0
        print(f"   - 평균 청크 크기: {avg_chunk_size:,} 문자")
        print(f"   - 최대 청크 크기: {max(len(chunk['content']) for chunk in chunks):,} 문자")
        print(f"   - 최소 청크 크기: {min(len(chunk['content']) for chunk in chunks):,} 문자")
        
        # 3. 임베딩 생성
        print("\n🧠 3단계: 임베딩 생성 중...")
        chunks_with_embeddings = doc_processor.generate_embeddings(chunks)
        print("✅ 임베딩 생성 완료")
        
        # 4. 벡터 DB 저장
        print("\n💾 4단계: 벡터 데이터베이스 저장 중...")
        vector_store.store_chunks(chunks_with_embeddings)
        
        print("\n" + "=" * 60)
        print(f"🎉 지식 베이스 '{kb_name}' 구축이 완료되었습니다!")
        print(f"📍 저장 위치: {Config.get_kb_path(kb_name)}")
        print(f"📊 처리된 청크 수: {len(chunks)}")
        print("=" * 60)
        
        return True
    
    def list_knowledge_bases(self):
        """지식 베이스 목록 출력"""
        print("=" * 60)
        print("📋 지식 베이스 목록")
        print("=" * 60)
        
        kb_list = Config.get_kb_list()
        
        if not kb_list:
            print("❌ 등록된 지식 베이스가 없습니다.")
            return
        
        for i, kb_name in enumerate(kb_list, 1):
            vector_store = VectorStore(kb_name)
            status = vector_store.get_status()
            
            print(f"{i}. 📚 {kb_name}")
            print(f"   └── 📊 청크 수: {status['count']:,}개")
            print(f"   └── 📍 경로: {status['path']}")
            print()
    
    def check_knowledge_base_status(self, kb_name: str = None):
        """지식 베이스 상태 확인"""
        if kb_name is None:
            # 전체 목록 상태 확인
            self.list_knowledge_bases()
            return
        
        print("=" * 60)
        print(f"📊 지식 베이스 '{kb_name}' 상태 확인")
        print("=" * 60)
        
        vector_store = VectorStore(kb_name)
        status = vector_store.get_status()
        
        if not status['exists'] or status['count'] == 0:
            print(f"❌ 지식 베이스 '{kb_name}'이 존재하지 않거나 비어있습니다.")
            return False
        
        print(f"✅ 지식 베이스가 존재합니다.")
        print(f"📊 저장된 청크 수: {status['count']:,}개")
        print(f"📍 저장 위치: {status['path']}")
        
        # 샘플 검색 테스트
        print("\n🔍 샘플 검색 테스트...")
        try:
            sample_results = vector_store.collection.query(
                query_texts=["test"],
                n_results=1
            )
            
            if sample_results['documents'] and sample_results['documents'][0]:
                sample_doc = sample_results['documents'][0][0]
                print(f"✅ 검색 기능 정상 (샘플 길이: {len(sample_doc)} 문자)")
            else:
                print("⚠️ 검색 기능에 문제가 있을 수 있습니다.")
        except Exception as e:
            print(f"⚠️ 검색 테스트 중 오류: {e}")
        
        return True
    
    def get_knowledge_base_status(self, kb_name: str) -> Dict[str, Any]:
        """지식 베이스 상태 정보 반환 (admin_tool.py 호환용)"""
        try:
            vector_store = VectorStore(kb_name)
            status = vector_store.get_status()
            
            if not status['exists']:
                return None
            
            # 파일 크기 계산
            kb_path = Config.get_kb_path(kb_name)
            size_bytes = 0
            if os.path.exists(kb_path):
                for dirpath, dirnames, filenames in os.walk(kb_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        size_bytes += os.path.getsize(filepath)
            
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            return {
                'path': status['path'],
                'chunk_count': status['count'],
                'size_mb': size_mb,
                'exists': True
            }
            
        except Exception as e:
            print(f"⚠️ 상태 조회 중 오류: {e}")
            return None
    
    def delete_knowledge_base(self, kb_name: str):
        """지식 베이스 삭제"""
        print("=" * 60)
        print(f"🗑️ 지식 베이스 '{kb_name}' 삭제")
        print("=" * 60)
        
        kb_path = Config.get_kb_path(kb_name)
        
        if not os.path.exists(kb_path):
            print(f"❌ 지식 베이스 '{kb_name}'이 존재하지 않습니다.")
            return
        
        print(f"⚠️ 삭제할 지식 베이스: {kb_name}")
        print(f"⚠️ 경로: {kb_path}")
        confirm = input("⚠️ 정말로 이 지식 베이스를 삭제하시겠습니까? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ 삭제가 취소되었습니다.")
            return
        
        try:
            shutil.rmtree(kb_path)
            print(f"✅ 지식 베이스 '{kb_name}'이 성공적으로 삭제되었습니다.")
        except Exception as e:
            print(f"❌ 삭제 중 오류 발생: {e}")
    
    def get_valid_kb_name(self) -> str:
        """유효한 지식 베이스 이름 입력받기"""
        while True:
            kb_name = input("📝 지식 베이스 이름을 입력하세요: ").strip()
            
            if not kb_name:
                print("❌ 지식 베이스 이름을 입력해주세요.")
                continue
            
            # 파일명으로 사용할 수 없는 문자 제거
            safe_name = "".join(c for c in kb_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            
            if not safe_name:
                print("❌ 올바른 지식 베이스 이름을 입력해주세요.")
                continue
            
            if safe_name != kb_name:
                print(f"📝 지식 베이스 이름이 '{safe_name}'으로 변경됩니다.")
                confirm = input("계속하시겠습니까? (Y/n): ").strip().lower()
                if confirm == 'n':
                    continue
            
            return safe_name
    
    def get_chunk_settings(self) -> tuple[int, int]:
        """청크 크기 설정 입력받기"""
        print("\n📏 청크 크기 설정")
        print("💡 청크 크기가 클수록 더 많은 컨텍스트를 유지하지만, 검색 정확도가 떨어질 수 있습니다.")
        print("💡 권장 설정:")
        print("   - 기본 (6,000자): 균형잡힌 성능")
        print("   - 작은 청크 (4,000자): 정확한 검색, 많은 청크 수")
        print("   - 큰 청크 (8,000-10,000자): 풍부한 컨텍스트, 적은 청크 수")
        print("   - 매우 큰 청크 (12,000-15,000자): 최대 컨텍스트, 매우 적은 청크 수")
        
        # 청크 크기 입력
        while True:
            chunk_input = input(f"\n📏 청크 크기를 입력하세요 (기본값: 8000): ").strip()
            if not chunk_input:
                chunk_size = 8000  # 개선된 기본값
                break
            
            try:
                chunk_size = int(chunk_input)
                if chunk_size < 1000:
                    print("❌ 청크 크기는 최소 1,000자 이상이어야 합니다.")
                    continue
                elif chunk_size > 20000:
                    print("❌ 청크 크기는 최대 20,000자까지 권장됩니다.")
                    continue
                break
            except ValueError:
                print("❌ 올바른 숫자를 입력해주세요.")
        
        # 청크 오버랩 입력
        while True:
            overlap_input = input(f"🔄 청크 오버랩을 입력하세요 (기본값: {min(200, chunk_size // 40)}): ").strip()
            if not overlap_input:
                chunk_overlap = min(200, chunk_size // 40)  # 청크 크기의 2.5% 또는 200자 중 작은 값
                break
            
            try:
                chunk_overlap = int(overlap_input)
                if chunk_overlap < 0:
                    print("❌ 오버랩은 0 이상이어야 합니다.")
                    continue
                elif chunk_overlap >= chunk_size // 2:
                    print(f"❌ 오버랩은 청크 크기의 절반({chunk_size // 2}자) 미만이어야 합니다.")
                    continue
                break
            except ValueError:
                print("❌ 올바른 숫자를 입력해주세요.")
        
        print(f"\n✅ 청크 설정: 크기 {chunk_size:,}자, 오버랩 {chunk_overlap}자")
        return chunk_size, chunk_overlap

def main():
    print("🔧 Spec 문서 지식 베이스 관리자")
    print("=" * 60)
    
    admin = KnowledgeBaseAdmin()
    
    while True:
        print("\n📋 메뉴:")
        print("1. 새 지식 베이스 구축 (청크 크기 설정 가능)")
        print("2. 지식 베이스 목록 보기")
        print("3. 지식 베이스 상태 확인")
        print("4. 지식 베이스 삭제")
        print("5. 종료")
        
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == '1':
            kb_name = admin.get_valid_kb_name()
            pdf_path = input("📄 Spec PDF 파일 경로를 입력하세요: ").strip()
            
            if pdf_path:
                # 청크 크기 설정 받기
                chunk_size, chunk_overlap = admin.get_chunk_settings()
                
                # 기존 지식 베이스 덮어쓰기 확인
                if kb_name in Config.get_kb_list():
                    overwrite = input(f"⚠️ '{kb_name}' 지식 베이스가 이미 존재합니다. 덮어쓰시겠습니까? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        print("❌ 구축이 취소되었습니다.")
                        continue
                
                admin.build_knowledge_base(kb_name, pdf_path, chunk_size, chunk_overlap)
            else:
                print("❌ 파일 경로를 입력해주세요.")
        
        elif choice == '2':
            admin.list_knowledge_bases()
        
        elif choice == '3':
            kb_list = Config.get_kb_list()
            if not kb_list:
                print("❌ 등록된 지식 베이스가 없습니다.")
                continue
            
            print("\n사용 가능한 지식 베이스:")
            for i, kb_name in enumerate(kb_list, 1):
                print(f"{i}. {kb_name}")
            
            choice_kb = input("\n확인할 지식 베이스 번호 (전체: Enter): ").strip()
            if choice_kb:
                try:
                    kb_index = int(choice_kb) - 1
                    if 0 <= kb_index < len(kb_list):
                        admin.check_knowledge_base_status(kb_list[kb_index])
                    else:
                        print("❌ 올바른 번호를 입력해주세요.")
                except ValueError:
                    print("❌ 숫자를 입력해주세요.")
            else:
                admin.check_knowledge_base_status()
        
        elif choice == '4':
            kb_list = Config.get_kb_list()
            if not kb_list:
                print("❌ 삭제할 지식 베이스가 없습니다.")
                continue
            
            print("\n사용 가능한 지식 베이스:")
            for i, kb_name in enumerate(kb_list, 1):
                print(f"{i}. {kb_name}")
            
            choice_kb = input("\n삭제할 지식 베이스 번호: ").strip()
            try:
                kb_index = int(choice_kb) - 1
                if 0 <= kb_index < len(kb_list):
                    admin.delete_knowledge_base(kb_list[kb_index])
                else:
                    print("❌ 올바른 번호를 입력해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
        
        elif choice == '5':
            print("👋 관리자 프로그램을 종료합니다.")
            break
        
        else:
            print("❌ 올바른 메뉴를 선택해주세요.")

if __name__ == "__main__":
    main()
