#!/usr/bin/env python3
"""
Output Parser 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.output_parser import ResultParser

def test_parser():
    parser = ResultParser()
    
    # 테스트 케이스 1: 정상적인 output 태그
    test1 = """
    이것은 마크다운 형식의 응답입니다.
    
    ## 요구사항 분석 결과
    
    다음과 같은 요구사항들이 추출되었습니다:
    
    <output>
    - REQ-001: 사용자 인증 기능
    - REQ-002: 데이터 백업 기능
    - REQ-003: 실시간 알림 시스템
    </output>
    
    추가 설명이 여기에 있습니다.
    """
    
    # 테스트 케이스 2: output 태그가 없는 경우
    test2 = """
    이것은 output 태그가 없는 응답입니다.
    단순한 텍스트 응답입니다.
    """
    
    # 테스트 케이스 3: 여러 줄의 output 태그
    test3 = """
    # 검증 결과
    
    <output>
    ## 검증된 요구사항
    
    ### 기능적 요구사항
    1. 로그인/로그아웃 기능
    2. 프로필 관리 기능
    
    ### 비기능적 요구사항
    1. 응답시간 < 2초
    2. 동시 사용자 1000명 지원
    </output>
    """
    
    print("=== Output Parser 테스트 ===\n")
    
    for i, test_case in enumerate([test1, test2, test3], 1):
        print(f"테스트 케이스 {i}:")
        try:
            result = parser.parse_node_output(test_case)
            print(f"  성공!")
            print(f"  Description 길이: {len(result.description)} 글자")
            print(f"  Output 길이: {len(result.output)} 글자")
            print(f"  Output 내용: {repr(result.output[:100])}...")
            print()
        except Exception as e:
            print(f"  실패: {e}")
            print()
    
    # 검증 테스트
    print("=== 검증 테스트 ===\n")
    
    for i, test_case in enumerate([test1, test2, test3], 1):
        print(f"검증 케이스 {i}:")
        validation = parser.validate_output_format(test_case)
        print(f"  유효성: {validation['valid']}")
        if validation['errors']:
            print(f"  오류: {validation['errors']}")
        print()

if __name__ == "__main__":
    test_parser()