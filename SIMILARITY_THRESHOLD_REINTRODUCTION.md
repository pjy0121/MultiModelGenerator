# Similarity Threshold Reintroduction

## Overview

**Problem**: Using only Top-K returns K results even when searching for irrelevant content, reducing quality
**Solution**: Reintroduce Similarity Threshold to filter out irrelevant results

## Implementation Details

### 1. Config Update (config.py)

```python
SEARCH_INTENSITY_CONFIG = {
    "exact": {
        "init": 10,
        "final": 5,
        "similarity_threshold": 0.7  # 70%+ similarity
    },
    "standard": {
        "init": 20,
        "final": 12,
        "similarity_threshold": 0.5  # 50%+ similarity
    },
    "comprehensive": {
        "init": 40,
        "final": 25,
        "similarity_threshold": 0.3  # 30%+ similarity
    }
}
```

### 2. Threshold Application Criteria

| Search Intensity | Threshold | Meaning | Use Scenario |
|------------------|-----------|---------|--------------|
| **EXACT** | 0.7 (70%) | Very high relevance required | Exact command IDs, specific specs |
| **STANDARD** | 0.5 (50%) | Clear relevance | General features, standard procedures |
| **COMPREHENSIVE** | 0.3 (30%) | Wide range allowed | Overall mechanisms, exploratory research |

### 3. Search Pipeline

```
Query → ChromaDB search (top_k=init)
      ↓
Similarity Threshold filtering (only pass threshold or above)
      ↓
Reranker (optional, LLM-based reordering)
      ↓
Final results (max final count)
```

**Features**:
- ✅ Automatic removal of irrelevant results
- ✅ Empty result prevention (minimum 1 result returned)
- ✅ Adjustable via Config anytime

### 4. Code Changes

**vector_store.py**:
```python
async def _search_initial_chunks(
    self,
    query: str,
    top_k: int,
    similarity_threshold: float = 0.0
) -> List[str]:
    # ChromaDB cosine distance → similarity conversion
    # similarity = 1 - distance

    # Threshold filtering
    filtered_chunks = [
        chunk for chunk, distance in zip(chunks, distances)
        if (1 - distance) >= similarity_threshold
    ]

    # Empty result prevention (minimum 1)
    if not filtered_chunks and chunks:
        return [chunks[0]]

    return filtered_chunks
```

**models.py**:
```python
def get_search_params(cls, intensity: str) -> Dict[str, any]:
    """
    Return value: {
        "init": int,                    # Initial search count
        "final": int,                   # Final count
        "similarity_threshold": float   # Minimum similarity (0.0~1.0)
    }
    """
```

### 5. Frontend Update

**constants.ts**:
```typescript
export const SEARCH_INTENSITY_CONFIG = {
  exact: {
    init: 10,
    final: 5,
    similarity_threshold: 0.7,
    label: 'Exact Search'
  },
  // ...
};
```

## Test Updates

**test_search_intensity.py**:
- ❌ Removed: `test_no_threshold_in_params`
- ✅ Added: `test_similarity_threshold_in_params`

```python
def test_similarity_threshold_in_params(self):
    """Verify similarity_threshold value exists and range"""
    exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)

    # Existence check
    assert "similarity_threshold" in exact

    # Range check (0.0~1.0)
    assert 0.0 <= exact["similarity_threshold"] <= 1.0

    # Order check (EXACT > STANDARD > COMPREHENSIVE)
    assert exact["similarity_threshold"] > standard["similarity_threshold"]
```

**Result**: ✅ 10/10 passed

## Expected Effects

### Before (Top-K only)
```
Query: "Search for irrelevant content"
→ ChromaDB Top-20 search
→ 20 results returned (including irrelevant content with 0.1~0.3 similarity)
```

### After (Top-K + Threshold)
```
Query: "Search for irrelevant content"
→ ChromaDB Top-20 search
→ Similarity ≥ 0.5 filtering
→ 2 results returned (only 0.52, 0.51 pass) or minimum 1
```

## Tuning Guide

**Threshold value adjustment (config.py)**:

```python
# More strict (reduce false positives)
"exact": {"similarity_threshold": 0.8}  # 80%+ similarity only

# More lenient (increase recall)
"comprehensive": {"similarity_threshold": 0.2}  # 20%+ similarity
```

**Recommended ranges**:
- EXACT: 0.6~0.8 (precision-focused)
- STANDARD: 0.4~0.6 (balanced)
- COMPREHENSIVE: 0.2~0.4 (recall-focused)

## Documentation Updates

1. ✅ `config.py`: SEARCH_INTENSITY_CONFIG updated
2. ✅ `vector_store.py`: Threshold filtering logic added
3. ✅ `models.py`: Docstring updated
4. ✅ `constants.ts`: Frontend config synchronized
5. ✅ `copilot-instructions.md`: Architecture document updated
6. ✅ `test_search_intensity.py`: Test cases updated

## Post-Deployment Verification

1. Verify empty or minimal results when searching for irrelevant queries
2. Verify sufficient results when searching for relevant queries
3. Check threshold filtering info in logs:
   ```
   🔍 Similarity range of 20 searched chunks: 0.123 ~ 0.678
   📚 Found 3 relevant chunks after threshold 0.50 filtering (out of 20 total)
   ```

## Conclusion

✅ **Problem solved**: Irrelevant results automatically filtered
✅ **Flexibility**: Threshold adjustable via Config anytime
✅ **Stability**: Empty result prevention logic guarantees minimum 1
✅ **Verification complete**: All tests passed
