from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import time
from datetime import datetime
import logging
from typing import List

from ..core.layer_engine import LayerEngine
from ..services.llm_factory import LLMFactory
from ..core.config import Config
from ..services.vector_store import VectorStore
from ..core.models import (
    KnowledgeBaseInfo, 
    KnowledgeBaseListResponse,
    NodeConfig,
    NodeOutput,
    # 새로운 Layer별 프롬프트 시스템 모델들
    LayerPromptRequest,
    LayerPromptResponse,
    ValidationLayerPromptResponse,
    # 기존 단계별 워크플로우 모델들
    SearchRequest,
    SearchResponse,
    # 모델 관리
    AvailableModel,
    AvailableModelsResponse,
)

# Layer별 실행기 import
from .layer_executors import LayerExecutorFactory, parse_structured_output

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Spec 문서 기반 요구사항 생성 API",
    description="RAG와 Perplexity AI를 사용한 지능형 요구사항 생성 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
async def root():
    """서버 상태 확인"""
    return {
        "service": "Spec 문서 기반 요구사항 생성 API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now()
    }

@app.get("/health", tags=["Health Check"])
async def health_check():
    """상세 헬스체크"""
    try:
        # 지식 베이스 목록 확인
        kb_list = Config.get_kb_list()
        
        # Perplexity API 키 확인
        api_key_status = "configured" if Config.PERPLEXITY_API_KEY else "missing"
        
        return {
            "status": "healthy",
            "perplexity_api_key": api_key_status,
            "knowledge_bases_count": len(kb_list),
            "knowledge_bases": kb_list,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"서비스 불안정: {str(e)}"
        )

@app.get("/knowledge-bases", 
         response_model=KnowledgeBaseListResponse, 
         tags=["Knowledge Base"])
async def get_knowledge_bases():
    """지식 베이스 목록 조회"""
    try:
        kb_list = Config.get_kb_list()
        knowledge_bases = []
        
        for kb_name in kb_list:
            vector_store = VectorStore(kb_name)
            status = vector_store.get_status()
            
            knowledge_bases.append(KnowledgeBaseInfo(
                name=kb_name,
                chunk_count=status['count'],
                path=status['path'],
                exists=status['exists']
            ))
        
        return KnowledgeBaseListResponse(
            knowledge_bases=knowledge_bases,
            total_count=len(knowledge_bases)
        )
        
    except Exception as e:
        logger.error(f"지식 베이스 목록 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"지식 베이스 목록 조회 실패: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지식 베이스 목록을 조회할 수 없습니다."
        )

@app.get("/knowledge-bases/{kb_name}/status", 
         response_model=KnowledgeBaseInfo, 
         tags=["Knowledge Base"])
async def get_knowledge_base_status(kb_name: str):
    """특정 지식 베이스 상태 조회"""
    try:
        vector_store = VectorStore(kb_name)
        status = vector_store.get_status()
        
        if not status['exists']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"지식 베이스 '{kb_name}'을 찾을 수 없습니다."
            )
        
        return KnowledgeBaseInfo(
            name=kb_name,
            chunk_count=status['count'],
            path=status['path'],
            exists=status['exists']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지식 베이스 상태 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"지식 베이스 상태를 조회할 수 없습니다: {str(e)}"
        )

@app.get("/available-models/{provider}", tags=["Models"], response_model=List[AvailableModel])
async def get_provider_models(provider: str):
    """특정 Provider의 모델 목록 조회"""
    try:
        # LLMFactory를 통해 직접 클라이언트 가져오기
        client = LLMFactory.get_client_by_provider(provider)
        if client and client.is_available():
            models = client.get_available_models()
            return models
        else:
            return []
            
    except Exception as e:
        logger.warning(f"{provider} 모델 목록 조회 실패: {e}")
        return []

# ==================== 컨텍스트 검색 엔드포인트 ====================

@app.post("/search-context", response_model=SearchResponse)
async def search_context(request: SearchRequest):
    """
    지식 베이스에서 컨텍스트 검색
    """
    try:
        logger.info(f"컨텍스트 검색 시작: {request.knowledge_base}, 쿼리: {request.query[:50]}...")
        
        # VectorStore 초기화
        vector_store = VectorStore(request.knowledge_base)
        
        # 검색 실행
        chunks = vector_store.search_similar_chunks(
            query=request.query,
            top_k=request.top_k or 50
        )
        
        logger.info(f"검색 완료: {len(chunks)}개 청크 반환")
        
        return SearchResponse(
            success=True,
            knowledge_base=request.knowledge_base,
            query=request.query,
            chunks=chunks,
            chunk_count=len(chunks)
        )
        
    except Exception as e:
        logger.error(f"컨텍스트 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"컨텍스트 검색에 실패했습니다: {str(e)}"
        )

# ==================== Layer별 프롬프트 시스템 엔드포인트들 ====================

@app.post("/execute-layer-prompt", response_model=LayerPromptResponse)
async def execute_layer_prompt(request: LayerPromptRequest):
    """
    Layer별 프롬프트로 실행 (새로운 구조: 노드별 general_output + 통합 forward_data)
    """
    try:
        start_time = time.time()
        logger.info(f"{request.layer_type} Layer 프롬프트 실행 시작: {request.knowledge_base}")
        
        # 노드들이 비어있으면 기본 노드 생성
        nodes = request.nodes
        if not nodes:
            default_node = NodeConfig(
                id=f"{request.layer_type[:3]}_sonar_pro_{int(time.time())}",
                model_type="sonar-pro",
                prompt=request.prompt,
                layer=request.layer_type,
                position={"x": 100, "y": 100}
            )
            nodes = [default_node]
        
        # 모든 노드의 프롬프트를 요청된 프롬프트로 업데이트
        for node in nodes:
            node.prompt = request.prompt
        
        # 컨텍스트 준비
        context_chunks = request.context_chunks or []
        
        # Layer별 실행 (새로운 함수 방식)
        if request.layer_type == "generation":
            from .layer_executors import execute_generation_layer
            result = execute_generation_layer(nodes, request.layer_input, context_chunks)
        elif request.layer_type == "ensemble":
            from .layer_executors import execute_ensemble_layer
            result = execute_ensemble_layer(nodes, request.layer_input, context_chunks)
        elif request.layer_type == "validation":
            from .layer_executors import execute_validation_layer
            result = execute_validation_layer(nodes, request.layer_input, context_chunks)
        else:
            raise ValueError(f"지원하지 않는 Layer 타입: {request.layer_type}")
        
        execution_time = (time.time() - start_time) * 1000
        
        # 새로운 응답 구조
        response_data = {
            "success": True,
            "layer_type": request.layer_type,
            "knowledge_base": request.knowledge_base,
            "layer_input": request.layer_input,
            "layer_prompt": request.prompt,
            "node_outputs": result,  # 노드별 general_output + forward_data
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"{request.layer_type} Layer 실행 완료: {execution_time:.1f}ms, 노드 수: {len(nodes)}")
        return LayerPromptResponse(**response_data)
        
    except Exception as e:
        logger.error(f"{request.layer_type} Layer 실행 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{request.layer_type} Layer 실행에 실패했습니다: {str(e)}"
        )
