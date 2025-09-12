import time
from typing import List, Optional, Dict
from ..core.models import NodeConfig, NodeOutput
from ..services.llm_factory import LLMFactory

class LayerEngine:
    """Layer별 노드 실행 엔진 - 추상화된 LLM 클라이언트 사용"""
    
    def __init__(self):
        """LayerEngine 초기화 - 지연 로딩으로 실제 사용 시 LLM 클라이언트 초기화"""
        self._initialized = False
        self._available_providers = None
    
    def _ensure_initialized(self):
        """LLM 팩토리 초기화 확인 (지연 로딩)"""
        if self._initialized:
            return
            
        try:
            # LLM 팩토리를 통해 사용 가능한 제공자 확인
            self._available_providers = LLMFactory.get_available_providers()
            if not self._available_providers:
                raise RuntimeError("사용 가능한 LLM 제공자가 없습니다. API 키를 확인하세요.")
            
            print(f"✅ 사용 가능한 LLM 제공자: {', '.join(self._available_providers)}")
            self._initialized = True
            
        except Exception as e:
            print(f"⚠️ LayerEngine 초기화 실패: {e}")
            print("💡 .env 파일의 API 키들이 올바르게 설정되어 있는지 확인하세요.")
            raise
    
    def execute_node(self, node: NodeConfig, input_data: str, context_chunks: List[str]) -> NodeOutput:
        """개별 노드 실행 - LLM 팩토리를 통한 동적 클라이언트 선택"""
        start_time = time.time()
        
        try:
            # 지연 로딩으로 초기화 확인
            self._ensure_initialized()
            
            # 모델 타입 결정 (인덱스 우선, 호환성 지원)
            model_name = self._resolve_model_name(node)
            if not model_name:
                raise ValueError("유효한 모델을 찾을 수 없습니다.")
            
            # 선택된 모델에 맞는 클라이언트 자동 선택
            try:
                # provider 정보가 있으면 사용, 없으면 자동 선택
                provider = getattr(node, 'provider', None)
                llm_client = LLMFactory.get_client_for_model(model_name, provider)
                print(f"✅ 모델 {model_name}에 대해 {llm_client.__class__.__name__} 사용")
            except Exception as e:
                # 사용 불가능한 모델인 경우 명확한 오류 메시지
                raise ValueError(f"모델 '{model_name}'을 사용할 수 없습니다: {str(e)}")
            
            # LLM API 호출
            result = self._execute_llm_node(llm_client, node, input_data, context_chunks, model_name)
            
            execution_time = time.time() - start_time
            
            return NodeOutput(
                node_id=node.id,
                model_type=model_name,
                requirements=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return NodeOutput(
                node_id=node.id,
                model_type="unknown",
                requirements=f"오류 발생: {str(e)}",
                execution_time=execution_time
            )
    
    def _resolve_model_name(self, node: NodeConfig) -> Optional[str]:
        """노드의 모델명 결정"""
        if node.model:
            print(f"✅ 노드에서 모델 사용: {node.model}")
            return node.model
        
        print("❌ 모델을 결정할 수 없습니다. model 필드가 필요합니다.")
        return None
    
    def _execute_llm_node(self, llm_client, node: NodeConfig, input_data: str, context_chunks: List[Dict], model_name: str) -> str:
        """LLM 노드 실행 - 클라이언트에서 완성된 프롬프트 사용"""
        # 클라이언트에서 이미 {context}와 {layer_input}을 모두 처리한 완성된 프롬프트를 받음
        formatted_prompt = node.prompt
        
        print(f"🤖 사용할 모델: {model_name}")
        if context_chunks:
            print(f"📚 전달받은 context_chunks: {len(context_chunks)}개")
            for i, chunk in enumerate(context_chunks[:2]):  # 처음 2개 청크만 로깅
                chunk_text = str(chunk) if not isinstance(chunk, str) else chunk
                print(f"📄 청크 {i+1}: {chunk_text[:100]}...")
        else:
            print("⚠️ context_chunks가 비어있음")

        # 간단한 시스템 프롬프트
        system_prompt = "당신은 전문적인 AI 어시스턴트입니다. 주어진 요청에 정확하고 유용한 답변을 제공하세요."
        
        try:
            # LLM 클라이언트 인터페이스를 통한 호출
            result = llm_client.chat_completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ LLM API 호출 오류: {error_msg}")
            return f"⚠️ API 호출 오류: {error_msg}"
