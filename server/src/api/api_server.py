from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import logging
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

if __name__ == "__main__":
    main()
