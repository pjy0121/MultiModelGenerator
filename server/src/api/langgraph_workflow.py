"""
LangGraph 기반 멀티 레이어 워크플로우 구현
StateGraph를 사용한 Generation → Ensemble → Validation 플로우
"""
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..core.models import LayerType
from ..services.vector_store import VectorStore
from .chain_executors import LayerChainExecutor

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """워크플로우 상태 정의"""
    # 메시지들
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 워크플로우 데이터
    knowledge_base: str
    initial_input: str
    current_layer_input: str
    
    # 레이어별 결과
    generation_results: Dict[str, Any]
    ensemble_results: Dict[str, Any]
    validation_results: Dict[str, Any]
    
    # 최종 결과
    final_output: str
    forward_data: str
    
    # 실행 상태
    current_layer: str
    error_occurred: bool
    error_message: str


class LangGraphWorkflowEngine:
    """LangGraph 기반 워크플로우 엔진"""
    
    def __init__(self):
        self.chain_executor = LayerChainExecutor()
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """워크플로우 그래프 구성"""
        # StateGraph 생성
        workflow = StateGraph(WorkflowState)
        
        # 노드들 추가
        workflow.add_node("generation_layer", self._execute_generation_layer)
        workflow.add_node("ensemble_layer", self._execute_ensemble_layer)
        workflow.add_node("validation_layer", self._execute_validation_layer)
        workflow.add_node("finalize_output", self._finalize_output)
        
        # 시작점 설정
        workflow.set_entry_point("generation_layer")
        
        # 엣지들 정의
        workflow.add_edge("generation_layer", "ensemble_layer")
        workflow.add_edge("ensemble_layer", "validation_layer")
        workflow.add_edge("validation_layer", "finalize_output")
        workflow.add_edge("finalize_output", END)
        
        # 조건부 엣지 (에러 처리)
        workflow.add_conditional_edges(
            "generation_layer",
            self._check_layer_success,
            {
                "continue": "ensemble_layer",
                "error": "finalize_output"
            }
        )
        
        workflow.add_conditional_edges(
            "ensemble_layer", 
            self._check_layer_success,
            {
                "continue": "validation_layer",
                "error": "finalize_output"
            }
        )
        
        workflow.add_conditional_edges(
            "validation_layer",
            self._check_layer_success,
            {
                "continue": "finalize_output",
                "error": "finalize_output"
            }
        )
        
        # 그래프 컴파일
        self.graph = workflow.compile()
        logger.info("LangGraph 워크플로우 구성 완료")
    
    def _check_layer_success(self, state: WorkflowState) -> str:
        """레이어 실행 성공 여부 확인"""
        if state.get("error_occurred", False):
            return "error"
        return "continue"
    
    def _execute_generation_layer(self, state: WorkflowState) -> WorkflowState:
        """Generation Layer 실행"""
        try:
            logger.info("LangGraph Generation Layer 실행 시작")
            
            # 임시로 단일 노드 실행 (실제로는 노드 목록을 받아야 함)
            # 여기서는 Chain executor를 직접 사용
            result = self.chain_executor.execute_node_with_chain(
                node=self._create_default_node("generation"), 
                layer_input=state["initial_input"],
                knowledge_base=state["knowledge_base"],
                layer_type="requirement"
            )
            
            # 상태 업데이트
            state["generation_results"] = {"node1": result}
            state["current_layer_input"] = result[:500]  # 다음 레이어를 위한 입력
            state["current_layer"] = "generation"
            
            # 메시지 추가
            state["messages"].append(HumanMessage(content=f"Generation 완료: {result[:100]}..."))
            
            logger.info("LangGraph Generation Layer 실행 완료")
            
        except Exception as e:
            logger.error(f"Generation Layer 실행 실패: {e}")
            state["error_occurred"] = True
            state["error_message"] = str(e)
        
        return state
    
    def _execute_ensemble_layer(self, state: WorkflowState) -> WorkflowState:
        """Ensemble Layer 실행"""
        try:
            logger.info("LangGraph Ensemble Layer 실행 시작")
            
            result = self.chain_executor.execute_node_with_chain(
                node=self._create_default_node("ensemble"),
                layer_input=state["current_layer_input"],
                knowledge_base=state["knowledge_base"],
                layer_type="ensemble"
            )
            
            # 상태 업데이트
            state["ensemble_results"] = {"node1": result}
            state["current_layer_input"] = result[:500]
            state["current_layer"] = "ensemble"
            
            # 메시지 추가
            state["messages"].append(HumanMessage(content=f"Ensemble 완료: {result[:100]}..."))
            
            logger.info("LangGraph Ensemble Layer 실행 완료")
            
        except Exception as e:
            logger.error(f"Ensemble Layer 실행 실패: {e}")
            state["error_occurred"] = True
            state["error_message"] = str(e)
        
        return state
    
    def _execute_validation_layer(self, state: WorkflowState) -> WorkflowState:
        """Validation Layer 실행"""
        try:
            logger.info("LangGraph Validation Layer 실행 시작")
            
            result = self.chain_executor.execute_node_with_chain(
                node=self._create_default_node("validation"),
                layer_input=state["current_layer_input"],
                knowledge_base=state["knowledge_base"],
                layer_type="validation"
            )
            
            # 상태 업데이트
            state["validation_results"] = {"node1": result}
            state["current_layer"] = "validation"
            
            # 메시지 추가
            state["messages"].append(HumanMessage(content=f"Validation 완료: {result[:100]}..."))
            
            logger.info("LangGraph Validation Layer 실행 완료")
            
        except Exception as e:
            logger.error(f"Validation Layer 실행 실패: {e}")
            state["error_occurred"] = True
            state["error_message"] = str(e)
        
        return state
    
    def _finalize_output(self, state: WorkflowState) -> WorkflowState:
        """최종 출력 생성"""
        try:
            if state.get("error_occurred", False):
                state["final_output"] = f"워크플로우 실행 중 오류 발생: {state.get('error_message', 'Unknown error')}"
                state["forward_data"] = ""
            else:
                # 최종 결과는 validation 결과 사용
                final_result = state["validation_results"].get("node1", "")
                state["final_output"] = final_result
                
                # forward_data 생성
                try:
                    import json
                    parsed = json.loads(final_result)
                    if "overall_valid" in parsed:
                        status = "PASS" if parsed["overall_valid"] else "FAIL"
                        state["forward_data"] = f"Validation: {status}"
                    else:
                        state["forward_data"] = final_result[:100]
                except:
                    state["forward_data"] = final_result[:100]
            
            # 최종 메시지 추가
            state["messages"].append(HumanMessage(content=f"워크플로우 완료: {state['final_output'][:100]}..."))
            
            logger.info("LangGraph 워크플로우 최종화 완료")
            
        except Exception as e:
            logger.error(f"최종화 실패: {e}")
            state["final_output"] = f"최종화 실패: {str(e)}"
            state["forward_data"] = ""
        
        return state
    
    def _create_default_node(self, layer_type: str) -> Dict[str, Any]:
        """기본 노드 설정 생성 (임시)"""
        prompts = {
            "generation": "주어진 입력에 대해 체계적인 요구사항을 생성하세요.",
            "ensemble": "여러 관점을 종합하여 최종 결정을 내리세요.",
            "validation": "주어진 내용을 검증하고 개선점을 제시하세요."
        }
        
        return {
            "id": f"{layer_type}_node",
            "model": "gpt-3.5-turbo",  # 기본 모델
            "provider": "openai",
            "prompt": prompts.get(layer_type, "주어진 작업을 수행하세요."),
            "layer": layer_type,
            "position": {"x": 0, "y": 0}
        }
    
    def execute_workflow(
        self, 
        initial_input: str, 
        knowledge_base: str,
        generation_nodes: Optional[List[Dict[str, Any]]] = None,
        ensemble_nodes: Optional[List[Dict[str, Any]]] = None,
        validation_nodes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """전체 워크플로우 실행"""
        
        # 초기 상태 설정
        initial_state = WorkflowState(
            messages=[HumanMessage(content=f"워크플로우 시작: {initial_input}")],
            knowledge_base=knowledge_base,
            initial_input=initial_input,
            current_layer_input=initial_input,
            generation_results={},
            ensemble_results={},
            validation_results={},
            final_output="",
            forward_data="",
            current_layer="",
            error_occurred=False,
            error_message=""
        )
        
        try:
            logger.info("LangGraph 워크플로우 실행 시작")
            
            # 그래프 실행
            final_state = self.graph.invoke(initial_state)
            
            # 결과 포맷팅
            result = {
                "success": not final_state.get("error_occurred", False),
                "layer_type": "langgraph_workflow",
                "knowledge_base": knowledge_base,
                "layer_input": initial_input,
                "layer_prompt": "LangGraph Multi-Layer Workflow",
                "node_outputs": {
                    "generation": final_state.get("generation_results", {}),
                    "ensemble": final_state.get("ensemble_results", {}),
                    "validation": final_state.get("validation_results", {}),
                    "forward_data": final_state.get("forward_data", "")
                },
                "execution_time": 0.0,  # TODO: 실제 실행 시간 측정
                "timestamp": "",
                "final_output": final_state.get("final_output", ""),
                "workflow_messages": [msg.content for msg in final_state.get("messages", [])]
            }
            
            logger.info("LangGraph 워크플로우 실행 완료")
            return result
            
        except Exception as e:
            logger.error(f"LangGraph 워크플로우 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_output": f"워크플로우 실행 실패: {str(e)}",
                "node_outputs": {"forward_data": ""}
            }


# 전역 워크플로우 엔진 인스턴스
workflow_engine = LangGraphWorkflowEngine()


def execute_langgraph_workflow(
    initial_input: str,
    knowledge_base: str,
    generation_nodes: Optional[List[Dict[str, Any]]] = None,
    ensemble_nodes: Optional[List[Dict[str, Any]]] = None,
    validation_nodes: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """LangGraph 워크플로우 실행 함수"""
    return workflow_engine.execute_workflow(
        initial_input=initial_input,
        knowledge_base=knowledge_base,
        generation_nodes=generation_nodes,
        ensemble_nodes=ensemble_nodes,
        validation_nodes=validation_nodes
    )