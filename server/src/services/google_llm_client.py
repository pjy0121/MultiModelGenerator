
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
            
            # 비동기 스트리밍 응답 생성 (executor를 통한 완전 병렬화)
            try:
                import concurrent.futures
                
                # 동기 스트리밍을 별도 스레드에서 실행하여 블로킹 방지
                def _sync_generate():
                    try:
                        response = genai_model.generate_content(prompt, stream=True)
                        chunks = []
                        for chunk in response:
                            if hasattr(chunk, 'text') and chunk.text:
                                chunks.append(chunk.text)
                        return chunks
                    except Exception as e:
                        raise e
                
                # ThreadPoolExecutor로 완전 비동기화
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    chunks = await loop.run_in_executor(executor, _sync_generate)
                
                print(f"✅ Google AI 응답 객체 생성 완료")
                
                # 비동기적으로 청크 전송
                for chunk in chunks:
                    yield chunk
                    await asyncio.sleep(0.01)  # 다른 태스크에게 제어권 양보
                        
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
        