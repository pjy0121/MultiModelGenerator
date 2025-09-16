import os
from typing import List, Dict, Any
from .llm_client_interface import LLMClientInterface
from ..core.config import Config

try:
    import google.generativeai as genai
    print(f"✅ Google AI 라이브러리 import 성공")
    print(f"🔍 Google AI 라이브러리 버전: {getattr(genai, '__version__', 'Unknown')}")
    print(f"🔍 Google AI 라이브러리 경로: {genai.__file__ if hasattr(genai, '__file__') else 'Unknown'}")
except ImportError as e:
    print(f"❌ Google AI 라이브러리 import 실패: {e}")
    genai = None

class GoogleLLMClient(LLMClientInterface):
    """Google AI Studio API 클라이언트"""
    
    def __init__(self):
        """Google AI API 클라이언트 초기화"""
        self.api_key = Config.GOOGLE_API_KEY
        self.client = None
        
        if genai is None:
            print("❌ Google AI 라이브러리가 import되지 않았습니다.")
            return
        
        if self.api_key:
            print(f"🔑 Google API Key 발견 (길이: {len(self.api_key)})")
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
                print("✅ Google AI 클라이언트 초기화 성공")
                
                # API 키 유효성 테스트는 thinking 필드 버그 때문에 스킵
                print("🧪 API 키 테스트 스킵 (라이브러리 버그 회피)")
                
            except Exception as e:
                print(f"❌ Google AI 클라이언트 초기화 실패: {e}")
                import traceback
                traceback.print_exc()
                self.client = None
        else:
            print("⚠️ GOOGLE_API_KEY가 설정되지 않았습니다.")
    
    def is_available(self) -> bool:
        """Google AI API 사용 가능 여부 확인"""
        return genai is not None and self.client is not None and self.api_key is not None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 Google AI 모델 목록 반환"""
        print(f"🔍 Google AI 모델 조회 시작 - 사용가능: {self.is_available()}")
        
        if not self.is_available():
            print("⚠️ Google AI 클라이언트가 사용 불가능합니다.")
            print(f"  - genai 모듈: {genai is not None}")
            print(f"  - client: {self.client is not None}")
            print(f"  - api_key: {self.api_key is not None}")
            return []
        
        print("✅ Google AI 클라이언트 사용 가능, 모델 목록 조회 중...")
        
        try:
            # Google AI 라이브러리의 thinking 필드 버그 때문에 하드코딩 모델 사용
            hardcoded_models = [
                "gemini-2.0-flash-exp",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.0-pro"
            ]
            
            print(f"🔄 {len(hardcoded_models)}개의 하드코딩된 Google AI 모델 사용")
            
            available_models = []
            for model_name in hardcoded_models:
                model_info = {
                    "value": model_name,
                    "label": model_name,
                    "provider": "google",
                    "model_type": model_name,
                    "disabled": False
                }
                available_models.append(model_info)
                print(f"  ✅ 모델 추가: {model_name}")
            
            print(f"✅ Google AI: {len(available_models)}개 모델 로드 완료")
            return available_models
            
        except Exception as e:
            print(f"❌ Google AI 모델 조회 실패: {e}")
            print(f"   에러 타입: {type(e).__name__}")
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