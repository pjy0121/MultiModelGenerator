# 웹페이지 미디어 가이드

이 문서는 `docs/index.html`에 삽입할 스크린샷과 동영상 목록입니다.

## 폴더 구조
```
docs/
├── index.html
├── assets/
│   ├── videos/
│   │   ├── demo-main.mp4          # 메인 데모 (전체 과정)
│   │   ├── demo-node-connect.mp4  # 노드 추가 및 연결
│   │   ├── demo-execution.mp4     # 워크플로우 실행
│   │   ├── demo-requirements.mp4  # 요구사항 추출 예시
│   │   └── demo-multi-model.mp4   # 다중 모델 비교 예시
│   └── screenshots/
│       ├── concept-diagram.png    # 워크플로우 컨셉 다이어그램
│       ├── canvas.png             # 워크플로우 캔버스
│       ├── node-config.png        # 노드 설정 패널
│       ├── kb-manager.png         # 지식 베이스 관리
│       ├── kb-create-modal.png    # KB 생성 모달
│       ├── kb-created.png         # KB 생성 완료
│       ├── node-generation.png    # 생성 노드 설정
│       ├── node-context.png       # 컨텍스트 노드 설정
│       ├── node-validation.png    # 검증 노드 설정
│       ├── result-panel.png       # 결과 확인 패널
│       └── save-export.png        # 저장 및 내보내기
```

---

## 필요한 미디어 목록

### 동영상 (5개)

| 파일명 | 위치 | 설명 | 권장 길이 |
|--------|------|------|-----------|
| `demo-main.mp4` | 히어로 섹션 | 워크플로우 구성부터 실행까지 전체 과정 | 1-2분 |
| `demo-node-connect.mp4` | 사용법 Step 2 | 노드 추가하고 드래그로 연결하는 과정 | 20-30초 |
| `demo-execution.mp4` | 기능 - 실시간 실행 | 실행 버튼 클릭 후 스트리밍 결과 표시 | 30-60초 |
| `demo-requirements.mp4` | 활용 예시 1 | 기술 문서에서 요구사항 추출 전체 과정 | 1-2분 |
| `demo-multi-model.mp4` | 활용 예시 2 | 여러 모델 비교 앙상블 과정 | 1-2분 |

### 스크린샷 (11개)

| 파일명 | 위치 | 설명 |
|--------|------|------|
| `concept-diagram.png` | 핵심 컨셉 | 노드 흐름 다이어그램 (Input→Context→Generation→Validation→Output) |
| `canvas.png` | 기능 - 워크플로우 캔버스 | 여러 노드가 연결된 캔버스 전체 화면 |
| `node-config.png` | 기능 - 노드 설정 | 생성 노드의 설정 패널 (모델, 프롬프트 등) |
| `kb-manager.png` | 기능 - 지식 베이스 | 좌측 KB 목록 패널 (폴더 구조 포함) |
| `kb-create-modal.png` | 사용법 Step 1 | KB 생성 모달 (파일 업로드 또는 텍스트 입력) |
| `kb-created.png` | 사용법 Step 1 | KB 생성 완료 후 목록에 표시된 모습 |
| `node-generation.png` | 사용법 Step 3 | 생성 노드 설정 화면 |
| `node-context.png` | 사용법 Step 3 | 컨텍스트 노드 설정 (KB 선택, 검색 강도) |
| `node-validation.png` | 사용법 Step 3 | 검증 노드 설정 화면 |
| `result-panel.png` | 사용법 Step 5 | 실행 결과가 표시된 우측 패널 |
| `save-export.png` | 사용법 Step 5 | 저장/내보내기 버튼 및 JSON 내보내기 |

---

## 삽입 방법

각 플레이스홀더에 주석으로 `<!-- TODO: ... -->`가 표시되어 있습니다.

### 동영상 삽입
```html
<!-- 변경 전 -->
<div class="video-placeholder ...">
    <!-- TODO: 메인 데모 동영상 삽입 -->
    <!-- <video src="assets/videos/demo-main.mp4" controls class="w-full h-full rounded-2xl"></video> -->
    <div class="text-center text-white/70 z-10">...</div>
</div>

<!-- 변경 후 -->
<div class="rounded-2xl overflow-hidden shadow-2xl">
    <video src="assets/videos/demo-main.mp4" controls class="w-full h-full"></video>
</div>
```

### 스크린샷 삽입
```html
<!-- 변경 전 -->
<div class="screenshot-placeholder rounded-xl aspect-video flex items-center justify-center">
    <!-- TODO: 워크플로우 캔버스 스크린샷 삽입 -->
    <!-- <img src="assets/screenshots/canvas.png" alt="워크플로우 캔버스"> -->
    <p class="text-gray-500">워크플로우 캔버스 스크린샷</p>
</div>

<!-- 변경 후 -->
<div class="rounded-xl overflow-hidden shadow-lg">
    <img src="assets/screenshots/canvas.png" alt="워크플로우 캔버스" class="w-full h-auto">
</div>
```

---

## 권장 사항

### 동영상
- 해상도: 1920x1080 또는 1280x720
- 형식: MP4 (H.264)
- 파일 크기: 각 10MB 이하 권장
- 마우스 커서 강조 효과 사용 권장

### 스크린샷
- 해상도: 최소 1280px 너비
- 형식: PNG (투명 배경 불필요)
- 브라우저 UI 제외하고 앱 화면만 캡처
- 민감한 정보(API 키 등) 마스킹

### GIF 대안
동영상 대신 GIF 사용 가능 (파일 크기가 더 작을 경우):
```html
<img src="assets/videos/demo-node-connect.gif" alt="노드 연결" class="w-full h-auto">
```
