## 프로젝트 컨셉
주어진 키워드와 관련된 요구사항 목록을 추출하기 위한 React 기반 Web Application. 사용자가 여러 LLM Model들을 활용한 워크플로우를 구성할 수 있는 기능을 제공함. 이를 위해 React Flow를 사용하며, 모던 UI 프레임워크를 사용해서 구현되어야 함

## 제공 기능
App GUI에서 다음과 같은 기능들을 제공해야 함
- 워크플로우 구성
- 지식 베이스 선택, 키워드 입력 후 워크플로우 실행
- 워크플로우 실행 결과를 시각화
- 워크플로우 실행 결과를 다양한 포맷의 파일로 추출

## 기능별 상세 설명
### 1. 워크플로우 구성
- 노드는 LLM 모델의 종류와 프롬프트 내용을 속성으로 가지고 있음
   - 노드 더블클릭 시 모델의 종류를 선택(드롭다운)하고 프롬프트 내용을 수정할 수 있는 수정창이 팝업됨. 프롬프트 내용은 기본적으로 특정 내용으로 채워져 있음
- Layer별 노드 추가/삭제 기능
   - Layer별 1개의 노드가 기본으로 존재
   - Layer별 첫 번째 노드는 삭제 불가하며, Layer별 마지막 노드에 대한 삭제 기능 제공
   - Generation Layer는 최대 3개, Ensemble Layer는 1개, Validation Layer는 5개까지 추가 가능
   - 다음 노드 추가가 가능한 위치에 PlaceholderNode가 보여야 함
- 워크플로우 로컬 저장/복원 기능
   - React Flow 내 노드들의 위치와 Canvas 내의 Zoom과 View Point도 함께 저장/복원되어야 함
- 현재의 워크플로우를 JSON 파일로 내보내기, JSON 불러오기 기능
- 모든 노드는 위치가 고정되며, 기본적으로 Canvas의 왼쪽에 배치
- 노드 간 Data Flow 방향대로 Directional Arrow가 이어져 있어야 함
   - Generation Layer의 모든 노드의 화살표가 Ensemble Layer의 유일 노드로 연결됨
   - Ensemble Layer의 유일 노드의 화살표가 Validation Layer의 첫 번째 노드로 연결됨
   - Validation Layer의 화살표가 같은 Layer의 다음 노드로 연결됨
   - 예시)
     Generation  ㅁ  ㅁ
                 ↓ ↙
     Ensemble    ㅁ
                 ↓
     Validation  ㅁ → ㅁ → ㅁ

### 2. 워크플로우 실행
- App 로드 시 Rest API를 호출하여 원격 서버에 구축되어 있는 지식 베이스 목록을 로드
- 지식 베이스와 키워드를 포함한 프롬프트 내용 및 노드 정보들을 워크플로우를 실행하기 위한 Rest API로 전달하고 결과를 받아옴

### 3. 워크플로우 결과 시각화
- Validation Layer의 마지막 노드의 결과로 나온 요구사항 목록을 표 형식으로 시각화하여 실행 결과 영역에서 제공해야 함
