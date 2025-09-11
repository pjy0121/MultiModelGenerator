from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import time
from datetime import datetime
import logging
from typing import List
from ..core.workflow_engine import WorkflowEngine
from ..core.prompts import get_default_prompt

from ..core.config import Config
from ..services.vector_store import VectorStore
from ..services.perplexity_client import PerplexityClient
from ..core.models import (
    RequirementRequest, 
    RequirementResponse, 
    ErrorResponse, 
    KnowledgeBaseInfo, 
    KnowledgeBaseListResponse,
    WorkflowRequest, 
    WorkflowResponse,
    # 새로운 개별 노드 실행 모델들
    SearchRequest,
    SearchResponse,
    SingleNodeRequest,
    SingleNodeResponse,
    EnsembleRequest,
    ValidationRequest,
    ValidationResponse,
    ValidationChange,
    NodeConfig,
    NodeOutput,
    ModelType,
    # 새로운 Layer별 실행 모델들
    LayerExecutionRequest,
    LayerExecutionResponse,
    ValidationLayerResponse,
    # 새로운 Layer별 프롬프트 시스템 모델들
    LayerPromptRequest,
    LayerPromptResponse,
    ValidationLayerPromptResponse,
)

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

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequirementGenerator:
    """요구사항 생성 서비스"""
    
    def __init__(self):
        self.perplexity_client = None
    
    def _get_perplexity_client(self):
        """지연 로딩으로 Perplexity 클라이언트 초기화"""
        if self.perplexity_client is None:
            try:
                self.perplexity_client = PerplexityClient()
                logger.info("Perplexity 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"Perplexity 클라이언트 초기화 실패: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Perplexity API 연결 실패: {str(e)}"
                )
        return self.perplexity_client
    
    def generate_requirements(self, kb_name: str, keyword: str, validation_rounds: int = 1) -> dict:
        """요구사항 생성 (다중 검증 지원)"""
        try:
            # 지식베이스 초기화 및 확인
            vector_store = VectorStore(kb_name)
            status = vector_store.get_status()
            
            if not status['exists'] or status['count'] == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"지식베이스 '{kb_name}'을 찾을 수 없거나 비어있습니다."
                )
            
            # 관련 청크 검색
            logger.info(f"지식베이스 '{kb_name}'에서 키워드 '{keyword}' 검색 중...")
            relevant_chunks = vector_store.search_similar_chunks(keyword)
            
            if not relevant_chunks:
                return {
                    "success": True,
                    "knowledge_base": kb_name,
                    "keyword": keyword,
                    "requirements": "관련 문서를 찾을 수 없어 요구사항을 생성할 수 없습니다.",
                    "chunks_found": 0,
                    "validation_rounds": 0,
                    "generated_at": datetime.now()
                }
            
            logger.info(f"{len(relevant_chunks)}개의 관련 청크 발견")
            
            # Perplexity 클라이언트 가져오기
            perplexity_client = self._get_perplexity_client()
            
            # 다단계 검증을 통한 요구사항 생성
            logger.info(f"AI 요구사항 생성 및 {validation_rounds}회 검증 시작...")
            final_requirements = perplexity_client.multi_stage_validation(
                keyword, relevant_chunks, validation_rounds
            )
            
            logger.info(f"요구사항 생성 완료 (검증 {validation_rounds}회)")
            
            return {
                "success": True,
                "knowledge_base": kb_name,
                "keyword": keyword,
                "requirements": final_requirements,
                "chunks_found": len(relevant_chunks),
                "validation_rounds": validation_rounds,
                "generated_at": datetime.now()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"요구사항 생성 중 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"서버 내부 오류: {str(e)}"
            )

# 서비스 인스턴스
requirement_generator = RequirementGenerator()
workflow_engine = None

