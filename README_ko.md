# MultiModelGenerator

<div align="center">

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)
![React](https://img.shields.io/badge/react-18-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)

**여러 LLM 모델을 오케스트레이션하는 노드 기반 시각적 AI 워크플로우 빌더**

[기능](#주요-기능) | [설치](#설치) | [사용법](#사용법) | [기여하기](#기여하기)

[English README](README.md)

</div>

---

## 개요

MultiModelGenerator는 기술 문서에서 요구사항을 추출, 검증, 종합하기 위해 여러 LLM 모델을 오케스트레이션하는 강력한 시각적 워크플로우 빌더입니다. 노드 기반 그래프 인터페이스를 통해 여러 AI 프로바이더를 활용하고 RAG(Retrieval-Augmented Generation)를 위한 지식 베이스와 통합하는 복잡한 AI 파이프라인을 설계할 수 있습니다.

## 누구를 위한 도구인가요?

| 사용자 | 혜택 |
|--------|------|
| **시스템 분석가 & PM** | 기술 문서에서 요구사항 자동 추출 - 수백 페이지를 몇 분 만에 분석 |
| **AI/ML 연구자** | LLM 모델(GPT-4, Gemini 등) 비교 및 프롬프트 실험 |
| **기술 문서 담당자** | RAG 기반 맥락 인식 Q&A로 문서 요약 자동화 |
| **개발자 & 엔지니어** | 코드 없이 복잡한 AI 파이프라인 구축, JSON 내보내기로 자동화 통합 |

## 주요 기능

### 시각적 워크플로우 빌더
- **노드 기반 그래프 인터페이스**: 직관적인 드래그 앤 드롭으로 AI 파이프라인 설계
- **실시간 스트리밍**: LLM 응답을 실시간으로 확인
- **병렬 실행**: 독립 노드가 동시에 실행되어 최적의 성능 제공
- **워크플로우 관리**: 저장, 복원, 내보내기(JSON), 가져오기

### 다중 모델 지원
| 프로바이더 | 모델 |
|------------|------|
| OpenAI | GPT-4, GPT-4 Turbo, GPT-3.5 Turbo |
| Google | Gemini Pro, Gemini Ultra |
| Internal | 커스텀/엔터프라이즈 LLM 엔드포인트 |

### 지식 베이스 (RAG) 통합
- **벡터 스토어**: ChromaDB 기반 문서 임베딩 및 검색
- **BGE-M3**: 100개 이상 언어 지원 다국어 임베딩 모델
- **지능형 리랭킹**: BAAI/bge-reranker-v2-m3로 관련성 향상
- **폴더 구조**: 비밀번호 보호가 가능한 계층 구조

### 노드 타입

| 노드 | 아이콘 | 설명 |
|------|--------|------|
| 입력 | 📥 | 텍스트 데이터 입력 지점 |
| 생성 | 🤖 | LLM 기반 콘텐츠 생성 |
| 앙상블 | 🔀 | 여러 노드의 출력 결합 |
| 검증 | ✅ | 지식 베이스 기반 결과 검증 |
| 컨텍스트 | 🔍 | RAG 기반 컨텍스트 검색 |
| 출력 | 📤 | 최종 결과 표시 |

## 설치

### 사전 요구사항
- Python 3.9+
- Node.js 18+
- npm 또는 yarn

### 빠른 시작

```bash
# 저장소 클론
git clone https://github.com/YOUR_USERNAME/MultiModelGenerator.git
cd MultiModelGenerator

# 백엔드 설정
pip install -r requirements.txt
cp .env.example .env  # API 키 설정

# 백엔드 시작
cd server && python main.py

# 프론트엔드 설정 (새 터미널)
cd client/react-app
npm install
npm run dev
```

### 환경 변수

루트 디렉토리에 `.env` 파일 생성:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
INTERNAL_API_KEY=your_internal_api_key        # 선택
INTERNAL_API_ENDPOINT=your_internal_endpoint  # 선택
```

## 사용법

### 워크플로우 생성

1. **노드 추가**: 노드 버튼 클릭하여 캔버스에 추가
2. **노드 연결**: 핸들을 드래그하여 연결 생성
3. **설정**: 노드 클릭하여 LLM 프로바이더, 모델, 프롬프트 설정
4. **실행**: "워크플로우 실행" 클릭하여 스트리밍 결과 확인

### 프롬프트 변수

프롬프트에서 다음 플레이스홀더 사용:
- `{input_data}` - 연결된 상위 노드의 입력
- `{context}` - 지식 베이스에서 검색된 컨텍스트 (Context 노드)

### 지식 베이스

```
PDF/TXT 업로드 → BGE-M3로 자동 임베딩 → ChromaDB에 저장 → Context 노드로 쿼리
```

## 아키텍처

```
MultiModelGenerator/
├── client/                    # 프론트엔드 (React + TypeScript)
│   └── react-app/
│       ├── src/
│       │   ├── components/    # React 컴포넌트
│       │   ├── store/         # Zustand 상태 관리
│       │   ├── services/      # API 통신
│       │   └── types/         # TypeScript 정의
│       └── package.json
├── server/                    # 백엔드 (Python + FastAPI)
│   ├── src/
│   │   ├── api/              # FastAPI 엔드포인트
│   │   ├── models/           # Pydantic 모델
│   │   ├── services/         # LLM 클라이언트, 벡터 스토어
│   │   └── workflow/         # 실행 엔진
│   └── main.py
├── tests/                     # Pytest 테스트 스위트
└── docs/                      # 문서
```

## 기술 스택

<table>
<tr>
<td valign="top" width="50%">

### 프론트엔드
- React 18 + TypeScript
- React Flow (그래프 에디터)
- Ant Design (UI)
- Zustand (상태 관리)
- Vite (빌드)

</td>
<td valign="top" width="50%">

### 백엔드
- FastAPI (비동기 REST)
- ChromaDB (벡터 스토어)
- BGE-M3 (임베딩)
- Pydantic (검증)

</td>
</tr>
</table>

## 테스트

```bash
# 테스트 의존성 설치
pip install -r requirements-test.txt

# 테스트 실행
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=server --cov-report=html
```

## 기여하기

기여를 환영합니다! 자세한 내용은 [기여 가이드](CONTRIBUTING.md)를 참조하세요.

### 기여자를 위한 빠른 시작

1. 저장소 포크
2. 기능 브랜치 생성: `git checkout -b feature/amazing-feature`
3. 변경사항 작성
4. 테스트 실행: `pytest tests/ -v`
5. 커밋: `git commit -m 'feat: add amazing feature'`
6. 푸시: `git push origin feature/amazing-feature`
7. Pull Request 생성

기여하기 전에 [행동 강령](CODE_OF_CONDUCT.md)을 읽어주세요.

## 보안

보안 이슈는 [보안 정책](SECURITY.md)을 참조하세요.

**보안 취약점은 공개 GitHub 이슈를 통해 보고하지 마세요.**

## 라이선스

이 프로젝트는 Apache License 2.0으로 라이선스됩니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 감사의 글

- [React Flow](https://reactflow.dev/) - 그래프 에디터
- [ChromaDB](https://www.trychroma.com/) - 벡터 스토리지
- [BGE-M3](https://huggingface.co/BAAI/bge-m3) - 다국어 임베딩
- 모든 [기여자분들](https://github.com/YOUR_USERNAME/MultiModelGenerator/graphs/contributors)

---

<div align="center">

**[문서](docs/)** | **[버그 리포트](.github/ISSUE_TEMPLATE/bug_report.md)** | **[기능 요청](.github/ISSUE_TEMPLATE/feature_request.md)**

MultiModelGenerator 팀이 정성을 다해 만들었습니다

</div>
