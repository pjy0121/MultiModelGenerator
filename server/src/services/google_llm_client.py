
import asyncio
import traceback
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
            
            print(f"🔄 Google AI 응답 생성 시작...")
            
            # 스트리밍 응답 생성
            try:
                response = genai_model.generate_content(prompt, stream=True)
                print(f"✅ Google AI 응답 객체 생성 완료")
                
                # 응답 스트림 처리
                for chunk in response:
                    try:
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text
                            await asyncio.sleep(0.01)
                        
                    except AttributeError as attr_e:
                        # 알려지지 않은 필드나 구조 변경에 대한 안전장치
                        print(f"⚠️ Google AI chunk 처리 중 속성 오류: {attr_e}")
                        continue
                    except Exception as chunk_e:
                        # 개별 chunk 처리 오류는 로그만 남기고 계속 진행
                        print(f"⚠️ Google AI chunk 처리 오류: {chunk_e}")
                        continue
                        
            except Exception as stream_e:
                error_detail = traceback.format_exc()
                print(f"⚠️ Google AI 스트림 생성 오류: {stream_e}")
                print(f"⚠️ 상세 오류 정보:\n{error_detail}")
                raise
                    
        except Exception as e:
            error_msg = str(e)
            # 특정 에러 메시지에 대한 더 명확한 설명 제공
            if "finish_message" in error_msg:
                error_msg = f"Google AI API 구조 변경으로 인한 오류: {error_msg}"
            elif "Unknown field" in error_msg:
                error_msg = f"Google AI API 필드 변경으로 인한 오류: {error_msg}"
            
            raise Exception(f"Google AI 스트리밍 응답 생성 실패: {error_msg}")
        