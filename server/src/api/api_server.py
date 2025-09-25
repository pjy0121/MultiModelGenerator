from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from copy import deepcopy
import logging
import json
import requests

# Node-based workflow imports
from ..core.node_execution_engine import NodeExecutionEngine
from ..core.workflow_validator import WorkflowValidator
from ..core.config import SERVER_CONFIG, LLM_CONFIG, get_kb_list
from ..core.models import (
    WorkflowExecutionRequest, 
    WorkflowExecutionResponse,
    WorkflowDefinition,
    KnowledgeBase,
    KnowledgeBaseListResponse
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

# Global instances
execution_engine = NodeExecutionEngine()
validator = WorkflowValidator()
vector_store_service = VectorStoreService()

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
    
    async def generate_stream():
        try:
            logger.info(f"Starting streaming workflow execution with {len(request.workflow.nodes)} nodes")
            
            # 실행 전 검증
            validation_result = validator.validate_workflow(request.workflow)
            if not validation_result["valid"]:
                error_details = {
                    'type': 'validation_error',
                    'message': 'Workflow validation failed',
                    'errors': validation_result['errors'],
                    'warnings': validation_result.get('warnings', [])
                }
                yield f"data: {json.dumps(error_details)}\n\n"
                return
            
            # 스트리밍으로 워크플로우 실행
            async for chunk in execution_engine.execute_workflow_stream(
                workflow=request.workflow
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # 완료 또는 에러 시 스트림 종료
                if chunk.get('type') in ['complete', 'error']:
                    logger.info(f"Stream terminated with event: {chunk.get('type')}")
                    break
                
        except Exception as e:
            logger.error(f"Streaming workflow execution failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """지식베이스 목록 조회"""
    try:
        knowledge_bases = []
        kb_names = vector_store_service.get_knowledge_bases()
        
        for name in kb_names:
            try:
                # VectorStoreService의 새로운 메서드 사용 (await 추가)
                kb_info = await vector_store_service.get_knowledge_base_info(name)
                
                knowledge_bases.append(KnowledgeBase(
                    name=kb_info['name'],
                    chunk_count=kb_info.get('count', 0),  # VectorStore는 'count' 사용
                    created_at=kb_info.get('created_at', 'Unknown')  # 생성일 정보가 없으면 Unknown
                ))
            except Exception as e:
                logger.warning(f"Failed to get info for KB {name}: {e}")
                # 오류가 발생해도 기본값으로 추가
                knowledge_bases.append(KnowledgeBase(
                    name=name,
                    chunk_count=0,  # 기본값
                    created_at="Unknown"
                ))
                continue
        
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
        
        # top_k를 search_intensity로 매핑 (간단한 매핑)
        if top_k <= 7:
            search_intensity = "very_low"
        elif top_k <= 10:
            search_intensity = "low" 
        elif top_k <= 20:
            search_intensity = "medium"
        elif top_k <= 30:
            search_intensity = "high"
        else:
            search_intensity = "very_high"
            
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

        # LLMFactory를 통해 직접 클라이언트에서 모델 목록 가져오기
        client = LLMFactory.get_client(provider)
        if not client:
            raise HTTPException(status_code=500, detail=f"Failed to create client for {provider}")
            
        if not client.is_available():
            if provider == "internal":
                raise HTTPException(
                    status_code=503, 
                    detail=f"Internal LLM service is not available. Please check INTERNAL_API_KEY and INTERNAL_API_ENDPOINT environment variables."
                )
            else:
                raise HTTPException(status_code=503, detail=f"{provider} service is not available")
            
        models = client.get_available_models()
        
        return models
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get models for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))