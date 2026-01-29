from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import uuid
import os
import shutil
import asyncio
from typing import Dict

# Node-based workflow imports
from ..workflow import NodeExecutionEngine, WorkflowValidator
from ..utils import (
    ErrorResponse, handle_api_errors,
    format_sse_data,
    PathResolver,
    safe_delete_with_retry, safe_rename_with_retry,
    create_secure_marker, remove_secure_marker,
    is_protected, check_protection_before_operation
)
from ..config import LLM_CONFIG
from ..models import (
    WorkflowExecutionRequest,
    WorkflowDefinition,
    KnowledgeBase,
    KnowledgeBaseListResponse,
    SearchIntensity,
    LLMProvider
)
from ..services.vector_store_service import VectorStoreService
from ..services.llm_factory import LLMFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Node-based Workflow API",
    description="Multi-model AI system for requirements extraction using node-based workflows",
    version="2.0.0"
)

# Global lock for file system operations (concurrency issue resolution)
fs_lock = asyncio.Lock()

# VectorStoreService instance tracking (for closing connections on KB delete/rename)
_active_vector_services: Dict[int, VectorStoreService] = {}

def register_vector_service(service: VectorStoreService):
    """Register VectorStoreService instance"""
    service_id = id(service)
    _active_vector_services[service_id] = service
    return service_id

def close_kb_in_all_services(kb_name: str):
    """Close connections for a specific KB in all active VectorStoreServices"""
    import gc
    for service_id, service in list(_active_vector_services.items()):
        try:
            service.close_and_remove_kb(kb_name)
        except Exception as e:
            logger.warning(f"Failed to close KB '{kb_name}' (service {service_id}): {e}")
    # Force garbage collection
    gc.collect()
    logger.info(f"KB '{kb_name}' connections closed in all services")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (stateless services only)
validator = WorkflowValidator()
# vector_store_service is created per request

# Active workflow executions tracking (multi-user support)
active_executions: Dict[str, NodeExecutionEngine] = {}

@app.get("/")
async def health():
    return {"status": "Node-based workflow API is running", "version": "2.0.0"}

@app.post("/validate-workflow")
@handle_api_errors(default_status=500)
async def validate_workflow(workflow: WorkflowDefinition):
    """Workflow validation (based on project_reference.md connection rules)"""
    result = validator.validate_workflow(workflow)
    return result

@app.post("/execute-workflow-stream")
async def execute_workflow_stream(request: WorkflowExecutionRequest):
    """
    Node-based workflow execution (streaming)
    Streams LLM responses in real-time while also returning final parsed results
    """
    # Generate unique execution ID for this workflow
    execution_id = str(uuid.uuid4())

    async def generate_stream():
        execution_engine = None
        try:
            logger.info(f"Starting streaming workflow execution {execution_id} with {len(request.workflow.nodes)} nodes")

            # Create and register execution engine
            execution_engine = NodeExecutionEngine()
            active_executions[execution_id] = execution_engine
            logger.info(f"Registered execution {execution_id} for stop control")

            # Send execution_id as first event
            yield format_sse_data({
                'type': 'execution_started',
                'execution_id': execution_id,
                'message': 'Workflow execution started'
            })

            # Pre-execution validation
            validation_result = validator.validate_workflow(request.workflow)
            if not validation_result["valid"]:
                error_details = {
                    'type': 'validation_error',
                    'message': 'Workflow validation failed',
                    'errors': validation_result['errors'],
                    'warnings': validation_result.get('warnings', [])
                }
                yield format_sse_data(error_details)
                return

            # Execute workflow with streaming (using independent instance)
            async for chunk in execution_engine.execute_workflow_stream(
                workflow=request.workflow
            ):
                yield format_sse_data(chunk)

                # Terminate stream on completion or error
                if chunk.get('type') in ['complete', 'error']:
                    logger.info(f"Stream terminated with event: {chunk.get('type')}")
                    break

        except Exception as e:
            logger.error(f"Streaming workflow execution {execution_id} failed: {e}")
            yield format_sse_data({'type': 'error', 'message': str(e)})
        finally:
            # Cleanup on execution completion
            if execution_id in active_executions:
                del active_executions[execution_id]
                logger.info(f"Cleaned up execution {execution_id}")

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/stop-workflow/{execution_id}")
async def stop_workflow(execution_id: str):
    """
    Stop workflow execution

    Stops the workflow with the specified execution_id.
    Currently executing nodes will complete, but new node execution will be stopped.
    Stop requests for already completed or non-existent workflows are also treated as success.
    """
    try:
        if execution_id not in active_executions:
            logger.info(f"Execution {execution_id} not found or already completed")
            return {
                "success": True,
                "message": "Workflow has already completed or been stopped."
            }

        # Set stop flag
        active_executions[execution_id].stop()
        logger.info(f"Stop signal sent to execution {execution_id}")

        return {
            "success": True,
            "message": "Stop request sent. Executing nodes will complete before stopping."
        }
    except Exception as e:
        logger.error(f"Failed to stop workflow {execution_id}: {e}")
        # Treat as success even on exception
        return {
            "success": True,
            "message": "Workflow stop has been requested."
        }

