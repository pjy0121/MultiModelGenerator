import os
import google.generativeai as genai
from typing import List, Dict, Any
from .llm_client_interface import LLMClientInterface
from ..core.models import AvailableModel
from ..core.config import Config

class GoogleLLMClient(LLMClientInterface):
    """Google AI Studio API 클라이언트"""
    
    def __init__(self):
        """Google AI API 클라이언트 초기화"""
        self.api_key = Config.GOOGLE_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.client = genai
        else:
            self.client = None
    
    def is_available(self) -> bool:
        """Google AI API 사용 가능 여부 확인"""
        return self.client is not None and self.api_key is not None
    
    def get_available_models(self) -> List[AvailableModel]:
        """사용 가능한 Google AI 모델 목록 반환"""
        if not self.is_available():
            return []
        
        try:
            # 실제 API에서 모델 목록 가져오기
            models = []
            index = 0
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    model_id = model.name.replace('models/', '')
                    models.append({
                        "index": index,
                        "value": model_id,         # 서버 필드명
                        "label": model_id,         # 서버 필드명
                        "provider": "google",
                        "model_type": model_id,
                        "disabled": False          # 서버 필드명
                    })
                    index += 1
                
            return [AvailableModel(**model) for model in models]
            
        except Exception as e:
            print(f"Google AI 모델 목록 가져오기 실패: {e}")
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
    
    def generate_stream_response(self, prompt: str, model: str):
        """Google AI를 사용하여 스트리밍 응답 생성"""
        if not self.is_available():
            raise Exception("Google AI API 키가 설정되지 않았습니다.")
        
        try:
            # 모델 이름에 'models/' 접두사가 없으면 추가
            if not model.startswith('models/'):
                model = f'models/{model}'
            
            # 생성형 모델 초기화
            genai_model = genai.GenerativeModel(model)
            
            # 스트리밍 응답 생성
            response = genai_model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
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