import chromadb
import os
import threading
from typing import List, Dict, Optional
from ..config import VECTOR_DB_CONFIG
from ..utils import get_kb_path
from ..models import SearchIntensity
from .rerank import ReRanker

# ChromaDBManager class removed - each VectorStore instance uses independent client

class VectorStore:
    def __init__(self, kb_name: str):
        # Select TEI or local embedding function
        config = VECTOR_DB_CONFIG
        if config.get('tei_enabled', False):
            from .tei_embedding import TEIEmbeddingFunction
            self.embedding_function = TEIEmbeddingFunction(
                base_url=config.get('tei_base_url', 'http://localhost:8080'),
                timeout=config.get('tei_timeout', 30)
            )
        else:
            # Use local sentence-transformers
            self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=config.get('local_embedding_model', 'all-MiniLM-L6-v2')
            )

        self.kb_name = kb_name
        self.db_path = get_kb_path(kb_name)

        # Lazy initialization - access ChromaDB files only when actually used
        self.client = None
        self.collection = None
        self._closed = False
    
    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically close connection"""
        self.close()
        return False

    def close(self):
        """Explicitly close ChromaDB connection (includes SQLite WAL checkpoint)"""
        if self._closed:
            return

        try:
            # Force SQLite WAL checkpoint (ensure write completion)
            import sqlite3
            db_file = os.path.join(self.db_path, 'chroma.sqlite3')
            if os.path.exists(db_file):
                try:
                    conn = sqlite3.connect(db_file, timeout=10.0)
                    conn.execute('PRAGMA wal_checkpoint(FULL);')  # Merge WAL file
                    conn.commit()
                    conn.close()
                except Exception as checkpoint_err:
                    print(f"⚠️ WAL checkpoint failed (ignored): {checkpoint_err}")

            # Remove collection and client references
            self.collection = None
            if self.client is not None:
                # ChromaDB client has no explicit close, just remove reference
                self.client = None

            # Force garbage collection (2 times)
            import gc
            gc.collect()
            import time
            time.sleep(0.05)  # Wait for file handle release
            gc.collect()

            self._closed = True
            print(f"✅ VectorStore '{self.kb_name}' connection closed (WAL checkpoint completed)")
        except Exception as e:
            print(f"⚠️ Error closing VectorStore '{self.kb_name}': {e}")
        
    def get_collection(self):
        """Return collection with lazy initialization (concurrency issues resolved)"""
        if self.collection is None:
            # Create independent ChromaDB client for each VectorStore instance
            if self.client is None:
                os.makedirs(self.db_path, exist_ok=True)
                # Attempt database open with retry to prevent concurrent access conflicts
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        # ChromaDB settings: SQLite concurrency improvement
                        settings = chromadb.Settings(
                            allow_reset=True,
                            anonymized_telemetry=False,
                            # SQLite WAL mode is automatically set (ChromaDB internal)
                        )
                        self.client = chromadb.PersistentClient(
                            path=self.db_path,
                            settings=settings
                        )

                        # Set SQLite busy_timeout (mitigate readonly errors)
                        # Direct access to ChromaDB's internal SQLite connection
                        import sqlite3
                        db_file = os.path.join(self.db_path, 'chroma.sqlite3')
                        if os.path.exists(db_file):
                            conn = sqlite3.connect(db_file, timeout=30.0)
                            conn.execute('PRAGMA journal_mode=WAL;')  # Force WAL mode
                            conn.execute('PRAGMA busy_timeout=30000;')  # 30 second wait
                            conn.close()

                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️ ChromaDB client creation attempt {attempt + 1}/{max_retries} failed (KB: {self.kb_name}): {e}")
                            import time
                            time.sleep(0.2 * (2 ** attempt))  # Exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s
                        else:
                            raise e

            # Apply retry logic to collection access
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    self.collection = self.client.get_or_create_collection(
                        name="spec_documents",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self.embedding_function
                    )
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    is_readonly = 'readonly' in error_msg or 'locked' in error_msg

                    if is_readonly and attempt < max_retries - 1:
                        print(f"⚠️ DB locked/readonly error - retry {attempt + 1}/{max_retries} (KB: {self.kb_name})")
                        import time
                        time.sleep(0.5 * (2 ** attempt))  # Exponential backoff: 0.5s, 1s, 2s, 4s

                        # Complete client recreation
                        self.client = None
                        import gc
                        gc.collect()  # Force garbage collection
                        time.sleep(0.1)  # Wait for file handle release

                        # Recreate
                        settings = chromadb.Settings(
                            allow_reset=True,
                            anonymized_telemetry=False,
                        )
                        self.client = chromadb.PersistentClient(
                            path=self.db_path,
                            settings=settings
                        )
                    elif attempt < max_retries - 1:
                        print(f"⚠️ Collection access attempt {attempt + 1}/{max_retries} failed (KB: {self.kb_name}): {e}")
                        import time
                        time.sleep(0.2 * (2 ** attempt))
                    else:
                        raise e

        return self.collection

    def store_chunks(self, chunks: List[Dict], max_retries: int = 3) -> None:
        """Store chunks to vector DB (includes retry logic)"""
        print(f"💾 Storing {len(chunks)} chunks to knowledge base '{self.kb_name}'...")

        import time
        import sqlite3

        for attempt in range(max_retries):
            try:
                collection = self.get_collection()

                # Delete existing data (safe method: query existing IDs then delete)
                try:
                    existing_data = collection.get()
                    if existing_data and existing_data['ids']:
                        collection.delete(ids=existing_data['ids'])
                        print(f"🗑️  Deleted {len(existing_data['ids'])} existing chunks")
                except Exception as e:
                    print(f"⚠️ Error deleting existing data (ignoring and continuing): {e}")

                ids = [f"chunk_{chunk['id']}" for chunk in chunks]
                documents = [chunk['content'] for chunk in chunks]
                embeddings = [chunk['embedding'] for chunk in chunks]
                metadatas = [{'length': chunk['length'], 'chunk_id': chunk['id']} for chunk in chunks]

                # Store in batches (ChromaDB limit)
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    end_idx = min(i + batch_size, len(chunks))

                    collection.add(
                        ids=ids[i:end_idx],
                        documents=documents[i:end_idx],
                        embeddings=embeddings[i:end_idx],
                        metadatas=metadatas[i:end_idx]
                    )

                print(f"✅ Knowledge base '{self.kb_name}' storage complete!")
                return  # Exit on success

            except (sqlite3.OperationalError, Exception) as e:
                error_msg = str(e).lower()
                is_db_error = 'readonly' in error_msg or 'locked' in error_msg or 'database' in error_msg

                if is_db_error and attempt < max_retries - 1:
                    print(f"⚠️ DB write error occurred - retry {attempt + 1}/{max_retries}: {e}")
                    time.sleep(1.0 * (2 ** attempt))  # 1s, 2s wait

                    # Reinitialize collection
                    self.collection = None
                    self.client = None
                    import gc
                    gc.collect()
                    time.sleep(0.2)
                else:
                    raise Exception(f"Knowledge base storage failed ({attempt + 1} attempts): {e}")

    async def _search_initial_chunks(self, query: str, top_k: int, similarity_threshold: float = 0.0) -> List[str]:
        """Internal helper function for initial vector search (async improved version)

        Args:
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity (0.0~1.0, cosine similarity)
        """
        print(f"🔍 Searching keyword '{query}' in knowledge base '{self.kb_name}'... (top_k={top_k}, threshold={similarity_threshold:.2f})")

        try:
            # Access collection asynchronously
            import asyncio
            collection = await asyncio.get_event_loop().run_in_executor(
                None, self.get_collection
            )

            # Also query count asynchronously
            collection_count = await asyncio.get_event_loop().run_in_executor(
                None, collection.count
            )

            if collection_count == 0:
                print("❌ Knowledge base is empty.")
                return []

            actual_top_k = min(top_k, collection_count)

            # Also run vector search asynchronously
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.query(
                    query_texts=[query],
                    n_results=actual_top_k,
                    include=['documents', 'distances']
                )
            )

            if not results['documents'] or not results['documents'][0]:
                print("❌ No related documents found.")
                return []

            chunks = results['documents'][0]
            distances = results['distances'][0] if results['distances'] else []

            # Output distance info (ChromaDB cosine distance: 0=identical, 2=opposite)
            if distances:
                print(f"🔍 Similarity range for {len(chunks)} searched chunks: {1-max(distances):.3f} ~ {1-min(distances):.3f} (cosine similarity)")
            else:
                print(f"📚 Found {len(chunks)} chunks")

            # Similarity threshold filtering (based on cosine similarity)
            if similarity_threshold > 0.0 and distances:
                # Convert cosine distance to similarity: similarity = 1 - distance
                filtered_chunks = [
                    chunk for chunk, distance in zip(chunks, distances)
                    if (1 - distance) >= similarity_threshold
                ]

                print(f"📚 Found {len(filtered_chunks)} related chunks after threshold {similarity_threshold:.2f} filtering (out of {len(chunks)} total)")

                # Return at least 1 most similar chunk if no chunks pass threshold (prevent empty result)
                if not filtered_chunks and chunks:
                    best_similarity = 1 - distances[0]
                    print(f"⚠️ No chunks passed threshold, returning 1 most similar (similarity: {best_similarity:.3f})")
                    filtered_chunks = [chunks[0]]

                return filtered_chunks
            else:
                # Return all when threshold is not used
                return chunks

        except Exception as e:
            print(f"⚠️ Error during initial search: {e}")
            return []

    async def search(
        self,
        query: str,
        search_intensity: str,
        rerank_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        Unified search method - consolidates common logic

        Args:
            query: Search query
            search_intensity: Search intensity
            rerank_info: Rerank info {"provider": "openai", "model": "gpt-3.5-turbo"}

        Returns:
            Dict with 'chunks' (search results), 'total_chunks' (total chunk count), 'found_chunks' (found chunk count)
        """
        # Get total chunk count
        import asyncio
        collection = await asyncio.get_event_loop().run_in_executor(
            None, self.get_collection
        )
        total_chunks = await asyncio.get_event_loop().run_in_executor(
            None, collection.count
        )

        # Common: Set search parameters (Top-K + Similarity Threshold)
        search_params = SearchIntensity.get_search_params(search_intensity)

        top_k_init = search_params["init"]
        similarity_threshold = search_params.get("similarity_threshold", 0.0)

        print(f"🎯 Search intensity: {search_intensity} (initial {top_k_init}, similarity {similarity_threshold:.2f}+)")

        # More initial search when using rerank, otherwise return only init count
        if rerank_info:
            initial_chunks = await self._search_initial_chunks(query, top_k_init, similarity_threshold)

            if not initial_chunks:
                return {"chunks": [], "total_chunks": total_chunks, "found_chunks": 0}

            top_k_final = search_params["final"]
            try:
                reranker = ReRanker(provider=rerank_info["provider"], model=rerank_info["model"])
                reranked_chunks = await reranker.rerank_documents(query, initial_chunks, top_k_final)
                return {"chunks": reranked_chunks, "total_chunks": total_chunks, "found_chunks": len(reranked_chunks)}
            except Exception as e:
                print(f"⚠️ Error during reranking: {e}. Returning part of initial search results.")
                result_chunks = initial_chunks[:top_k_final]
                return {"chunks": result_chunks, "total_chunks": total_chunks, "found_chunks": len(result_chunks)}
        else:
            # When not using rerank, use init count + threshold filtering
            initial_chunks = await self._search_initial_chunks(query, top_k_init, similarity_threshold)
            return {"chunks": initial_chunks, "total_chunks": total_chunks, "found_chunks": len(initial_chunks)}
    
    async def get_status(self) -> dict:
        """Return knowledge base status info (async improved version)"""
        try:
            import asyncio
            collection = await asyncio.get_event_loop().run_in_executor(
                None, self.get_collection
            )
            count = await asyncio.get_event_loop().run_in_executor(
                None, collection.count
            )
            return {
                'exists': True,
                'count': count,
                'path': self.db_path,
                'name': self.kb_name
            }
        except:
            return {
                'exists': False,
                'count': 0,
                'path': self.db_path,
                'name': self.kb_name
            }
    
    def get_knowledge_bases(self) -> List[str]:
        """Return list of available knowledge bases (recursively search all subdirectories)"""
        try:
            kb_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_bases')
            kb_base_path = os.path.abspath(kb_base_path)

            if not os.path.exists(kb_base_path):
                return []

            knowledge_bases = []

            def scan_directory(current_path: str, relative_path: str = ""):
                """Recursively scan directories - only consider directories with chroma.sqlite3 as KB"""
                try:
                    for item in os.listdir(current_path):
                        item_path = os.path.join(current_path, item)

                        if os.path.isdir(item_path):
                            # Consider as KB if chroma.sqlite3 file exists and size > 0
                            chroma_file = os.path.join(item_path, 'chroma.sqlite3')
                            if os.path.exists(chroma_file):
                                try:
                                    # Check file size (exclude empty files)
                                    file_size = os.path.getsize(chroma_file)
                                    if file_size > 0:
                                        # Store with relative path
                                        if relative_path:
                                            kb_name = f"{relative_path}/{item}"
                                        else:
                                            kb_name = item
                                        knowledge_bases.append(kb_name)
                                    else:
                                        # Ignore empty chroma.sqlite3 file and scan subdirectories
                                        new_relative = f"{relative_path}/{item}" if relative_path else item
                                        scan_directory(item_path, new_relative)
                                except OSError:
                                    # Scan subdirectories if file size check fails
                                    new_relative = f"{relative_path}/{item}" if relative_path else item
                                    scan_directory(item_path, new_relative)
                            else:
                                # Scan subdirectories if chroma.sqlite3 doesn't exist
                                new_relative = f"{relative_path}/{item}" if relative_path else item
                                scan_directory(item_path, new_relative)
                except Exception as e:
                    print(f"Directory scan failed ({current_path}): {e}")

            scan_directory(kb_base_path)
            return sorted(knowledge_bases)

        except Exception as e:
            print(f"Failed to get knowledge base list: {e}")
            return []
    
    async def get_knowledge_base_info(self) -> Dict:
        """Return detailed knowledge base info (includes actual ChromaDB chunk count)"""
        import asyncio

        def get_info_with_chromadb():
            """Query actual chunk count from ChromaDB"""
            exists = os.path.exists(self.db_path)

            actual_count = 0
            if exists:
                try:
                    # Query count from actual ChromaDB collection
                    collection = self.get_collection()
                    actual_count = collection.count()
                except Exception as e:
                    print(f"⚠️ ChromaDB count query failed ({self.kb_name}): {e}")
                    actual_count = 0

            return {
                'name': self.kb_name,
                'count': actual_count,  # Actual chunk count
                'path': self.db_path,
                'exists': exists
            }

        # Run asynchronously to prevent blocking
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, get_info_with_chromadb)
    
    def close(self):
        """Explicitly close ChromaDB connection to release file lock"""
        try:
            if self.collection is not None:
                self.collection = None
            if self.client is not None:
                # Close ChromaDB client connection
                try:
                    # PersistentClient has no explicit close method
                    # Set reference to None and let garbage collection handle it
                    self.client = None
                except Exception as e:
                    print(f"⚠️ Error closing ChromaDB client: {e}")
            print(f"✅ VectorStore '{self.kb_name}' connection closed")
        except Exception as e:
            print(f"⚠️ Error closing VectorStore: {e}")