@app.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """List knowledge bases"""
    try:
        # Create independent VectorStoreService per request and register
        vector_store_service = VectorStoreService()
        register_vector_service(vector_store_service)
        knowledge_bases = []
        kb_names = await vector_store_service.get_knowledge_bases()

        # Async parallel processing for knowledge base info retrieval (performance improvement and blocking prevention)
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        async def get_kb_info_safe(name: str):
            try:
                # Use independent VectorStoreService instance for each KB
                kb_vector_service = VectorStoreService()
                register_vector_service(kb_vector_service)
                kb_info = await kb_vector_service.get_knowledge_base_info(name)
                return KnowledgeBase(
                    name=kb_info['name'],
                    chunk_count=kb_info.get('count', 0),  # VectorStore uses 'count'
                    created_at=kb_info.get('created_at', 'Unknown')  # Unknown if no creation date
                )
            except Exception as e:
                logger.warning(f"Failed to get info for KB {name}: {e}")
                # Add with default values even on error
                return KnowledgeBase(
                    name=name,
                    chunk_count=0,  # Default value
                    created_at="Unknown"
                )

        # Query all KB info in parallel
        knowledge_bases = await asyncio.gather(*[get_kb_info_safe(name) for name in kb_names])

        return KnowledgeBaseListResponse(knowledge_bases=knowledge_bases)

    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        raise ErrorResponse.internal_error(f"Failed to list knowledge bases: {str(e)}")

@app.get("/knowledge-bases/structure")
async def get_knowledge_base_structure():
    """Return knowledge base directory structure (including folders)"""
    try:
        kb_base_path = PathResolver.get_kb_base_path()

        if not os.path.exists(kb_base_path):
            return {"structure": {}}

        structure = {}

        def scan_directory_structure(current_path: str, relative_path: str = "", parent_id: str = "root"):
            """Recursively scan directory structure"""
            try:
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)

                    if os.path.isdir(item_path):
                        # Skip if .delete_marker exists (considered deleted)
                        delete_marker = os.path.join(item_path, '.delete_marker')
                        if os.path.exists(delete_marker):
                            continue  # Exclude deleted folders/KBs from structure

                        # Determine folder by .folder_marker file
                        folder_marker = os.path.join(item_path, '.folder_marker')
                        chroma_file = os.path.join(item_path, 'chroma.sqlite3')

                        is_folder = os.path.exists(folder_marker)

                        # KB determination: If no .folder_marker and has chroma.sqlite3, it's a KB
                        # If determined as folder, cannot be KB
                        is_kb = False
                        chunk_count = 0

                        if not is_folder:
                            if os.path.exists(chroma_file):
                                try:
                                    file_size = os.path.getsize(chroma_file)
                                    # KB if chroma.sqlite3 exists and size > 0
                                    if file_size > 0:
                                        is_kb = True
                                        # Get KB chunk count (auto-close with context manager)
                                        try:
                                            from ..services.vector_store import VectorStore
                                            new_relative = f"{relative_path}/{item}" if relative_path else item
                                            with VectorStore(new_relative) as vector_store:
                                                collection = vector_store.get_collection()
                                                chunk_count = collection.count()
                                            logger.info(f"KB '{new_relative}' has {chunk_count} chunks")
                                        except Exception as e:
                                            logger.warning(f"Failed to get chunk count for {item}: {e}")
                                            chunk_count = 0
                                except OSError as e:
                                    logger.warning(f"Failed to check chroma file size for {item}: {e}")
                                    pass

                        # Calculate relative path (prevent duplicates)
                        if not is_kb:  # Only calculate here if not KB
                            new_relative = f"{relative_path}/{item}" if relative_path else item

                        # Check protection status
                        secure_marker = os.path.join(item_path, '.secure_marker')
                        item_is_protected = os.path.exists(secure_marker)

                        item_id = f"{'kb' if is_kb else 'folder'}_{new_relative.replace('/', '_')}"

                        if is_kb:
                            # Treat as KB
                            structure[item_id] = {
                                "type": "kb",
                                "name": item,
                                "parent": parent_id,
                                "actualKbName": new_relative,
                                "chunkCount": chunk_count,
                                "isProtected": item_is_protected
                            }
                        else:
                            # Treat as folder (may be empty)
                            structure[item_id] = {
                                "type": "folder",
                                "name": item,
                                "parent": parent_id,
                                "isProtected": item_is_protected
                            }
                            # Scan subdirectories
                            scan_directory_structure(item_path, new_relative, item_id)
            except Exception as e:
                logger.error(f"Directory scan failed ({current_path}): {e}")

        scan_directory_structure(kb_base_path)
        return {"structure": structure}

    except Exception as e:
        logger.error(f"Failed to get knowledge base structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/create-folder")
