import requests
import json
from datetime import datetime

class RequirementAPIClient:
    """요구사항 생성 API 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def get_knowledge_bases(self) -> dict:
        """지식 베이스 목록 조회"""
        try:
            response = requests.get(f"{self.base_url}/knowledge-bases")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_knowledge_base_status(self, kb_name: str) -> dict:
        """특정 지식 베이스 상태 조회"""
        try:
            response = requests.get(f"{self.base_url}/knowledge-bases/{kb_name}/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def generate_requirements_with_validation(self, payload: dict) -> dict:
        """검증 횟수를 포함한 요구사항 생성"""
        try:
            response = requests.post(
                f"{self.base_url}/generate-requirements",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def health_check(self) -> dict:
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def main():
    """API 클라이언트 사용 예제"""
    print("🔧 요구사항 생성 API 클라이언트 테스트")
    print("=" * 60)
    
    client = RequirementAPIClient()
    
        # 1. 서버 상태 확인
    print("1. 서버 상태 확인...")
    health = client.health_check()
    if "error" in health:
        print(f"❌ 서버 연결 실패: {health['error']}")
        print("💡 API 서버가 실행중인지 확인하세요: python api_server.py")
        return
    
    print("✅ 서버 연결 성공!")
    print(f"📊 지식 베이스 수: {health['knowledge_bases_count']}")
    
    # 2. 지식 베이스 목록 조회
    print("\n2. 지식 베이스 목록 조회...")
    kb_list = client.get_knowledge_bases()
    
    if "error" in kb_list:
        print(f"❌ 오류: {kb_list['error']}")
        return
    
    if kb_list['total_count'] == 0:
        print("❌ 등록된 지식 베이스가 없습니다.")
        print("💡 admin.py를 실행하여 지식 베이스를 구축하세요.")
        return
    
    print(f"✅ {kb_list['total_count']}개 지식 베이스 발견:")
    for kb in kb_list['knowledge_bases']:
        print(f"  📚 {kb['name']} (청크 수: {kb['chunk_count']:,})")
    
    # 3. 사용자 입력
    kb_name = input(f"\n사용할 지식 베이스 이름: ").strip()
    keyword = input("키워드: ").strip()
    
    # 검증 횟수 입력 추가
    while True:
        try:
            validation_rounds = input("검증 횟수 (1-5, 기본값 1): ").strip()
            if not validation_rounds:
                validation_rounds = 1
            else:
                validation_rounds = int(validation_rounds)
            
            if 1 <= validation_rounds <= 5:
                break
            else:
                print("❌ 검증 횟수는 1-5 사이여야 합니다.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
    
    if not kb_name or not keyword:
        print("❌ 지식 베이스 이름과 키워드를 모두 입력해주세요.")
        return
    
    # 4. 요구사항 생성
    print(f"\n3. 요구사항 생성 중... (KB: {kb_name}, 키워드: {keyword}, 검증: {validation_rounds}회)")
    print("⏳ AI가 처리하고 있습니다...")
    
    # 클라이언트 메서드도 수정 필요
    payload = {
        "knowledge_base": kb_name,
        "keyword": keyword,
        "validation_rounds": validation_rounds
    }
    
    result = client.generate_requirements_with_validation(payload)
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
        return
    
    # 5. 결과 출력
    print("\n" + "=" * 60)
    print("📋 생성된 요구사항")
    print("=" * 60)
    print(f"🏷️ 지식 베이스: {result['knowledge_base']}")
    print(f"🔍 키워드: {result['keyword']}")
    print(f"📚 검색된 청크: {result['chunks_found']}개")
    print(f"🕐 생성 시간: {result['generated_at']}")
    print("\n📝 요구사항:")
    print(result['requirements'])
    print("=" * 60)
    
    # 6. JSON 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_result_{kb_name}_{keyword}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"💾 결과가 저장되었습니다: {filename}")
    except Exception as e:
        print(f"⚠️ 파일 저장 실패: {e}")

if __name__ == "__main__":
    main()