def get_workflow_engine():
    """WorkflowEngine 지연 로딩"""
    global workflow_engine
    if workflow_engine is None:
        try:
            workflow_engine = WorkflowEngine()
            logger.info("WorkflowEngine 초기화 완료")
        except Exception as e:
            logger.error(f"WorkflowEngine 초기화 실패: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"워크플로우 엔진 초기화 실패: {str(e)}"
            )
    return workflow_engine

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
        # 지식베이스 목록 확인
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
    """지식베이스 목록 조회"""
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
        logger.error(f"지식베이스 목록 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="지식베이스 목록을 조회할 수 없습니다."
        )

@app.get("/knowledge-bases/{kb_name}/status", 
         response_model=KnowledgeBaseInfo, 
         tags=["Knowledge Base"])
async def get_knowledge_base_status(kb_name: str):
    """특정 지식베이스 상태 조회"""
    try:
        vector_store = VectorStore(kb_name)
        status = vector_store.get_status()
        
        if not status['exists']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"지식베이스 '{kb_name}'을 찾을 수 없습니다."
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
        logger.error(f"지식베이스 상태 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"지식베이스 상태를 조회할 수 없습니다: {str(e)}"
        )

@app.post("/generate-requirements", 
          response_model=RequirementResponse, 
          tags=["Requirements"])
async def generate_requirements(request: RequirementRequest):
    """요구사항 생성 API (다중 검증 지원)"""
    try:
        logger.info(f"요구사항 생성 요청: KB={request.knowledge_base}, 키워드={request.keyword}, 검증횟수={request.validation_rounds}")
        
        result = requirement_generator.generate_requirements(
            request.knowledge_base, 
            request.keyword,
            request.validation_rounds
        )
        
        return RequirementResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요구사항 생성 API 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"요구사항 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_type="HTTP_ERROR",
            error_message=exc.detail
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.error(f"예상치 못한 오류: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_type="INTERNAL_SERVER_ERROR",
            error_message="서버 내부 오류가 발생했습니다."
        ).dict()
    )

@app.get("/available-models", tags=["Models"])
async def get_available_models():
    """사용 가능한 모델 목록 조회"""
    try:
        # Perplexity Client를 통해 실제 모델 목록 조회
        perplexity_client = PerplexityClient()
        available_models = perplexity_client.get_available_models()
        
        # 기본 모델 목록에 실제 Perplexity 모델들 추가
        models = [
            {"value": "sonar-pro", "label": "Perplexity Sonar Pro", "provider": "perplexity"},
            {"value": "sonar-medium", "label": "Perplexity Sonar Medium", "provider": "perplexity"},
        ]
        
        # 실제 API에서 가져온 모델들 추가
        for model in available_models:
            if model not in [m["value"] for m in models]:
                models.append({
                    "value": model,
                    "label": f"Perplexity {model.replace('-', ' ').title()}",
                    "provider": "perplexity"
                })
        
        # 향후 확장용 모델들
        models.extend([
            {"value": "gpt-4", "label": "OpenAI GPT-4 (Coming Soon)", "provider": "openai", "disabled": True},
            {"value": "gpt-3.5-turbo", "label": "OpenAI GPT-3.5 (Coming Soon)", "provider": "openai", "disabled": True}
        ])
        
        return {"models": models}
        
    except Exception as e:
        logger.warning(f"모델 목록 조회 실패: {e}")
        # 오류 시 기본 모델 목록 반환
        return {
            "models": [
                {"value": "sonar-pro", "label": "Perplexity Sonar Pro", "provider": "perplexity"},
                {"value": "sonar-medium", "label": "Perplexity Sonar Medium", "provider": "perplexity"},
                {"value": "gpt-4", "label": "OpenAI GPT-4 (Coming Soon)", "provider": "openai", "disabled": True},
                {"value": "gpt-3.5-turbo", "label": "OpenAI GPT-3.5 (Coming Soon)", "provider": "openai", "disabled": True}
            ]
        }

@app.get("/default-prompts", tags=["Prompts"])
async def get_default_prompts():
    """기본 프롬프트 템플릿 조회"""
    return {
        "generation": get_default_prompt("generation"),
        "ensemble": get_default_prompt("ensemble"),
        "validation": get_default_prompt("validation")
    }

