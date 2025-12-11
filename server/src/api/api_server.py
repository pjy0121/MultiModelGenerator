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

# 파일 시스템 작업을 위한 글로벌 락 (동시성 문제 해결)
fs_lock = asyncio.Lock()

# VectorStoreService 인스턴스 추적 (KB 삭제/이름 변경 시 연결 닫기용)
_active_vector_services: Dict[int, VectorStoreService] = {}

def register_vector_service(service: VectorStoreService):
    """VectorStoreService 인스턴스 등록"""
    service_id = id(service)
    _active_vector_services[service_id] = service
    return service_id

def close_kb_in_all_services(kb_name: str):
    """모든 활성 VectorStoreService에서 특정 KB의 연결 닫기"""
    import gc
    for service_id, service in list(_active_vector_services.items()):
        try:
            service.close_and_remove_kb(kb_name)
        except Exception as e:
            logger.warning(f"KB '{kb_name}' 닫기 실패 (service {service_id}): {e}")
    # 가비지 컬렉션 강제 실행
    gc.collect()
    logger.info(f"✅ 모든 서비스에서 KB '{kb_name}' 연결 닫힘")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (stateless services only)
validator = WorkflowValidator()
# vector_store_service는 요청별로 생성

# Active workflow executions tracking (multi-user support)
active_executions: Dict[str, NodeExecutionEngine] = {}

@app.get("/")
async def health():
    return {"status": "Node-based workflow API is running", "version": "2.0.0"}

@app.post("/validate-workflow")
@handle_api_errors(default_status=500)
async def validate_workflow(workflow: WorkflowDefinition):
    """워크플로우 유효성 검증 (project_reference.md 연결 조건 기준)"""
    result = validator.validate_workflow(workflow)
    return result

