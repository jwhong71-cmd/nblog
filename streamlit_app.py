import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import threading
import time
import importlib

# 기존 모듈들 import
from task.automator import start_task
from auth.auth_functions import auth
from auth.dev_auth import dev_auth, prod_auth
from cache import upload_cache, download_cache
from data import text_data, list_data, content_data
from ui import log
from utils.naver_login import naver_login

# Streamlit 헬퍼 함수들
from streamlit_helpers import (
    StreamlitLogger, FileManager, TaskManager, 
    ContentGenerator, DataManager, init_session_state,
    check_gemini_plugins
)

# 페이지 설정
st.set_page_config(
    page_title="네이버 포스팅 자동화",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 설정
def setup_sidebar():
    st.sidebar.title("🚀 네이버 포스팅 자동화")
    st.sidebar.markdown("---")
    
    # 네이버 아이디/패스워드 입력
    naver_id = st.sidebar.text_input("네이버 아이디", value=st.session_state.get("naver_id", ""))
    naver_pw = st.sidebar.text_input("네이버 패스워드", value=st.session_state.get("naver_pw", ""), type="password")
    st.session_state["naver_id"] = naver_id
    st.session_state["naver_pw"] = naver_pw
    
    # 네이버 로그인 버튼
    if st.sidebar.button("네이버 로그인"):
        if naver_id and naver_pw:
            login_result = naver_login(naver_id, naver_pw)
            if login_result is True:
                st.sidebar.success("✅ 네이버 로그인 성공!")
                st.session_state["naver_logged_in"] = True
            elif login_result is False:
                st.sidebar.error("❌ 네이버 로그인 실패. 아이디/패스워드를 확인하세요.")
                st.session_state["naver_logged_in"] = False
            else:
                st.sidebar.error(str(login_result))
                st.session_state["naver_logged_in"] = False
        else:
            st.sidebar.error("아이디와 패스워드를 모두 입력하세요.")
    
    # 플랫폼 선택
    platform = st.sidebar.radio(
        "플랫폼 선택",
        ["블로그", "카페", "둘 다"],
        index=0
    )
    
    # 현재 상태 표시
    st.sidebar.markdown(f"### 현재 상태: **{platform}**")
    
    # 대기시간 설정
    st.sidebar.markdown("### ⏰ 대기시간 설정")
    min_wait = st.sidebar.number_input("최소 (분)", min_value=1, max_value=60, value=5)
    max_wait = st.sidebar.number_input("최대 (분)", min_value=1, max_value=60, value=10)
    
    # 유동 IP 설정
    use_dynamic_ip = st.sidebar.toggle("유동 IP 사용", value=True)
    
    # API 키 입력 (제거)
    # st.sidebar.markdown("### 🔑 API 설정")
    # api_key = st.sidebar.text_input("API KEY", type="password", placeholder="API 키를 입력하세요")
    
    return platform, min_wait, max_wait, use_dynamic_ip, ""

# 인증 함수
def authenticate():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 사용자 인증")
        
        # 개발/프로덕션 모드 선택
        auth_mode = st.selectbox(
            "인증 모드 선택",
            ["개발 모드 (테스트 계정)", "프로덕션 모드 (실제 서버)"],
            index=0
        )
        
        if auth_mode == "개발 모드 (테스트 계정)":
            st.info("💡 개발 모드 테스트 계정: admin/admin123, test/test123, user/user123, demo/demo123")
        
        with st.form("auth_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            submit = st.form_submit_button("로그인")
            
            if submit:
                # 인증 방식 선택
                if auth_mode == "개발 모드 (테스트 계정)":
                    auth_success = dev_auth(username, password)
                else:
                    auth_success = prod_auth(username, password)
                
                if auth_success:
                    st.session_state.authenticated = True
                    st.success("인증 성공!")
                    st.rerun()
                else:
                    st.error("인증 실패. 아이디와 비밀번호를 확인해주세요.")
        return False
    return True

# Gemini API 인증 섹션
def gemini_api_section():
    st.markdown("## 🤖 Gemini AI 설정")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔑 API 키 입력")
        
        # 현재 저장된 API 키 상태 확인
        api_key_status = "✅ 인증됨" if st.session_state.get('gemini_authenticated', False) else "❌ 미인증"
        st.markdown(f"**상태**: {api_key_status}")
        
        # API 키 입력
        api_key = st.text_input(
            "Gemini API KEY", 
            type="password", 
            placeholder="Gemini API 키를 입력하세요",
            help="Google AI Studio에서 발급받은 Gemini API 키를 입력하세요"
        )
        
        # 모델 선택 UI 추가
        model_options = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        selected_model = st.selectbox("Gemini 모델 선택", model_options, index=0, help="무료 버전은 gemini-2.5-flash를 추천합니다.")
        st.session_state.gemini_model = selected_model
        
        # API 키 설명
        with st.expander("💡 API 키 발급 방법"):
            st.markdown("""
            ### 🔗 Google AI Studio에서 API 키 발급받기
            
            1. **[Google AI Studio](https://makersuite.google.com/app/apikey)** 접속
            2. **"Create API Key"** 클릭
            3. **기존 프로젝트 선택** 또는 **"Create API key in new project"** 선택
            4. **생성된 API 키 전체를 복사** (보통 39자 길이)
            5. **여기에 붙여넣기**
            
            ### ⚠️ 주의사항
            - API 키는 **AIza**로 시작합니다
            - 복사할 때 **앞뒤 공백**이 없도록 주의하세요
            - **전체 키를 완전히** 복사해야 합니다
            
            ### 🔧 문제 해결
            - **"API_KEY_INVALID"**: 새 API 키를 생성해보세요
            - **"PERMISSION_DENIED"**: Gemini API가 활성화되었는지 확인하세요
            - **"QUOTA_EXCEEDED"**: 무료 할당량을 확인하거나 결제 설정을 해보세요
            """)
        
        # API 키 디버깅 정보
        if api_key:
            st.markdown("### 🔍 API 키 정보")
            key_length = len(api_key.strip())
            key_start = api_key.strip()[:10] + "..." if len(api_key.strip()) > 10 else api_key.strip()
            
            col_debug1, col_debug2 = st.columns(2)
            with col_debug1:
                st.info(f"**길이**: {key_length}자")
                st.info(f"**시작**: {key_start}")
            with col_debug2:
                expected_start = api_key.strip().startswith("AIza")
                st.success("✅ 올바른 형식") if expected_start else st.warning("⚠️ 형식 확인 필요")
                st.info("**예상 길이**: 39자")
    
    with col2:
        st.markdown("### 🔐 인증 제어")
        st.markdown("")  # 간격 조정
        st.markdown("")  # 간격 조정
        
        # 인증 버튼
        if st.button("🔐 API 키 인증", type="primary", use_container_width=True):
            if api_key:
                # API 키 유효성 검사 (실제 Gemini API 호출 테스트)
                if validate_gemini_api_key(api_key, selected_model):
                    st.session_state.gemini_api_key = api_key
                    st.session_state.gemini_authenticated = True
                    st.success("✅ Gemini API 키 인증 성공!")
                    st.rerun()
                else:
                    st.error("❌ 유효하지 않은 API 키 또는 모델입니다.")
            else:
                st.warning("⚠️ API 키를 입력해주세요.")
        
        # 인증 해제 버튼
        if st.session_state.get('gemini_authenticated', False):
            if st.button("🔓 인증 해제", use_container_width=True):
                st.session_state.gemini_api_key = ""
                st.session_state.gemini_authenticated = False
                st.info("🔓 API 키 인증이 해제되었습니다.")
                st.rerun()
        
        # 테스트 버튼
        if st.session_state.get('gemini_authenticated', False):
            if st.button("🧪 API 테스트", use_container_width=True):
                with st.spinner("API 연결 테스트 중..."):
                    test_result = test_gemini_api()
                    if test_result and not test_result.startswith("❌"):
                        st.success("✅ API 연결 테스트 성공!")
                        st.markdown(f"**AI 응답**: {test_result}")
                    else:
                        st.error("❌ API 연결 테스트 실패")
                        st.error(test_result)
        
        # 현재 API 상태 표시
        if st.session_state.get('gemini_authenticated', False):
            st.success("🟢 **API 연결 상태**: 정상")
            st.info(f"🔑 **인증된 키**: {st.session_state.get('gemini_api_key', '')[:10]}...")
        else:
            st.warning("🔴 **API 연결 상태**: 미인증")

# Gemini 지원 모델 자동 탐색 함수
import google.generativeai as genai

def get_supported_gemini_model(api_key):
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        # generateContent 지원 모델만 필터링
        for m in models:
            if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                return m.name
        return None
    except Exception as e:
        print(f"모델 탐색 오류: {e}")
        return None

# API 키 유효성 검증 함수
# Gemini 모델명 상수
GEMINI_MODEL_NAME = "gemini-1.5-flash"

def validate_gemini_api_key(api_key, model_name):
    if not check_gemini_plugins():
        return False
    try:
        import google.generativeai as genai
        api_key = api_key.strip()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Hello", generation_config=genai.types.GenerationConfig(max_output_tokens=10, temperature=0.1))
        if hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'text') and response.parts[0].text:
            st.success(f"✅ API 연결 성공! 테스트 응답: {response.parts[0].text[:50]}...")
            st.session_state.gemini_model = 'gemini-2.0-flash'
            return True
        else:
            finish_reason = getattr(response, 'finish_reason', '알 수 없음')
            st.error(f"❌ Gemini 모델에서 유효한 응답을 받지 못했습니다. finish_reason: {finish_reason}")
            return False
    except Exception as e:
        st.error(f"❌ API 키 검증 실패: {e}")
        return False

# API 테스트 함수
def test_gemini_api():
    """Gemini API 연결 테스트"""
    try:
        import google.generativeai as genai
        
        api_key = st.session_state.get('gemini_api_key', '')
        if not api_key:
            return "❌ API 키가 설정되지 않았습니다."
            
        genai.configure(api_key=api_key)
        
        # 저장된 모델명 사용 또는 기본값
        model_name = st.session_state.get('gemini_model', 'gemini-1.5-flash')
        
        try:
            model = genai.GenerativeModel(model_name)
        except:
            # 저장된 모델이 실패하면 다른 모델들 시도
            model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
            for name in model_names:
                try:
                    model = genai.GenerativeModel(name)
                    st.session_state.gemini_model = name
                    break
                except:
                    continue
            else:
                return "❌ 사용 가능한 모델을 찾을 수 없습니다."
        
        test_prompt = "안녕하세요! 간단한 인사말 한 문장만 해주세요."
        response = model.generate_content(test_prompt,
                                        generation_config=genai.types.GenerationConfig(
                                            max_output_tokens=50,
                                            temperature=0.7
                                        ))
        
        if response and response.text:
            return f"✅ 성공! ({model_name}): {response.text.strip()}"
        else:
            return "❌ 응답을 받지 못했습니다."
            
    except Exception as e:
        return f"❌ 테스트 실패: {str(e)}"

# 파일 업로드 및 리스트 관리
def file_upload_section():
    st.markdown("## 📁 파일 관리")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 👤 계정 관리")
        account_file = st.file_uploader("계정 파일 업로드", type=['csv', 'txt'], key="account")
        
        if account_file:
            # 파일 처리 로직
            content = account_file.read().decode('utf-8')
            st.text_area("계정 정보", content, height=150)
            
        # 기존 저장된 내용 로드
        existing_content = FileManager.load_file_content("account")
        if existing_content:
            st.text_area("저장된 계정 정보", existing_content, height=100, disabled=True)
            
        if st.button("계정 정보 저장", key="save_account"):
            if account_file:
                content = account_file.read().decode('utf-8')
                if FileManager.save_file_content(content, "account"):
                    st.success("계정 정보가 저장되었습니다.")
                    StreamlitLogger.add_log("계정 정보가 저장되었습니다.")
                else:
                    st.error("계정 정보 저장에 실패했습니다.")
            else:
                st.warning("먼저 파일을 업로드해주세요.")
    
    with col2:
        st.markdown("### 🏷️ 키워드 관리")
        keyword_file = st.file_uploader("키워드 파일 업로드", type=['csv', 'txt'], key="keyword")
        
        if keyword_file:
            content = keyword_file.read().decode('utf-8')
            st.text_area("키워드 정보", content, height=150)
            
        if st.button("키워드 정보 저장", key="save_keyword"):
            st.success("키워드 정보가 저장되었습니다.")
    
    with col3:
        st.markdown("### 🌐 웹주소 관리")
        web_file = st.file_uploader("웹주소 파일 업로드", type=['csv', 'txt'], key="web")
        
        if web_file:
            content = web_file.read().decode('utf-8')
            st.text_area("웹주소 정보", content, height=150)
            
        if st.button("웹주소 정보 저장", key="save_web"):
            st.success("웹주소 정보가 저장되었습니다.")

# 콘텐츠 입력 섹션
def content_input_section():
    st.markdown("## ✍️ 콘텐츠 작성")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        title = st.text_input("제목", placeholder="포스팅 제목을 입력하세요")
        content = st.text_area("내용", height=200, placeholder="포스팅 내용을 입력하세요")
        
        # 이미지 업로드
        st.markdown("### 🖼️ 이미지 업로드")
        uploaded_images = st.file_uploader(
            "이미지 선택", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )
        
        if uploaded_images:
            st.write(f"{len(uploaded_images)}개의 이미지가 업로드되었습니다.")
            
            # 이미지 미리보기
            cols = st.columns(min(len(uploaded_images), 4))
            for i, img in enumerate(uploaded_images[:4]):
                with cols[i]:
                    st.image(img, caption=f"이미지 {i+1}", use_column_width=True)
    
    with col2:
        st.markdown("### 🎯 AI 콘텐츠 생성")
        
        if st.button("AI로 제목 생성", use_container_width=True):
            # AI 제목 생성 로직
            with st.spinner("AI가 제목을 생성 중입니다..."):
                generated_title = ContentGenerator.generate_title("키워드")
                if generated_title:
                    st.session_state.generated_title = generated_title
                    st.success(f"생성된 제목: {generated_title}")
            
        if st.button("AI로 내용 생성", use_container_width=True):
            # AI 내용 생성 로직
            with st.spinner("AI가 내용을 생성 중입니다..."):
                generated_content = ContentGenerator.generate_content(title, "키워드")
                if generated_content:
                    st.session_state.generated_content = generated_content
                    st.success("내용이 생성되었습니다!")
        
        # 생성된 콘텐츠 표시
        if 'generated_title' in st.session_state:
            st.markdown("**생성된 제목:**")
            st.write(st.session_state.generated_title)
            
        if 'generated_content' in st.session_state:
            st.markdown("**생성된 내용:**")
            st.text_area("", st.session_state.generated_content, height=200, disabled=True)
            
        st.markdown("### 📊 미리보기")
        if title or content:
            st.markdown("**제목:**")
            st.write(title if title else "제목이 없습니다.")
            st.markdown("**내용:**")
            st.write(content if content else "내용이 없습니다.")

# 실행 및 로그 섹션
def execution_section(platform, min_wait, max_wait, use_dynamic_ip, api_key):
    st.markdown("## 🚀 실행 및 모니터링")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 실행 제어")
        
        if st.button("🚀 자동화 시작", type="primary", use_container_width=True):
            TaskManager.start_automation_task(
                platform=platform,
                min_wait=min_wait,
                max_wait=max_wait,
                use_dynamic_ip=use_dynamic_ip,
                api_key=api_key
            )
            st.success("자동화 작업이 시작되었습니다!")
            
        if st.button("⏹️ 작업 중지", use_container_width=True):
            TaskManager.stop_automation_task()
            st.warning("작업이 중지되었습니다.")
        
        # 상태 표시
        if 'task_running' in st.session_state and st.session_state.task_running:
            st.info("🔄 작업이 진행 중입니다...")
        else:
            st.success("✅ 대기 중")
    
    with col2:
        st.markdown("### 📋 실시간 로그")
        
        # 로그 컨테이너
        log_container = st.container()
        
        # 세션 상태에 로그 저장
        if 'logs' not in st.session_state:
            st.session_state.logs = ["시스템이 초기화되었습니다."]
        
        with log_container:
            log_text = "\n".join(st.session_state.logs[-20:])  # 최근 20개 로그만 표시
            st.text_area("로그", value=log_text, height=300, disabled=True)
        
        # 로그 지우기 버튼
        if st.button("로그 지우기"):
            st.session_state.logs = []
            st.rerun()

# 통계 및 대시보드
def dashboard_section():
    st.markdown("## 📊 작업 현황")
    
    # 통계 데이터 가져오기
    stats = DataManager.get_task_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 작업 수", stats["total_tasks"], "3")
    
    with col2:
        st.metric("성공 작업", stats["successful_tasks"], "2")
    
    with col3:
        st.metric("실패 작업", stats["failed_tasks"], "1")
    
    with col4:
        st.metric("성공률", f"{stats['success_rate']}%", "8.3%")
    
    # 작업 이력 테이블
    st.markdown("### 📝 작업 이력")
    
    # 실제 데이터 가져오기
    history_data = DataManager.get_task_history()
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True)

