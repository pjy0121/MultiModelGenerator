# Rerank 기능 Context-Node 이전 변경 계획

## 1. 현재 상황 분석

### 1.1 현재 Rerank 구조
- **글로벌 설정**: UI에서 전역 checkbox로 rerank 사용 여부 결정 (`globalUseRerank`)
- **서버 적용**: 전역 `rerank_enabled` bool 값이 모든 context 검색에 적용
- **기본 모델 사용**: rerank 시 서버 설정의 기본 LLM (config에서 설정된 provider/model) 사용
- **적용 범위**: LLM 노드의 knowledge_base 검색과 context-node 검색에 모두 적용

### 1.2 Context-Node 현재 상태
- `context-node`는 이미 구현되어 있음 (`NodeType.CONTEXT`)
- 벡터 DB 검색만 담당하고 LLM 설정은 없음
- `knowledge_base`와 `search_intensity` 설정 가능
- rerank는 전역 설정에 의존

## 2. 목표 변경사항

### 2.1 새로운 Rerank 구조
- **Context-Node 전용**: context-node에서만 rerank 설정 관리
- **노드별 LLM**: 각 context-node마다 rerank용 LLM Provider와 모델 선택 가능
- **선택적 비활성화**: '재정렬 사용 안 함' 옵션으로 rerank 완전 비활성화 가능
- **모델 기반 판단**: rerank 여부를 bool이 아닌 모델 존재 여부로 판단

### 2.2 UI 변경사항
- **전역 설정 제거**: Canvas의 "청크 재정렬" checkbox 제거
- **Context-Node 편집창 확장**: 
  - LLM Provider 드롭다운 추가 (기존 LLM 노드와 동일)
  - "재정렬 사용 안 함" 옵션 포함
  - 모델 드롭다운 추가 (Provider 선택 시 활성화)
  - Provider가 "재정렬 사용 안 함"일 때 모델 드롭다운 비활성화

## 3. 파일별 상세 변경 계획

### 3.1 Frontend 변경사항

#### 3.1.1 타입 정의 (`src/types/nodeWorkflow.ts`)
```typescript
// LLMProvider enum에 추가
export enum LLMProvider {
  GOOGLE = 'google',
  OPENAI = 'openai', 
  INTERNAL = 'internal',
  NO_RERANK = 'no_rerank'  // 새로 추가
}

// WorkflowNodeData interface 확장
export interface WorkflowNodeData {
  // ... 기존 필드들
  
  // context-node용 rerank 설정 (새로 추가)
  rerank_provider?: string;  // LLM Provider for rerank
  rerank_model?: string;     // LLM Model for rerank
}
```

#### 3.1.2 Store 변경 (`src/store/nodeWorkflowStore.ts`)
```typescript
// 전역 rerank 설정 제거
interface NodeWorkflowState {
  // globalUseRerank: boolean; // 제거
  // setGlobalUseRerank: (useRerank: boolean) => void; // 제거
}

// executeWorkflowStream에서 rerank_enabled 제거
const request = {
  workflow: workflowDefinition,
  // rerank_enabled: state.globalUseRerank, // 제거
};
```

#### 3.1.3 Canvas 컴포넌트 (`src/components/NodeWorkflowCanvas.tsx`)
```typescript
// 전역 rerank checkbox 제거
// globalUseRerank, setGlobalUseRerank 사용 부분 모두 제거
```

#### 3.1.4 Node 편집 Modal (`src/components/NodeEditModal.tsx`)
```typescript
// context-node 섹션에 LLM 설정 추가
{isContextNode && (
  <>
    {/* 기존 지식베이스, 검색강도 필드 */}
    
    {/* 새로 추가: Rerank LLM Provider */}
    <Form.Item label="재정렬 LLM Provider" name="rerank_provider">
      <Select placeholder="재정렬 방식 선택" onChange={handleRerankProviderChange}>
        <Option value="no_rerank">재정렬 사용 안 함</Option>
        <Option value={LLMProvider.GOOGLE}>Google AI Studio</Option>
        <Option value={LLMProvider.OPENAI}>OpenAI</Option>
        <Option value={LLMProvider.INTERNAL}>Internal LLM</Option>
      </Select>
    </Form.Item>
    
    {/* 새로 추가: Rerank Model */}
    <Form.Item label="재정렬 모델" name="rerank_model">
      <Select 
        placeholder="모델 선택"
        disabled={form.getFieldValue('rerank_provider') === 'no_rerank'}
        // ... 기존 LLM 노드와 동일한 로직
      >
      </Select>
    </Form.Item>
  </>
)}
```

### 3.2 Backend 변경사항

