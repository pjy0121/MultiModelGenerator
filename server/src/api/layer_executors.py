"""
Layer별 실행 로직을 담당하는 모듈
"""
import time
import logging
import re
from typing import List, Tuple, Dict, Any

from ..core.layer_engine import LayerEngine
from ..core.models import NodeConfig, NodeOutput
from ..services.vector_store import VectorStore

logger = logging.getLogger(__name__)

def parse_structured_output(content: str) -> Tuple[str, str]:
    """
    LLM 출력에서 JSON 구조를 파싱하여 general_output과 forward_data를 추출
    강화된 파싱 로직으로 다양한 JSON 형태를 처리
    """
    import json
    import re
    
    if not content or not content.strip():
        print("❌ Content is empty or None")
        return "", ""
    
    print(f"🔍 Starting to parse content (length: {len(content)})")
    print(f"🔍 First 500 chars: {content[:500]}")
    logger.info("구조화된 출력 파싱 시작")
    
    try:
        # 1. 다양한 코드 블록 패턴 시도
        code_block_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json ... ```
            r'```JSON\s*(.*?)\s*```',  # ```JSON ... ```
            r'```\s*(.*?)\s*```',      # ``` ... ```
            r'`json\s*(.*?)\s*`',      # `json ... `
            r'`(.*?)`'                 # ` ... `
        ]
        
        for pattern in code_block_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                json_str = match.group(1).strip()
                
                if not json_str:
                    continue
                
                print(f"📝 Found code block: {json_str[:300]}...")
                
                # JSON 문자열 정리
                json_str = json_str.replace('\\\\\\', '\\')  # 삼중 백슬래시 정리
                json_str = json_str.replace('\\\\', '\\')    # 이중 백슬래시 정리
                json_str = re.sub(r'^\s*json\s*', '', json_str, flags=re.IGNORECASE)  # 시작 json 키워드 제거
                json_str = re.sub(r'\s*json\s*$', '', json_str, flags=re.IGNORECASE)  # 끝 json 키워드 제거
                json_str = re.sub(r'^\s*json\s*$', '', json_str, flags=re.MULTILINE | re.IGNORECASE)  # 단독 json 라인 제거
                
                # JSON 객체 추출
                first_brace = json_str.find('{')
                last_brace = json_str.rfind('}')
                
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_str = json_str[first_brace:last_brace + 1]
                    
                    # 마지막 콤마 제거 (잘못된 JSON 수정)
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    
                    try:
                        parsed_json = json.loads(json_str)
                        print(f"✅ Successfully parsed JSON from code block: {type(parsed_json)}")
                        
                        general_output = parsed_json.get("general_output", "")
                        forward_data = parsed_json.get("forward_data", "")
                        
                        # 문자열 정리
                        if general_output:
                            general_output = general_output.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                        if forward_data:
                            forward_data = forward_data.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                        
                        print(f"📦 Extracted general_output length: {len(general_output)}")
                        print(f"📦 Extracted forward_data length: {len(forward_data)}")
                        print(f"📦 forward_data preview: {forward_data[:200] if forward_data else 'EMPTY'}")
                        
                        logger.info(f"JSON 파싱 성공 - general_output: {len(general_output)}자, forward_data: {len(forward_data)}자")
                        return general_output, forward_data
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error in code block: {e}")
                        continue
        
        # 2. 전체 내용에서 JSON 객체 찾기 (코드 블록 없이)
        print("🔍 No code block found, trying to find JSON object in content")
        
        # 다양한 JSON 패턴 시도
        json_patterns = [
            r'\{\s*"general_output".*?"forward_data".*?\}',  # general_output과 forward_data 포함
            r'\{\s*"forward_data".*?"general_output".*?\}',  # 순서 바뀐 경우
            r'\{.*?"general_output".*?\}',                   # general_output만 있는 경우
            r'\{.*?"forward_data".*?\}',                     # forward_data만 있는 경우
            r'\{.*?\}'                                       # 모든 JSON 객체
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                json_str = match.group(0).strip()
                
                # JSON 정리
                json_str = json_str.replace('\\\\\\', '\\').replace('\\\\', '\\')
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # 마지막 콤마 제거
                
                print(f"📝 Found JSON object: {json_str[:300]}...")
                
                try:
                    parsed_json = json.loads(json_str)
                    general_output = parsed_json.get("general_output", "")
                    forward_data = parsed_json.get("forward_data", "")
                    
                    # 문자열 정리
                    if general_output:
                        general_output = general_output.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                    if forward_data:
                        forward_data = forward_data.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                    
                    print(f"✅ Successfully parsed JSON object")
                    print(f"📦 general_output length: {len(general_output)}")
                    print(f"📦 forward_data length: {len(forward_data)}")
                    
                    return general_output, forward_data
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error in object: {e}")
                    continue
        
        # 3. 정규식으로 키-값 쌍 직접 추출
        print("🔍 Trying regex extraction of key-value pairs")
        
        general_output_match = re.search(r'"general_output"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"', content, re.DOTALL)
        forward_data_match = re.search(r'"forward_data"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"', content, re.DOTALL)
        
        if general_output_match or forward_data_match:
            general_output = general_output_match.group(1) if general_output_match else ""
            forward_data = forward_data_match.group(1) if forward_data_match else ""
            
            # 문자열 정리
            if general_output:
                general_output = general_output.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
            if forward_data:
                forward_data = forward_data.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
            
            print(f"✅ Successfully extracted via regex")
            print(f"📦 general_output length: {len(general_output)}")
            print(f"📦 forward_data length: {len(forward_data)}")
            
            return general_output, forward_data
        
        # 4. 전체 내용이 JSON인지 마지막 확인
        trimmed_content = content.strip()
        
        # "json" 키워드 제거
        trimmed_content = re.sub(r'^\s*json\s*', '', trimmed_content, flags=re.IGNORECASE)
        trimmed_content = re.sub(r'\s*json\s*$', '', trimmed_content, flags=re.IGNORECASE)
        trimmed_content = trimmed_content.replace('\\\\\\', '\\').replace('\\\\', '\\')
        
        if trimmed_content.startswith('{') and trimmed_content.endswith('}'):
            print("🔍 Trying to parse entire content as JSON")
            
            # 마지막 콤마 제거
            trimmed_content = re.sub(r',(\s*[}\]])', r'\1', trimmed_content)
            
            try:
                parsed_json = json.loads(trimmed_content)
                general_output = parsed_json.get("general_output", "")
                forward_data = parsed_json.get("forward_data", "")
                
                # 문자열 정리
                if general_output:
                    general_output = general_output.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                if forward_data:
                    forward_data = forward_data.replace("\\n", "\n").replace('\\"', '"').replace('\\\\', '\\')
                
                print(f"✅ JSON 직접 파싱 성공")
                return general_output, forward_data
            except json.JSONDecodeError as e:
                print(f"❌ Final JSON parse failed: {e}")
        
        # 5. JSON이 아닌 경우 전체 내용을 general_output으로 처리
        print("❌ No valid JSON found. Using entire content as general_output")
        logger.warning("JSON 블록을 찾을 수 없음. 전체 내용을 general_output으로 처리")
        return content, ""
            
    except Exception as e:
        print(f"❌ Unexpected error in parse_structured_output: {e}")
        logger.error(f"구조화된 출력 파싱 중 예외 발생: {e}")
        return content, ""


def execute_generation_layer(nodes: List[NodeConfig], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Generation Layer 실행
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 모든 노드의 forward_data를 append한 결과
    }
    """
    logger.info(f"Generation Layer 실행 시작: {len(nodes)}개 노드")
    
    engine = LayerEngine()
    result = {}
    forward_data_list = []
    
    # 각 노드 병렬 실행
    for node in nodes:
        try:
            node_output = engine.execute_node(node, layer_input, context_chunks)
            
            # 구조화된 출력 파싱
            general_output, forward_data = parse_structured_output(node_output.requirements)
            
            # 노드별 general_output 저장
            result[f"node{node.id}"] = general_output
            
            # forward_data 수집 (append 방식)
            if forward_data.strip():
                forward_data_list.append(forward_data.strip())
                
            logger.info(f"노드 {node.id} 실행 완료")
            
        except Exception as e:
            logger.error(f"노드 {node.id} 실행 실패: {str(e)}")
            result[f"node{node.id}"] = f"실행 실패: {str(e)}"
    
    # 모든 forward_data를 append하여 결합
    result["forward_data"] = "\n\n".join(forward_data_list)
    
    logger.info(f"Generation Layer 완료: {len(forward_data_list)}개 노드 결과 결합")
    return result


def execute_ensemble_layer(nodes: List[NodeConfig], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Ensemble Layer 실행
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 모든 노드의 forward_data를 append한 결과
    }
    """
    logger.info(f"Ensemble Layer 실행 시작: {len(nodes)}개 노드")
    
    engine = LayerEngine()
    result = {}
    forward_data_list = []
    
    # 각 노드 병렬 실행
    for node in nodes:
        try:
            node_output = engine.execute_node(node, layer_input, context_chunks)
            
            # 구조화된 출력 파싱
            general_output, forward_data = parse_structured_output(node_output.requirements)
            
            # 노드별 general_output 저장
            result[f"node{node.id}"] = general_output
            
            # forward_data 수집 (append 방식)
            if forward_data.strip():
                forward_data_list.append(forward_data.strip())
                
            logger.info(f"노드 {node.id} 실행 완료")
            
        except Exception as e:
            logger.error(f"노드 {node.id} 실행 실패: {str(e)}")
            result[f"node{node.id}"] = f"실행 실패: {str(e)}"
    
    # 모든 forward_data를 append하여 결합
    result["forward_data"] = "\n\n".join(forward_data_list)
    
    logger.info(f"Ensemble Layer 완료: {len(forward_data_list)}개 노드 결과 결합")
    return result


def execute_validation_layer(nodes: List[NodeConfig], layer_input: str, context_chunks: List[str]) -> Dict[str, Any]:
    """
    Validation Layer 실행
    Returns: {
        "node1": node1의 general_output,
        "node2": node2의 general_output,
        ...
        "forward_data": 마지막 노드의 forward_data (덮어쓰기 방식)
    }
    """
    print(f"🔍 Validation Layer Input: {layer_input[:200] if layer_input else 'EMPTY'}")
    logger.info(f"Validation Layer 실행 시작: {len(nodes)}개 노드")
    
    engine = LayerEngine()
    result = {}
    final_forward_data = ""
    
    # 각 노드 순차 실행 (Validation은 순서가 중요할 수 있음)
    for node in nodes:
        try:
            print(f"🚀 Executing Validation node {node.id}")
            node_output = engine.execute_node(node, layer_input, context_chunks)
            print(f"📝 Raw node output length: {len(node_output.requirements)}")
            print(f"📝 Raw node output preview: {node_output.requirements[:300]}")
            
            # 구조화된 출력 파싱
            general_output, forward_data = parse_structured_output(node_output.requirements)
            print(f"📦 Parsed general_output length: {len(general_output)}")
            print(f"📦 Parsed forward_data length: {len(forward_data)}")
            print(f"📦 forward_data preview: {forward_data[:100] if forward_data else 'EMPTY'}")
            
            # 노드별 general_output 저장
            result[f"node{node.id}"] = general_output
            
            # forward_data 덮어쓰기 (마지막 노드 결과만 남김)
            if forward_data.strip():
                final_forward_data = forward_data.strip()
                print(f"✅ Updated final_forward_data from node {node.id}")
                
            logger.info(f"노드 {node.id} 실행 완료")
            
        except Exception as e:
            print(f"❌ Node {node.id} execution failed: {str(e)}")
            logger.error(f"노드 {node.id} 실행 실패: {str(e)}")
            result[f"node{node.id}"] = f"실행 실패: {str(e)}"
    
    # 마지막 노드의 forward_data만 사용
    result["forward_data"] = final_forward_data
    print(f"🎯 Final result forward_data length: {len(final_forward_data)}")
    print(f"🎯 Final result keys: {list(result.keys())}")
    
    logger.info(f"Validation Layer 완료: 최종 forward_data 길이 {len(final_forward_data)}")
    return result


class ValidationLayerExecutor:
    """Validation Layer 실행을 담당하는 클래스"""
    
    def __init__(self):
        self.engine = LayerEngine()
    
    def enhance_context_for_validation(self, layer_input: str, knowledge_base: str, 
                                     existing_chunks: List[str], top_k: int = 10) -> List[str]:
        """
        Validation을 위한 컨텍스트 확장
        """
        try:
            logger.info(f"🔍 Validation Layer 컨텍스트 확장 시작 - 기존 청크: {len(existing_chunks)}개")
            
            vector_store = VectorStore(knowledge_base)
            
            # 입력 데이터에서 키워드 추출하여 추가 검색
            requirement_texts = re.findall(r'\|\s*[^|]+\s*\|\s*([^|]+)\s*\|', layer_input)
            search_terms = []
            
            logger.info(f"입력 데이터에서 {len(requirement_texts)}개 요구사항 텍스트 추출")
            
            # 요구사항에서 중요한 키워드들 추출
            for req_text in requirement_texts[:3]:  # 처음 3개 요구사항만 사용
                if req_text.strip() and len(req_text.strip()) > 10:
                    search_term = req_text.strip()[:50]  # 처음 50자만 사용
                    search_terms.append(search_term)
                    logger.info(f"검색어 추가: {search_term}")
            
            # 각 검색어로 컨텍스트 검색
            all_chunks = set(existing_chunks)
            for i, term in enumerate(search_terms):
                if term:
                    logger.info(f"검색어 {i+1}/{len(search_terms)} 실행: '{term[:30]}...'")
                    chunks = vector_store.search_similar_chunks(term, top_k=top_k)
                    chunk_count_before = len(all_chunks)
                    all_chunks.update(chunks)
                    logger.info(f"새로 추가된 청크: {len(all_chunks) - chunk_count_before}개")
            
            enhanced_chunks = list(all_chunks)[:20]  # 최대 20개 청크
            logger.info(f"Validation을 위한 최종 컨텍스트: {len(enhanced_chunks)}개 청크")
            
            return enhanced_chunks
            
        except Exception as e:
            logger.error(f"Validation 컨텍스트 확장 실패: {e}")
            return existing_chunks
    
    def execute(self, nodes: List[NodeConfig], layer_input: str, context_chunks: List[str]) -> Tuple[List[NodeOutput], List[str], List[Dict]]:
        """
        Validation Layer 실행 - 순차적으로 노드 실행하여 검증 과정 진행
        """
        logger.info(f"Validation Layer 실행 시작: {len(nodes)}개 노드")
        
        outputs = []
        failed_nodes = []
        validation_steps = []
        current_input = layer_input
        
        # 노드를 순차적으로 실행
        for i, node in enumerate(nodes):
            try:
                logger.info(f"Validation 노드 {i+1}/{len(nodes)} 실행 중: {node.id}")
                
                # 안전한 노드 실행
                node_output = self.engine.execute_node(node, current_input, context_chunks)
                if not node_output:
                    logger.error(f"노드 {node.id}에서 None 결과 반환")
                    failed_nodes.append(node.id)
                    continue
                    
                outputs.append(node_output)
                
                # 검증 단계 기록
                validation_step = {
                    "step": i + 1,
                    "node_id": node.id,
                    "model_type": getattr(node, 'model_type', 'unknown'),
                    "input": current_input[:200] + "..." if len(current_input) > 200 else current_input,
                    "output": (node_output.requirements[:200] + "..." if len(node_output.requirements) > 200 else node_output.requirements) if hasattr(node_output, 'requirements') and node_output.requirements else "Empty output",
                    "execution_time": getattr(node_output, 'execution_time', 0)
                }
                validation_steps.append(validation_step)
                
                # 다음 노드를 위해 현재 출력을 입력으로 설정
                if hasattr(node_output, 'requirements') and node_output.requirements:
                    current_input = node_output.requirements
                else:
                    logger.warning(f"노드 {node.id}에서 유효한 requirements 출력이 없음")
                
                logger.info(f"Validation 노드 {node.id} 실행 완료")
                
            except Exception as e:
                failed_nodes.append(node.id)
                logger.error(f"Validation 노드 {node.id} 실행 실패: {str(e)}")
                logger.error(f"노드 실행 오류 상세: {repr(e)}")
        
        if not outputs:
            logger.error("모든 Validation 노드 실행이 실패했습니다.")
        
        return outputs, failed_nodes, validation_steps
    
    def combine_results(self, outputs: List[NodeOutput]) -> str:
        """Validation Layer 결과 결합 - 마지막 노드의 출력이 최종 결과"""
        if not outputs:
            logger.error("Validation Layer: 결합할 출력이 없습니다.")
            return "모든 노드 실행이 실패했습니다."
        
        last_output = outputs[-1]
        if not hasattr(last_output, 'requirements') or not last_output.requirements:
            logger.error("Validation Layer: 마지막 노드의 출력이 비어있습니다.")
            return "검증 결과를 생성할 수 없습니다."
        
        logger.info(f"Validation Layer 결과 결합 완료: {len(last_output.requirements)}자")
        return last_output.requirements
    
    def extract_requirements_analysis(self, final_output: str, original_input: str) -> Tuple[List[str], List[str]]:
        """
        Validation Layer 전용: 검증 결과에서 필터링된 요구사항과 제거된 요구사항을 추출
        (Ensemble Layer는 요구사항을 제거하지 않고 검증 상태만 변경함)
        """
        filtered_requirements = []
        removed_requirements = []
        
        try:
            logger.info(f"요구사항 분석 시작 - final_output 길이: {len(final_output)}")
            
            # 필터링된 요구사항 표 추출
            filtered_table_match = re.search(r'\*\*필터링된 요구사항 표:\*\*(.*?)(?=\*\*제거된 요구사항:|\Z)', final_output, re.DOTALL)
            if filtered_table_match:
                filtered_table = filtered_table_match.group(1).strip()
                logger.info(f"필터링된 요구사항 표 찾음: {len(filtered_table)}자")
                
                table_rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', filtered_table)
                logger.info(f"테이블 행 추출: {len(table_rows)}개")
                
                for i, row in enumerate(table_rows):
                    try:
                        if len(row) >= 4 and row[0].strip() and not row[0].strip().startswith('ID') and not row[0].strip().startswith('-'):
                            req_id = row[0].strip()
                            req_text = row[1].strip()
                            source = row[2].strip() if len(row) > 2 else ""
                            status = row[3].strip() if len(row) > 3 else ""
                            if req_id and req_text:
                                filtered_requirements.append(f"{req_id}: {req_text} (출처: {source}, 상태: {status})")
                                logger.debug(f"필터링된 요구사항 {i+1} 추가: {req_id}")
                    except (IndexError, AttributeError) as row_e:
                        logger.warning(f"테이블 행 {i+1} 처리 중 오류: {row_e}")
                        continue
            else:
                logger.warning("필터링된 요구사항 표를 찾을 수 없음")
            
            # 제거된 요구사항 추출
            removed_match = re.search(r'\*\*제거된 요구사항:\*\*(.*?)$', final_output, re.DOTALL)
            if removed_match:
                removed_section = removed_match.group(1).strip()
                logger.info(f"제거된 요구사항 섹션 찾음: {len(removed_section)}자")
                
                removed_lines = [line.strip() for line in removed_section.split('\n') if line.strip() and not line.strip().startswith('(')]
                for line in removed_lines:
                    if line and '-' in line:
                        removed_requirements.append(line)
                        logger.debug(f"제거된 요구사항 추가: {line[:50]}...")
            else:
                logger.warning("제거된 요구사항 섹션을 찾을 수 없음")
            
            # 통계 로깅
            try:
                original_table_rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', original_input)
                original_count = len([row for row in original_table_rows if len(row) >= 2 and row[0].strip() and not row[0].strip().startswith('ID') and not row[0].strip().startswith('-')])
                filtered_count = len(filtered_requirements)
                
                logger.info(f"Validation 필터링 결과: 원본 {original_count}개 → 필터링 후 {filtered_count}개 (제거: {original_count - filtered_count}개)")
            except Exception as stat_e:
                logger.error(f"통계 계산 중 오류: {stat_e}")
            
        except Exception as e:
            logger.error(f"요구사항 분석 중 전체 오류 발생: {e}")
            logger.error(f"final_output 내용 (처음 500자): {final_output[:500] if final_output else 'None'}")
            # 빈 결과 반환하여 500 에러 방지
            return [], []
        
        return filtered_requirements, removed_requirements


class LayerExecutorFactory:
    """Layer별 실행기를 생성하는 팩토리 클래스"""
    
    @staticmethod
    def get_executor(layer_type: str):
        """Layer 타입에 따른 실행기 반환"""
        if layer_type == "generation":
            return GenerationLayerExecutor()
        elif layer_type == "ensemble":
            return EnsembleLayerExecutor()
        elif layer_type == "validation":
            return ValidationLayerExecutor()
        else:
            raise ValueError(f"지원하지 않는 Layer 타입: {layer_type}")