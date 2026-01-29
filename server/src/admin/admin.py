import os
import shutil
import time
from typing import Dict, Any
from ..config import VECTOR_DB_CONFIG, ADMIN_CONFIG
from ..utils import get_kb_path, format_file_size, truncate_text, get_kb_list_sync
from ..services.document_processor import DocumentProcessor
from ..services.vector_store import VectorStore

class KnowledgeBaseAdmin:
    def __init__(self):
        # Create root directory
        os.makedirs(VECTOR_DB_CONFIG["root_dir"], exist_ok=True)
        self.vector_stores: Dict[str, VectorStore] = {}

    def get_vector_store(self, kb_name: str) -> VectorStore:
        """Get or create VectorStore instance (with caching)."""
        if kb_name not in self.vector_stores:
            self.vector_stores[kb_name] = VectorStore(kb_name)
        return self.vector_stores[kb_name]

    def build_knowledge_base(self, kb_name: str, pdf_path: str, chunk_size: int = 8000, chunk_overlap: int = 200) -> bool:
        """Build knowledge base"""
        print("=" * 60)
        print(f"📚 Building knowledge base '{kb_name}'...")
        print(f"📏 Chunk size: {chunk_size:,} characters (token-based calculation)")
        print(f"🔄 Chunk overlap: {chunk_overlap} characters (token-based calculation)")
        print("=" * 60)

        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            return False

        print(f"📄 PDF to process: {pdf_path}")
        print(f"🏷️ Knowledge base name: {kb_name}")
        
        # Initialize DocumentProcessor with custom chunk size
        doc_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        # Initialize VectorStore
        vector_store = self.get_vector_store(kb_name)

        # 1. Extract PDF text
        print("\n🔍 Step 1: Extracting text from PDF...")
        text = doc_processor.extract_text_from_pdf(pdf_path)
        if not text.strip():
            print("❌ Cannot extract text from PDF.")
            return False

        print(f"✅ Total text length: {len(text):,} characters")

        # 2. Chunking
        print("\n📝 Step 2: Chunking document...")
        chunks = doc_processor.semantic_chunking(text)
        print(f"✅ Created {len(chunks)} chunks")

        # Print chunk info
        total_chars = sum(len(chunk['content']) for chunk in chunks)
        avg_chunk_size = total_chars // len(chunks) if chunks else 0
        print(f"   - Average chunk size: {avg_chunk_size:,} characters")
        print(f"   - Maximum chunk size: {max(len(chunk['content']) for chunk in chunks):,} characters")
        print(f"   - Minimum chunk size: {min(len(chunk['content']) for chunk in chunks):,} characters")

        # 3. Generate embeddings
        print("\n🧠 Step 3: Generating embeddings...")
        chunks_with_embeddings = doc_processor.generate_embeddings(chunks)
        print("✅ Embedding generation complete")

        # 4. Store in vector DB
        print("\n💾 Step 4: Storing in vector database...")
        vector_store.store_chunks(chunks_with_embeddings)

        print("\n" + "=" * 60)
        print(f"🎉 Knowledge base '{kb_name}' build complete!")
        print(f"📍 Storage location: {get_kb_path(kb_name)}")
        print(f"📊 Processed chunks: {len(chunks)}")
        print("=" * 60)

        return True
    
    def list_knowledge_bases(self):
        """Print knowledge base list"""
        print("=" * 60)
        print("📋 Knowledge Base List")
        print("=" * 60)

        kb_list = get_kb_list_sync()

        if not kb_list:
            print("❌ No registered knowledge bases.")
            return

        for i, kb_name in enumerate(kb_list, 1):
            vector_store = self.get_vector_store(kb_name)
            status = vector_store.get_status()

            print(f"{i}. 📚 {kb_name}")
            print(f"   └── 📊 Chunks: {status['count']:,}")
            print(f"   └── 📍 Path: {status['path']}")
            print()
    
    def check_knowledge_base_status(self, kb_name: str = None):
        """Check knowledge base status"""
        if kb_name is None:
            # Check all knowledge bases
            self.list_knowledge_bases()
            return

        print("=" * 60)
        print(f"📊 Checking knowledge base '{kb_name}' status")
        print("=" * 60)

        vector_store = self.get_vector_store(kb_name)
        status = vector_store.get_status()

        if not status['exists'] or status['count'] == 0:
            print(f"❌ Knowledge base '{kb_name}' does not exist or is empty.")
            return False

        print(f"✅ Knowledge base exists.")
        print(f"📊 Stored chunks: {status['count']:,}")
        print(f"📍 Storage location: {status['path']}")

        # Sample search test
        print("\n🔍 Sample search test...")
        try:
            collection = vector_store.get_collection()
            sample_results = collection.query(
                query_texts=["test"],
                n_results=1
            )

            if sample_results['documents'] and sample_results['documents'][0]:
                sample_doc = sample_results['documents'][0][0]
                print(f"✅ Search function working (sample length: {len(sample_doc)} characters)")
            else:
                print("⚠️ Search function may have issues.")
        except Exception as e:
            print(f"⚠️ Error during search test: {e}")

        return True
    
    def get_knowledge_base_status(self, kb_name: str) -> Dict[str, Any]:
        """Return knowledge base status info (for admin_tool.py compatibility)"""
        try:
            vector_store = self.get_vector_store(kb_name)
            status = vector_store.get_status()

            if not status['exists']:
                return None

            # Calculate file size
            kb_path = get_kb_path(kb_name)
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
            print(f"⚠️ Error during status query: {e}")
            return None
    
    def delete_knowledge_base(self, kb_name: str):
        """Delete knowledge base"""
        print("=" * 60)
        print(f"🗑️ Deleting knowledge base '{kb_name}'")
        print("=" * 60)

        kb_path = get_kb_path(kb_name)

        if not os.path.exists(kb_path):
            print(f"❌ Knowledge base '{kb_name}' does not exist.")
            return

        print(f"⚠️ Knowledge base to delete: {kb_name}")
        print(f"⚠️ Path: {kb_path}")
        confirm = input("⚠️ Are you sure you want to delete this knowledge base? (y/n): ").strip().lower()

        if confirm != 'y':
            print("❌ Deletion cancelled.")
            return

        # Reset ChromaDB client connection if VectorStore instance is cached
        if kb_name in self.vector_stores:
            try:
                print(f"🔍 Resetting ChromaDB client connection for '{kb_name}'...")
                vector_store = self.vector_stores[kb_name]
                vector_store.client.reset()  # Disconnect database
                del self.vector_stores[kb_name]
                print("✅ Client connection reset complete.")
            except Exception as e:
                print(f"⚠️ Error during client reset: {e}")

        # Delete directory from filesystem (with retry logic)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                shutil.rmtree(kb_path)
                print(f"✅ Knowledge base '{kb_name}' successfully deleted.")
                return  # Exit function on success
            except PermissionError as e:
                print(f"❌ Permission error during deletion (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait and retry
                else:
                    print("❌ Deletion failed after multiple attempts. Please delete the files manually.")
            except Exception as e:
                print(f"❌ Unexpected error during deletion: {e}")
                break  # Don't retry for other types of errors
    
    def get_valid_kb_name(self) -> str:
        """Get valid knowledge base name from user input"""
        while True:
            kb_name = input("📝 Enter knowledge base name: ").strip()

            if not kb_name:
                print("❌ Please enter a knowledge base name.")
                continue

            # Remove characters not allowed in filenames (allow ., -, _)
            safe_name = "".join(c for c in kb_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
            safe_name = safe_name.replace(' ', '_')

            if not safe_name:
                print("❌ Please enter a valid knowledge base name.")
                continue

            if safe_name != kb_name:
                print(f"📝 Knowledge base name will be changed to '{safe_name}'.")
                confirm = input("Continue? (Y/n): ").strip().lower()
                if confirm == 'n':
                    continue

            return safe_name
    
    def get_custom_chunk_settings(self) -> tuple[int, int]:
        """Get custom chunk size settings from user input"""
        print("\n🛠️ Custom chunk settings")
        print("💡 1 token is calculated as approximately 4 characters.")

        # Chunk size input
        while True:
            chunk_input = input(f"\n📏 Enter chunk size (default: {ADMIN_CONFIG['chunk_size_default']}): ").strip()
            if not chunk_input:
                chunk_size = ADMIN_CONFIG['chunk_size_default']
                break

            try:
                chunk_size = int(chunk_input)
                if chunk_size < ADMIN_CONFIG['chunk_size_min']:
                    print(f"❌ Chunk size must be at least {ADMIN_CONFIG['chunk_size_min']} characters.")
                    continue
                elif chunk_size > ADMIN_CONFIG['chunk_size_max']:
                    print(f"❌ Chunk size is recommended to be at most {ADMIN_CONFIG['chunk_size_max']} characters.")
                    continue
                break
            except ValueError:
                print("❌ Please enter a valid number.")

        # Chunk overlap input
        while True:
            default_overlap = int(chunk_size * ADMIN_CONFIG['chunk_overlap_ratio'])  # Configured ratio
            overlap_input = input(f"🔄 Enter chunk overlap (default: {default_overlap}, {int(ADMIN_CONFIG['chunk_overlap_ratio']*100)}% of size): ").strip()
            if not overlap_input:
                chunk_overlap = default_overlap
                break

            try:
                chunk_overlap = int(overlap_input)
                if chunk_overlap < 0:
                    print("❌ Overlap must be 0 or greater.")
                    continue
                elif chunk_overlap >= chunk_size:
                    print(f"❌ Overlap must be less than chunk size ({chunk_size} characters).")
                    continue
                break
            except ValueError:
                print("❌ Please enter a valid number.")

        print(f"\n✅ Custom settings: size {chunk_size:,} characters, overlap {chunk_overlap} characters")
        return chunk_size, chunk_overlap

def main():
    print("🔧 Spec Document Knowledge Base Manager")
    print("=" * 60)

    admin = KnowledgeBaseAdmin()

    while True:
        print("\n📋 Menu:")
        print("1. Build new knowledge base (BGE-M3 optimized)")
        print("2. View knowledge base list")
        print("3. Check knowledge base status")
        print("4. Delete knowledge base")
        print("5. Exit")

        choice = input("\nSelect (1-5): ").strip()

        if choice == '1':
            kb_name = admin.get_valid_kb_name()
            pdf_path = input("📄 Enter Spec PDF file path: ").strip()

            if pdf_path:
                # BGE-M3 optimized chunk settings (token-based)
                from ..config import VECTOR_DB_CONFIG
                chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
                overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
                chars_per_token = VECTOR_DB_CONFIG.get('chars_per_token', 4)

                # Character-based calculation (for fallback display)
                chunk_size = chunk_tokens * chars_per_token
                chunk_overlap = int(chunk_size * overlap_ratio)

                print(f"\n📏 Chunk settings (BGE-M3): {chunk_tokens} tokens ({chunk_size} chars), Overlap: {int(overlap_ratio*100)}% ({chunk_overlap} chars)")

                # Check if overwriting existing knowledge base
                if kb_name in get_kb_list_sync():
                    overwrite = input(f"⚠️ Knowledge base '{kb_name}' already exists. Overwrite? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        print("❌ Build cancelled.")
                        continue

                admin.build_knowledge_base(kb_name, pdf_path, chunk_size, chunk_overlap)
            else:
                print("❌ Please enter a file path.")

        elif choice == '2':
            admin.list_knowledge_bases()

        elif choice == '3':
            kb_list = get_kb_list_sync()
            if not kb_list:
                print("❌ No registered knowledge bases.")
                continue

            print("\nAvailable knowledge bases:")
            for i, kb_name in enumerate(kb_list, 1):
                print(f"{i}. {kb_name}")

            choice_kb = input("\nEnter knowledge base number to check (all: Enter): ").strip()
            if choice_kb:
                try:
                    kb_index = int(choice_kb) - 1
                    if 0 <= kb_index < len(kb_list):
                        admin.check_knowledge_base_status(kb_list[kb_index])
                    else:
                        print("❌ Please enter a valid number.")
                except ValueError:
                    print("❌ Please enter a number.")
            else:
                admin.check_knowledge_base_status()

        elif choice == '4':
            kb_list = get_kb_list_sync()
            if not kb_list:
                print("❌ No knowledge bases to delete.")
                continue

            print("\nAvailable knowledge bases:")
            for i, kb_name in enumerate(kb_list, 1):
                print(f"{i}. {kb_name}")

            choice_kb = input("\nEnter knowledge base number to delete: ").strip()
            try:
                kb_index = int(choice_kb) - 1
                if 0 <= kb_index < len(kb_list):
                    admin.delete_knowledge_base(kb_list[kb_index])
                else:
                    print("❌ Please enter a valid number.")
            except ValueError:
                print("❌ Please enter a number.")

        elif choice == '5':
            print("👋 Exiting manager program.")
            break

        else:
            print("❌ Please select a valid menu option.")

if __name__ == "__main__":
    main()