@app.post("/execute-workflow", response_model=WorkflowResponse, tags=["Workflow"])
async def execute_workflow(request: WorkflowRequest):
    """워크플로우 실행"""
    try:
        logger.info(f"워크플로우 실행 요청: KB={request.knowledge_base}, 키워드={request.keyword}")
        
        # 지식베이스에서 관련 청크 검색
        vector_store = VectorStore(request.knowledge_base)
        status = vector_store.get_status()
        
        if not status['exists'] or status['count'] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"지식베이스 '{request.knowledge_base}'를 찾을 수 없습니다."
            )
        
        relevant_chunks = vector_store.search_similar_chunks(request.keyword)
        
        if not relevant_chunks:
            raise HTTPException(
                status_code=404,
                detail=f"키워드 '{request.keyword}'와 관련된 문서를 찾을 수 없습니다."
            )
        
        # 워크플로우 실행
        workflow_engine = get_workflow_engine()
        result = workflow_engine.execute_workflow(
            request.workflow_config,
            request.keyword,
            relevant_chunks
        )
        
        return WorkflowResponse(
            success=True,
            knowledge_base=request.knowledge_base,
            keyword=request.keyword,
            final_requirements=result["final_requirements"],
            node_outputs=result["node_outputs"],
            total_execution_time=result["total_execution_time"],
            generated_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"워크플로우 실행 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}"
        )

# ==================== 새로운 개별 노드 실행 API들 ====================

