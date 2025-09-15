"""
LangChain 기반 LLM Factory - 간소화된 구조
OpenAI와 Google LLM 제공자 지원
"""
import os
import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

from ..core.models import AvailableModel

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI LLM 제공자"""
    
    MODELS = {
        "gpt-3.5-turbo": {"label": "GPT-3.5 Turbo", "max_tokens": 4096},
        "gpt-4": {"label": "GPT-4", "max_tokens": 8192},
        "gpt-4-turbo": {"label": "GPT-4 Turbo", "max_tokens": 8192},
        "gpt-4o": {"label": "GPT-4o", "max_tokens": 8192},
        "gpt-4o-mini": {"label": "GPT-4o Mini", "max_tokens": 16384},
    }
    
    @classmethod
    def is_available(cls) -> bool:
        """OpenAI API 사용 가능한지 확인"""
        return bool(os.getenv('OPENAI_API_KEY'))
    
    @classmethod
    def create_llm(cls, model_id: str) -> ChatOpenAI:
        """OpenAI LLM 인스턴스 생성"""
        if model_id not in cls.MODELS:
            raise ValueError(f"지원하지 않는 OpenAI 모델: {model_id}")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
        
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            temperature=0.1,
            max_tokens=cls.MODELS[model_id]["max_tokens"]
        )
    
    @classmethod
    def get_available_models(cls) -> List[AvailableModel]:
        """사용 가능한 OpenAI 모델 목록"""
        models = []
        available = cls.is_available()
        
        for idx, (model_id, config) in enumerate(cls.MODELS.items()):
            models.append(AvailableModel(
                index=idx,
                value=f"openai_{model_id}",
                label=f"{config['label']} (OpenAI)",
                provider="openai",
                disabled=not available,
                model_type=model_id
            ))
        
        return models


class GoogleProvider:
    """Google AI LLM 제공자"""
    
    MODELS = {
        "gemini-pro": {"label": "Gemini Pro", "max_tokens": 8192},
        "gemini-1.5-pro": {"label": "Gemini 1.5 Pro", "max_tokens": 8192},
        "gemini-1.5-flash": {"label": "Gemini 1.5 Flash", "max_tokens": 8192},
        "gemini-2.0-flash": {"label": "Gemini 2.0 Flash", "max_tokens": 8192},
    }
    
    @classmethod
    def is_available(cls) -> bool:
        """Google AI API 사용 가능한지 확인"""
        return bool(os.getenv('GOOGLE_API_KEY'))
    
    @classmethod
    def create_llm(cls, model_id: str) -> ChatGoogleGenerativeAI:
        """Google LLM 인스턴스 생성"""
        if model_id not in cls.MODELS:
            raise ValueError(f"지원하지 않는 Google 모델: {model_id}")
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")
        
        return ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=api_key,
            temperature=0.1,
            max_output_tokens=cls.MODELS[model_id]["max_tokens"]
        )
    
    @classmethod
    def get_available_models(cls) -> List[AvailableModel]:
        """사용 가능한 Google 모델 목록"""
        models = []
        available = cls.is_available()
        
        for idx, (model_id, config) in enumerate(cls.MODELS.items()):
            models.append(AvailableModel(
                index=idx + 100,  # OpenAI 이후 인덱스
                value=f"google_{model_id}",
                label=f"{config['label']} (Google)",
                provider="google",
                disabled=not available,
                model_type=model_id
            ))
        
        return models

class LangChainLLMFactory:
    """간소화된 LangChain LLM 팩토리"""
    
    _llm_cache: Dict[str, BaseLanguageModel] = {}
    
    @classmethod
    def get_llm(cls, provider: str, model_id: str) -> BaseLanguageModel:
        """지정된 제공자와 모델의 LangChain LLM 인스턴스 반환"""
        cache_key = f"{provider}_{model_id}"
        
        if cache_key in cls._llm_cache:
            return cls._llm_cache[cache_key]
        
        if provider == "openai":
            llm = OpenAIProvider.create_llm(model_id)
        elif provider == "google":
            llm = GoogleProvider.create_llm(model_id)
        else:
            raise ValueError(f"지원하지 않는 제공자: {provider}")
        
        cls._llm_cache[cache_key] = llm
        return llm
    
    @classmethod
    def get_llm_by_model_id(cls, model_id: str) -> BaseLanguageModel:
        """모델 ID에 기반해 적절한 LangChain LLM 인스턴스 반환"""
        if model_id.startswith("gpt-"):
            provider = "openai"
        elif model_id.startswith("gemini-"):
            provider = "google"
        else:
            raise ValueError(f"알 수 없는 모델 ID: {model_id}")
        
        return cls.get_llm(provider, model_id)
    
    @classmethod
    def get_available_models(cls) -> List[AvailableModel]:
        """모든 사용 가능한 모델 목록 반환"""
        models = []
        
        # OpenAI 모델 추가
        models.extend(OpenAIProvider.get_available_models())
        
        # Google 모델 추가  
        models.extend(GoogleProvider.get_available_models())
        
        return models
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """사용 가능한 LLM 제공자 목록 반환"""
        providers = []
        
        if OpenAIProvider.is_available():
            providers.append("openai")
        
        if GoogleProvider.is_available():
            providers.append("google")
        
        return providers
    
    @classmethod
    def chat_completion(
        cls, 
        model_id: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """채팅 완성 요청"""
        llm = cls.get_llm_by_model_id(model_id)
        
        # 메시지를 LangChain BaseMessage 객체로 변환
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:  # user
                langchain_messages.append(HumanMessage(content=content))
        
        # LLM 파라미터 업데이트
        if hasattr(llm, 'temperature'):
            llm.temperature = temperature
        if hasattr(llm, 'max_tokens'):
            llm.max_tokens = max_tokens
        elif hasattr(llm, 'max_output_tokens'):
            llm.max_output_tokens = max_tokens
        
        try:
            response = llm.invoke(langchain_messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            raise
class LangChainLLMWrapper:
    """기존 LLMClientInterface와의 호환성을 위한 래퍼 클래스"""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.factory = LangChainLLMFactory
    
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """채팅 완성 요청"""
        return self.factory.chat_completion(model, messages, temperature, max_tokens)
    
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부 확인"""
        available_providers = self.factory.get_available_providers()
        return self.provider in available_providers
    
    def get_available_models(self) -> List[AvailableModel]:
        """사용 가능한 모델 목록 반환"""
        all_models = self.factory.get_available_models()
        return [model for model in all_models if model.provider == self.provider]