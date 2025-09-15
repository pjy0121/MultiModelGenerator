#!/usr/bin/env python3
"""
MultiModelGenerator Python Client
GET 요청 기반 단순 워크플로우 실행 클라이언트
"""

import requests
import json
import time
import argparse
from typing import Dict, Any
from datetime import datetime
import os


class MultiModelGeneratorClient:
    """MultiModelGenerator Python Client"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        """
        클라이언트 초기화
        
        Args:
            base_url: 서버 기본 URL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def get_knowledge_bases(self) -> Dict[str, Any]:
        """사용 가능한 지식 베이스 목록 조회"""
        try:
            response = self.session.get(f"{self.base_url}/knowledge-bases")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 지식 베이스 목록 조회 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_models(self) -> Dict[str, Any]:
        """사용 가능한 LLM 모델 목록 조회"""
        try:
            response = self.session.get(f"{self.base_url}/models/available")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 모델 목록 조회 실패: {e}")
            return {"models": [], "error": str(e)}
    
    def execute_workflow(
        self,
        knowledge_base: str,
        keyword: str,
        search_intensity: str = "medium",
        generation_nodes: int = 2,
        ensemble_nodes: int = 1,
        validation_nodes: int = 1,
        model_name: str = "gpt-3.5-turbo",
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """
        전체 워크플로우 실행
        
        Args:
            knowledge_base: 사용할 지식 베이스 이름
            keyword: 검색 키워드
            search_intensity: 검색 강도 (low/medium/high)
            generation_nodes: Generation 레이어 노드 개수
            ensemble_nodes: Ensemble 레이어 노드 개수  
            validation_nodes: Validation 레이어 노드 개수
            model_name: 사용할 LLM 모델명
            provider: LLM 제공자
            
        Returns:
            Dict: 실행 결과
        """
        try:
            print(f"🚀 워크플로우 실행 시작...")
            print(f"   - 지식 베이스: {knowledge_base}")
            print(f"   - 키워드: {keyword}")
            print(f"   - 검색 강도: {search_intensity}")
            print(f"   - 노드 구성: Gen({generation_nodes}) → Ens({ensemble_nodes}) → Val({validation_nodes})")
            print(f"   - 모델: {provider}/{model_name}")
            print()
            
            # GET 파라미터 구성
            params = {
                "knowledge_base": knowledge_base,
                "keyword": keyword,
                "search_intensity": search_intensity,
                "generation_nodes": generation_nodes,
                "ensemble_nodes": ensemble_nodes,
                "validation_nodes": validation_nodes,
                "model_name": model_name,
                "provider": provider
            }
            
            start_time = time.time()
            
            # GET 요청 실행
            response = self.session.get(f"{self.base_url}/simple-workflow", params=params)
            response.raise_for_status()
            
            result = response.json()
            execution_time = time.time() - start_time
            
            print(f"✅ 워크플로우 완료 (클라이언트 측 실행시간: {execution_time:.2f}초)")
            print(f"   서버 측 실행시간: {result.get('total_execution_time', 0):.2f}초")
            print()
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP 요청 실패: {e}")
            return {"success": False, "error": f"HTTP 요청 실패: {str(e)}"}
        except Exception as e:
            print(f"❌ 워크플로우 실행 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def save_result_to_file(self, result: Dict[str, Any], keyword: str, knowledge_base: str):
        """validation layer 결과를 로컬 파일로 저장"""
        if not result.get("success", False):
            print(f"❌ 실행 실패로 인해 파일 저장 불가: {result.get('error', '알 수 없는 오류')}")
            return
        
        # execution_summary에서 validation 결과 추출
        summary = result.get("execution_summary", {})
        layer_results = summary.get("layer_results", {})
        validation_output = layer_results.get("validation_output", "")
        
        # 만약 validation_output이 비어있다면 final_result에서 가져오기 시도
        if not validation_output:
            validation_output = result.get("final_result", "")
            if not validation_output:
                print("❌ Validation layer 결과가 없습니다.")
                return
        
        # 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_keyword = safe_keyword.replace(' ', '_')
        filename = f"validation_result_{knowledge_base}_{safe_keyword}_{timestamp}.txt"
        
        try:
            # 파일 저장
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Validation Layer 결과\n")
                f.write(f"===================\n\n")
                f.write(f"지식 베이스: {knowledge_base}\n")
                f.write(f"검색 키워드: {keyword}\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 실행시간: {result.get('total_execution_time', 0):.2f}초\n\n")
                f.write("Validation 결과:\n")
                f.write("-" * 50 + "\n")
                f.write(validation_output)
                f.write("\n")
            
            # 파일 경로 출력
            full_path = os.path.abspath(filename)
            print(f"💾 Validation 결과가 저장되었습니다:")
            print(f"   📁 파일: {filename}")
            print(f"   📂 경로: {full_path}")
            print()
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")

    def print_result_table(self, result: Dict[str, Any]):
        """결과 마크다운 표 출력 - 더 이상 사용하지 않음"""
        pass
    
    def print_execution_summary(self, result: Dict[str, Any]):
        """실행 요약 정보 출력"""
        if not result.get("success", False):
            return
        
        summary = result.get("execution_summary", {})
        if not summary:
            return
        
        print("📊 실행 요약:")
        print("-" * 50)
        print(f"지식 베이스: {summary.get('knowledge_base', 'N/A')}")
        print(f"검색 키워드: {summary.get('keyword', 'N/A')}")
        print(f"검색 강도: {summary.get('search_intensity', 'N/A')} (top_k: {summary.get('top_k_used', 'N/A')})")
        
        nodes = summary.get('nodes_executed', {})
        print(f"실행된 노드: Gen({nodes.get('generation', 0)}) → Ens({nodes.get('ensemble', 0)}) → Val({nodes.get('validation', 0)})")
        
        model_info = summary.get('model_info', {})
        print(f"사용 모델: {model_info.get('provider', 'N/A')}/{model_info.get('model_name', 'N/A')}")
        
        print(f"총 실행시간: {result.get('total_execution_time', 0):.2f}초")
        print("-" * 50)
        print()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="MultiModelGenerator Python Client")
    parser.add_argument("--server", default="http://localhost:5001", help="서버 URL")
    parser.add_argument("--kb", "--knowledge-base", help="지식 베이스 이름")
    parser.add_argument("--keyword", help="검색 키워드")
    parser.add_argument("--intensity", choices=["low", "medium", "high"], default="medium", help="검색 강도")
    parser.add_argument("--gen-nodes", type=int, default=2, help="Generation 노드 개수")
    parser.add_argument("--ens-nodes", type=int, default=1, help="Ensemble 노드 개수")
    parser.add_argument("--val-nodes", type=int, default=1, help="Validation 노드 개수")
    parser.add_argument("--model", default="gemini-2.0-flash", help="LLM 모델명")
    parser.add_argument("--provider", choices=["openai", "google"], default="google", help="LLM 제공자")
    parser.add_argument("--list-kb", action="store_true", help="지식 베이스 목록만 조회")
    parser.add_argument("--list-models", action="store_true", help="모델 목록만 조회")
    
    args = parser.parse_args()
    
    # 클라이언트 초기화
    client = MultiModelGeneratorClient(args.server)
    
    # 지식 베이스 목록 조회
    if args.list_kb:
        print("📚 지식 베이스 목록:")
        kb_result = client.get_knowledge_bases()
        if kb_result.get("success", False):
            for kb in kb_result.get("knowledge_bases", []):
                status = "✅" if kb.get("exists", False) else "❌"
                print(f"   {status} {kb.get('name', 'N/A')} ({kb.get('chunk_count', 0)} chunks)")
        else:
            print(f"   ❌ 조회 실패: {kb_result.get('error', 'Unknown error')}")
        return
    
    # 모델 목록 조회
    if args.list_models:
        print("🤖 사용 가능한 모델:")
        models_result = client.get_available_models()
        for model in models_result.get("models", []):
            status = "✅" if not model.get("disabled", True) else "❌"
            print(f"   {status} {model.get('provider', 'N/A')}/{model.get('model_type', 'N/A')} - {model.get('label', 'N/A')}")
        return
    
    # 워크플로우 실행을 위한 필수 인수 확인
    if not args.kb or not args.keyword:
        parser.error("워크플로우 실행을 위해서는 --kb와 --keyword 인수가 필요합니다.")
    
    # 워크플로우 실행
    result = client.execute_workflow(
        knowledge_base=args.kb,
        keyword=args.keyword,
        search_intensity=args.intensity,
        generation_nodes=args.gen_nodes,
        ensemble_nodes=args.ens_nodes,
        validation_nodes=args.val_nodes,
        model_name=args.model,
        provider=args.provider
    )
    
    # 결과 출력
    client.print_execution_summary(result)
    client.save_result_to_file(result, args.keyword, args.kb)


if __name__ == "__main__":
    main()