#### 3.2.1 모델 정의 (`src/core/models.py`)
```python
class WorkflowNode(BaseModel):
    # ... 기존 필드들
    
    # context-node용 rerank 설정 (새로 추가)
    rerank_provider: Optional[str] = Field(None, description="Rerank LLM provider")
    rerank_model: Optional[str] = Field(None, description="Rerank LLM model")

# WorkflowExecution 요청에서 rerank_enabled 제거
class WorkflowExecution(BaseModel):
    workflow: Workflow
    # rerank_enabled: bool = False  # 제거
```

#### 3.2.2 Node Executors (`src/api/node_executors.py`)
```python
# 모든 execute 메서드에서 rerank_enabled 파라미터 제거
async def execute_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
    return await self.execute_node_with_context(node, pre_outputs, [])

async def execute_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
    # rerank_enabled 파라미터 제거

async def _execute_context_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
    # context-node에서 자체적으로 rerank 설정 결정
    rerank_info = None
    if node.rerank_provider and node.rerank_provider != "no_rerank" and node.rerank_model:
        rerank_info = {
            "provider": node.rerank_provider,
            "model": node.rerank_model
        }
    
    context_results = await self.vector_store_service.search(
        kb_name=knowledge_base,
        query=input_data, 
        search_intensity=search_intensity,
        rerank_info=rerank_info  # context-node 설정 사용
    )

# LLM 노드들에서는 rerank 완전 제거 (knowledge_base 검색 없음)
async def _execute_llm_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
    # knowledge_base 검색 로직 제거 (context는 context-node에서만)
```

#### 3.2.3 API 서버 (`src/api/api_server.py`)
```python
# execute_workflow_stream에서 rerank_enabled 제거
@app.post("/execute-workflow-stream")
async def execute_workflow_stream(request: WorkflowExecution):
    workflow = request.workflow
    # rerank_enabled = request.rerank_enabled  # 제거
```

#### 3.2.4 워크플로우 실행 엔진 (`src/core/node_execution_engine.py`)
```python
# execute_workflow에서 rerank_enabled 파라미터 제거
async def execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
    # rerank_enabled 관련 로직 모두 제거
```

#### 3.2.5 벡터 스토어 서비스 (`src/services/vector_store_service.py`)
```python
# 변경사항 없음 - 이미 rerank_info 파라미터로 동작함
# 단지 호출하는 곳에서 context-node 설정을 전달받음
```

### 3.3 테스트 변경사항

#### 3.3.1 기존 테스트 업데이트
- `test_workflow_execution.py`: rerank_enabled 관련 테스트 제거
- `test_context_node.py`: context-node rerank 설정 테스트 추가
- `test_validation_chain_bug.py`: 변경사항 없음

#### 3.3.2 새 테스트 추가
```python
# test_context_node_rerank.py
class TestContextNodeRerank:
    def test_context_node_with_rerank(self):
        """Test context-node with rerank settings"""
        
    def test_context_node_without_rerank(self):  
        """Test context-node with no_rerank setting"""
        
    def test_context_node_invalid_rerank_model(self):
        """Test context-node with invalid rerank model"""
```

## 4. 마이그레이션 순서

### Phase 1: Backend 구조 변경
1. `models.py` - WorkflowNode에 rerank_provider, rerank_model 필드 추가
2. `node_executors.py` - context-node에서 자체 rerank 설정 사용하도록 수정
3. `api_server.py` - WorkflowExecution에서 rerank_enabled 제거
4. 기존 테스트 수정 및 새 테스트 추가

### Phase 2: Frontend 구조 변경  
1. `nodeWorkflowStore.ts` - globalUseRerank 관련 제거
2. `NodeWorkflowCanvas.tsx` - 전역 rerank checkbox 제거
3. `NodeEditModal.tsx` - context-node에 LLM Provider/Model 설정 추가
4. 타입 정의 업데이트

### Phase 3: 통합 테스트 및 디버깅
1. 전체 워크플로우 실행 테스트
2. Context-node rerank 동작 확인
3. UI/UX 검증
4. 기존 기능 정상 동작 확인

## 5. 주의사항

### 5.1 하위 호환성
- 기존 워크플로우 JSON에 rerank_provider/rerank_model이 없는 경우 기본값으로 "no_rerank" 처리
- 기존 전역 rerank 설정은 완전히 제거되므로 사용자 안내 필요

### 5.2 성능 고려사항  
- Context-node별로 다른 LLM을 사용할 수 있어 성능 영향 최소화
- Rerank를 사용하지 않는 context-node는 기존과 동일한 성능

### 5.3 에러 처리
- 잘못된 rerank_provider/model 설정 시 graceful fallback
- Context-node에 rerank 설정이 있지만 LLM 접근 실패 시 일반 검색으로 fallback

## 6. 예상 개발 시간
- Backend 변경: 4-6시간
- Frontend 변경: 3-4시간  
- 테스트 작성 및 디버깅: 2-3시간
- **총 예상 시간: 9-13시간**

이 계획에 따라 단계별로 진행하면 안전하게 대규모 변경사항을 적용할 수 있습니다.