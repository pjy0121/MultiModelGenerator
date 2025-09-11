import time
from typing import List, Dict, Any
from openai import OpenAI
from config import Config
from models import WorkflowConfig, NodeConfig, NodeOutput, ModelType, LayerType

class WorkflowEngine:
    """워크플로우 실행 엔진"""
    
    def __init__(self):
        self.perplexity_client = OpenAI(
            api_key=Config.PERPLEXITY_API_KEY,
            base_url=Config.PERPLEXITY_BASE_URL
        )
    
    def execute_node(self, node: NodeConfig, input_data: str, context_chunks: List[str]) -> NodeOutput:
        """개별 노드 실행"""
        start_time = time.time()
        
        try:
            if node.model_type in [ModelType.PERPLEXITY_SONAR_PRO, ModelType.PERPLEXITY_SONAR_MEDIUM]:
                model_name = "sonar-pro" if node.model_type == ModelType.PERPLEXITY_SONAR_PRO else "sonar-medium"
                result = self._execute_perplexity_node(node, input_data, context_chunks, model_name)
            else:
                # OpenAI 모델들은 향후 확장용
                result = "OpenAI 모델은 아직 구현되지 않았습니다."
            
            execution_time = time.time() - start_time
            
            return NodeOutput(
                node_id=node.id,
                model_type=node.model_type.value,
                requirements=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return NodeOutput(
                node_id=node.id,
                model_type=node.model_type.value,
                requirements=f"오류 발생: {str(e)}",
                execution_time=execution_time
            )
    
    def _execute_perplexity_node(self, node: NodeConfig, input_data: str, context_chunks: List[str], model_name: str) -> str:
        """Perplexity 모델 노드 실행"""
        context = "\n\n".join(context_chunks) if context_chunks else ""
        
        # 프롬프트에서 변수 치환
        formatted_prompt = node.prompt.format(
            input_data=input_data,
            context=context
        )
        
        response = self.perplexity_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "당신은 기술 사양서 분석 전문가입니다. 모든 출력은 마크다운 표 형식의 요구사항 목록이어야 합니다."},
                {"role": "user", "content": formatted_prompt}
            ],
            temperature=0.1,
            max_tokens=2500
        )
        
        return response.choices[0].message.content
    
    def execute_workflow(self, workflow_config: WorkflowConfig, keyword: str, context_chunks: List[str]) -> Dict[str, Any]:
        """전체 워크플로우 실행"""
        start_time = time.time()
        node_outputs = []
        
        # 1. Generation Layer 실행
        generation_results = []
        for node in workflow_config.generation_nodes:
            output = self.execute_node(node, keyword, context_chunks)
            node_outputs.append(output)
            generation_results.append(output.requirements)
        
        # 2. Ensemble Layer 실행
        ensemble_input = "\n\n=== 다음 결과들을 통합하세요 ===\n\n" + "\n\n".join(generation_results)
        ensemble_output = self.execute_node(workflow_config.ensemble_node, ensemble_input, context_chunks)
        node_outputs.append(ensemble_output)
        
        # 3. Validation Layer 실행
        validation_input = ensemble_output.requirements
        for node in workflow_config.validation_nodes:
            validation_output = self.execute_node(node, validation_input, context_chunks)
            node_outputs.append(validation_output)
            validation_input = validation_output.requirements  # 다음 노드의 입력으로 사용
        
        total_time = time.time() - start_time
        
        # 최종 결과는 마지막 validation 노드의 출력
        final_result = validation_input if workflow_config.validation_nodes else ensemble_output.requirements
        
        return {
            "final_requirements": final_result,
            "node_outputs": node_outputs,
            "total_execution_time": total_time
        }
