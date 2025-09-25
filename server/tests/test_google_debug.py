import os
import pytest
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

# .env 파일에서 환경변수 로드
load_dotenv()

@pytest.mark.asyncio
async def test_google_ai_basic():
    """Google AI API 기본 동작 테스트"""
    
    # API 키 확인
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
    
    print(f"✅ API 키 발견: {api_key[:10]}...")
    
    try:
        # API 설정
        genai.configure(api_key=api_key)
        print("✅ Google AI 설정 완료")
        
        # 모델 생성
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ 모델 생성 완료")
        
        # 간단한 테스트 프롬프트
        prompt = "Hello, how are you today?"
        print(f"🔄 테스트 프롬프트: {prompt}")
        
        # 스트리밍 응답 테스트
        print("🔄 스트리밍 응답 생성 중...")
        response = model.generate_content(prompt, stream=True)
        print("✅ 응답 객체 생성 완료")
        
        # 응답 처리
        chunk_count = 0
        for chunk in response:
            chunk_count += 1
            print(f"📦 청크 {chunk_count} 수신: {type(chunk)}")
            
            # 청크 구조 분석
            if hasattr(chunk, 'text'):
                print(f"✅ 텍스트: {chunk.text}")
            elif hasattr(chunk, 'candidates'):
                print(f"📋 후보 수: {len(chunk.candidates)}")
                for i, candidate in enumerate(chunk.candidates):
                    print(f"  후보 {i}: {candidate}")
            else:
                print(f"❓ 알 수 없는 청크 구조: {dir(chunk)}")
        
        print(f"✅ 스트리밍 테스트 완료 (총 {chunk_count}개 청크)")
        assert chunk_count > 0, "스트리밍 응답에서 청크를 받지 못했습니다"
        
    except Exception as e:
        import traceback
        print(f"❌ 에러 발생: {e}")
        print(f"🔍 상세 정보:\n{traceback.format_exc()}")
        raise

def test_google_ai_sync_wrapper():
    """동기 방식으로 Google AI 테스트 실행"""
    asyncio.run(test_google_ai_basic())