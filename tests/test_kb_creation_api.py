"""
Knowledge Base Creation API 테스트 - chunk_type 제거 검증
"""
import pytest
import requests
import base64


class TestKnowledgeBaseCreation:
    """지식 베이스 생성 API 테스트"""
    
    @pytest.fixture
    def sample_text_content(self):
        """테스트용 샘플 텍스트"""
        return "This is a test document for knowledge base creation. " * 50
    
    @pytest.fixture
    def sample_base64_content(self, sample_text_content):
        """Base64 인코딩된 샘플 텍스트"""
        return base64.b64encode(sample_text_content.encode('utf-8')).decode('ascii')
    
    def test_kb_creation_without_chunk_type(self, api_client: requests.Session, api_base_url: str, sample_text_content: str):
        """chunk_type 없이 KB 생성 가능한지 테스트"""
        payload = {
            "kb_name": "test_kb_no_chunk_type",
            "text_content": sample_text_content,
            "text_type": "plain",
            "chunk_size": 2048,
            "chunk_overlap": 307
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        # chunk_type 없이도 성공해야 함
        assert response.status_code == 200 or response.status_code == 409  # 409: already exists
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "kb_name" in data
    
    def test_kb_creation_with_base64_text(self, api_client: requests.Session, api_base_url: str, sample_base64_content: str):
        """Base64 인코딩된 텍스트로 KB 생성 테스트"""
        payload = {
            "kb_name": "test_kb_base64",
            "text_content": sample_base64_content,
            "text_type": "base64",
            "chunk_size": 2048,
            "chunk_overlap": 307
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        # Base64 텍스트가 올바르게 처리되어야 함
        assert response.status_code == 200 or response.status_code == 409
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
    
    def test_kb_creation_with_plain_text(self, api_client: requests.Session, api_base_url: str, sample_text_content: str):
        """Plain 텍스트로 KB 생성 테스트"""
        payload = {
            "kb_name": "test_kb_plain",
            "text_content": sample_text_content,
            "text_type": "plain",
            "chunk_size": 2048,
            "chunk_overlap": 307
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        assert response.status_code == 200 or response.status_code == 409
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
    
    def test_kb_creation_without_kb_name(self, api_client: requests.Session, api_base_url: str, sample_text_content: str):
        """kb_name 없이 KB 생성 시 400 에러 반환"""
        payload = {
            "text_content": sample_text_content,
            "text_type": "plain"
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "kb_name" in data["detail"].lower()
    
    def test_kb_creation_without_content(self, api_client: requests.Session, api_base_url: str):
        """내용 없이 KB 생성 시 400 에러 반환"""
        payload = {
            "kb_name": "test_kb_no_content"
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "content" in data["detail"].lower() or "text" in data["detail"].lower()
    
    def test_kb_creation_response_has_no_chunk_type(self, api_client: requests.Session, api_base_url: str, sample_text_content: str):
        """KB 생성 응답에 chunk_type이 없는지 확인"""
        payload = {
            "kb_name": "test_kb_response_check",
            "text_content": sample_text_content,
            "text_type": "plain",
            "chunk_size": 2048,
            "chunk_overlap": 307
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            # chunk_type 필드가 응답에 없어야 함
            assert "chunk_type" not in data, "Response should not contain 'chunk_type' field"
    
    def test_kb_name_no_prefix(self, api_client: requests.Session, api_base_url: str, sample_text_content: str):
        """KB 이름에 자동 prefix가 추가되지 않는지 확인"""
        test_kb_name = "my_custom_kb"
        payload = {
            "kb_name": test_kb_name,
            "text_content": sample_text_content,
            "text_type": "plain",
            "chunk_size": 2048,
            "chunk_overlap": 307
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            # 반환된 kb_name이 입력한 이름과 동일해야 함 (prefix 없음)
            assert data["kb_name"] == test_kb_name or data["kb_name"].endswith(test_kb_name)
            # keyword-, sentence- 같은 prefix가 없어야 함
            assert not data["kb_name"].startswith("keyword-")
            assert not data["kb_name"].startswith("sentence-")
            assert not data["kb_name"].startswith("custom-")
    
    def test_invalid_base64_content(self, api_client: requests.Session, api_base_url: str):
        """잘못된 Base64 내용으로 KB 생성 시 400 에러"""
        payload = {
            "kb_name": "test_kb_invalid_base64",
            "text_content": "This is not valid base64!!!@#$%",
            "text_type": "base64"
        }
        
        response = api_client.post(
            f"{api_base_url}/knowledge-bases/create",
            json=payload
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "base64" in data["detail"].lower()
