import requests
import json
from datetime import datetime

class RequirementAPIClient:
    """Requirements generation API client"""

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url

    def get_knowledge_bases(self) -> dict:
        """Get knowledge base list"""
        try:
            response = requests.get(f"{self.base_url}/knowledge-bases")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_knowledge_base_status(self, kb_name: str) -> dict:
        """Get specific knowledge base status"""
        try:
            response = requests.get(f"{self.base_url}/knowledge-bases/{kb_name}/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def generate_requirements_with_validation(self, payload: dict) -> dict:
        """Generate requirements with validation rounds"""
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
        """Check server health"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def main():
    """API client usage example"""
    print("Requirements Generation API Client Test")
    print("=" * 60)

    client = RequirementAPIClient()

    # 1. Check server health
    print("1. Checking server health...")
    health = client.health_check()
    if "error" in health:
        print(f"Server connection failed: {health['error']}")
        print("Please ensure the API server is running: python api_server.py")
        return

    print("Server connection successful!")
    print(f"Knowledge base count: {health['knowledge_bases_count']}")

    # 2. Get knowledge base list
    print("\n2. Fetching knowledge base list...")
    kb_list = client.get_knowledge_bases()

    if "error" in kb_list:
        print(f"Error: {kb_list['error']}")
        return

    if kb_list['total_count'] == 0:
        print("No knowledge bases found.")
        print("Run admin.py to build a knowledge base.")
        return

    print(f"{kb_list['total_count']} knowledge base(s) found:")
    for kb in kb_list['knowledge_bases']:
        print(f"  {kb['name']} (chunks: {kb['chunk_count']:,})")

    # 3. User input
    kb_name = input(f"\nEnter knowledge base name: ").strip()
    keyword = input("Enter keyword: ").strip()

    # Validation rounds input
    while True:
        try:
            validation_rounds = input("Validation rounds (1-5, default 1): ").strip()
            if not validation_rounds:
                validation_rounds = 1
            else:
                validation_rounds = int(validation_rounds)

            if 1 <= validation_rounds <= 5:
                break
            else:
                print("Validation rounds must be between 1-5.")
        except ValueError:
            print("Please enter a number.")

    if not kb_name or not keyword:
        print("Both knowledge base name and keyword are required.")
        return

    # 4. Generate requirements
    print(f"\n3. Generating requirements... (KB: {kb_name}, Keyword: {keyword}, Validation: {validation_rounds} rounds)")
    print("AI is processing...")

    payload = {
        "knowledge_base": kb_name,
        "keyword": keyword,
        "validation_rounds": validation_rounds
    }

    result = client.generate_requirements_with_validation(payload)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    # 5. Output results
    print("\n" + "=" * 60)
    print("Generated Requirements")
    print("=" * 60)
    print(f"Knowledge Base: {result['knowledge_base']}")
    print(f"Keyword: {result['keyword']}")
    print(f"Chunks found: {result['chunks_found']}")
    print(f"Generated at: {result['generated_at']}")
    print("\nRequirements:")
    print(result['requirements'])
    print("=" * 60)

    # 6. Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_result_{kb_name}_{keyword}_{timestamp}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"Results saved to: {filename}")
    except Exception as e:
        print(f"Failed to save file: {e}")

if __name__ == "__main__":
    main()
