# 워크플로우 구성 및 실행 방식 정의

## 클라이언트 사이드

### 연결 조건

아래 조건들을 만족하는 노드들 간에만 연결이 가능하며, 아래 조건들을 만족하지 않는 경우 워크플로우를 실행할 수 없다.
워크플로우 실행 시 사용자에게 만족되지 않는 부분을 알려줘야 한다

1. 어떤 노드로 들어오는 방향으로 연결된 노드를 pre-node, 어떤 노드로부터 나가는 방향으로 연결된 노드를 post-node라고 한다
2. 모든 노드에는 최소 하나의 pre-node와 post-node가 있어야 한다. 단, input-node에는 pre-node가 존재할 수 없고 output-node에는 post-node가 존재할 수 없다
3. 여러 개의 pre-node와 연결될 수 있는 노드는 ensemble-node뿐이다
4. 여러 개의 post-node와 연결될 수 있는 노드는 input-node뿐이다
5. 최초 워크플로우에 input-node, output-node가 하나씩 연결된 채로 존재해야 한다
6. 워크플로우 실행 중일 때 노드 간 연결 정보를 변경할 수 없다

### 노드의 종류와 특성

노드의 타입엔 input-node, output-node, generation-node, ensemble-node, validation-node가 있다

1. input-node
   - 다음 노드의 input 데이터로 전달할 plain-text(content)를 갖고 있는 노드
   - pre-node를 연결할 수 없다
   - post-node를 여러 개 연결할 수 있다
   - 워크플로우 상에 최소 1개는 존재해야 하므로 마지막 1개는 삭제 불가능하다
   - ReactFlow의 TextNode 컴포넌트를 사용하며, 수정 창에서 content 수정이 가능하다
   - 속성 : content (string)

2. generation-node
   - LLM 모델로 프롬프트를 보내 초기 답변을 생성하는 노드
   - pre-node로 input-node만 올 수 있다
   - post-node로 ensemble-node, validation-node, output-node가 올 수 있다
   - ReactFlow의 ModelNode 컴포넌트를 사용하며, 수정 창에서 드롭다운을 통해 모델을 선택할 수 있다
   - 속성 : model_type (string), llm_provider (string)

3. ensemble-node
   - 연결된 pre-node들의 output을 이어 붙인 뒤 하나로 정리해주는 노드
   - pre-node를 여러 개 연결할 수 있다
   - pre-node로 output-node를 제외한 모든 노드들이 올 수 있다
   - post-node로 input-node를 제외한 모든 노드들이 올 수 있다
   - ReactFlow의 ModelNode 컴포넌트를 사용하며, 수정 창에서 드롭다운을 통해 모델을 선택할 수 있다
   - 속성 : model_type (string), llm_provider (string)

4. validation-node
   - input 데이터에 대한 검증 작업을 수행하는 노드
   - pre-node로 input-node, generation-node, ensemble-node, validation-node가 올 수 있다
   - post-node로 validation-node, ensemble-node, output-node가 올 수 있다
   - ReactFlow의 ModelNode 컴포넌트를 사용하며, 수정 창에서 드롭다운을 통해 모델을 선택할 수 있다
   - 속성 : model_type (string), llm_provider (string)

5. output-node
   - 이전 노드의 결과를 받아 출력하는 노드
   - post-node를 연결할 수 없다
   - 워크플로우 상에 단 하나만 존재할 수 있으며 제거할 수 없다
   - ReactFlow의 TextNode 컴포넌트를 사용하며, 수정 창에서 content 수정이 가능하다
   - 속성 : content (string)

### 워크플로우 실행

- 워크플로우 실행 버튼 클릭 시 서버측의 워크플로우 실행 API를 호출한다
- 구성되어 있는 워크플로우 구성 정보와 노드 종류별 프롬프트 내용, 선택되어 있는 Knowledge Base의 이름, 검색 강도가 Request 시 함께 전달된다
- 워크플로우 실행 중간중간에 서버측에서 응답하는 내용(description 또는 error)을 실행 결과 창에 출력한다
- 응답을 한 노드들은 ReactFlow의 canvas 상에서 실행 완료되었다는 표시를 해준다

## 서버 사이드

### 워크플로우 실행 API

워크플로우 실행 시 다음 과정을 수행한다

1. 워크플로우 상의 모든 input-node들을 찾아 실행 대기 목록에 추가한다
2. 목록에 더 이상 실행할 노드가 없을 때까지 다음을 반복한다
    1-2-1. 목록에서 pre-node가 없거나 모든 pre-node들의 output이 존재하는 노드들(즉, pre-node들의 실행이 모두 완료된 노드들)만 찾는다
    1-2-2. 찾은 노드들을 병렬로 실행한다
    1-2-3. 실행이 완료될 때까지 기다린다
    1-2-4. 실행이 끝난 노드의 경우, post-node들을 목록에 등록한 후 목록에서 제거되어야 한다

### ResultParser 실행

1. 항상 다음과 같은 형태의 json 포맷에서 "description"과 "output"을 parsing한다

```json
{
    "description": [UI 상에 print될 내용],
    "output": [다음 노드로 전달될 내용]
}
```

2. parsing 실패 시
   - 에러 내용을 client에 전달한다

3. parsing 성공 시
   - "description"의 내용을 client에 전달한다
   - "output"의 내용을 return한다

### 노드 실행

1. input-node, output-node 실행

1-1. 노드 실행 시 input은 다음과 같다

```json
{
    "input": [pre-node의 output 속성 (string)]
}
```

1-2. input값이 null이 아닐 경우 content 속성을 업데이트한다

1-3. 노드의 content 속성을 포함해 json 데이터를 만든다

```json
{
    "description": [content 속성 (string)],
    "output": [content 속성 (string)]
}

```

1-4. json 데이터를 인자로 ResultParser를 실행한다

1-5. ResultParser의 return값을 output 속성에 저장한다

2. 나머지 노드 실행

2-1. 노드 실행 시 input은 다음과 같다

```json
{
    "inputs": [pre-node들의 output 속성 배열 (string array)],
    "knowledge_base": [검색할 지식 베이스 이름 (string)],
    "intensity": [지식 베이스 내 검색 강도],
    "prompt": [LLM 모델에 전달할 프롬프트 (string)],
    "output_format": [프롬프트에 포함될 output 형식]
}
```

2-2. input으로 들어온 inputs의 원소들을 concatenation해서 input_data를 만든다

2-3. input prompt에서 '{input_data}'라는 문자열을 찾아 input_data 내용으로 replace한다

2-4. knowledge_base가 주어졌을 경우
   2-4-1. intensity값에 따라 검색 시의 top_k를 결정한다
   2-4-2. VectorDB에서 해당 knowledge_base를 찾고, input_data를 검색한 결과를 얻는다 2-4-3. input prompt에서 '{context}'라는 문자열을 찾아 knowledge_base에서 얻은 검색 결과로 replace한다

2-5. '{output_format}'이라는 문자열을 찾아 input으로 들어온 output_format 내용으로 replace한다
2-6. LLM API를 호출하여 prompt를 보낸다
2-7. LLM API의 호출 결과를 인자로 ResultParser를 실행한다
2-8. ResultParser의 return값을 output 속성에 저장한다
