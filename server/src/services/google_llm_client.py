import asyncio
import google.generativeai as genai
from typing import List, Dict, Any
from .llm_client_interface import LLMClientInterface
from ..core.config import API_KEYS, NODE_EXECUTION_CONFIG

class GoogleLLMClient(LLMClientInterface):
    """Google AI Studio API 클라이언트"""
    
    def __init__(self):
        """Google AI API 클라이언트 초기화"""
        self.api_key = API_KEYS["google"]
        self.client = None
        
        if genai is None:
            return
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
            except Exception:
                self.client = None
    
    def is_available(self) -> bool:
        """Google AI API 사용 가능 여부 확인"""
        return genai is not None and self.client is not None and self.api_key is not None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 Google AI 모델 목록 반환"""
        if not self.is_available():
            return []
        
        try:
            # thinking 필드 버그 우회: REST API 직접 호출
            import requests
            
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            headers = {"x-goog-api-key": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            models_data = data.get('models', [])
            
            available_models = []
            for model_data in models_data:
                model_name = model_data.get('name', '').replace('models/', '')
                supported_methods = model_data.get('supportedGenerationMethods', [])
                                
                # 생성 가능한 모델만 필터링
                if 'generateContent' in supported_methods:
                    model_info = {
                        "value": model_name,
                        "label": model_name,
                        "provider": "google",
                        "model_type": model_name,
                        "disabled": False
                    }
                    available_models.append(model_info)            
            return available_models
            
        except Exception as e:
            return []
    
    async def generate_stream(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ):
        """스트리밍으로 응답 생성 (통합된 단일 인터페이스)"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            # 모델 이름에 'models/' 접두사가 없으면 추가
            if not model.startswith('models/'):
                model = f'models/{model}'
            
            # 생성형 모델 초기화 (temperature 등 설정)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            genai_model = genai.GenerativeModel(
                model, 
                generation_config=generation_config
            )
            
            # 스트리밍 응답 생성
            response = genai_model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            raise Exception(f"Google AI 스트리밍 응답 생성 실패: {str(e)}")
        