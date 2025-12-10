# Similarity Threshold 재도입

## 📋 개요

**문제**: Top-K만으로는 무관한 내용 검색 시에도 K개의 결과가 항상 반환되어 품질 저하
**해결**: Similarity Threshold를 재도입하여 무관한 결과 필터링

## ✅ 구현 내용

### 1. Config 업데이트 (config.py)

```python
SEARCH_INTENSITY_CONFIG = {
    "exact": {
        "init": 10,
        "final": 5,
        "similarity_threshold": 0.7  # 70%+ 유사도
    },
    "standard": {
        "init": 20,
        "final": 12,
        "similarity_threshold": 0.5  # 50%+ 유사도
    },
    "comprehensive": {
        "init": 40,
        "final": 25,
        "similarity_threshold": 0.3  # 30%+ 유사도
    }
}
```

### 2. Threshold 적용 기준

| 검색 강도 | Threshold | 의미 | 사용 시나리오 |
|----------|-----------|------|--------------|
| **EXACT** | 0.7 (70%) | 매우 높은 관련성 필수 | 정확한 명령어 ID, 특정 사양 |
| **STANDARD** | 0.5 (50%) | 명확한 관련성 | 일반적인 기능, 표준 절차 |
| **COMPREHENSIVE** | 0.3 (30%) | 넓은 범위 허용 | 전반적인 메커니즘, 탐색적 조사 |

### 3. 검색 파이프라인

```
Query → ChromaDB 검색 (top_k=init)
      ↓
Similarity Threshold 필터링 (threshold 이상만 통과)
      ↓
Reranker (선택 사항, LLM 기반 재정렬)
      ↓
최종 결과 (최대 final개)
```

**특징**:
- ✅ 무관한 결과 자동 제거
- ✅ 빈 결과 방지 (최소 1개는 반환)
- ✅ Config로 언제든 조정 가능

### 4. 코드 변경 사항

**vector_store.py**:
```python
async def _search_initial_chunks(
    self, 
    query: str, 
    top_k: int, 
    similarity_threshold: float = 0.0
) -> List[str]:
    # ChromaDB cosine distance → similarity 변환
    # similarity = 1 - distance
    
    # Threshold 필터링
    filtered_chunks = [
        chunk for chunk, distance in zip(chunks, distances)
        if (1 - distance) >= similarity_threshold
    ]
    
    # 빈 결과 방지 (최소 1개)
    if not filtered_chunks and chunks:
        return [chunks[0]]
    
    return filtered_chunks
```

**models.py**:
```python
def get_search_params(cls, intensity: str) -> Dict[str, any]:
    """
    반환값: {
        "init": int,                    # 초기 검색 개수
        "final": int,                   # 최종 개수
        "similarity_threshold": float   # 최소 유사도 (0.0~1.0)
    }
    """
```

### 5. Frontend 업데이트

**constants.ts**:
```typescript
export const SEARCH_INTENSITY_CONFIG = {
  exact: {
    init: 10,
    final: 5,
    similarity_threshold: 0.7,
    label: '정확 검색'
  },
  // ...
};
```

## 🧪 테스트 업데이트

**test_search_intensity.py**:
- ❌ 제거: `test_no_threshold_in_params`
- ✅ 추가: `test_similarity_threshold_in_params`

```python
def test_similarity_threshold_in_params(self):
    """similarity_threshold 값 존재 및 범위 확인"""
    exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
    
    # 존재 확인
    assert "similarity_threshold" in exact
    
    # 범위 확인 (0.0~1.0)
    assert 0.0 <= exact["similarity_threshold"] <= 1.0
    
    # 순서 확인 (EXACT > STANDARD > COMPREHENSIVE)
    assert exact["similarity_threshold"] > standard["similarity_threshold"]
```

**결과**: ✅ 10/10 passed

## 📊 예상 효과

### Before (Top-K만 사용)
```
Query: "무관한 내용 검색"
→ ChromaDB Top-20 검색
→ 20개 결과 반환 (유사도 0.1~0.3의 무관한 내용 포함)
```

### After (Top-K + Threshold)
```
Query: "무관한 내용 검색"
→ ChromaDB Top-20 검색
→ Similarity ≥ 0.5 필터링
→ 2개 결과 반환 (유사도 0.52, 0.51만 통과) 또는 최소 1개
```

## 🎯 조정 가이드

**Threshold 값 조정 (config.py)**:

```python
# 더 엄격하게 (거짓 양성 감소)
"exact": {"similarity_threshold": 0.8}  # 80%+ 유사도만

# 더 관대하게 (재현율 증가)
"comprehensive": {"similarity_threshold": 0.2}  # 20%+ 유사도
```

**권장 범위**:
- EXACT: 0.6~0.8 (정밀도 중시)
- STANDARD: 0.4~0.6 (균형)
- COMPREHENSIVE: 0.2~0.4 (재현율 중시)

## 📝 문서 업데이트

1. ✅ `config.py`: SEARCH_INTENSITY_CONFIG 업데이트
2. ✅ `vector_store.py`: Threshold 필터링 로직 추가
3. ✅ `models.py`: Docstring 업데이트
4. ✅ `constants.ts`: Frontend config 동기화
5. ✅ `copilot-instructions.md`: 아키텍처 문서 업데이트
6. ✅ `test_search_intensity.py`: 테스트 케이스 업데이트

## 🚀 배포 후 확인 사항

1. 무관한 쿼리 검색 시 빈 결과 또는 최소 결과만 반환되는지 확인
2. 관련 쿼리 검색 시 충분한 결과가 반환되는지 확인
3. 로그에서 threshold 필터링 정보 확인:
   ```
   🔍 검색된 20개 청크의 유사도 범위: 0.123 ~ 0.678
   📚 Threshold 0.50 필터링 후 3개 관련 청크 발견 (전체 20개 중)
   ```

## 결론

✅ **문제 해결**: 무관한 결과가 자동으로 필터링됨  
✅ **유연성**: Config로 threshold 언제든 조정 가능  
✅ **안정성**: 빈 결과 방지 로직으로 최소 1개 보장  
✅ **검증 완료**: 모든 테스트 통과