@app.post("/search-context", response_model=SearchResponse, tags=["Workflow Steps"])
async def search_context(request: SearchRequest):
    """컨텍스트 청크 검색 (워크플로우 1단계)"""
    try:
        logger.info(f"컨텍스트 검색: KB={request.knowledge_base}, 쿼리={request.query}")
        
        # 지식베이스 확인
        vector_store = VectorStore(request.knowledge_base)
        status = vector_store.get_status()
        
        if not status['exists'] or status['count'] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"지식베이스 '{request.knowledge_base}'를 찾을 수 없습니다."
            )
        
        # 컨텍스트 검색
        chunks = vector_store.search_similar_chunks(request.query, request.top_k)
        
        return SearchResponse(
            success=True,
            knowledge_base=request.knowledge_base,
            query=request.query,
            chunks=chunks,
            chunk_count=len(chunks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"컨텍스트 검색 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"컨텍스트 검색 실패: {str(e)}"
        )

@app.post("/execute-node", response_model=SingleNodeResponse, tags=["Workflow Steps"])
async def execute_single_node(request: SingleNodeRequest):
    """단일 노드 실행 (Generation/Ensemble/Validation Layer)"""
    try:
        logger.info(f"노드 실행: {request.node_config.id} ({request.node_config.layer})")
        
        # 컨텍스트 청크가 없으면 자동으로 검색
        context_chunks = request.context_chunks
        if not context_chunks:
            vector_store = VectorStore(request.knowledge_base)
            context_chunks = vector_store.search_similar_chunks(request.input_data)
        
        # WorkflowEngine을 통한 노드 실행
        workflow_engine = get_workflow_engine()
        node_output = workflow_engine.execute_node(
            request.node_config, 
            request.input_data, 
            context_chunks
        )
        
        return SingleNodeResponse(
            success=True,
            node_output=node_output,
            context_chunks_used=context_chunks
        )
        
    except Exception as e:
        logger.error(f"노드 실행 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"노드 실행 실패: {str(e)}"
        )

@app.post("/execute-ensemble", response_model=SingleNodeResponse, tags=["Workflow Steps"])
async def execute_ensemble_node(request: EnsembleRequest):
    """앙상블 레이어 실행 (여러 Generation 결과 통합)"""
    try:
        logger.info(f"앙상블 노드 실행: {request.ensemble_node.id}")
        
        # Generation 결과들을 하나의 입력으로 결합
        combined_input = "\n\n=== Generation Layer 결과들 ===\n\n" + "\n\n".join(
            f"Generation {i+1}:\n{result}" 
            for i, result in enumerate(request.generation_results)
        )
        
        # 컨텍스트 청크 준비
        context_chunks = request.context_chunks or []
        
        # 앙상블 노드 실행
        workflow_engine = get_workflow_engine()
        node_output = workflow_engine.execute_node(
            request.ensemble_node,
            combined_input,
            context_chunks
        )
        
        return SingleNodeResponse(
            success=True,
            node_output=node_output,
            context_chunks_used=context_chunks
        )
        
    except Exception as e:
        logger.error(f"앙상블 실행 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"앙상블 실행 실패: {str(e)}"
        )

@app.post("/execute-validation", response_model=ValidationResponse, tags=["Workflow Steps"])
async def execute_validation_node(request: ValidationRequest):
    """검증 레이어 실행 (변경사항 추적 포함)"""
    try:
        logger.info(f"검증 노드 실행: {request.validation_node.id}")
        
        # 컨텍스트 청크 준비
        context_chunks = request.context_chunks or []
        
        # 검증 노드 실행
        workflow_engine = get_workflow_engine()
        node_output = workflow_engine.execute_node(
            request.validation_node,
            request.input_requirements,
            context_chunks
        )
        
        # 변경사항 분석 (간단한 구현 - 실제로는 더 정교한 비교 필요)
        changes = analyze_validation_changes(
            request.input_requirements, 
            node_output.requirements
        )
        
        return ValidationResponse(
            success=True,
            node_output=node_output,
            changes=changes,
            context_chunks_used=context_chunks
        )
        
    except Exception as e:
        logger.error(f"검증 실행 중 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"검증 실행 실패: {str(e)}"
        )

def analyze_validation_changes(input_requirements: str, output_requirements: str) -> List[ValidationChange]:
    """검증 과정에서 발생한 변경사항 분석"""
    changes = []
    
    try:
        # 간단한 변경사항 감지 (실제로는 더 정교한 구현 필요)
        input_lines = input_requirements.split('\n')
        output_lines = output_requirements.split('\n')
        
        # 테이블 행만 추출 (|로 시작하는 행들)
        input_rows = [line.strip() for line in input_lines if line.strip().startswith('|') and '---' not in line]
        output_rows = [line.strip() for line in output_lines if line.strip().startswith('|') and '---' not in line]
        
        # 헤더 제외
        if input_rows: input_rows = input_rows[1:]
        if output_rows: output_rows = output_rows[1:]
        
        # 길이가 다르면 요구사항이 추가/삭제된 것으로 간주
        if len(output_rows) > len(input_rows):
            for i in range(len(input_rows), len(output_rows)):
                if i < len(output_rows):
                    changes.append(ValidationChange(
                        requirement_id=f"REQ-{i+1:03d}",
                        original="",
                        modified=output_rows[i],
                        change_type="added",
                        reason="검증 과정에서 추가된 요구사항"
                    ))
        elif len(output_rows) < len(input_rows):
            for i in range(len(output_rows), len(input_rows)):
                changes.append(ValidationChange(
                    requirement_id=f"REQ-{i+1:03d}",
                    original=input_rows[i] if i < len(input_rows) else "",
                    modified="",
                    change_type="removed",
                    reason="검증 과정에서 제거된 요구사항"
                ))
        
        # 내용이 다른 행들 찾기
        min_len = min(len(input_rows), len(output_rows))
        for i in range(min_len):
            if input_rows[i] != output_rows[i]:
                changes.append(ValidationChange(
                    requirement_id=f"REQ-{i+1:03d}",
                    original=input_rows[i],
                    modified=output_rows[i],
                    change_type="modified",
                    reason="검증 과정에서 수정된 요구사항"
                ))
                
    except Exception as e:
        logger.warning(f"변경사항 분석 중 오류: {e}")
        # 오류 시 전체가 변경된 것으로 처리
        changes.append(ValidationChange(
            requirement_id="ALL",
            original=input_requirements[:100] + "...",
            modified=output_requirements[:100] + "...",
            change_type="modified",
            reason="전체 요구사항이 검증 과정에서 재구성됨"
        ))
    
    return changes

# ==================== 새로운 Layer별 실행 API ====================

@app.post("/execute-generation-layer", response_model=LayerExecutionResponse)
async def execute_generation_layer(request: LayerExecutionRequest):
    """Generation Layer 전체 실행"""
    start_time = time.time()
    
    try:
        logger.info(f"Generation Layer 실행 시작: {request.knowledge_base}")
        
        # 컨텍스트 검색 (없으면 새로 검색)
        if not request.context_chunks:
            vector_store = VectorStore(request.knowledge_base)
            context_chunks = vector_store.search_similar_chunks(request.input_data, Config.SEARCH_TOP_K)
        else:
            context_chunks = request.context_chunks
        
        outputs = []
        failed_nodes = []
        
        # 각 Generation 노드 병렬 실행
        for node in request.nodes:
            try:
                # Perplexity 클라이언트 초기화
                perplexity = PerplexityClient()
                
                # 프롬프트 생성
                context_text = "\n".join(context_chunks)
                prompt = f"""
{node.prompt}

참고 문서:
{context_text}

키워드: {request.input_data}

위 정보를 바탕으로 구체적인 기능 요구사항을 생성해주세요.
"""
                
                # AI 모델 실행
                node_start = time.time()
                ai_response = perplexity.generate_requirements(prompt, node.model_type)
                node_time = time.time() - node_start
                
                # 결과 저장
                outputs.append(NodeOutput(
                    node_id=node.id,
                    model_type=node.model_type,
                    requirements=ai_response,
                    execution_time=node_time
                ))
                
            except Exception as e:
                logger.error(f"노드 {node.id} 실행 실패: {e}")
                failed_nodes.append(node.id)
        
        # 결과 통합 (간단한 결합)
        if outputs:
            combined_result = "\n\n".join([output.requirements for output in outputs])
        else:
            combined_result = ""
        
        execution_time = time.time() - start_time
        
        return LayerExecutionResponse(
            success=len(outputs) > 0,
            layer_type="generation",
            knowledge_base=request.knowledge_base,
            input_data=request.input_data,
            outputs=outputs,
            combined_result=combined_result,
            failed_nodes=failed_nodes,
            execution_time=execution_time,
            context_chunks_used=context_chunks
        )
        
    except Exception as e:
        logger.error(f"Generation Layer 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation Layer 실행 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/execute-ensemble-layer", response_model=LayerExecutionResponse)
async def execute_ensemble_layer(request: LayerExecutionRequest):
    """Ensemble Layer 실행"""
    start_time = time.time()
    
    try:
        logger.info(f"Ensemble Layer 실행 시작: {request.knowledge_base}")
        
        if not request.nodes or len(request.nodes) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ensemble Layer는 정확히 하나의 노드가 필요합니다"
            )
        
        node = request.nodes[0]
        context_chunks = request.context_chunks or []
        
        # Perplexity 클라이언트 초기화
        perplexity = PerplexityClient()
        
        # 프롬프트 생성
        context_text = "\n".join(context_chunks)
        prompt = f"""
{node.prompt}

참고 문서:
{context_text}

여러 AI 모델이 생성한 요구사항들:
{request.input_data}

위 요구사항들을 종합하여 일관성 있고 완전한 요구사항으로 통합해주세요.
"""
        
        # AI 모델 실행
        node_start = time.time()
        ai_response = perplexity.generate_requirements(prompt, node.model_type)
        node_time = time.time() - node_start
        
        # 결과 저장
        output = NodeOutput(
            node_id=node.id,
            model_type=node.model_type,
            requirements=ai_response,
            execution_time=node_time
        )
        
        execution_time = time.time() - start_time
        
        return LayerExecutionResponse(
            success=True,
            layer_type="ensemble",
            knowledge_base=request.knowledge_base,
            input_data=request.input_data,
            outputs=[output],
            combined_result=ai_response,
            failed_nodes=[],
            execution_time=execution_time,
            context_chunks_used=context_chunks
        )
        
    except Exception as e:
        logger.error(f"Ensemble Layer 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ensemble Layer 실행 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/execute-validation-layer", response_model=ValidationLayerResponse)
