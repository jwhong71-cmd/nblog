#!/usr/bin/env python3
"""
Gemini API 모델 목록 확인 스크립트
"""

def test_gemini_models():
    import google.generativeai as genai
    
    # API 키 입력받기
    api_key = input("Gemini API 키를 입력하세요: ").strip()
    
    if not api_key:
        print("❌ API 키가 입력되지 않았습니다.")
        return
    
    try:
        # API 키 설정
        genai.configure(api_key=api_key)
        print("✅ API 키 설정 완료")
        
        # 사용 가능한 모델 목록 조회
        print("\n🔍 사용 가능한 모델 목록 조회 중...")
        models = list(genai.list_models())
        
        print(f"\n📋 총 {len(models)}개의 모델을 발견했습니다:")
        
        # generateContent를 지원하는 모델만 필터링
        content_models = []
        for model in models:
            print(f"\n📱 모델: {model.name}")
            print(f"   지원 메서드: {model.supported_generation_methods}")
            
            if 'generateContent' in model.supported_generation_methods:
                content_models.append(model.name)
                print(f"   ✅ generateContent 지원")
            else:
                print(f"   ❌ generateContent 미지원")
        
        print(f"\n🎯 generateContent를 지원하는 모델 ({len(content_models)}개):")
        for model_name in content_models:
            print(f"   - {model_name}")
        
        # 첫 번째 사용 가능한 모델로 테스트
        if content_models:
            test_model = content_models[0]
            print(f"\n🧪 {test_model} 모델로 테스트 중...")
            
            model = genai.GenerativeModel(test_model)
            response = model.generate_content("안녕하세요")
            
            if response and response.text:
                print(f"✅ 테스트 성공!")
                print(f"📝 응답: {response.text}")
            else:
                print("❌ 응답이 없습니다.")
        else:
            print("❌ 사용 가능한 모델이 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    test_gemini_models()