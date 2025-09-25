import PyPDF2
import re
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from ..core.config import VECTOR_DB_CONFIG

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or VECTOR_DB_CONFIG["chunk_size"]
        self.chunk_overlap = chunk_overlap or VECTOR_DB_CONFIG["chunk_overlap"]
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"⚠️ 임베딩 모델 로드 실패: {e}")
            print("💡 sentence-transformers 라이브러리가 설치되어 있는지 확인하세요.")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n[Page {page_num + 1}]\n{page_text}\n"
                
                return text
        except Exception as e:
            print(f"PDF 처리 중 오류 발생: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 특수문자 정리
        text = re.sub(r'[^\w\s가-힣.,;:()\[\]-]', ' ', text)
        # 너무 짧은 단어 제거
        words = text.split()
        words = [word for word in words if len(word) > 1]
        return ' '.join(words)
    
    def semantic_chunking(self, text: str) -> List[Dict[str, any]]:
        """의미론적 청킹"""
        # 단락 기준으로 1차 분할
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_id = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 청크 크기 체크
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        'id': chunk_id,
                        'content': self.clean_text(current_chunk),
                        'length': len(current_chunk)
                    })
                    chunk_id += 1
                
                # 오버랩 처리
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += " " + paragraph
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append({
                'id': chunk_id,
                'content': self.clean_text(current_chunk),
                'length': len(current_chunk)
            })
        
        return chunks
    
    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """임베딩 생성"""
        print("임베딩 생성 중...")
        
        contents = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_model.encode(contents, show_progress_bar=True)
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()
        
        return chunks
