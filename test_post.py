import sys
import json
import requests
from copy import deepcopy

# POST 요청 보낼 주소 (실제 URL로 변경하세요)
URL = "http://localhost:5001/execute-workflow-stream"

def load_template(path):
    """템플릿 JSON 로드"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def replace_values(template, provider, model, input_text):
    """JSON 내부에서 provider, model, input_text 값을 교체"""
    new_data = deepcopy(template)

    for node in new_data["workflow"]["nodes"]:
        if node.get("llm_provider") == "google":
            node["llm_provider"] = provider
        if node.get("model_type") == "gemini-1.5-flash":
            node["model_type"] = model
        if node.get("content") == "Sanitize":
            node["content"] = input_text

    return new_data

def main():
    if len(sys.argv) < 4:
        print("Usage: python test_post.py <provider> <model> <input>")
        sys.exit(1)

    provider = sys.argv[1]
    model = sys.argv[2]
    input_text = sys.argv[3]

    template = load_template("./post_param_example.json")
    payload = replace_values(template, provider, model, input_text)

    headers = {"Content-Type": "application/json"}
    response = requests.post(URL, headers=headers, json=payload)

    print("Status Code:", response.status_code)
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Response Text:", response.text)

if __name__ == "__main__":
    main()