@app.post("/execute-workflow-stream")
async def execute_workflow_stream(request: WorkflowExecutionRequest):
    """
    Node-based 워크플로우 실행 (스트리밍)
    LLM 응답을 실시간으로 스트리밍하면서 최종 파싱된 결과도 반환
    """
    # Generate unique execution ID for this workflow
    execution_id = str(uuid.uuid4())
    
    async def generate_stream():
        execution_engine = None
        try:
            logger.info(f"Starting streaming workflow execution {execution_id} with {len(request.workflow.nodes)} nodes")
            
            # 실행 엔진 생성 및 등록
            execution_engine = NodeExecutionEngine()
            active_executions[execution_id] = execution_engine
            logger.info(f"Registered execution {execution_id} for stop control")
            
            # 첫 이벤트로 execution_id 전달
            yield format_sse_data({
                'type': 'execution_started',
                'execution_id': execution_id,
                'message': 'Workflow execution started'
            })
            
            # 실행 전 검증
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
            
            # 스트리밍으로 워크플로우 실행 (독립적인 인스턴스 사용)
            async for chunk in execution_engine.execute_workflow_stream(
                workflow=request.workflow
            ):
                yield format_sse_data(chunk)
                
                # 완료 또는 에러 시 스트림 종료
                if chunk.get('type') in ['complete', 'error']:
                    logger.info(f"Stream terminated with event: {chunk.get('type')}")
                    break
                
        except Exception as e:
            logger.error(f"Streaming workflow execution {execution_id} failed: {e}")
            yield format_sse_data({'type': 'error', 'message': str(e)})
        finally:
            # 실행 완료 시 정리
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
    워크플로우 실행 중단
    
    특정 execution_id의 워크플로우를 중단합니다.
    현재 실행 중인 노드는 완료하고, 새로운 노드 실행을 중단합니다.
    이미 완료되었거나 존재하지 않는 워크플로우에 대한 중단 요청도 성공으로 처리됩니다.
    """
    try:
        if execution_id not in active_executions:
            logger.info(f"Execution {execution_id} not found or already completed")
            return {
                "success": True,
                "message": "워크플로우가 이미 완료되었거나 중단되었습니다."
            }
        
        # 중단 플래그 설정
        active_executions[execution_id].stop()
        logger.info(f"Stop signal sent to execution {execution_id}")
        
        return {
            "success": True,
            "message": "중단 요청이 전송되었습니다. 실행 중인 노드는 완료 후 중단됩니다."
        }
    except Exception as e:
        logger.error(f"Failed to stop workflow {execution_id}: {e}")
        # 예외 발생 시에도 중단은 성공으로 처리
        return {
            "success": True,
            "message": "워크플로우 중단이 요청되었습니다."
        }

@app.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """지식베이스 목록 조회"""
    try:
        # 요청별 독립적인 VectorStoreService 생성 및 등록
        vector_store_service = VectorStoreService()
        register_vector_service(vector_store_service)
        knowledge_bases = []
        kb_names = await vector_store_service.get_knowledge_bases()
        
        # 비동기 병렬 처리로 지식베이스 정보 조회 (성능 향상 및 블로킹 방지)
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        async def get_kb_info_safe(name: str):
            try:
                # 각 KB에 대해 독립적인 VectorStoreService 인스턴스 사용
                kb_vector_service = VectorStoreService()
                register_vector_service(kb_vector_service)
                kb_info = await kb_vector_service.get_knowledge_base_info(name)
                return KnowledgeBase(
                    name=kb_info['name'],
                    chunk_count=kb_info.get('count', 0),  # VectorStore는 'count' 사용
                    created_at=kb_info.get('created_at', 'Unknown')  # 생성일 정보가 없으면 Unknown
                )
            except Exception as e:
                logger.warning(f"Failed to get info for KB {name}: {e}")
                # 오류가 발생해도 기본값으로 추가
                return KnowledgeBase(
                    name=name,
                    chunk_count=0,  # 기본값
                    created_at="Unknown"
                )
        
        # 모든 KB 정보를 병렬로 조회
        knowledge_bases = await asyncio.gather(*[get_kb_info_safe(name) for name in kb_names])
        
        return KnowledgeBaseListResponse(knowledge_bases=knowledge_bases)
        
    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        raise ErrorResponse.internal_error(f"Failed to list knowledge bases: {str(e)}")

@app.get("/knowledge-bases/structure")
async def get_knowledge_base_structure():
    """지식 베이스 디렉토리 구조 반환 (폴더 포함)"""
    try:
        kb_base_path = PathResolver.get_kb_base_path()
        
        if not os.path.exists(kb_base_path):
            return {"structure": {}}
        
        structure = {}
        
        def scan_directory_structure(current_path: str, relative_path: str = "", parent_id: str = "root"):
            """재귀적으로 디렉토리 구조 스캔"""
            try:
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    
                    if os.path.isdir(item_path):
                        # ⚠️ .delete_marker가 있으면 삭제된 것으로 간주하고 무시
                        delete_marker = os.path.join(item_path, '.delete_marker')
                        if os.path.exists(delete_marker):
                            continue  # 삭제된 폴더/KB는 구조에서 제외
                        
                        # .folder_marker 파일로 폴더 판별
                        folder_marker = os.path.join(item_path, '.folder_marker')
                        chroma_file = os.path.join(item_path, 'chroma.sqlite3')
                        
                        is_folder = os.path.exists(folder_marker)
                        
                        # KB 판별: .folder_marker가 없고, chroma.sqlite3가 있으면 KB
                        # 폴더로 판정되면 KB가 될 수 없음
                        is_kb = False
                        chunk_count = 0
                        
                        if not is_folder:
                            if os.path.exists(chroma_file):
                                try:
                                    file_size = os.path.getsize(chroma_file)
                                    # chroma.sqlite3가 존재하고 크기가 0보다 크면 KB
                                    if file_size > 0:
                                        is_kb = True
                                        # KB의 chunk 개수 가져오기 (context manager로 자동 닫기)
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
                        
                        # 상대 경로 계산 (중복 방지)
                        if not is_kb:  # KB가 아닌 경우만 여기서 계산
                            new_relative = f"{relative_path}/{item}" if relative_path else item
                        
                        # 🔒 보호 상태 확인
                        secure_marker = os.path.join(item_path, '.secure_marker')
                        item_is_protected = os.path.exists(secure_marker)
                        
                        item_id = f"{'kb' if is_kb else 'folder'}_{new_relative.replace('/', '_')}"
                        
                        if is_kb:
                            # KB로 간주
                            structure[item_id] = {
                                "type": "kb",
                                "name": item,
                                "parent": parent_id,
                                "actualKbName": new_relative,
                                "chunkCount": chunk_count,
                                "isProtected": item_is_protected
                            }
                        else:
                            # 폴더로 간주 (빈 폴더일 수 있음)
                            structure[item_id] = {
                                "type": "folder",
                                "name": item,
                                "parent": parent_id,
                                "isProtected": item_is_protected
                            }
                            # 하위 디렉토리 스캔
                            scan_directory_structure(item_path, new_relative, item_id)
            except Exception as e:
                logger.error(f"디렉토리 스캔 실패 ({current_path}): {e}")
        
        scan_directory_structure(kb_base_path)
        return {"structure": structure}
        
    except Exception as e:
        logger.error(f"Failed to get knowledge base structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-bases/create-folder")
async def create_folder(request: dict):
    """폴더 생성 (동시성 안전)"""
    async with fs_lock:  # 락 획득
        try:
            folder_path = request.get("folder_path", "")
            
            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")
            
            kb_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_bases')
            kb_base_path = os.path.abspath(kb_base_path)
            
            # 전체 경로 생성
            full_path = os.path.join(kb_base_path, folder_path)
            
            # 이미 존재하는지 확인 (락 내부에서 재확인)
            if os.path.exists(full_path):
                # .delete_marker가 있으면 삭제된 폴더이므로 재생성 허용
                delete_marker = os.path.join(full_path, '.delete_marker')
                if os.path.exists(delete_marker):
                    # 삭제 마커 제거 (폴더 복구)
                    os.remove(delete_marker)
                    logger.info(f"Restoring previously deleted folder: '{folder_path}'")
                else:
                    raise HTTPException(status_code=409, detail=f"Folder '{folder_path}' already exists")
            
            # 폴더 생성
            os.makedirs(full_path, exist_ok=False)
            
            # .folder_marker 파일 생성 (ChromaDB와 구분하기 위해)
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
    """폴더 삭제 (소프트 삭제: .delete_marker 파일 생성)"""
    try:
        folder_path = request.get("folder_path", "")
        
        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")
        
        # 전체 경로 생성
        full_path = PathResolver.resolve_folder_path(folder_path)
        
        # 존재 여부 확인
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
        
        if not os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")
        
        # 🔒 보호 체크 (보호된 폴더 또는 내부에 보호된 콘텐츠가 있으면 삭제 불가)
        check_protection_before_operation(full_path, "delete", is_folder=True)
        
        # 소프트 삭제: .delete_marker 파일 생성
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
    """지식 베이스 검색"""
    try:
        query = request.get("query", "")
        knowledge_base = request.get("knowledge_base", "")
        top_k = request.get("top_k", 5)
        
        if not query or not knowledge_base:
            raise HTTPException(status_code=400, detail="Query and knowledge_base are required")
        
        # top_k를 search_intensity로 매핑
        search_intensity = SearchIntensity.from_top_k(top_k)
        
        # 요청별 독립적인 VectorStoreService 생성 및 등록
        vector_store_service = VectorStoreService()
        register_vector_service(vector_store_service)
        results = await vector_store_service.search(
            kb_name=knowledge_base,
            query=query,
            search_intensity=search_intensity,
            rerank_info=None  # 기본적으로 rerank 비활성화
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
    """지식 베이스 삭제 (소프트 삭제: .delete_marker 파일 생성)"""
    try:
        kb_name = request.get("kb_name", "")
        
        if not kb_name:
            raise HTTPException(status_code=400, detail="kb_name is required")
        
        from ..core.utils import get_kb_path
        
        kb_path = get_kb_path(kb_name)
        
        logger.info(f"KB Delete request - kb_name: '{kb_name}'")
        logger.info(f"Resolved kb_path: '{kb_path}', exists: {os.path.exists(kb_path)}")
        
        # 존재 여부 확인
        if not os.path.exists(kb_path):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found at '{kb_path}'")
        
        # 🔒 보호 체크 (보호된 KB는 삭제 불가)
        check_protection_before_operation(kb_path, "delete", is_folder=False)
        
        # 소프트 삭제: .delete_marker 파일 생성
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
    """폴더 이름 변경 (동시성 안전)"""
    try:
        old_path = request.get("old_path", "")
        new_name = request.get("new_name", "")
        
        if not old_path or not new_name:
            raise HTTPException(status_code=400, detail="old_path and new_name are required")
        
        # 전체 경로 생성
        full_old_path = PathResolver.resolve_folder_path(old_path)
        
        # 존재 확인
        if not os.path.exists(full_old_path):
            raise HTTPException(status_code=404, detail=f"Folder '{old_path}' not found")
        
        if not os.path.isdir(full_old_path):
            raise HTTPException(status_code=400, detail=f"'{old_path}' is not a folder")
        
        # ⚠️ 삭제된 폴더는 이름 변경 불가
        delete_marker = os.path.join(full_old_path, '.delete_marker')
        if os.path.exists(delete_marker):
            raise HTTPException(status_code=404, detail=f"Folder '{old_path}' has been deleted")
        
        # 🔒 보호 체크 (보호된 폴더 또는 내부에 보호된 콘텐츠가 있으면 이름 변경 불가)
        check_protection_before_operation(full_old_path, "rename", is_folder=True)
        
        # 새 경로 계산 (같은 부모 디렉토리 내에서)
        parent_dir = os.path.dirname(full_old_path)
        full_new_path = os.path.join(parent_dir, new_name)
        
        # 새 이름이 이미 존재하는지 확인
        if os.path.exists(full_new_path):
            raise HTTPException(status_code=409, detail=f"Folder or KB '{new_name}' already exists in the same location")
        
        # 📋 복사 후 원본 소프트 삭제 방식으로 이름 변경 (ChromaDB 락 문제 회피)
        try:
            # 1. 전체 폴더 복사
            shutil.copytree(full_old_path, full_new_path)
            logger.info(f"Folder copied: '{full_old_path}' -> '{full_new_path}'")
            
            # 2. 복사본에서 .delete_marker 제거 (혹시 있을 경우)
            copy_delete_marker = os.path.join(full_new_path, '.delete_marker')
            if os.path.exists(copy_delete_marker):
                os.remove(copy_delete_marker)
            
            # 3. 원본에 .delete_marker 생성 (소프트 삭제)
            import datetime
            original_delete_marker = os.path.join(full_old_path, '.delete_marker')
            with open(original_delete_marker, 'w') as f:
                f.write(f"Renamed to '{new_name}' at: {datetime.datetime.now().isoformat()}\n")
            
            logger.info(f"Folder renamed (copy+soft delete): '{old_path}' -> '{new_name}'")
            
        except Exception as e:
            # 복사 실패 시 복사본 정리
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
        
        # 새 상대 경로 계산
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
    """지식 베이스 이름 변경 (같은 디렉토리 내에서만, 동시성 안전)"""
    try:
        old_name = request.get("old_name", "")
        new_name = request.get("new_name", "")
        
        if not old_name or not new_name:
            raise HTTPException(status_code=400, detail="old_name and new_name are required")
        
        if old_name == new_name:
            raise HTTPException(status_code=400, detail="New name must be different from old name")
        
        from ..core.utils import get_kb_path
        
        old_path = get_kb_path(old_name)
        
        logger.info(f"KB Rename request - old_name: '{old_name}', new_name: '{new_name}'")
        logger.info(f"Resolved old_path: '{old_path}', exists: {os.path.exists(old_path)}")
        
        if not os.path.exists(old_path):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{old_name}' not found at '{old_path}'")
        
        # ⚠️ 삭제된 KB는 이름 변경 불가
        delete_marker = os.path.join(old_path, '.delete_marker')
        if os.path.exists(delete_marker):
            raise HTTPException(status_code=404, detail=f"Knowledge base '{old_name}' has been deleted")
        
        # 🔒 보호 체크 (보호된 KB는 이름 변경 불가)
        check_protection_before_operation(old_path, "rename", is_folder=False)
        
        # 같은 부모 디렉토리 내에서 이름만 변경
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)
        
        logger.info(f"Target new_path: '{new_path}'")
        
        if os.path.exists(new_path):
            raise HTTPException(status_code=409, detail=f"Knowledge base '{new_name}' already exists")
        
        # 📋 복사 후 원본 소프트 삭제 방식으로 이름 변경 (ChromaDB 락 문제 회피)
        try:
            # 1. 전체 KB 디렉토리 복사
            shutil.copytree(old_path, new_path)
            logger.info(f"KB copied: '{old_path}' -> '{new_path}'")
            
            # 2. 복사본에서 .delete_marker와 .secure_marker 제거 (혹시 있을 경우)
            copy_delete_marker = os.path.join(new_path, '.delete_marker')
            if os.path.exists(copy_delete_marker):
                os.remove(copy_delete_marker)
            
            # 3. 원본에 .delete_marker 생성 (소프트 삭제)
            import datetime
            original_delete_marker = os.path.join(old_path, '.delete_marker')
            with open(original_delete_marker, 'w') as f:
                f.write(f"Renamed to '{new_name}' at: {datetime.datetime.now().isoformat()}\n")
            
            logger.info(f"Knowledge base renamed (copy+soft delete): '{old_name}' -> '{new_name}'")
            
        except Exception as e:
            # 복사 실패 시 복사본 정리
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
        
        # 새 상대 경로 계산
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
    """폴더를 다른 폴더로 이동 (동시성 안전)"""
    async with fs_lock:
        try:
            old_path = request.get("old_path", "")
            target_folder = request.get("target_folder", "")
            
            if not old_path:
                raise HTTPException(status_code=400, detail="old_path is required")
            
            # 이동할 폴더의 전체 경로
            full_old_path = PathResolver.resolve_folder_path(old_path)
            
            logger.info(f"Folder Move request - old_path: '{old_path}', target_folder: '{target_folder}'")
            logger.info(f"Resolved full_old_path: '{full_old_path}', exists: {os.path.exists(full_old_path)}")
            
            if not os.path.exists(full_old_path):
                raise HTTPException(status_code=404, detail=f"Folder '{old_path}' not found")
            
            if not os.path.isdir(full_old_path):
                raise HTTPException(status_code=400, detail=f"'{old_path}' is not a folder")
            
            # ⚠️ 삭제된 폴더는 이동 불가
            delete_marker = os.path.join(full_old_path, '.delete_marker')
            if os.path.exists(delete_marker):
                raise HTTPException(status_code=404, detail=f"Folder '{old_path}' has been deleted")
            
            # 🔒 보호 체크 (보호된 폴더 또는 내부에 보호된 콘텐츠가 있으면 이동 불가)
            check_protection_before_operation(full_old_path, "move", is_folder=True)
            
            # 대상 폴더 경로 계산
            target_dir = PathResolver.resolve_folder_path(target_folder) if (target_folder and target_folder != 'root') else PathResolver.get_kb_base_path()
            
            # 대상 폴더가 없으면 생성
            os.makedirs(target_dir, exist_ok=True)
            
            # 폴더 이름 추출
            folder_basename = os.path.basename(full_old_path)
            new_path = os.path.join(target_dir, folder_basename)
            
            logger.info(f"Target new_path: '{new_path}'")
            
            # 같은 위치로 이동하려는지 확인
            if os.path.normpath(full_old_path) == os.path.normpath(new_path):
                logger.info(f"Folder is already in target location")
                return {
                    "success": True,
                    "message": f"Folder is already in target location",
                    "old_path": old_path,
                    "new_path": PathResolver.to_relative_path(new_path)
                }
            
            # 새 경로가 이미 존재하는지 확인
            if os.path.exists(new_path):
                raise HTTPException(status_code=409, detail=f"Folder '{folder_basename}' already exists in target location")
            
            # 자기 자신의 하위 폴더로 이동하려는지 확인
            if new_path.startswith(full_old_path + os.sep):
                raise HTTPException(status_code=400, detail="Cannot move folder into its own subfolder")
            
            # 새 상대 경로 미리 계산 (로그 및 에러 처리용)
            new_relative_path = PathResolver.to_relative_path(new_path)
            
            # 📋 복사 후 원본 소프트 삭제 방식으로 이동 (ChromaDB 락 문제 회피)
            try:
                # 1. 전체 폴더 복사
                shutil.copytree(full_old_path, new_path)
                logger.info(f"Folder copied: '{full_old_path}' -> '{new_path}'")
                
                # 2. 복사본에서 .delete_marker 제거 (혹시 있을 경우)
                copy_delete_marker = os.path.join(new_path, '.delete_marker')
                if os.path.exists(copy_delete_marker):
                    os.remove(copy_delete_marker)
                
                # 3. 원본에 .delete_marker 생성 (소프트 삭제)
                import datetime
                original_delete_marker = os.path.join(full_old_path, '.delete_marker')
                with open(original_delete_marker, 'w') as f:
                    target_name = target_folder if target_folder else 'root'
                    f.write(f"Moved to '{target_name}' at: {datetime.datetime.now().isoformat()}\n")
                
                logger.info(f"Folder moved (copy+soft delete): '{old_path}' -> '{new_relative_path}'")
                
            except Exception as e:
                # 복사 실패 시 복사본 정리
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
    """지식 베이스를 다른 폴더로 이동 (동시성 안전)"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            target_folder = request.get("target_folder", "")
            
            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")
            
            from ..core.utils import get_kb_path
            
            old_path = get_kb_path(kb_name)
            
            logger.info(f"KB Move request - kb_name: '{kb_name}', target_folder: '{target_folder}'")
            logger.info(f"Resolved old_path: '{old_path}'")
            logger.info(f"Path exists: {os.path.exists(old_path)}")
            
            if not os.path.exists(old_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found at '{old_path}'")
            
            # ⚠️ 삭제된 KB는 이동 불가
            delete_marker = os.path.join(old_path, '.delete_marker')
            if os.path.exists(delete_marker):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' has been deleted")
            
            # 🔒 보호 체크 (보호된 KB는 이동 뵣8가)
            check_protection_before_operation(old_path, "move", is_folder=False)
            
            # 대상 폴더 경로 생성
            target_dir = PathResolver.resolve_folder_path(target_folder) if (target_folder and target_folder != 'root') else PathResolver.get_kb_base_path()
            
            # 대상 폴더가 없으면 생성
            os.makedirs(target_dir, exist_ok=True)
            
            # KB 이름 추출
            kb_basename = os.path.basename(old_path)
            new_path = os.path.join(target_dir, kb_basename)
            
            logger.info(f"Target new_path: '{new_path}'")
            
            # 같은 위치로 이동하려는지 확인
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
            
            # 새 상대 경로 미리 계산 (로그 및 에러 처리용)
            new_relative_path = PathResolver.to_relative_path(new_path)
            
            # 📋 복사 후 원본 소프트 삭제 방식으로 이동 (ChromaDB 락 문제 회피)
            try:
                # 1. 전체 KB 디렉토리 복사
                shutil.copytree(old_path, new_path)
                logger.info(f"KB copied: '{old_path}' -> '{new_path}'")
                
                # 2. 복사본에서 .delete_marker 제거 (혹시 있을 경우)
                copy_delete_marker = os.path.join(new_path, '.delete_marker')
                if os.path.exists(copy_delete_marker):
                    os.remove(copy_delete_marker)
                
                # 3. 원본에 .delete_marker 생성 (소프트 삭제)
                import datetime
                original_delete_marker = os.path.join(old_path, '.delete_marker')
                with open(original_delete_marker, 'w') as f:
                    target_name = target_folder if target_folder else 'root'
                    f.write(f"Moved to '{target_name}' at: {datetime.datetime.now().isoformat()}\n")
                
                logger.info(f"Knowledge base moved (copy+soft delete): '{kb_name}' -> '{new_relative_path}'")
                
            except Exception as e:
                # 복사 실패 시 복사본 정리
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
    """Plain text 처리"""
    logger.info("Using plain text directly")
    return text_content

def _process_base64_text(text_content_base64: str, doc_processor=None) -> str:
    """Base64 인코딩된 텍스트 처리 (바이너리 파일 자동 감지)"""
    import base64
    logger.info(f"Processing base64 text content (length: {len(text_content_base64)})...")
    try:
        text_bytes = base64.b64decode(text_content_base64, validate=True)
        
        # UTF-8 텍스트 디코딩 시도
        try:
            text = text_bytes.decode('utf-8')
            logger.info(f"Successfully decoded base64 text (decoded length: {len(text)} chars)")
            return text
        except UnicodeDecodeError:
            # UTF-8 실패 시 PDF 매직 넘버 확인
            if text_bytes[:4] == b'%PDF':
                logger.info("Detected PDF file in base64 content, processing as PDF...")
                if doc_processor is None:
                    raise HTTPException(status_code=400, detail="PDF content detected but no document processor available")
                
                # PDF로 처리
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
                # PDF가 아닌 경우 다른 인코딩 시도
                logger.warning("UTF-8 decode failed, trying alternative encodings...")
                try:
                    text = text_bytes.decode('cp949')  # 한글 Windows
                    logger.info(f"Successfully decoded as CP949 (length: {len(text)} chars)")
                    return text
                except UnicodeDecodeError:
                    try:
                        text = text_bytes.decode('latin-1')  # 최후의 수단
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
    """파일 업로드 처리 (PDF 또는 TXT)"""
    import base64
    import tempfile
    
    logger.info(f"Processing {file_type.upper()} file...")
    
    try:
        file_content = base64.b64decode(file_content_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 file content: {str(e)}")
    
    if file_type == "pdf":
        # PDF 파일 처리
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
        # TXT 파일 처리 (다중 인코딩 지원)
        try:
            text = file_content.decode('utf-8')
            logger.info(f"Loaded text from TXT file (UTF-8): {len(text)} characters")
        except UnicodeDecodeError:
            try:
                text = file_content.decode('cp949')  # 한글 Windows
                logger.info(f"Loaded text from TXT file (CP949): {len(text)} characters")
            except:
                text = file_content.decode('latin-1')  # 최후의 수단
                logger.info(f"Loaded text from TXT file (Latin-1): {len(text)} characters")
        return text
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

@app.post("/knowledge-bases/create")
async def create_knowledge_base(request: dict):
    """지식 베이스 생성 (plain text, base64 text, 또는 파일 업로드) - BGE-M3 최적화"""
    # 요청 파라미터 추출
    kb_name_input = request.get("kb_name", "")
    text_content = request.get("text_content", "")
    file_content_base64 = request.get("file_content", "")
    chunk_size = request.get("chunk_size", 8000)
    chunk_overlap = request.get("chunk_overlap", 200)
    target_folder = request.get("target_folder", "")
    
    # 입력 검증 (락 밖에서 수행)
    if not kb_name_input:
        raise HTTPException(status_code=400, detail="kb_name is required")
    
    if not text_content and not file_content_base64:
        raise HTTPException(status_code=400, detail="Either text_content or file_content is required")
    
    # KB 이름은 입력값 그대로 사용
    kb_name = kb_name_input
    
    # 파일 시스템 작업만 락으로 보호
    async with fs_lock:
        try:
            if target_folder and target_folder != 'root':
                kb_full_name = f"{target_folder}/{kb_name}"
                kb_dir = PathResolver.resolve_folder_path(target_folder)
            else:
                kb_full_name = kb_name
                kb_dir = PathResolver.get_kb_base_path()
            
            os.makedirs(kb_dir, exist_ok=True)
            
            from ..core.utils import get_kb_path
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
    
    # 락 해제 후 무거운 작업 수행
    try:
        # BGE-M3 최적화 chunk 설정 (Token 기반)
        from ..core.config import VECTOR_DB_CONFIG
        chunk_tokens = VECTOR_DB_CONFIG.get('chunk_tokens', 512)
        chars_per_token = VECTOR_DB_CONFIG.get('chars_per_token', 4)
        overlap_ratio = VECTOR_DB_CONFIG.get('overlap_ratio', 0.15)
        
        chunk_size = chunk_tokens * chars_per_token
        chunk_overlap = int(chunk_size * overlap_ratio)
        
        logger.info(f"Building KB with BGE-M3 settings: {chunk_tokens} tokens ({chunk_size} chars), {int(overlap_ratio*100)}% overlap ({chunk_overlap} chars)")
        
        # DocumentProcessor 초기화
        from ..services.document_processor import DocumentProcessor
        from ..services.vector_store import VectorStore
        
        doc_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # 입력 방식에 따라 텍스트 추출
        if file_content_base64:
            # 파일 업로드 처리
            file_type = request.get("file_type", "pdf")
            logger.info(f"Processing file upload (type: {file_type})")
            text = _process_file_upload(file_content_base64, file_type, doc_processor)
        
        elif text_content:
            # 텍스트 입력 처리
            text_type = request.get("text_type", "plain")
            logger.info(f"Processing text content (type: {text_type}, length: {len(text_content)})")
            
            if text_type == "base64":
                text = _process_base64_text(text_content, doc_processor)
            else:  # plain
                text = _process_plain_text(text_content)
        else:
            raise HTTPException(status_code=400, detail="No content provided (neither file_content nor text_content)")
        
        # 텍스트 검증
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text content is empty")
        
        logger.info(f"Text length: {len(text)} characters")
        
        # 청킹 및 임베딩 생성
        logger.info("Starting chunking...")
        chunks = doc_processor.semantic_chunking(text)
        logger.info(f"Created {len(chunks)} chunks")
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to create chunks from text")
        
        logger.info("Generating embeddings...")
        chunks_with_embeddings = doc_processor.generate_embeddings(chunks)
        logger.info("Embeddings generated")
        
        # 벡터 DB 저장 (context manager로 자동 닫기, 자체 재시도 로직 포함)
        logger.info("Storing in vector database...")
        with VectorStore(kb_full_name) as vector_store:
            vector_store.store_chunks(chunks_with_embeddings)
        logger.info(f"Knowledge base '{kb_full_name}' created successfully with {len(chunks)} chunks")
        
        # 명시적 가비지 컬렉션 및 리소스 해제
        import gc
        gc.collect()
        
        # 짧은 대기로 파일 핸들 완전 해제 보장
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
    """Provider별 사용 가능한 모델 목록 반환"""
    try:
        # Normalize provider
        provider = provider.lower()
        if provider not in LLM_CONFIG["supported_providers"]:
            supported_providers = ", ".join(LLM_CONFIG["supported_providers"])
            raise HTTPException(status_code=400, detail=f"Unsupported provider. Only '{supported_providers}' are supported.")

        # 요청별 독립적인 LLMFactory 인스턴스로 완전 병렬 처리
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def get_models_sync():
            """동기적 모델 조회를 별도 스레드에서 실행 - 블로킹 방지"""
            llm_factory = LLMFactory()  # 요청별 독립 인스턴스
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
        
        # ThreadPoolExecutor로 완전 비동기 실행하여 모든 요청 블로킹 방지
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
    """폴더에 비밀번호 기반 보호 설정"""
    async with fs_lock:
        try:
            folder_path = request.get("folder_path", "")
            password = request.get("password", "")
            reason = request.get("reason", "")
            
            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")
            
            if not password:
                raise HTTPException(status_code=400, detail="password is required")
            
            # 전체 경로 생성
            full_path = PathResolver.resolve_folder_path(folder_path)
            
            # 존재 여부 확인
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
            
            if not os.path.isdir(full_path):
                raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")
            
            # 이미 보호되어 있는지 확인
            if is_protected(full_path):
                raise HTTPException(status_code=409, detail="Folder is already protected")
            
            # 보호 설정
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
    """폴더 보호 해제 (비밀번호 검증 필요)"""
    async with fs_lock:
        try:
            folder_path = request.get("folder_path", "")
            password = request.get("password", "")
            
            if not folder_path:
                raise HTTPException(status_code=400, detail="folder_path is required")
            
            if not password:
                raise HTTPException(status_code=400, detail="password is required")
            
            # 전체 경로 생성
            full_path = PathResolver.resolve_folder_path(folder_path)
            
            # 존재 여부 확인
            if not os.path.exists(full_path):
                raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
            
            if not os.path.isdir(full_path):
                raise HTTPException(status_code=400, detail=f"'{folder_path}' is not a folder")
            
            # 보호되어 있지 않으면 에러
            if not is_protected(full_path):
                raise HTTPException(status_code=404, detail="Folder is not protected")
            
            # 비밀번호 검증 및 보호 해제
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
    """지식 베이스에 비밀번호 기반 보호 설정"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            password = request.get("password", "")
            reason = request.get("reason", "")
            
            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")
            
            if not password:
                raise HTTPException(status_code=400, detail="password is required")
            
            from ..core.utils import get_kb_path
            
            kb_path = get_kb_path(kb_name)
            
            # 존재 여부 확인
            if not os.path.exists(kb_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")
            
            # 이미 보호되어 있는지 확인
            if is_protected(kb_path):
                raise HTTPException(status_code=409, detail="Knowledge base is already protected")
            
            # 보호 설정
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
    """지식 베이스 보호 해제 (비밀번호 검증 필요)"""
    async with fs_lock:
        try:
            kb_name = request.get("kb_name", "")
            password = request.get("password", "")
            
            if not kb_name:
                raise HTTPException(status_code=400, detail="kb_name is required")
            
            if not password:
                raise HTTPException(status_code=400, detail="password is required")
            
            from ..core.utils import get_kb_path
            
            kb_path = get_kb_path(kb_name)
            
            # 존재 여부 확인
            if not os.path.exists(kb_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")
            
            # 보호되어 있지 않으면 에러
            if not is_protected(kb_path):
                raise HTTPException(status_code=404, detail="Knowledge base is not protected")
            
            # 비밀번호 검증 및 보호 해제
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