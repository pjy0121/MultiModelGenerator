from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
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

def extract_final_requirements_table(content: str) -> str:
    """
    컨텐츠에서 최종 요구사항 표만 추출하는 함수 - 완전한 표 추출 보장
    마지막 행 잘림 방지를 위한 개선된 로직
    """
    import re
    
    if not content or not content.strip():
        return ""
    
    logger.info("최종 요구사항 표 추출 시작")
    logger.info(f"입력 콘텐츠 길이: {len(content)} 문자")
    
    # 방법 1: 라인별 분석으로 완전한 표 추출
    lines = content.split('\n')
    table_start = -1
    table_end = -1
    
    # 표 시작점 찾기
    for i, line in enumerate(lines):
        if '|' in line and line.count('|') >= 3:  # 최소 3개 컬럼
            # 다음 줄이 구분선인지 확인
            if i + 1 < len(lines) and ('---' in lines[i + 1] or '===' in lines[i + 1]):
                table_start = i
                break
    
    # 표 끝점 찾기 (마지막 | 포함 행까지)
    if table_start >= 0:
        for i in range(table_start + 2, len(lines)):  # 헤더와 구분선 다음부터
            if '|' in lines[i] and lines[i].strip():
                table_end = i
            elif lines[i].strip() == '' and table_end >= 0:
                # 빈 줄을 만나면 표 끝으로 간주하되, 다음 줄도 체크
                if i + 1 < len(lines) and '|' not in lines[i + 1]:
                    break
            elif '|' not in lines[i] and lines[i].strip():
                # 표가 아닌 내용을 만나면 표 끝
                break
    
    # 라인별 분석으로 추출된 표
    line_based_table = ""
    if table_start >= 0 and table_end >= 0:
        table_lines = lines[table_start:table_end + 1]
        line_based_table = '\n'.join(table_lines).strip()
        logger.info(f"라인별 분석으로 표 추출 성공 - 시작: {table_start}, 끝: {table_end}, 줄 수: {len(table_lines)}")
    
    # 방법 2: 개선된 정규식 패턴 (더 포괄적)
    # 표의 모든 행을 캡처하되 마지막 행 누락 방지
    enhanced_pattern = r'(\|[^\n]*\|[^\n]*\n\s*\|[-\s:=]+\|[-\s:=]+[^\n]*\n(?:\s*\|[^\n]*\|[^\n]*\n?)*)'
    
    enhanced_tables = re.findall(enhanced_pattern, content, re.MULTILINE | re.DOTALL)
    
    # 방법 3: 단순 패턴으로 모든 연속된 표 행 찾기
    simple_pattern = r'(\|[^\n]*\n(?:\s*\|[^\n]*\n)*)'
    simple_tables = re.findall(simple_pattern, content, re.MULTILINE)
    
    # 모든 후보 테이블 수집
    all_candidates = []
    
    if line_based_table:
        all_candidates.append(('line_based', line_based_table))
    
    for table in enhanced_tables:
        if table.strip():
            all_candidates.append(('enhanced_regex', table.strip()))
    
    for table in simple_tables:
        if table.strip() and table.count('\n') >= 2:  # 최소 3줄
            all_candidates.append(('simple_regex', table.strip()))
    
    # 유효한 표 필터링 및 선택 (강화된 제거 테이블 감지)
    valid_tables = []
    for method, table in all_candidates:
        lines = [line.strip() for line in table.split('\n') if line.strip()]
        if len(lines) >= 3:  # 헤더 + 구분선 + 최소 1개 데이터 행
            
            # 강화된 제거된 항목 키워드 검사
            removal_keywords = [
                '제거된', '삭제된', '제외된', '제거 사유', '삭제 사유',
                'removed', 'deleted', 'excluded', 'elimination', 'removal',
                '필터링된', '걸러진', '배제된', '탈락된',
                '부적절한', '불필요한', '중복된'
            ]
            
            # 전체 테이블 내용에서 제거 키워드 검사
            has_removal_keywords = any(keyword.lower() in table.lower() for keyword in removal_keywords)
            
            # 제거 테이블의 일반적인 패턴 검사
            removal_patterns = [
                r'제거.*표',
                r'삭제.*표', 
                r'제외.*표',
                r'필터링.*결과',
                r'제거.*목록',
                r'부적절.*요구사항',
                r'중복.*요구사항'
            ]
            
            has_removal_pattern = any(re.search(pattern, table, re.IGNORECASE) for pattern in removal_patterns)
            
            # 테이블 내용 분석 - 대부분 행이 제거 관련 내용인지 확인
            table_rows = [line for line in lines if '|' in line]
            if len(table_rows) >= 3:
                data_rows = table_rows[2:]  # 헤더와 구분선 제외
                removal_content_count = sum(1 for row in data_rows 
                                          if any(keyword.lower() in row.lower() for keyword in removal_keywords))
                
                # 50% 이상의 행이 제거 관련 내용이면 제거 테이블로 간주
                is_mostly_removal_content = removal_content_count > len(data_rows) * 0.5
            else:
                is_mostly_removal_content = False
            
            if not (has_removal_keywords or has_removal_pattern or is_mostly_removal_content):
                valid_tables.append((method, table, len(lines)))
                logger.info(f"✅ 유효한 표 발견 ({method}) - 줄 수: {len(lines)}")
            else:
                logger.warning(f"❌ 제거된 항목 표 감지되어 제외 ({method}): keywords={has_removal_keywords}, patterns={has_removal_pattern}, content={is_mostly_removal_content}")
                logger.warning(f"제외된 표 미리보기: {table[:150]}...")
    
    if valid_tables:
        # 가장 긴 표 선택 (더 완전할 가능성이 높음)
        selected_method, selected_table, line_count = max(valid_tables, key=lambda x: x[2])
        logger.info(f"최종 표 선택: {selected_method} 방식, 줄 수: {line_count}")
        logger.info(f"선택된 표 미리보기: {selected_table[:200]}...")
        return selected_table
    
    # 최후 수단: 전체 내용 반환
    logger.error("유효한 표를 찾을 수 없음, 전체 내용 반환")
    return content.strip()

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
        print(f"🔄 API: {provider} 프로바이더 모델 목록 요청")
        
        # LLMFactory를 통해 직접 클라이언트 가져오기
        client = LLMFactory.get_client_by_provider(provider)
        if client and client.is_available():
            models = client.get_available_models()
            print(f"✅ API: {provider}에서 {len(models)}개 모델 반환")
            return models
        else:
            print(f"⚠️ API: {provider} 클라이언트를 사용할 수 없습니다")
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
    Layer별 프롬프트로 실행 (모든 Layer 타입 지원)
    """
    try:
        start_time = time.time()
        logger.info(f"{request.layer_type} Layer 프롬프트 실행 시작: {request.knowledge_base}")
        
        # Layer 엔진 초기화
        engine = LayerEngine()
        
        # 요청에서 전달받은 노드들 사용
        nodes = request.nodes
        
        # 노드들이 비어있으면 기본 노드 생성 (백업)
        if not nodes:
            if request.layer_type == "generation":
                nodes = [
                    NodeConfig(
                        id=f"gen_sonar_pro_{int(time.time())}",
                        model_type="sonar-pro",
                        prompt=request.prompt,
                        layer="generation",
                        position={"x": 100, "y": 100}
                    )
                ]
            elif request.layer_type == "ensemble":
                nodes = [
                    NodeConfig(
                        id=f"ens_sonar_pro_{int(time.time())}",
                        model_type="sonar-pro",
                        prompt=request.prompt,
                        layer="ensemble",
                        position={"x": 300, "y": 200}
                    )
                ]
            elif request.layer_type == "validation":
                nodes = [
                    NodeConfig(
                        id=f"val_sonar_pro_{int(time.time())}",
                        model_type="sonar-pro",
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
                logger.info(f"🔍 Validation Layer 입력 데이터 상세 분석:")
                logger.info(f"  - layer_input 길이: {len(request.layer_input)} 문자")
                logger.info(f"  - layer_input 미리보기: {request.layer_input[:300]}...")
                logger.info(f"  - layer_input 전체 내용: {request.layer_input}")
                logger.info(f"  - 테이블 라인 수: {len([line for line in request.layer_input.split(chr(10)) if '|' in line])}")
                logger.info(f"Validation Layer 컨텍스트 확장 시작 - 기존 청크: {len(enhanced_context_chunks)}개")
                
                # Validation을 위해 더 많은 컨텍스트 검색
                vector_store = VectorStore(request.knowledge_base)
                
                # 입력 데이터에서 키워드 추출하여 추가 검색
                import re
                # 테이블에서 요구사항 텍스트 추출
                requirement_texts = re.findall(r'\|\s*[^|]+\s*\|\s*([^|]+)\s*\|', request.layer_input)
                search_terms = []
                
                logger.info(f"입력 데이터에서 {len(requirement_texts)}개 요구사항 텍스트 추출")
                
                # 요구사항에서 중요한 키워드들 추출
                for req_text in requirement_texts[:3]:  # 처음 3개 요구사항만 사용
                    if req_text.strip() and len(req_text.strip()) > 10:
                        search_term = req_text.strip()[:50]  # 처음 50자만 사용
                        search_terms.append(search_term)
                        logger.info(f"검색어 추가: {search_term}")
                
                # 각 검색어로 컨텍스트 검색
                all_chunks = set(enhanced_context_chunks)
                for i, term in enumerate(search_terms):
                    if term:
                        logger.info(f"검색어 {i+1}/{len(search_terms)} 실행: '{term[:30]}...'")
                        chunks = vector_store.search_similar_chunks(term, top_k=request.top_k)
                        chunk_count_before = len(all_chunks)
                        all_chunks.update(chunks)
                        logger.info(f"새로 추가된 청크: {len(all_chunks) - chunk_count_before}개")
                
                enhanced_context_chunks = list(all_chunks)[:20]  # 최대 20개 청크로 증가
                logger.info(f"Validation을 위한 최종 컨텍스트: {len(enhanced_context_chunks)}개 청크")
                
                # 각 청크의 상세 정보 로깅
                for i, chunk in enumerate(enhanced_context_chunks[:3]):  # 처음 3개만 로깅
                    logger.info(f"📄 청크 {i+1}: {chunk[:150]}...")
                
                # 첫 번째 청크 샘플 로깅
                if enhanced_context_chunks:
                    logger.info(f"✅ Knowledge base 활용 준비 완료: {len(enhanced_context_chunks)}개 청크")
                else:
                    logger.warning(f"⚠️ Knowledge base context가 비어있음")
                
            except Exception as e:
                logger.error(f"Validation 컨텍스트 확장 실패: {e}")
                # 실패해도 기존 컨텍스트로 진행
        
        # 각 노드 개별 실행
        outputs = []
        failed_nodes = []
        validation_steps = []
        current_input = request.layer_input
        
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
                        "model_type": node.model_type if isinstance(node.model_type, str) else node.model_type.value,
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
                    node_output = engine.execute_node(node, request.layer_input, request.context_chunks or [])
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
                
                # final_result 추출: 마지막 요구사항 표만 추출
                final_result = extract_final_requirements_table(combined_result)
            else:
                # Generation/Ensemble: 모든 출력을 결합
                combined_result = "\n\n".join([output.requirements for output in outputs])
                final_validated_result = ""
                
                # final_result 추출: 마지막 요구사항 표만 추출
                final_result = extract_final_requirements_table(combined_result)
        else:
            combined_result = "모든 노드 실행이 실패했습니다."
            final_validated_result = ""
            final_result = ""
        
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
                original_input = request.layer_input
                original_table_rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', original_input)
                original_count = len([row for row in original_table_rows if row[0].strip() and not row[0].strip().startswith('ID') and not row[0].strip().startswith('-')])
                filtered_count = len(filtered_requirements)
                
                logger.info(f"Validation 필터링 결과: 원본 {original_count}개 → 필터링 후 {filtered_count}개 (제거: {original_count - filtered_count}개)")
            
            return ValidationLayerPromptResponse(
                success=len(outputs) > 0,
                layer_type=request.layer_type,
                knowledge_base=request.knowledge_base,
                layer_input=request.layer_input,
                layer_prompt=request.prompt,
                outputs=outputs,
                combined_result=combined_result,
                final_result=final_result,
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
                layer_input=request.layer_input,
                layer_prompt=request.prompt,
                outputs=outputs,
                combined_result=combined_result,
                final_result=final_result,
                failed_nodes=failed_nodes,
                execution_time=execution_time,
                context_chunks_used=request.context_chunks or [],
                updated_input=combined_result
            )
            
    except Exception as e:
        logger.error(f"{request.layer_type} Layer 프롬프트 실행 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{request.layer_type} Layer 프롬프트 실행 실패: {str(e)}")

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
