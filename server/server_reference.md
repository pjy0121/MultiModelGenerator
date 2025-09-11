## 프로젝트 컨셉
Vector DB에 저장된 지식 베이스에서 주어진 키워드와 관련된 요구사항 목록을 추출하기 기능을 가진 Fast API 기반 Back-end 서버. 여러 개의 LLM 모델들에 질의 후 답변들을 취합한 후 다시 검증 목적으로 질의하는 것을 반복하는 Multi model validation 방식으로 동작.

다음과 같은 3개의 Layer를 거침
- Layer 1. Generation Layer : LLM 모델들에 프롬프트를 보내서 답변을 생성하는 Layer
- Layer 2. Ensemble Layer : 모델들의 답변을 취합하여 하나로 만드는 Layer
- Layer 3. Validation Layer : 취합된 답변이 주어진 Spec에 위배되지는 않는지 검증하는 Layer


## 제공 기능
- 외부 LLM 쿼리 기능
- 현재 구축된 지식 베이스 목록 제공 기능
- 요구사항 목록 생성 기능

## 기능별 상세 설명
### 1. 외부 LLM 쿼리 기능
- Perplextity AI API를 이용하여 사용할 수 있는 LLM 모델의 종류를 Rest API로 제공할 수 있어야 함
- Perplexity AI API를 이용하여 지정된 LLM 모델에 대해 프롬프트를 쿼리할 수 있어야 함

### 2. 현재 구축된 지식 베이스 목록 제공 기능
- 서버 내 지식 베이스 경로에 구축되어 있는 지식 베이스들의 목록 확인 및 Rest API를 통한 제공이 가능해야 함

### 3. 요구사항 목록 생성 기능
- 지식 베이스에 있는 내용을 기반으로 주어진 키워드에 대한 요구사항 목록을 생성해야 함
- 주어진 Generation Layer Node들의 Configuration을 바탕으로 1개 이상의 요구사항 쿼리를 한 후 나온 결과들을 종합하여 Ensemble Layer Node로 전달해야 함
- Ensemble Layer Node에서 통합된 결과를 주어진 Validation Layer Node의 첫 번째 노드에게 전달한 후 결과를 다음 노드로 순차 전달한 뒤 최종 결과를 반환해야 함
