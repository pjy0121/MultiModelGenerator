import PyPDF2
import re
from typing import List, Dict
from ..core.config import VECTOR_DB_CONFIG
from transformers import AutoTokenizer

# TEI 또는 로컬 모델 조건부 import
config = VECTOR_DB_CONFIG
if config.get('tei_enabled', False):
    from .tei_embedding import TEIClient
else:
    from sentence_transformers import SentenceTransformer

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or VECTOR_DB_CONFIG["chunk_size"]
        self.chunk_overlap = chunk_overlap or VECTOR_DB_CONFIG["chunk_overlap"]
        
        # BGE-M3 tokenizer 초기화 (token 기반 청킹용)
        tokenizer_model = VECTOR_DB_CONFIG.get('tokenizer_model', 'BAAI/bge-m3')
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_model)
            print(f"✅ {tokenizer_model} tokenizer 로드 성공")
        except Exception as e:
            print(f"⚠️ {tokenizer_model} tokenizer 로드 실패: {e}")
            print("💡 transformers 라이브러리를 설치하고 인터넷 연결을 확인하세요.")
            self.tokenizer = None
        
        # TEI 또는 로컬 모델 선택
        config = VECTOR_DB_CONFIG
        self.use_tei = config.get('tei_enabled', False)
        
        if self.use_tei:
            # TEI 클라이언트 초기화
            self.tei_client = TEIClient(
                base_url=config.get('tei_base_url', 'http://localhost:8080'),
                timeout=config.get('tei_timeout', 30)
            )
            
            # TEI 서버 연결 테스트
            success, message = self.tei_client.test_connection()
            if success:
                print(f"✅ {message}")
                print(f"📊 TEI 서버: {config.get('tei_base_url')}")
                print(f"🤖 모델: {config.get('tei_model_name', 'BAAI/bge-m3')}")
                print(f"📐 임베딩 차원: {config.get('embedding_dimension', 1024)}")
            else:
                print(f"❌ {message}")
                print(f"💡 TEI 서버를 시작하거나 config.py에서 tei_enabled=False로 설정하세요")
                raise RuntimeError(f"TEI 서버 연결 실패: {message}")
        else:
            # 로컬 sentence-transformers 모델 사용
            try:
                model_name = config.get('local_embedding_model', 'all-MiniLM-L6-v2')
                self.embedding_model = SentenceTransformer(model_name)
                print(f"✅ 로컬 임베딩 모델 로드: {model_name}")
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
    
    def chunk_by_tokens(self, text: str, chunk_size: int = None, overlap_ratio: float = None) -> List[str]:
        """BGE-M3 tokenizer 기반 정확한 token 청킹
        
        Args:
            text: 청킹할 텍스트
            chunk_size: 청크당 토큰 수 (None이면 config 사용)
            overlap_ratio: 오버랩 비율 0~1 (None이면 config 사용)
        
        Returns:
            List[str]: 청크 리스트
        """
        if not self.tokenizer:
            # tokenizer가 없으면 character 기반 방식으로 fallback
            print("⚠️ Tokenizer 비활성화, character 기반 청킹 사용")
            return None
        
        # config에서 기본값 가져오기
        if chunk_size is None:
            chunk_size = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        if overlap_ratio is None:
            overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
        
        # overlap을 토큰 수로 계산
        overlap_tokens = int(chunk_size * overlap_ratio)
        
        try:
            # 텍스트를 토큰으로 변환
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
            chunks = []
            
            # 오버랩을 고려하여 슬라이딩
            stride = chunk_size - overlap_tokens
            for i in range(0, len(tokens), stride):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
                chunks.append(chunk_text)
            
            return chunks
        except Exception as e:
            print(f"⚠️ Token 기반 청킹 실패: {e}")
            return None
    
    def semantic_chunking(self, text: str) -> List[Dict[str, any]]:
        """의미론적 청킹 (BGE-M3 tokenizer 기반)"""
        # BGE-M3 tokenizer 기반 청킹 시도
        if self.tokenizer:
            try:
                # Token 기반 청킹 (config에서 가져오기)
                chunk_texts = self.chunk_by_tokens(text)
                
                if chunk_texts:
                    chunks = []
                    for chunk_id, chunk_text in enumerate(chunk_texts):
                        # 텍스트 정제 및 메타데이터 추가
                        cleaned_text = self.clean_text(chunk_text)
                        if cleaned_text.strip():  # 빈 청크 제외
                            chunks.append({
                                'id': chunk_id,
                                'content': cleaned_text,
                                'length': len(cleaned_text)
                            })
                    
                    chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
                    overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
                    print(f"✅ Token 기반 청킹 성공: {len(chunks)}개 청크 ({chunk_tokens} tokens, {int(overlap_ratio*100)}% overlap)")
                    return chunks
            except Exception as e:
                print(f"⚠️ Token 기반 청킹 실패, character 기반 청킹으로 대체: {e}")
        
        # Fallback: Character 기반 청킹 (token config에서 계산)
        chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        chars_per_token = VECTOR_DB_CONFIG.get('chars_per_token', 4)
        overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
        
        self.chunk_size = chunk_tokens * chars_per_token  # 512 * 4 = 2048
        self.chunk_overlap = int(self.chunk_size * overlap_ratio)  # 2048 * 0.15 = 307
        
        print(f"💡 Character 기반 fallback: {self.chunk_size}자 ({self.chunk_overlap}자 overlap, {int(overlap_ratio*100)}%)")
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
        
        # TEI 또는 로컬 모델 사용
        if self.use_tei:
            embeddings = self.tei_client.encode(contents)
        else:
            embeddings = self.embedding_model.encode(contents, show_progress_bar=True)
            embeddings = [emb.tolist() for emb in embeddings]
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i] if isinstance(embeddings[i], list) else embeddings[i].tolist()
        
        return chunks
