#!/usr/bin/env python3
"""Google AI API 테스트 스크립트"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_google_api():
    """Google AI API 연결 테스트"""
    
    # API 키 확인
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
        
    print(f"🔑 Google API Key 발견 (길이: {len(api_key)})")
    
    # Google AI 라이브러리 import 테스트
    try:
        import google.generativeai as genai
        print("✅ google.generativeai 라이브러리 import 성공")
        print(f"📋 라이브러리 버전: {getattr(genai, '__version__', 'Unknown')}")
    except ImportError as e:
        print(f"❌ google.generativeai 라이브러리 import 실패: {e}")
        return False
    
    # API 키 설정
    try:
        genai.configure(api_key=api_key)
        print("✅ API 키 설정 완료")
    except Exception as e:
        print(f"❌ API 키 설정 실패: {e}")
        return False
    
    # 모델 목록 가져오기 테스트
    try:
        print("🔍 모델 목록 조회 중...")
        models = list(genai.list_models())
        print(f"📋 총 {len(models)}개 모델 발견")
        
        if len(models) == 0:
            print("⚠️ 모델이 없습니다. API 키를 확인해주세요.")
            return False
        
        # 처음 5개 모델 정보 출력
        for i, model in enumerate(models[:5]):
            print(f"  {i+1}. {model.name}")
            print(f"     지원 메서드: {getattr(model, 'supported_generation_methods', 'Unknown')}")
            
        # generateContent 지원 모델 찾기
        content_models = []
        for model in models:
            if hasattr(model, 'supported_generation_methods') and 'generateContent' in model.supported_generation_methods:
                content_models.append(model.name.replace('models/', ''))
        
        print(f"📋 generateContent 지원 모델: {len(content_models)}개")
        for model_name in content_models[:10]:  # 처음 10개만 출력
            print(f"  - {model_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 모델 목록 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Google AI API 테스트 시작")
    success = test_google_api()
    
    if success:
        print("🎉 Google AI API 테스트 성공!")
    else:
        print("💥 Google AI API 테스트 실패!")