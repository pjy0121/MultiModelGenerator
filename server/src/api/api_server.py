from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import time
from datetime import datetime
import logging
from typing import List

from ..services.langchain_llm_factory import LangChainLLMFactory
from ..core.config import Config
from ..services.vector_store import VectorStore
from ..core.models import (
    KnowledgeBaseInfo, 
    KnowledgeBaseListResponse,
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
    # 새로운 GET 기반 워크플로우 모델들
    SimpleWorkflowRequest,
    SimpleWorkflowResponse,
)

# LangChain 기반 실행기 import
from ..core.output_parser import parse_structured_output

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Spec 문서 기반 요구사항 생성 API",
    description="RAG와 LangChain을 사용한 지능형 요구사항 생성 시스템",
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
        
        # OpenAI, Google API 키 확인
        openai_status = "configured" if Config.OPENAI_API_KEY else "missing"
        google_status = "configured" if Config.GOOGLE_API_KEY else "missing"
        
        return {
            "status": "healthy",
            "openai_api_key": openai_status,
            "google_api_key": google_status,
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
        # LangChain Factory를 통해 모델 목록 가져오기
        llm_factory = LangChainLLMFactory()
        if provider == "openai":
            models = llm_factory.get_available_openai_models()
        elif provider == "google":
            models = llm_factory.get_available_google_models()
        else:
            # 지원하지 않는 제공자
            models = []
        
        # AvailableModel 형식으로 변환
        available_models = []
        for model in models:
            if isinstance(model, str):
                available_models.append(AvailableModel(
                    id=model,
                    name=model,
                    provider=provider
                ))
            else:
                available_models.append(model)
                
        return available_models
            
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
            default_node = {
                "id": f"{request.layer_type[:3]}_gpt35_{int(time.time())}",
                "model": "gpt-3.5-turbo",
                "prompt": request.prompt,
                "layer": request.layer_type,
                "position": {"x": 100, "y": 100}
            }
            nodes = [default_node]
        
        # 모든 노드의 프롬프트를 요청된 프롬프트로 업데이트
        for node in nodes:
            node["prompt"] = request.prompt
        
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


# ==================== LangGraph 워크플로우 API ====================

@app.post("/execute-langgraph-workflow")
async def execute_langgraph_workflow_endpoint(request: LayerPromptRequest):
    """
    LangGraph 기반 전체 워크플로우 실행
    Generation → Ensemble → Validation 순차 실행
    """
    start_time = time.time()
    
    try:
        logger.info(f"LangGraph 워크플로우 실행 시작: {request.knowledge_base}")
        
        # LangGraph 워크플로우 import (지연 로딩)
        try:
            from .langgraph_workflow import execute_langgraph_workflow
        except ImportError as import_error:
            logger.warning(f"LangGraph 임포트 실패: {import_error}")
            # Chain 기반 fallback 실행
            return await _execute_chain_fallback_workflow(request, start_time)
        
        # LangGraph 워크플로우 실행
        result = execute_langgraph_workflow(
            initial_input=request.layer_input,
            knowledge_base=request.knowledge_base,
            generation_nodes=request.nodes if request.nodes else None,
            ensemble_nodes=None,  # TODO: 구분해서 전달
            validation_nodes=None  # TODO: 구분해서 전달
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        if result.get("success", False):
            # 성공적인 LangGraph 실행
            response_data = {
                "success": True,
                "layer_type": "langgraph_workflow",
                "knowledge_base": request.knowledge_base,
                "layer_input": request.layer_input,
                "layer_prompt": "LangGraph Multi-Layer Workflow",
                "node_outputs": result.get("node_outputs", {}),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"LangGraph 워크플로우 완료: {execution_time:.1f}ms")
            return LayerPromptResponse(**response_data)
        else:
            # LangGraph 실행 실패, Chain 기반 fallback
            logger.warning("LangGraph 실행 실패, Chain 기반 fallback 시도")
            return await _execute_chain_fallback_workflow(request, start_time)
        
    except Exception as e:
        logger.error(f"LangGraph 워크플로우 실행 실패: {str(e)}")
        # Chain 기반 fallback
        try:
            return await _execute_chain_fallback_workflow(request, start_time)
        except Exception as fallback_error:
            logger.error(f"Fallback 실행도 실패: {fallback_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"워크플로우 실행에 실패했습니다: {str(e)}"
            )


async def _execute_chain_fallback_workflow(request: LayerPromptRequest, start_time: float):
    """Chain 기반 fallback 워크플로우"""
    from .chain_executors import ChainBasedLayerExecutors
    
    logger.info("Chain 기반 fallback 워크플로우 실행")
    
    chain_executors = ChainBasedLayerExecutors()
    
    # 단순화된 순차 실행
    try:
        # Generation
        gen_result = chain_executors.execute_generation_layer_with_chains(
            request.nodes if request.nodes else [],
            request.layer_input,
            request.knowledge_base
        )
        
        # Ensemble
        ens_input = gen_result.get("forward_data", request.layer_input)
        ens_result = chain_executors.execute_ensemble_layer_with_chains(
            request.nodes if request.nodes else [],
            ens_input,
            request.knowledge_base
        )
        
        # Validation
        val_input = ens_result.get("forward_data", ens_input)
        val_result = chain_executors.execute_validation_layer_with_chains(
            request.nodes if request.nodes else [],
            val_input,
            request.knowledge_base
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        # 결과 통합
        response_data = {
            "success": True,
            "layer_type": "chain_workflow",
            "knowledge_base": request.knowledge_base,
            "layer_input": request.layer_input,
            "layer_prompt": "Chain-based Multi-Layer Workflow",
            "node_outputs": {
                "generation": gen_result,
                "ensemble": ens_result,
                "validation": val_result,
                "forward_data": val_result.get("forward_data", "")
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Chain fallback 워크플로우 완료: {execution_time:.1f}ms")
        return LayerPromptResponse(**response_data)
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Chain fallback 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallback 워크플로우 실행에 실패했습니다: {str(e)}"
        )


# ==================== 새로운 GET 기반 단순 워크플로우 API ====================

@app.get("/simple-workflow", response_model=SimpleWorkflowResponse)
async def execute_simple_workflow(
    knowledge_base: str,
    keyword: str,
    search_intensity: str = "medium",
    generation_nodes: int = 2,
    ensemble_nodes: int = 1, 
    validation_nodes: int = 1,
    model_name: str = "gpt-3.5-turbo",
    provider: str = "openai"
):
    """
    GET 요청으로 전체 3-레이어 워크플로우를 한 번에 실행
    Python 클라이언트를 위한 단순화된 API
    """
    start_time = time.time()
    
    try:
        # 기본 프롬프트 import
        from ..core.default_prompts import DEFAULT_LAYER_PROMPTS, SEARCH_INTENSITY_MAPPING
        from .chain_executors import ChainBasedLayerExecutors
        
        logger.info(f"단순 워크플로우 실행 시작 - KB: {knowledge_base}, 키워드: {keyword}")
        
        # 검색 강도에 따른 top_k 값 설정
        top_k = SEARCH_INTENSITY_MAPPING.get(search_intensity, 50)
        
        # Chain 실행기 초기화
        chain_executors = ChainBasedLayerExecutors()
        
        # 1단계: Generation Layer 실행
        logger.info(f"Generation Layer 실행 - {generation_nodes}개 노드")
        
        # Generation 노드들 생성
        generation_layer_nodes = []
        for i in range(generation_nodes):
            node = {
                "id": f"gen_{i+1}",
                "model": model_name,
                "provider": provider,
                "prompt": DEFAULT_LAYER_PROMPTS["generation"],
                "layer": "generation"
            }
            generation_layer_nodes.append(node)
        
        # Generation Layer 실행
        gen_result = chain_executors.execute_generation_layer_with_chains(
            generation_layer_nodes,
            keyword,
            knowledge_base
        )
        
        logger.info("Generation Layer 완료")
        
        # 2단계: Ensemble Layer 실행
        logger.info(f"Ensemble Layer 실행 - {ensemble_nodes}개 노드")
        
        # Ensemble 노드들 생성
        ensemble_layer_nodes = []
        for i in range(ensemble_nodes):
            node = {
                "id": f"ens_{i+1}",
                "model": model_name,
                "provider": provider,
                "prompt": DEFAULT_LAYER_PROMPTS["ensemble"],
                "layer": "ensemble"
            }
            ensemble_layer_nodes.append(node)
        
        # Generation 결과를 Ensemble 입력으로 사용
        gen_forward_data = gen_result.get("forward_data", "")
        
        # Ensemble Layer 실행
        ens_result = chain_executors.execute_ensemble_layer_with_chains(
            ensemble_layer_nodes,
            gen_forward_data,
            knowledge_base
        )
        
        logger.info("Ensemble Layer 완료")
        
        # 3단계: Validation Layer 실행
        logger.info(f"Validation Layer 실행 - {validation_nodes}개 노드")
        
        # Validation 노드들 생성
        validation_layer_nodes = []
        for i in range(validation_nodes):
            node = {
                "id": f"val_{i+1}",
                "model": model_name,
                "provider": provider,
                "prompt": DEFAULT_LAYER_PROMPTS["validation"],
                "layer": "validation"
            }
            validation_layer_nodes.append(node)
        
        # Ensemble 결과를 Validation 입력으로 사용
        ens_forward_data = ens_result.get("forward_data", "")
        
        # Validation Layer 실행
        val_result = chain_executors.execute_validation_layer_with_chains(
            validation_layer_nodes,
            ens_forward_data,
            knowledge_base
        )
        
        logger.info("Validation Layer 완료")
        
        # 실행 시간 계산
        total_execution_time = time.time() - start_time
        
        # 최종 결과 추출 (마크다운 표)
        final_result = val_result.get("forward_data", "")
        
        # 실행 요약 정보
        execution_summary = {
            "knowledge_base": knowledge_base,
            "keyword": keyword,
            "search_intensity": search_intensity,
            "top_k_used": top_k,
            "nodes_executed": {
                "generation": generation_nodes,
                "ensemble": ensemble_nodes,
                "validation": validation_nodes
            },
            "model_info": {
                "model_name": model_name,
                "provider": provider
            },
            "layer_results": {
                "generation_outputs": gen_result.get("forward_data", ""),
                "ensemble_output": ens_result.get("forward_data", ""),
                "validation_output": val_result.get("forward_data", "")
            }
        }
        
        logger.info(f"단순 워크플로우 완료 - 총 실행시간: {total_execution_time:.2f}초")
        
        return SimpleWorkflowResponse(
            success=True,
            final_result=final_result,
            execution_summary=execution_summary,
            total_execution_time=total_execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"단순 워크플로우 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"단순 워크플로우 실행에 실패했습니다: {str(e)}"
        )