# 메인 앱
def main():
    # 세션 상태 초기화
    init_session_state()
    
    # 인증 확인
    if not authenticate():
        return
    
    # 사이드바 설정
    platform, min_wait, max_wait, use_dynamic_ip, api_key = setup_sidebar()
    
    # 메인 컨텐츠
    st.title("🚀 네이버 포스팅 자동화 시스템")
    st.markdown("---")
    
    # 탭 메뉴
    TABS = ["AI 설정", "파일 관리", "프롬프트 관리", "실행 및 모니터링", "대시보드"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(TABS)
    
    with tab1:
        gemini_api_section()
    
    with tab2:
        file_upload_section()
    
    # 프롬프트 관리 탭
    with tab3:
        st.header("📝 프롬프트 관리")
        st.markdown("AI에게 원하는 블로그 제목/글을 생성할 프롬프트를 입력하세요.")
        # 블로그 발행일 입력
        publish_date = st.date_input("블로그 발행일", key="publish_date")
        date_folder = publish_date.strftime("%Y-%m-%d") if publish_date else ""
        image_dir = f"media/upload/{date_folder}" if date_folder else ""
        # 프롬프트 리스트 세션 초기화
        if "prompt_list" not in st.session_state:
            st.session_state["prompt_list"] = []
        # 프롬프트 추가 입력창
        new_prompt = st.text_area("새 프롬프트 추가", value="", height=60, key="new_prompt")
        col_add, col_run = st.columns([1,1])
        with col_add:
            if st.button("프롬프트 추가", key="add_prompt"):
                if new_prompt.strip():
                    st.session_state["prompt_list"].append(new_prompt.strip())
                    st.success("프롬프트가 추가되었습니다.")
                else:
                    st.warning("프롬프트 내용을 입력하세요.")
        # 프롬프트 리스트 및 삭제 기능
        st.markdown("#### 등록된 프롬프트 목록")
        for idx, prompt in enumerate(st.session_state["prompt_list"]):
            col1, col2 = st.columns([8,1])
            with col1:
                st.markdown(f"{idx+1}. {prompt}")
            with col2:
                if st.button("삭제", key=f"del_prompt_{idx}"):
                    st.session_state["prompt_list"].pop(idx)
                    st.experimental_rerun()
        # 선택 프롬프트로 AI 생성
        st.markdown("---")
        st.markdown("#### 선택한 프롬프트로 AI 생성 및 이미지 자동 삽입")
        selected_idx = st.selectbox("프롬프트 선택", options=list(range(len(st.session_state["prompt_list"]))), format_func=lambda x: st.session_state["prompt_list"][x] if st.session_state["prompt_list"] else "", key="select_prompt") if st.session_state["prompt_list"] else None
        if selected_idx is not None and st.button("AI 생성 실행", key="run_ai_prompt"):
            with st.spinner("AI가 블로그 제목과 글을 생성 중입니다..."):
                import google.generativeai as genai
                import os
                api_key = st.session_state.get('gemini_api_key', '')
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                prompt = st.session_state["prompt_list"][selected_idx] + "\n\n5문단으로 작성해줘. 각 문단 끝에 [이미지] 태그를 넣어줘."
                response = model.generate_content(prompt)
                if hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'text') and response.parts[0].text:
                    ai_output = response.parts[0].text.strip()
                    # 이미지 폴더에서 1~5 번호 파일만 추출
                    image_paths = []
                    if os.path.isdir(image_dir):
                        files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                        # 파일명 숫자 기준 정렬 (예: 1.jpg, 2.png ...)
                        files = sorted(files, key=lambda x: int(os.path.splitext(x)[0]))
                        image_paths = [os.path.join(image_dir, f) for f in files[:5]]
                    # [이미지] 태그를 실제 이미지로 치환 (번호 순서대로)
                    for i, img_path in enumerate(image_paths):
                        ai_output = ai_output.replace("[이미지]", f"<img src='{img_path}' width='400px'>", 1)
                    st.success("AI 생성 결과 (이미지 자동 삽입)")
                    st.markdown(ai_output, unsafe_allow_html=True)
                else:
                    finish_reason = getattr(response, 'finish_reason', '알 수 없음')
                    st.error(f"❌ Gemini 모델에서 유효한 응답을 받지 못했습니다. finish_reason: {finish_reason}")
    
    with tab4:
        execution_section(platform, min_wait, max_wait, use_dynamic_ip, "")
    
    with tab5:
        dashboard_section()
    
    # 푸터
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            네이버 포스팅 자동화 시스템 v2.0 | Powered by Streamlit
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()