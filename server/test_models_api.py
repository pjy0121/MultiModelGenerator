"""
모델 목록 API 테스트
"""

import asyncio
import aiohttp

async def test_models_api():
    """모델 목록 API 테스트"""
    print("=== 모델 목록 API 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    providers = ["google", "openai", "internal"]
    
    async with aiohttp.ClientSession() as session:
        for provider in providers:
            print(f"\n--- {provider} 모델 목록 테스트 ---")
            try:
                async with session.get(f'{base_url}/available-models/{provider}', timeout=10) as resp:
                    if resp.status == 200:
                        models = await resp.json()
                        print(f"✅ {provider} 성공!")
                        print(f"모델 수: {len(models.get('models', []))}")
                        if models.get('models'):
                            print(f"첫 번째 모델: {models['models'][0]}")
                    else:
                        error_text = await resp.text()
                        print(f"❌ {provider} 실패: {resp.status}")
                        print(f"에러 내용: {error_text}")
            except Exception as e:
                print(f"❌ {provider} 예외: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_models_api())