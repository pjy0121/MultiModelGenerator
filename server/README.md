# MultiModelGenerator Server

Vector DB 기반 Multi-Model Validation을 통한 요구사항 추출 서버

## 프로젝트 구조

```text
server/
├── main.py                 # 서버 실행 진입점
├── admin_tool.py          # 관리자 도구 CLI
├── requirements.txt       # Python 의존성
├── .env                   # 환경 변수 (API 키 등)
├── .gitignore            # Git 무시 파일
├── admin_reference.md    # 관리자 도구 참조 문서
├── server_reference.md   # 서버 참조 문서
├── knowledge_bases/      # Vector DB 저장소 (Git에서 제외)
└── src/                  # 소스 코드
    ├── api/              # FastAPI 엔드포인트
    │   └── api_server.py
    ├── core/             # 핵심 모듈
    │   ├── config.py     # 설정 관리
    │   ├── models.py     # 데이터 모델
    │   ├── prompts.py    # 프롬프트 템플릿
    │   └── workflow_engine.py  # 워크플로우 엔진
    ├── services/         # 외부 서비스 연동
    │   ├── document_processor.py  # 문서 처리
    │   ├── perplexity_client.py   # Perplexity AI 클라이언트
    │   └── vector_store.py        # Vector DB 관리
    └── admin/            # 관리자 도구
        └── admin.py      # 지식 베이스 관리
```

## 주요 기능

### 1. Multi-Layer Architecture

- **Generation Layer**: 여러 LLM 모델에서 답변 생성
- **Ensemble Layer**: 모델 답변들을 통합
- **Validation Layer**: 통합된 답변을 검증

### 2. 지식 베이스 관리

- PDF 문서에서 Vector DB 구축
- 지식 베이스 목록 조회, 상태 확인
- 지식 베이스 추가/삭제

### 3. REST API

- 요구사항 추출 API
- 지식 베이스 관리 API
- LLM 모델 쿼리 API

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일에 API 키 설정:

```env
PERPLEXITY_API_KEY=your_api_key_here
```

### 3. 서버 실행

```bash
python main.py
```

### 4. 관리자 도구 사용

```bash
# 지식 베이스 목록 조회
python admin_tool.py list

# 지식 베이스 구축
python admin_tool.py build <kb_name> <pdf_path>

# 지식 베이스 삭제
python admin_tool.py delete <kb_name>

# 지식 베이스 상태 확인
python admin_tool.py status <kb_name>
```

## API 문서

서버 실행 후 다음 URL에서 API 문서 확인:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## 개발 노트

- 모든 소스 코드는 `src/` 디렉토리 하위에 기능별로 분류
- 상대 import를 사용하여 모듈 간 의존성 관리
- `__pycache__`와 `knowledge_bases/`는 Git에서 제외
