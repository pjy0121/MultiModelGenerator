from typing import List, Dict, Any
import google.generativeai as genai
from .llm_client_interface import LLMClientInterface
from ..core.config import Config

class GoogleLLMClient(LLMClientInterface):
    """Google AI Studio API 클라이언트"""
    
    def __init__(self):
        """Google AI API 클라이언트 초기화"""
        self.api_key = Config.GOOGLE_API_KEY
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
    
    def chat_completion(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Google AI를 사용하여 채팅 완성"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            # messages를 하나의 프롬프트로 변환
            prompt_parts = []
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            
            prompt = "\n".join(prompt_parts)
            return self.generate_response(prompt, model)
            
        except Exception as e:
            raise Exception(f"Google AI 채팅 완성 실패: {str(e)}")
    
    def generate_response(self, prompt: str, model: str) -> str:
        """Google AI를 사용하여 응답 생성"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            # 모델 이름에 'models/' 접두사가 없으면 추가
            if not model.startswith('models/'):
                model = f'models/{model}'
            
            # 생성형 모델 초기화
            genai_model = genai.GenerativeModel(model)
            
            # 응답 생성
            response = genai_model.generate_content(prompt)
            
            if response.text:
                return response.text
            else:
                raise Exception("Google AI에서 빈 응답을 받았습니다.")
                
        except Exception as e:
            raise Exception(f"Google AI 응답 생성 실패: {str(e)}")
    
    async def chat_completion_stream(self, model: str, messages: List[Dict[str, Any]], **kwargs):
        """Google AI를 사용하여 스트리밍 채팅 완성"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            # messages를 하나의 프롬프트로 변환
            prompt_parts = []
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            
            prompt = "\n".join(prompt_parts)
            
            # 스트리밍 응답 생성
            async for chunk in self.generate_stream_response(prompt, model):
                yield chunk
                
        except Exception as e:
            raise Exception(f"Google AI 스트리밍 채팅 완성 실패: {str(e)}")
    
    async def generate_stream_response(self, prompt: str, model: str):
        """Google AI를 사용하여 스트리밍 응답 생성"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            import asyncio
            
            # 모델 이름에 'models/' 접두사가 없으면 추가
            if not model.startswith('models/'):
                model = f'models/{model}'
            
            # 생성형 모델 초기화
            genai_model = genai.GenerativeModel(model)
            
            # Google AI는 스트리밍을 지원하므로 이를 활용
            try:
                response = genai_model.generate_content(
                    prompt,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                        await asyncio.sleep(0.01)  # 약간의 지연
            except Exception as stream_error:
                # 스트리밍이 실패하면 일반 응답으로 fallback
                response = genai_model.generate_content(prompt)
                full_text = response.text if response.text else ""
                
                # 텍스트를 청크로 나누어 스트리밍 시뮬레이션
                chunk_size = 20
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i:i+chunk_size]
                    yield chunk
                    await asyncio.sleep(0.05)
                    
        except Exception as e:
            raise Exception(f"Google AI 스트리밍 응답 생성 실패: {str(e)}")
    
    def estimate_tokens(self, text: str, model: str) -> int:
        """토큰 수 추정 (대략적)"""
        if not self.is_available():
            # 간단한 추정: 단어 수 * 1.3
            return int(len(text.split()) * 1.3)
        
        try:
            # 모델 이름에 'models/' 접두사가 없으면 추가
            if not model.startswith('models/'):
                model = f'models/{model}'
            
            # Google AI의 토큰 카운트 기능 사용 (가능한 경우)
            genai_model = genai.GenerativeModel(model)
            token_count = genai_model.count_tokens(text)
            return token_count.total_tokens
            
        except Exception:
            # 실패 시 간단한 추정
            return int(len(text.split()) * 1.3)
