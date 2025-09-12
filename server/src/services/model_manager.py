from typing import Dict, List, Optional
from ..core.models import AvailableModel, AvailableModelsResponse
from .llm_factory import LLMFactory

class ModelManager:
    """모델 인덱스 및 가용성 관리 - 각 클라이언트가 자체 모델 로드"""
    
    _model_registry: List[AvailableModel] = []
    _initialized = False
    
    @classmethod
    def _ensure_initialized(cls):
        """모델 레지스트리 초기화 확인"""
        if not cls._initialized:
            cls._load_all_models()
    
    @classmethod
    def _load_all_models(cls):
        """모든 프로바이더에서 모델 로드"""
        print("🔄 ModelManager: 모델 로드 시작...")
        cls._model_registry.clear()
        index = 0
        
        # 각 프로바이더별로 클라이언트에서 모델 목록 가져오기
        providers = ["openai", "perplexity", "google"]
        
        for provider in providers:
            print(f"🔄 {provider} 프로바이더 모델 로드 중...")
            try:
                client = LLMFactory.get_client(provider)
                if client:
                    print(f"✅ {provider} 클라이언트 생성 성공")
                    models = client.get_available_models()
                    print(f"📋 {provider}에서 {len(models)}개 모델 반환")
                    
                    # 각 모델에 전역 인덱스 할당
                    for model in models:
                        # 클라이언트에서 반환된 모델을 그대로 사용하되, 전역 인덱스만 업데이트
                        model.index = index
                        cls._model_registry.append(model)
                        print(f"  📝 모델 추가: {model.label} (disabled: {model.disabled})")
                        index += 1
                else:
                    print(f"❌ {provider} 클라이언트 생성 실패")
                        
            except Exception as e:
                print(f"⚠️ {provider} 모델 로드 실패: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        cls._initialized = True
        print(f"✅ 총 {len(cls._model_registry)}개 모델 로드 완료")
    
    @classmethod
    def get_all_models(cls) -> List[AvailableModel]:
        """모든 사용 가능한 모델 반환"""
        cls._ensure_initialized()
        return cls._model_registry.copy()
    
    @classmethod
    def get_models_by_provider(cls, provider: str) -> List[AvailableModel]:
        """특정 프로바이더의 모델만 반환"""
        cls._ensure_initialized()
        return [model for model in cls._model_registry if model.provider == provider]
    
    @classmethod
    def get_model_by_index(cls, index: int) -> Optional[AvailableModel]:
        """인덱스로 모델 조회"""
        cls._ensure_initialized()
        for model in cls._model_registry:
            if model.index == index:
                return model
        return None
    
    @classmethod
    def get_model_by_type(cls, model_type: str) -> Optional[AvailableModel]:
        """모델 타입으로 모델 조회"""
        cls._ensure_initialized()
        for model in cls._model_registry:
            if model.model_type == model_type:
                return model
        return None
    
    @classmethod
    def reload_models(cls):
        """모델 목록 다시 로드"""
        cls._initialized = False
        cls._load_all_models()
    
    @classmethod
    def get_available_models_response(cls) -> AvailableModelsResponse:
        """API 응답용 모델 목록 반환"""
        models = cls.get_all_models()
        available_providers = list(set(model.provider for model in models if not model.disabled))
        return AvailableModelsResponse(
            models=models,
            available_providers=available_providers,
            total_count=len(models),
            available_count=len([m for m in models if not m.disabled])
        )
    
    @classmethod
    def is_model_available(cls, model_type: str) -> bool:
        """모델 사용 가능 여부 확인"""
        model = cls.get_model_by_type(model_type)
        return model is not None and not model.disabled