async def execute_validation_layer(request: LayerExecutionRequest):
    """Validation Layer 실행"""
    start_time = time.time()
    
    try:
        logger.info(f"Validation Layer 실행 시작: {request.knowledge_base}")
        
        context_chunks = request.context_chunks or []
        outputs = []
        failed_nodes = []
        validation_changes = []
        filtered_requirements = []
        
        current_requirements = request.input_data
        
        # 각 Validation 노드 순차 실행
        for i, node in enumerate(request.nodes):
            try:
                # Perplexity 클라이언트 초기화
                perplexity = PerplexityClient()
                
                # 프롬프트 생성
                context_text = "\n".join(context_chunks)
                prompt = f"""
{node.prompt}

참고 문서:
{context_text}

현재 요구사항:
{current_requirements}

위 요구사항을 검증하고 개선해주세요.
"""
                
                # AI 모델 실행
                node_start = time.time()
                ai_response = perplexity.generate_requirements(prompt, node.model_type)
                node_time = time.time() - node_start
                
                # 변경사항 분석
                changes = analyze_validation_changes(current_requirements, ai_response)
                validation_changes.extend(changes)
                
                # 필터링된 요구사항 추출 (제거된 것들)
                for change in changes:
                    if change.change_type == "removed":
                        filtered_requirements.append(change.original)
                
                # 결과 저장
                outputs.append(NodeOutput(
                    node_id=node.id,
                    model_type=node.model_type,
                    requirements=ai_response,
                    execution_time=node_time
                ))
                
                # 다음 노드를 위해 결과 업데이트
                current_requirements = ai_response
                
            except Exception as e:
                logger.error(f"Validation 노드 {node.id} 실행 실패: {e}")
                failed_nodes.append(node.id)
        
        execution_time = time.time() - start_time
        
        return ValidationLayerResponse(
            success=len(outputs) > 0,
            layer_type="validation",
            knowledge_base=request.knowledge_base,
            input_data=request.input_data,
            outputs=outputs,
            combined_result=current_requirements,
            failed_nodes=failed_nodes,
            execution_time=execution_time,
            context_chunks_used=context_chunks,
            filtered_requirements=filtered_requirements,
            validation_changes=validation_changes
        )
        
    except Exception as e:
        logger.error(f"Validation Layer 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation Layer 실행 중 오류가 발생했습니다: {str(e)}"
        )

