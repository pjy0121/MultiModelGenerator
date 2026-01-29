import PyPDF2
import re
from typing import List, Dict
from ..config import VECTOR_DB_CONFIG
from transformers import AutoTokenizer

# Conditional import for TEI or local model
config = VECTOR_DB_CONFIG
if config.get('tei_enabled', False):
    from .tei_embedding import TEIClient
else:
    from sentence_transformers import SentenceTransformer

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or VECTOR_DB_CONFIG["chunk_size"]
        self.chunk_overlap = chunk_overlap or VECTOR_DB_CONFIG["chunk_overlap"]

        # Initialize BGE-M3 tokenizer (for token-based chunking)
        tokenizer_model = VECTOR_DB_CONFIG.get('tokenizer_model')
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_model)
            print(f"✅ {tokenizer_model} tokenizer loaded successfully")
        except Exception as e:
            print(f"⚠️ {tokenizer_model} tokenizer load failed: {e}")
            print("💡 Install transformers library and check internet connection.")
            self.tokenizer = None

        # Select TEI or local model
        config = VECTOR_DB_CONFIG
        self.use_tei = config.get('tei_enabled', False)

        if self.use_tei:
            # Initialize TEI client
            self.tei_client = TEIClient(
                base_url=config.get('tei_base_url', 'http://localhost:8080'),
                timeout=config.get('tei_timeout', 30)
            )

            # Test TEI server connection
            success, message = self.tei_client.test_connection()
            if success:
                print(f"✅ {message}")
                print(f"📊 TEI server: {config.get('tei_base_url')}")
                print(f"🤖 Model: {config.get('tei_model_name')}")
                print(f"📐 Embedding dimension: {config.get('embedding_dimension', 1024)}")
            else:
                print(f"❌ {message}")
                print(f"💡 Start TEI server or set tei_enabled=False in config.py")
                raise RuntimeError(f"TEI server connection failed: {message}")
        else:
            # Use local sentence-transformers model
            try:
                model_name = config.get('local_embedding_model', 'all-MiniLM-L6-v2')
                self.embedding_model = SentenceTransformer(model_name)
                print(f"✅ Local embedding model loaded: {model_name}")
            except Exception as e:
                print(f"⚠️ Embedding model load failed: {e}")
                print("💡 Check if sentence-transformers library is installed.")
                raise

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n[Page {page_num + 1}]\n{page_text}\n"
                
                return text
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Clean text"""
        # Multiple whitespace to single
        text = re.sub(r'\s+', ' ', text)
        # Clean special characters
        text = re.sub(r'[^\w\s가-힣.,;:()\[\]-]', ' ', text)
        # Remove too short words
        words = text.split()
        words = [word for word in words if len(word) > 1]
        return ' '.join(words)

    def chunk_by_tokens(self, text: str, chunk_size: int = None, overlap_ratio: float = None) -> List[str]:
        """Precise token chunking based on BGE-M3 tokenizer

        Args:
            text: Text to chunk
            chunk_size: Tokens per chunk (None uses config)
            overlap_ratio: Overlap ratio 0~1 (None uses config)

        Returns:
            List[str]: List of chunks
        """
        if not self.tokenizer:
            # Fallback to character-based method if no tokenizer
            print("⚠️ Tokenizer disabled, using character-based chunking")
            return None

        # Get defaults from config
        if chunk_size is None:
            chunk_size = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        if overlap_ratio is None:
            overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)

        # Calculate overlap in tokens
        overlap_tokens = int(chunk_size * overlap_ratio)

        try:
            # Convert text to tokens
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
            chunks = []

            # Slide with overlap
            stride = chunk_size - overlap_tokens
            for i in range(0, len(tokens), stride):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
                chunks.append(chunk_text)

            return chunks
        except Exception as e:
            print(f"⚠️ Token-based chunking failed: {e}")
            return None

    def semantic_chunking(self, text: str) -> List[Dict[str, any]]:
        """Semantic chunking (BGE-M3 tokenizer based)"""
        # Try BGE-M3 tokenizer based chunking
        if self.tokenizer:
            try:
                # Token-based chunking (get from config)
                chunk_texts = self.chunk_by_tokens(text)

                if chunk_texts:
                    chunks = []
                    for chunk_id, chunk_text in enumerate(chunk_texts):
                        # Clean text and add metadata
                        cleaned_text = self.clean_text(chunk_text)
                        if cleaned_text.strip():  # Exclude empty chunks
                            chunks.append({
                                'id': chunk_id,
                                'content': cleaned_text,
                                'length': len(cleaned_text)
                            })

                    chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
                    overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
                    print(f"✅ Token-based chunking success: {len(chunks)} chunks ({chunk_tokens} tokens, {int(overlap_ratio*100)}% overlap)")
                    return chunks
            except Exception as e:
                print(f"⚠️ Token-based chunking failed, falling back to character-based: {e}")

        # Fallback: Character-based chunking (calculated from token config)
        chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        chars_per_token = VECTOR_DB_CONFIG.get('chars_per_token', 4)
        overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)

        self.chunk_size = chunk_tokens * chars_per_token  # 512 * 4 = 2048
        self.chunk_overlap = int(self.chunk_size * overlap_ratio)  # 2048 * 0.15 = 307

        print(f"💡 Character-based fallback: {self.chunk_size} chars ({self.chunk_overlap} chars overlap, {int(overlap_ratio*100)}%)")
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_id = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        'id': chunk_id,
                        'content': self.clean_text(current_chunk),
                        'length': len(current_chunk)
                    })
                    chunk_id += 1

                # Handle overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += " " + paragraph

        # Add last chunk
        if current_chunk:
            chunks.append({
                'id': chunk_id,
                'content': self.clean_text(current_chunk),
                'length': len(current_chunk)
            })

        return chunks

    def generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings"""
        print("Generating embeddings...")
        
        contents = [chunk['content'] for chunk in chunks]
        
        # Use TEI or local model
        if self.use_tei:
            embeddings = self.tei_client.encode(contents)
        else:
            embeddings = self.embedding_model.encode(contents, show_progress_bar=True)
            embeddings = [emb.tolist() for emb in embeddings]
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i] if isinstance(embeddings[i], list) else embeddings[i].tolist()
        
        return chunks
