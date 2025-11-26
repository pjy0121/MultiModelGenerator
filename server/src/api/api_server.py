from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import json
import uuid
from typing import Dict, Optional

# Node-based workflow imports
from ..core.node_execution_engine import NodeExecutionEngine
from ..core.workflow_validator import WorkflowValidator
from ..core.config import LLM_CONFIG
from ..core.utils import format_sse_data
from ..core.models import (
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
async def validate_workflow(workflow: WorkflowDefinition):
    """워크플로우 유효성 검증 (project_reference.md 연결 조건 기준)"""
    try:
        result = validator.validate_workflow(workflow)
        return result
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """
    try:
        if execution_id not in active_executions:
            logger.warning(f"Execution not found: {execution_id}")
            return {
                "success": False,
                "message": "실행 중인 워크플로우를 찾을 수 없습니다."
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """지식베이스 목록 조회"""
    try:
        # 요청별 독립적인 VectorStoreService 생성
        vector_store_service = VectorStoreService()
        knowledge_bases = []
        kb_names = await vector_store_service.get_knowledge_bases()
        
        # 비동기 병렬 처리로 지식베이스 정보 조회 (성능 향상 및 블로킹 방지)
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        async def get_kb_info_safe(name: str):
            try:
                # 각 KB에 대해 독립적인 VectorStoreService 인스턴스 사용
                kb_vector_service = VectorStoreService()
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
        
        # 요청별 독립적인 VectorStoreService 생성
        vector_store_service = VectorStoreService()
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