def main():
    """API 서버 실행"""
    print("🚀 Spec 문서 기반 요구사항 생성 API 서버 시작")
    print("=" * 60)
    
    # 환경 변수 확인
    if not Config.PERPLEXITY_API_KEY:
        print("❌ PERPLEXITY_API_KEY가 설정되지 않았습니다!")
        print("💡 .env 파일을 확인하거나 환경 변수를 설정하세요.")
        return
    
    print("✅ 환경 변수 확인 완료")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔄 ReDoc: http://localhost:8000/redoc")
    print("❤️ Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 중에만 사용
        log_level="info"
    )

# ==================== Layer별 프롬프트 시스템 엔드포인트들 ====================

@app.post("/execute-layer-prompt", response_model=LayerPromptResponse)
async def execute_layer_prompt(request: LayerPromptRequest):
    """
    Layer별 프롬프트로 실행 (모든 Layer 타입 지원)
    """
    try:
        start_time = time.time()
        logger.info(f"{request.layer_type} Layer 프롬프트 실행 시작: {request.knowledge_base}")
        
        # 워크플로우 엔진 초기화
        engine = WorkflowEngine()
        
        # 요청에서 전달받은 노드들 사용
        nodes = request.nodes
        
        # 노드들이 비어있으면 기본 노드 생성 (백업)
        if not nodes:
            if request.layer_type == "generation":
                nodes = [
                    NodeConfig(
                        id=f"gen_sonar_pro_{int(time.time())}",
                        model_type=ModelType.PERPLEXITY_SONAR_PRO,
                        prompt=request.prompt,
                        layer="generation",
                        position={"x": 100, "y": 100}
                    )
                ]
            elif request.layer_type == "ensemble":
                nodes = [
                    NodeConfig(
                        id=f"ens_sonar_pro_{int(time.time())}",
                        model_type=ModelType.PERPLEXITY_SONAR_PRO,
                        prompt=request.prompt,
                        layer="ensemble",
                        position={"x": 300, "y": 200}
                    )
                ]
            elif request.layer_type == "validation":
                nodes = [
                    NodeConfig(
                        id=f"val_sonar_pro_{int(time.time())}",
                        model_type=ModelType.PERPLEXITY_SONAR_PRO,
                        prompt=request.prompt,
                        layer="validation",
                        position={"x": 500, "y": 100}
                    )
                ]
            else:
                raise ValueError(f"지원하지 않는 Layer 타입: {request.layer_type}")
        
        # 모든 노드의 프롬프트를 요청된 프롬프트로 업데이트
        for node in nodes:
            node.prompt = request.prompt
        
        # Validation Layer를 위한 추가 컨텍스트 검색
        enhanced_context_chunks = request.context_chunks or []
        if request.layer_type == "validation" and request.knowledge_base:
            try:
                # Validation을 위해 더 많은 컨텍스트 검색
                vector_store = VectorStore(request.knowledge_base)
                
                # 입력 데이터에서 키워드 추출하여 추가 검색
                import re
                # 테이블에서 요구사항 텍스트 추출
                requirement_texts = re.findall(r'\|\s*[^|]+\s*\|\s*([^|]+)\s*\|', request.input_data)
                search_terms = []
                
                # 요구사항에서 중요한 키워드들 추출
                for req_text in requirement_texts[:3]:  # 처음 3개 요구사항만 사용
                    if req_text.strip() and len(req_text.strip()) > 10:
                        search_terms.append(req_text.strip()[:50])  # 처음 50자만 사용
                
                # 각 검색어로 컨텍스트 검색
                all_chunks = set(enhanced_context_chunks)
                for term in search_terms:
                    if term:
                        chunks = vector_store.search_similar_chunks(term, top_k=5)
                        all_chunks.update(chunks)
                
                enhanced_context_chunks = list(all_chunks)[:15]  # 최대 15개 청크
                logger.info(f"Validation을 위한 확장 컨텍스트: {len(enhanced_context_chunks)}개 청크")
                
            except Exception as e:
                logger.warning(f"Validation 컨텍스트 확장 실패: {e}")
                # 실패해도 기존 컨텍스트로 진행
        
        # 각 노드 개별 실행
        outputs = []
        failed_nodes = []
        validation_steps = []
        current_input = request.input_data
        
        if request.layer_type == "validation":
            # Validation Layer: 노드를 순차적으로 실행하여 검증 과정 진행
            for i, node in enumerate(nodes):
                try:
                    logger.info(f"Validation 노드 {i+1}/{len(nodes)} 실행 중: {node.id}")
                    node_output = engine.execute_node(node, current_input, enhanced_context_chunks)
                    outputs.append(node_output)
                    outputs.append(node_output)
                    
                    # 검증 단계 기록
                    validation_step = {
                        "step": i + 1,
                        "node_id": node.id,
                        "model_type": node.model_type.value,
                        "input": current_input[:200] + "..." if len(current_input) > 200 else current_input,
                        "output": node_output.requirements[:200] + "..." if len(node_output.requirements) > 200 else node_output.requirements,
                        "execution_time": node_output.execution_time
                    }
                    validation_steps.append(validation_step)
                    
                    # 다음 노드를 위해 현재 출력을 입력으로 설정
                    current_input = node_output.requirements
                    
                except Exception as e:
                    failed_nodes.append(node.id)
                    logger.error(f"Validation 노드 {node.id} 실행 실패: {str(e)}")
        else:
            # Generation/Ensemble Layer: 병렬 실행 (기존 컨텍스트 사용)
            for node in nodes:
                try:
                    node_output = engine.execute_node(node, request.input_data, request.context_chunks or [])
                    outputs.append(node_output)
                except Exception as e:
                    failed_nodes.append(node.id)
                    logger.error(f"노드 {node.id} 실행 실패: {str(e)}")
        
        # 결과 취합
        if outputs:
            if request.layer_type == "validation":
                # Validation: 마지막 노드의 출력이 최종 결과
                combined_result = outputs[-1].requirements if outputs else ""
                final_validated_result = combined_result
            else:
                # Generation/Ensemble: 모든 출력을 결합
                combined_result = "\n\n".join([output.requirements for output in outputs])
                final_validated_result = ""
        else:
            combined_result = "모든 노드 실행이 실패했습니다."
            final_validated_result = ""
        
        execution_time = (time.time() - start_time) * 1000
        
        if request.layer_type == "validation":
            # 요구사항 필터링 및 분석
            filtered_requirements = []
            removed_requirements = []
            
            if outputs:
                # 마지막 검증 결과에서 요구사항 추출
                final_output = outputs[-1].requirements
                import re
                
                # 필터링된 요구사항 표 추출
                filtered_table_match = re.search(r'\*\*필터링된 요구사항 표:\*\*(.*?)(?=\*\*제거된 요구사항:|\Z)', final_output, re.DOTALL)
                if filtered_table_match:
                    filtered_table = filtered_table_match.group(1).strip()
                    table_rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', filtered_table)
                    for row in table_rows:
                        if row[0].strip() and not row[0].strip().startswith('ID') and not row[0].strip().startswith('-'):
                            req_id = row[0].strip()
                            req_text = row[1].strip()
                            source = row[2].strip()
                            status = row[3].strip()
                            if req_id and req_text:
                                filtered_requirements.append(f"{req_id}: {req_text} (출처: {source}, 상태: {status})")
                
                # 제거된 요구사항 추출
                removed_match = re.search(r'\*\*제거된 요구사항:\*\*(.*?)$', final_output, re.DOTALL)
                if removed_match:
                    removed_section = removed_match.group(1).strip()
                    # 제거된 요구사항 파싱 (간단한 형태)
                    removed_lines = [line.strip() for line in removed_section.split('\n') if line.strip() and not line.strip().startswith('(')]
                    for line in removed_lines:
                        if line and '-' in line:
                            removed_requirements.append(line)
                
                # 원본 요구사항과 비교하여 필터링 통계 생성
                original_input = request.input_data
                original_table_rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', original_input)
                original_count = len([row for row in original_table_rows if row[0].strip() and not row[0].strip().startswith('ID') and not row[0].strip().startswith('-')])
                filtered_count = len(filtered_requirements)
                
                logger.info(f"Validation 필터링 결과: 원본 {original_count}개 → 필터링 후 {filtered_count}개 (제거: {original_count - filtered_count}개)")
            
            return ValidationLayerPromptResponse(
                success=len(outputs) > 0,
                layer_type=request.layer_type,
                knowledge_base=request.knowledge_base,
                input_data=request.input_data,
                layer_prompt=request.prompt,
                outputs=outputs,
                combined_result=combined_result,
                failed_nodes=failed_nodes,
                execution_time=execution_time,
                context_chunks_used=enhanced_context_chunks,
                updated_input=combined_result,  # Validation의 경우 결과가 다음 입력
                filtered_requirements=filtered_requirements,
                validation_changes=removed_requirements,  # 제거된 요구사항을 변경사항으로 활용
                final_validated_result=final_validated_result,
                validation_steps=validation_steps
            )
        else:
            return LayerPromptResponse(
                success=len(outputs) > 0,
                layer_type=request.layer_type,
                knowledge_base=request.knowledge_base,
                input_data=request.input_data,
                layer_prompt=request.prompt,
                outputs=outputs,
                combined_result=combined_result,
                failed_nodes=failed_nodes,
                execution_time=execution_time,
                context_chunks_used=request.context_chunks or [],
                updated_input=combined_result
            )
            
    except Exception as e:
        logger.error(f"{request.layer_type} Layer 프롬프트 실행 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{request.layer_type} Layer 프롬프트 실행 실패: {str(e)}")

if __name__ == "__main__":
    main()
