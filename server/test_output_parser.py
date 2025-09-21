#!/usr/bin/env python3
"""
output_parser.py 테스트 - 정규표현식 검증
"""

from src.core.output_parser import ResultParser

def test_output_patterns():
    """다양한 출력 패턴 테스트"""
    
    parser = ResultParser()
    
    # 테스트 케이스들
    test_cases = [
        # 기본 영문 태그
        {
            "name": "기본 영문 태그",
            "input": """분석 결과입니다.

<output>
요구사항 1: 시스템은 사용자 인증을 지원해야 함
요구사항 2: 데이터베이스 백업 기능 필요
</output>

추가 설명이 있습니다.""",
            "expected_output": "요구사항 1: 시스템은 사용자 인증을 지원해야 함\n요구사항 2: 데이터베이스 백업 기능 필요"
        },
        
        # 한글 태그
        {
            "name": "한글 태그",
            "input": """분석 결과입니다.

<출력>
요구사항 1: 시스템은 사용자 인증을 지원해야 함
요구사항 2: 데이터베이스 백업 기능 필요
</출력>

추가 설명이 있습니다.""",
            "expected_output": "요구사항 1: 시스템은 사용자 인증을 지원해야 함\n요구사항 2: 데이터베이스 백업 기능 필요"
        },
        
        # 대소문자 혼합
        {
            "name": "대소문자 혼합",
            "input": """분석 결과입니다.

<OUTPUT>
요구사항 1: 시스템은 사용자 인증을 지원해야 함
</OUTPUT>""",
            "expected_output": "요구사항 1: 시스템은 사용자 인증을 지원해야 함"
        },
        
        # 태그 없음
        {
            "name": "태그 없음",
            "input": "단순한 텍스트입니다.",
            "expected_output": "단순한 텍스트입니다."
        },
        
        # 멀티라인 복잡한 케이스
        {
            "name": "복잡한 멀티라인",
            "input": """분석을 시작합니다.

여러 줄의 설명이 있고...

<output>
요구사항 목록:

1. 기능적 요구사항
   - 사용자 로그인
   - 데이터 저장

2. 비기능적 요구사항
   - 성능: 응답시간 < 2초
   - 보안: HTTPS 필수

마지막 줄입니다.
</output>

후속 설명입니다.""",
            "expected_output": """요구사항 목록:

1. 기능적 요구사항
   - 사용자 로그인
   - 데이터 저장

2. 비기능적 요구사항
   - 성능: 응답시간 < 2초
   - 보안: HTTPS 필수

마지막 줄입니다."""
        }
    ]
    
    print("=== Output Parser 정규표현식 테스트 ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"테스트 {i}: {test_case['name']}")
        print("-" * 50)
        
        try:
            result = parser.parse_node_output(test_case['input'])
            
            print(f"입력 길이: {len(test_case['input'])} 글자")
            print(f"출력 길이: {len(result.output)} 글자")
            print(f"기대값과 일치: {'✅' if result.output == test_case['expected_output'] else '❌'}")
            
            if result.output != test_case['expected_output']:
                print("\n[기대값]")
                print(repr(test_case['expected_output']))
                print("\n[실제값]")
                print(repr(result.output))
            
            # 유효성 검증도 테스트
            validation = parser.validate_output_format(test_case['input'])
            print(f"유효성 검증: {'✅' if validation['valid'] else '❌'}")
            if not validation['valid']:
                print(f"오류: {validation['errors']}")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_output_patterns()