async def create_folder(request: dict):
    """Create folder (concurrency safe)"""
    async with fs_lock:  # Acquire lock
        try:
            folder_path = request.get("folder_path", "")

            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")

            kb_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_bases')
            kb_base_path = os.path.abspath(kb_base_path)

            # Create full path
            full_path = os.path.join(kb_base_path, folder_path)

            # Check if already exists (recheck inside lock)
            if os.path.exists(full_path):
                # Allow recreation if .delete_marker exists (deleted folder)
                delete_marker = os.path.join(full_path, '.delete_marker')
                if os.path.exists(delete_marker):
                    # Remove delete marker (restore folder)
                    os.remove(delete_marker)
                    logger.info(f"Restoring previously deleted folder: '{folder_path}'")
                else:
                    raise HTTPException(status_code=409, detail=f"Folder '{folder_path}' already exists")

            # Create folder
            os.makedirs(full_path, exist_ok=False)

            # Create .folder_marker file (to distinguish from ChromaDB)
            marker_file = os.path.join(full_path, '.folder_marker')
            with open(marker_file, 'w') as f:
                f.write('This is a user-created folder, not a knowledge base.')

            logger.info(f"Folder created with marker: '{folder_path}'")

            return {
                "success": True,
                "message": f"Folder '{folder_path}' created successfully",
                "folder_path": folder_path
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            raise ErrorResponse.internal_error(f"Failed to create folder: {str(e)}")

@app.post("/knowledge-bases/delete-folder")
async def delete_folder(request: dict):
    """Delete folder (soft delete: create .delete_marker file)"""
    try:
        folder_path = request.get("folder_path", "")

        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")

        # Create full path
        full_path = PathResolver.resolve_folder_path(folder_path)

        # Check existence
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")

        if not os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")

        # Protection check (cannot delete protected folder or folder with protected content)
        check_protection_before_operation(full_path, "delete", is_folder=True)

        # Soft delete: create .delete_marker file
        delete_marker_path = os.path.join(full_path, '.delete_marker')
        try:
            with open(delete_marker_path, 'w') as f:
                import datetime
                f.write(f"Deleted at: {datetime.datetime.now().isoformat()}\n")
            logger.info(f"Folder soft-deleted (marker created): '{folder_path}'")
        except Exception as e:
            logger.error(f"Failed to create delete marker for folder '{folder_path}': {e}")
            raise HTTPException(status_code=500, detail=f"Cannot mark folder as deleted: {str(e)}")

        return {
            "success": True,
            "message": f"Folder '{folder_path}' deleted successfully",
            "folder_path": folder_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-knowledge-base")
async def search_knowledge_base(request: dict):
    """Search knowledge base"""
    try:
        query = request.get("query", "")
        knowledge_base = request.get("knowledge_base", "")
        top_k = request.get("top_k", 5)

        if not query or not knowledge_base:
            raise HTTPException(status_code=400, detail="Query and knowledge_base are required")

        # Map top_k to search_intensity
        search_intensity = SearchIntensity.from_top_k(top_k)

        # Create independent VectorStoreService per request and register
        vector_store_service = VectorStoreService()
        register_vector_service(vector_store_service)
        results = await vector_store_service.search(
            kb_name=knowledge_base,
            query=query,
            search_intensity=search_intensity,
            rerank_info=None  # Rerank disabled by default
        )

        return {
            "results": results,
            "query": query,
            "knowledge_base": knowledge_base,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/delete")
async def delete_knowledge_base(request: dict):
    """Delete knowledge base (soft delete: create .delete_marker file)"""
    try:
        kb_name = request.get("kb_name", "")

        if not kb_name:
            raise HTTPException(status_code=400, detail="kb_name is required")

        from ..utils import get_kb_path

        kb_path = get_kb_path(kb_name)

        logger.info(f"KB Delete request - kb_name: '{kb_name}'")
        logger.info(f"Resolved kb_path: '{kb_path}', exists: {os.path.exists(kb_path)}")

        # Check existence
        if not os.path.exists(kb_path):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found at '{kb_path}'")

        # Protection check (cannot delete protected KB)
        check_protection_before_operation(kb_path, "delete", is_folder=False)

        # Soft delete: create .delete_marker file
        delete_marker_path = os.path.join(kb_path, '.delete_marker')
        try:
            with open(delete_marker_path, 'w') as f:
                import datetime
                f.write(f"Deleted at: {datetime.datetime.now().isoformat()}\n")
            logger.info(f"Knowledge base '{kb_name}' soft-deleted (marker created)")
        except Exception as e:
            logger.error(f"Failed to delete '{kb_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot delete knowledge base: files are in use. Please close any applications using them and try again. Error: {str(e)}"
            )

        return {
            "success": True,
            "message": f"Knowledge base '{kb_name}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge base '{kb_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/knowledge-bases/rename-folder")
async def rename_folder(request: dict):
    """Rename folder (concurrency safe)"""
    try:
        old_path = request.get("old_path", "")
        new_name = request.get("new_name", "")

        if not old_path or not new_name:
            raise HTTPException(status_code=400, detail="old_path and new_name are required")

        # Create full path
        full_old_path = PathResolver.resolve_folder_path(old_path)

        # Check existence
        if not os.path.exists(full_old_path):
            raise HTTPException(status_code=404, detail=f"Folder '{old_path}' not found")

        if not os.path.isdir(full_old_path):
            raise HTTPException(status_code=400, detail=f"'{old_path}' is not a folder")

        # Cannot rename deleted folder
        delete_marker = os.path.join(full_old_path, '.delete_marker')
        if os.path.exists(delete_marker):
            raise HTTPException(status_code=404, detail=f"Folder '{old_path}' has been deleted")

        # Protection check (cannot rename protected folder or folder with protected content)
        check_protection_before_operation(full_old_path, "rename", is_folder=True)

        # Calculate new path (within same parent directory)
        parent_dir = os.path.dirname(full_old_path)
        full_new_path = os.path.join(parent_dir, new_name)

        # Check if new name already exists
        if os.path.exists(full_new_path):
            raise HTTPException(status_code=409, detail=f"Folder or KB '{new_name}' already exists in the same location")

        # Copy and soft delete original for rename (avoid ChromaDB lock issues)
        try:
            # 1. Copy entire folder
            shutil.copytree(full_old_path, full_new_path)
            logger.info(f"Folder copied: '{full_old_path}' -> '{full_new_path}'")

            # 2. Remove .delete_marker from copy if exists
            copy_delete_marker = os.path.join(full_new_path, '.delete_marker')
            if os.path.exists(copy_delete_marker):
                os.remove(copy_delete_marker)

            # 3. Create .delete_marker in original (soft delete)
            import datetime
            original_delete_marker = os.path.join(full_old_path, '.delete_marker')
            with open(original_delete_marker, 'w') as f:
                f.write(f"Renamed to '{new_name}' at: {datetime.datetime.now().isoformat()}\n")

            logger.info(f"Folder renamed (copy+soft delete): '{old_path}' -> '{new_name}'")

        except Exception as e:
            # Clean up copy on failure
            if os.path.exists(full_new_path):
                try:
                    shutil.rmtree(full_new_path, ignore_errors=True)
                except:
                    pass
            logger.error(f"Failed to rename folder '{old_path}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot rename folder: {str(e)}"
            )

        # Calculate new relative path
        new_relative_path = PathResolver.to_relative_path(full_new_path)

        logger.info(f"Folder renamed: '{old_path}' -> '{new_relative_path}'")

        return {
            "success": True,
            "message": f"Folder renamed successfully",
            "old_path": old_path,
            "new_path": new_relative_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/rename")
async def rename_knowledge_base(request: dict):
    """Rename knowledge base (within same directory only, concurrency safe)"""
    try:
        old_name = request.get("old_name", "")
        new_name = request.get("new_name", "")

        if not old_name or not new_name:
            raise HTTPException(status_code=400, detail="old_name and new_name are required")

        if old_name == new_name:
            raise HTTPException(status_code=400, detail="New name must be different from old name")

        from ..utils import get_kb_path

        old_path = get_kb_path(old_name)

        logger.info(f"KB Rename request - old_name: '{old_name}', new_name: '{new_name}'")
        logger.info(f"Resolved old_path: '{old_path}', exists: {os.path.exists(old_path)}")

        if not os.path.exists(old_path):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{old_name}' not found at '{old_path}'")

        # Cannot rename deleted KB
        delete_marker = os.path.join(old_path, '.delete_marker')
        if os.path.exists(delete_marker):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{old_name}' has been deleted")

        # Protection check (cannot rename protected KB)
        check_protection_before_operation(old_path, "rename", is_folder=False)

        # Rename only within same parent directory
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)

        logger.info(f"Target new_path: '{new_path}'")

        if os.path.exists(new_path):
            raise HTTPException(status_code=409, detail=f"Knowledge base '{new_name}' already exists")

        # Copy and soft delete original for rename (avoid ChromaDB lock issues)
        try:
            # 1. Copy entire KB directory
            shutil.copytree(old_path, new_path)
            logger.info(f"KB copied: '{old_path}' -> '{new_path}'")

            # 2. Remove .delete_marker and .secure_marker from copy if exists
            copy_delete_marker = os.path.join(new_path, '.delete_marker')
            if os.path.exists(copy_delete_marker):
                os.remove(copy_delete_marker)

            # 3. Create .delete_marker in original (soft delete)
            import datetime
            original_delete_marker = os.path.join(old_path, '.delete_marker')
            with open(original_delete_marker, 'w') as f:
                f.write(f"Renamed to '{new_name}' at: {datetime.datetime.now().isoformat()}\n")

            logger.info(f"Knowledge base renamed (copy+soft delete): '{old_name}' -> '{new_name}'")

        except Exception as e:
            # Clean up copy on failure
            if os.path.exists(new_path):
                try:
                    shutil.rmtree(new_path, ignore_errors=True)
                except:
                    pass
            logger.error(f"Failed to rename KB '{old_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot rename knowledge base: {str(e)}"
            )

        # Calculate new relative path
        new_relative_path = PathResolver.to_relative_path(new_path)

        logger.info(f"Knowledge base renamed: '{old_name}' -> '{new_relative_path}'")

        return {
            "success": True,
            "message": f"Knowledge base renamed successfully",
            "old_name": old_name,
            "new_name": new_relative_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename knowledge base '{old_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/knowledge-bases/move-folder")
async def move_folder(request: dict):
    """Move folder to another folder (concurrency safe)"""
    async with fs_lock:
        try:
            old_path = request.get("old_path", "")
            target_folder = request.get("target_folder", "")

            if not old_path:
                raise HTTPException(status_code=400, detail="old_path is required")

            # Full path of folder to move
            full_old_path = PathResolver.resolve_folder_path(old_path)

            logger.info(f"Folder Move request - old_path: '{old_path}', target_folder: '{target_folder}'")
            logger.info(f"Resolved full_old_path: '{full_old_path}', exists: {os.path.exists(full_old_path)}")

            if not os.path.exists(full_old_path):
                raise HTTPException(status_code=404, detail=f"Folder '{old_path}' not found")

            if not os.path.isdir(full_old_path):
                raise HTTPException(status_code=400, detail=f"'{old_path}' is not a folder")

            # Cannot move deleted folder
            delete_marker = os.path.join(full_old_path, '.delete_marker')
            if os.path.exists(delete_marker):
                raise HTTPException(status_code=404, detail=f"Folder '{old_path}' has been deleted")

            # Protection check (cannot move protected folder or folder with protected content)
            check_protection_before_operation(full_old_path, "move", is_folder=True)

            # Calculate target folder path
            target_dir = PathResolver.resolve_folder_path(target_folder) if (target_folder and target_folder != 'root') else PathResolver.get_kb_base_path()

            # Create target folder if not exists
            os.makedirs(target_dir, exist_ok=True)

            # Extract folder name
            folder_basename = os.path.basename(full_old_path)
            new_path = os.path.join(target_dir, folder_basename)

            logger.info(f"Target new_path: '{new_path}'")

            # Check if trying to move to same location
            if os.path.normpath(full_old_path) == os.path.normpath(new_path):
                logger.info(f"Folder is already in target location")
                return {
                    "success": True,
                    "message": f"Folder is already in target location",
                    "old_path": old_path,
                    "new_path": PathResolver.to_relative_path(new_path)
                }

            # Check if new path already exists
            if os.path.exists(new_path):
                raise HTTPException(status_code=409, detail=f"Folder '{folder_basename}' already exists in target location")

            # Check if trying to move into own subfolder
            if new_path.startswith(full_old_path + os.sep):
                raise HTTPException(status_code=400, detail="Cannot move folder into its own subfolder")

            # Calculate new relative path in advance (for logs and error handling)
            new_relative_path = PathResolver.to_relative_path(new_path)

            # Copy and soft delete original for move (avoid ChromaDB lock issues)
            try:
                # 1. Copy entire folder
                shutil.copytree(full_old_path, new_path)
                logger.info(f"Folder copied: '{full_old_path}' -> '{new_path}'")

                # 2. Remove .delete_marker from copy if exists
                copy_delete_marker = os.path.join(new_path, '.delete_marker')
                if os.path.exists(copy_delete_marker):
                    os.remove(copy_delete_marker)

                # 3. Create .delete_marker in original (soft delete)
                import datetime
                original_delete_marker = os.path.join(full_old_path, '.delete_marker')
                with open(original_delete_marker, 'w') as f:
                    target_name = target_folder if target_folder else 'root'
                    f.write(f"Moved to '{target_name}' at: {datetime.datetime.now().isoformat()}\n")

                logger.info(f"Folder moved (copy+soft delete): '{old_path}' -> '{new_relative_path}'")

            except Exception as e:
                # Clean up copy on failure
                if os.path.exists(new_path):
                    try:
                        shutil.rmtree(new_path, ignore_errors=True)
                    except:
                        pass
                logger.error(f"Failed to move folder: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Cannot move folder: {str(e)}"
                )

            return {
                "success": True,
                "message": f"Folder moved successfully",
                "old_path": old_path,
                "new_path": new_relative_path
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to move folder: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/move")
async def move_knowledge_base(request: dict):
    """Move knowledge base to another folder (concurrency safe)"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            target_folder = request.get("target_folder", "")

            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")

            from ..utils import get_kb_path

            old_path = get_kb_path(kb_name)

            logger.info(f"KB Move request - kb_name: '{kb_name}', target_folder: '{target_folder}'")
            logger.info(f"Resolved old_path: '{old_path}'")
            logger.info(f"Path exists: {os.path.exists(old_path)}")

            if not os.path.exists(old_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found at '{old_path}'")

            # Cannot move deleted KB
            delete_marker = os.path.join(old_path, '.delete_marker')
            if os.path.exists(delete_marker):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' has been deleted")

            # Protection check (cannot move protected KB)
            check_protection_before_operation(old_path, "move", is_folder=False)

            # Create target folder path
            target_dir = PathResolver.resolve_folder_path(target_folder) if (target_folder and target_folder != 'root') else PathResolver.get_kb_base_path()

            # Create target folder if not exists
            os.makedirs(target_dir, exist_ok=True)

            # Extract KB name
            kb_basename = os.path.basename(old_path)
            new_path = os.path.join(target_dir, kb_basename)

            logger.info(f"Target new_path: '{new_path}'")

            # Check if trying to move to same location
            if os.path.normpath(old_path) == os.path.normpath(new_path):
                logger.info(f"KB is already in target location")
                return {
                    "success": True,
                    "message": f"Knowledge base is already in target location",
                    "old_path": kb_name,
                    "new_path": PathResolver.to_relative_path(new_path)
                }

            if os.path.exists(new_path):
                raise HTTPException(status_code=409, detail=f"Knowledge base '{kb_basename}' already exists in target folder")

            # Calculate new relative path in advance (for logs and error handling)
            new_relative_path = PathResolver.to_relative_path(new_path)

            # Copy and soft delete original for move (avoid ChromaDB lock issues)
            try:
                # 1. Copy entire KB directory
                shutil.copytree(old_path, new_path)
                logger.info(f"KB copied: '{old_path}' -> '{new_path}'")

                # 2. Remove .delete_marker from copy if exists
                copy_delete_marker = os.path.join(new_path, '.delete_marker')
                if os.path.exists(copy_delete_marker):
                    os.remove(copy_delete_marker)

                # 3. Create .delete_marker in original (soft delete)
                import datetime
                original_delete_marker = os.path.join(old_path, '.delete_marker')
                with open(original_delete_marker, 'w') as f:
                    target_name = target_folder if target_folder else 'root'
                    f.write(f"Moved to '{target_name}' at: {datetime.datetime.now().isoformat()}\n")

                logger.info(f"Knowledge base moved (copy+soft delete): '{kb_name}' -> '{new_relative_path}'")

            except Exception as e:
                # Clean up copy on failure
                if os.path.exists(new_path):
                    try:
                        shutil.rmtree(new_path, ignore_errors=True)
                    except:
                        pass
                logger.error(f"Failed to move KB '{kb_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Cannot move knowledge base: {str(e)}"
                )

            return {
                "success": True,
                "message": f"Knowledge base moved successfully",
                "old_path": kb_name,
                "new_path": new_relative_path
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to move knowledge base '{kb_name}': {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Helper functions for KB creation
def _process_plain_text(text_content: str) -> str:
    """Process plain text"""
    logger.info("Using plain text directly")
    return text_content

def _process_base64_text(text_content_base64: str, doc_processor=None) -> str:
    """Process base64 encoded text (auto-detect binary files)"""
    import base64
    logger.info(f"Processing base64 text content (length: {len(text_content_base64)})...")
    try:
        text_bytes = base64.b64decode(text_content_base64, validate=True)

        # Try UTF-8 text decode
        try:
            text = text_bytes.decode('utf-8')
            logger.info(f"Successfully decoded base64 text (decoded length: {len(text)} chars)")
            return text
        except UnicodeDecodeError:
            # Check PDF magic number if UTF-8 fails
            if text_bytes[:4] == b'%PDF':
                logger.info("Detected PDF file in base64 content, processing as PDF...")
                if doc_processor is None:
                    raise HTTPException(status_code=400, detail="PDF content detected but no document processor available")

                # Process as PDF
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(text_bytes)
                    temp_pdf_path = temp_file.name

                try:
                    text = doc_processor.extract_text_from_pdf(temp_pdf_path)
                    logger.info(f"Extracted text from PDF: {len(text)} characters")
                    return text
                finally:
                    try:
                        os.unlink(temp_pdf_path)
                    except:
                        pass
            else:
                # Try alternative encodings if not PDF
                logger.warning("UTF-8 decode failed, trying alternative encodings...")
                try:
                    text = text_bytes.decode('cp949')  # Korean Windows
                    logger.info(f"Successfully decoded as CP949 (length: {len(text)} chars)")
                    return text
                except UnicodeDecodeError:
                    try:
                        text = text_bytes.decode('latin-1')  # Last resort
                        logger.info(f"Successfully decoded as Latin-1 (length: {len(text)} chars)")
                        return text
                    except Exception as e:
                        logger.error(f"All encoding attempts failed: {e}")
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid text encoding. Content must be UTF-8, CP949, or Latin-1 text, or PDF file."
                        )
    except base64.binascii.Error as e:
        logger.error(f"Base64 decode error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing base64 text: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing base64 content: {str(e)}")

def _process_file_upload(file_content_base64: str, file_type: str, doc_processor) -> str:
    """Process file upload (PDF or TXT)"""
    import base64
    import tempfile

    logger.info(f"Processing {file_type.upper()} file...")

    try:
        file_content = base64.b64decode(file_content_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 file content: {str(e)}")

    if file_type == "pdf":
        # Process PDF file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_pdf_path = temp_file.name

        try:
            text = doc_processor.extract_text_from_pdf(temp_pdf_path)
            logger.info(f"Extracted text from PDF: {len(text)} characters")
            return text
        finally:
            try:
                os.unlink(temp_pdf_path)
            except:
                pass

    elif file_type == "txt":
        # Process TXT file (multi-encoding support)
        try:
            text = file_content.decode('utf-8')
            logger.info(f"Loaded text from TXT file (UTF-8): {len(text)} characters")
        except UnicodeDecodeError:
            try:
                text = file_content.decode('cp949')  # Korean Windows
                logger.info(f"Loaded text from TXT file (CP949): {len(text)} characters")
            except:
                text = file_content.decode('latin-1')  # Last resort
                logger.info(f"Loaded text from TXT file (Latin-1): {len(text)} characters")
        return text

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

@app.post("/knowledge-bases/create")
async def create_knowledge_base(request: dict):
    """Create knowledge base (plain text, base64 text, or file upload) - BGE-M3 optimized"""
    # Extract request parameters
    kb_name_input = request.get("kb_name", "")
    text_content = request.get("text_content", "")
    file_content_base64 = request.get("file_content", "")
    chunk_size = request.get("chunk_size", 8000)
    chunk_overlap = request.get("chunk_overlap", 200)
    target_folder = request.get("target_folder", "")

    # Input validation (outside lock)
    if not kb_name_input:
        raise HTTPException(status_code=400, detail="kb_name is required")

    if not text_content and not file_content_base64:
        raise HTTPException(status_code=400, detail="Either text_content or file_content is required")

    # Use input KB name as-is
    kb_name = kb_name_input

    # Only protect file system operations with lock
    async with fs_lock:
        try:
            if target_folder and target_folder != 'root':
                kb_full_name = f"{target_folder}/{kb_name}"
                kb_dir = PathResolver.resolve_folder_path(target_folder)
            else:
                kb_full_name = kb_name
                kb_dir = PathResolver.get_kb_base_path()

            os.makedirs(kb_dir, exist_ok=True)

            from ..utils import get_kb_path
            kb_path = get_kb_path(kb_full_name)

            logger.info(f"KB Create request - kb_name: '{kb_name}', target_folder: '{target_folder}'")
            logger.info(f"Full KB name: '{kb_full_name}', path: '{kb_path}'")

            if os.path.exists(kb_path):
                raise HTTPException(status_code=409, detail=f"Knowledge base '{kb_name}' already exists in this location")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to setup KB path: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Perform heavy operations after releasing lock
    try:
        # BGE-M3 optimized chunk settings (Token-based)
        from ..config import VECTOR_DB_CONFIG
        chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        chars_per_token = VECTOR_DB_CONFIG.get('chars_per_token', 4)
        overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)

        chunk_size = chunk_tokens * chars_per_token
        chunk_overlap = int(chunk_size * overlap_ratio)

        logger.info(f"Building KB with BGE-M3 settings: {chunk_tokens} tokens ({chunk_size} chars), {int(overlap_ratio*100)}% overlap ({chunk_overlap} chars)")

        # Initialize DocumentProcessor
        from ..services.document_processor import DocumentProcessor
        from ..services.vector_store import VectorStore

        doc_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        # Extract text based on input method
        if file_content_base64:
            # Process file upload
            file_type = request.get("file_type", "pdf")
            logger.info(f"Processing file upload (type: {file_type})")
            text = _process_file_upload(file_content_base64, file_type, doc_processor)

        elif text_content:
            # Process text input
            text_type = request.get("text_type", "plain")
            logger.info(f"Processing text content (type: {text_type}, length: {len(text_content)})")

            if text_type == "base64":
                text = _process_base64_text(text_content, doc_processor)
            else:  # plain
                text = _process_plain_text(text_content)
        else:
            raise HTTPException(status_code=400, detail="No content provided (neither file_content nor text_content)")

        # Text validation
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text content is empty")

        logger.info(f"Text length: {len(text)} characters")

        # Chunking and embedding generation
        logger.info("Starting chunking...")
        chunks = doc_processor.semantic_chunking(text)
        logger.info(f"Created {len(chunks)} chunks")

        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to create chunks from text")

        logger.info("Generating embeddings...")
        chunks_with_embeddings = doc_processor.generate_embeddings(chunks)
        logger.info("Embeddings generated")

        # Store in vector DB (auto-close with context manager, includes retry logic)
        logger.info("Storing in vector database...")
        with VectorStore(kb_full_name) as vector_store:
            vector_store.store_chunks(chunks_with_embeddings)
        logger.info(f"Knowledge base '{kb_full_name}' created successfully with {len(chunks)} chunks")

        # Explicit garbage collection and resource release
        import gc
        gc.collect()

        # Short wait to ensure complete file handle release
        import asyncio
        await asyncio.sleep(0.1)

        return {
            "success": True,
            "message": f"Knowledge base '{kb_name}' created successfully",
            "kb_name": kb_full_name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunk_count": len(chunks)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/available-models/{provider}")
async def get_available_models(provider: str):
    """Return available models by provider"""
    try:
        # Normalize provider
        provider = provider.lower()
        if provider not in LLM_CONFIG["supported_providers"]:
            supported_providers = ", ".join(LLM_CONFIG["supported_providers"])
            raise HTTPException(status_code=400, detail=f"Unsupported provider. Only '{supported_providers}' are supported.")

        # Full parallel processing with independent LLMFactory instance per request
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def get_models_sync():
            """Run synchronous model query in separate thread - prevent blocking"""
            llm_factory = LLMFactory()  # Independent instance per request
            try:
                client = llm_factory.get_client(provider)
                if not client:
                    raise Exception(f"Failed to create client for {provider}")

                if not client.is_available():
                    if provider == LLMProvider.INTERNAL:
                        raise Exception("Internal LLM service is not available. Please check INTERNAL_API_KEY and INTERNAL_API_ENDPOINT environment variables.")
                    else:
                        raise Exception(f"{provider} service is not available")

                return client.get_available_models()
            except Exception as e:
                raise e

        # Execute fully async with ThreadPoolExecutor to prevent blocking all requests
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            models = await loop.run_in_executor(executor, get_models_sync)

        return models

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get models for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/protect-folder")
async def protect_folder(request: dict):
    """Set password-based protection on folder"""
    async with fs_lock:
        try:
            folder_path = request.get("folder_path", "")
            password = request.get("password", "")
            reason = request.get("reason", "")

            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")

            if not password:
                raise HTTPException(status_code=400, detail="password is required")

            # Create full path
            full_path = PathResolver.resolve_folder_path(folder_path)

            # Check existence
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")

            if not os.path.isdir(full_path):
                raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")

            # Check if already protected
            if is_protected(full_path):
                raise HTTPException(status_code=409, detail="Folder is already protected")

            # Set protection
            create_secure_marker(full_path, password, reason)

            logger.info(f"Folder protected: '{folder_path}'")

            return {
                "success": True,
                "message": f"Folder '{folder_path}' is now protected",
                "folder_path": folder_path
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to protect folder: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/unprotect-folder")
async def unprotect_folder(request: dict):
    """Remove folder protection (requires password verification)"""
    async with fs_lock:
        try:
            folder_path = request.get("folder_path", "")
            password = request.get("password", "")

            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")

            if not password:
                raise HTTPException(status_code=400, detail="password is required")

            # Create full path
            full_path = PathResolver.resolve_folder_path(folder_path)

            # Check existence
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")

            if not os.path.isdir(full_path):
                raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")

            # Error if not protected
            if not is_protected(full_path):
                raise HTTPException(status_code=404, detail="Folder is not protected")

            # Verify password and remove protection
            remove_secure_marker(full_path, password)

            logger.info(f"Folder unprotected: '{folder_path}'")

            return {
                "success": True,
                "message": f"Folder '{folder_path}' protection removed",
                "folder_path": folder_path
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unprotect folder: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/protect")
async def protect_knowledge_base(request: dict):
    """Set password-based protection on knowledge base"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            password = request.get("password", "")
            reason = request.get("reason", "")

            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")

            if not password:
                raise HTTPException(status_code=400, detail="password is required")

            from ..utils import get_kb_path

            kb_path = get_kb_path(kb_name)

            # Check existence
            if not os.path.exists(kb_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")

            # Check if already protected
            if is_protected(kb_path):
                raise HTTPException(status_code=409, detail="Knowledge base is already protected")

            # Set protection
            create_secure_marker(kb_path, password, reason)

            logger.info(f"Knowledge base protected: '{kb_name}'")

            return {
                "success": True,
                "message": f"Knowledge base '{kb_name}' is now protected",
                "kb_name": kb_name
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to protect knowledge base: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/unprotect")
async def unprotect_knowledge_base(request: dict):
    """Remove knowledge base protection (requires password verification)"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            password = request.get("password", "")

            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")

            if not password:
                raise HTTPException(status_code=400, detail="password is required")

            from ..utils import get_kb_path

            kb_path = get_kb_path(kb_name)

            # Check existence
            if not os.path.exists(kb_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")

            # Error if not protected
            if not is_protected(kb_path):
                raise HTTPException(status_code=404, detail="Knowledge base is not protected")

            # Verify password and remove protection
            remove_secure_marker(kb_path, password)

            logger.info(f"Knowledge base unprotected: '{kb_name}'")

            return {
                "success": True,
                "message": f"Knowledge base '{kb_name}' protection removed",
                "kb_name": kb_name
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unprotect knowledge base: {e}")
            raise HTTPException(status_code=500, detail=str(e))
