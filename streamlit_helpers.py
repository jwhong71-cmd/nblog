"""
Streamlit 앱을 위한 헬퍼 함수들
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import threading
import time
import importlib

# 기존 모듈들
from task.automator import start_task
from data import text_data, list_data, content_data
from cache import upload_cache, download_cache

class StreamlitLogger:
    """Streamlit용 로거 클래스"""
    
    @staticmethod
    def add_log(message):
        """로그 메시지 추가"""
        if 'logs' not in st.session_state:
            st.session_state.logs = []
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        st.session_state.logs.append(log_entry)
        
        # 최대 100개 로그만 유지
        if len(st.session_state.logs) > 100:
            st.session_state.logs = st.session_state.logs[-100:]

class FileManager:
    """파일 관리 클래스"""
    
    @staticmethod
    def save_file_content(content, file_type):
        """파일 내용을 저장"""
        try:
            cache_dir = "cache"
            os.makedirs(cache_dir, exist_ok=True)
            
            filename = f"{file_type}_data.txt"
            filepath = os.path.join(cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            StreamlitLogger.add_log(f"{file_type} 파일이 저장되었습니다: {filename}")
            return True
        except Exception as e:
            StreamlitLogger.add_log(f"{file_type} 파일 저장 실패: {str(e)}")
            return False
    
    @staticmethod
    def load_file_content(file_type):
        """파일 내용을 로드"""
        try:
            cache_dir = "cache"
            filename = f"{file_type}_data.txt"
            filepath = os.path.join(cache_dir, filename)
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            return ""
        except Exception as e:
            StreamlitLogger.add_log(f"{file_type} 파일 로드 실패: {str(e)}")
            return ""

class TaskManager:
    """작업 관리 클래스"""
    
    @staticmethod
    def start_automation_task(platform, min_wait, max_wait, use_dynamic_ip, api_key):
        """자동화 작업 시작"""
        def run_task():
            try:
                StreamlitLogger.add_log("자동화 작업을 시작합니다...")
                
                # 설정값들을 세션 상태에 저장
                st.session_state.current_platform = platform
                st.session_state.min_wait = min_wait
                st.session_state.max_wait = max_wait
                st.session_state.use_dynamic_ip = use_dynamic_ip
                st.session_state.api_key = api_key
                
                # 기존 자동화 함수 호출
                start_task()
                
            except Exception as e:
                StreamlitLogger.add_log(f"작업 중 오류 발생: {str(e)}")
            finally:
                StreamlitLogger.add_log("작업이 모두 끝났습니다.")
                st.session_state.task_running = False
                StreamlitLogger.add_log("작업 상태: 대기 중")
        
        # 백그라운드 스레드에서 실행
        st.session_state.task_running = True
        threading.Thread(target=run_task, daemon=True).start()
    
    @staticmethod
    def stop_automation_task():
        """자동화 작업 중지"""
        st.session_state.task_running = False
        StreamlitLogger.add_log("작업이 중지되었습니다.")

def check_gemini_plugins():
    required = ["google.generativeai", "protobuf"]
    missing = []
    for pkg in required:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    return missing

class ContentGenerator:
    """AI 콘텐츠 생성 클래스"""
    
    @staticmethod
    def generate_title(keywords):
        missing = check_gemini_plugins()
        if missing:
            return f"필수 패키지 미설치: {', '.join(missing)}. 터미널에서 'pip install google-generativeai protobuf' 실행 필요."
        try:
            import streamlit as st
            import google.generativeai as genai
            if not st.session_state.get('gemini_authenticated', False):
                return "❌ Gemini API 인증이 필요합니다."
            api_key = st.session_state.get('gemini_api_key', '')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"다음 키워드를 바탕으로 네이버 블로그/카페에 적합한 제목을 생성해주세요:\n키워드: {keywords}\n조건:\n1. 클릭률이 높은 매력적인 제목\n2. 20자 이내\n3. 자연스러운 한국어\n4. SEO에 최적화된 제목\n제목만 반환해주세요."
            response = model.generate_content(prompt)
            if hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'text') and response.parts[0].text:
                StreamlitLogger.add_log(f"AI 제목이 생성되었습니다: {response.parts[0].text}")
                return response.parts[0].text.strip()
            else:
                finish_reason = getattr(response, 'finish_reason', '알 수 없음')
                return f"❌ Gemini 모델에서 유효한 응답을 받지 못했습니다. finish_reason: {finish_reason}"
        except Exception as e:
            StreamlitLogger.add_log(f"제목 생성 실패: {str(e)}")
            import random
            sample_titles = [f"{keywords} 완벽 가이드", f"{keywords}의 모든 것", f"{keywords} 추천 베스트", f"{keywords} 후기 및 리뷰"]
            return random.choice(sample_titles)

    @staticmethod
    def generate_content(title, keywords):
        missing = check_gemini_plugins()
        if missing:
            return f"필수 패키지 미설치: {', '.join(missing)}. 터미널에서 'pip install google-generativeai protobuf' 실행 필요."
        try:
            import streamlit as st
            import google.generativeai as genai
            if not st.session_state.get('gemini_authenticated', False):
                return "❌ Gemini API 인증이 필요합니다. 'AI 설정' 탭에서 API 키를 인증해주세요."
            api_key = st.session_state.get('gemini_api_key', '')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"다음 정보를 바탕으로 네이버 블로그/카페에 적합한 포스팅 내용을 작성해주세요:\n제목: {title}\n키워드: {keywords}\n조건:\n1. 1000-1500자 분량\n2. 자연스러운 한국어\n3. 읽기 쉬운 구성 (제목, 소제목 포함)\n4. 유용한 정보 제공\n5. 마케팅 스타일이 아닌 정보 전달 위주\n6. 이미지 삽입 위치를 [이미지1], [이미지2] 등으로 표시\n마크다운 형식으로 작성해주세요."
            response = model.generate_content(prompt)
            if hasattr(response, 'parts') and response.parts and hasattr(response.parts[0], 'text') and response.parts[0].text:
                StreamlitLogger.add_log("AI 콘텐츠가 생성되었습니다.")
                return response.parts[0].text.strip()
            else:
                finish_reason = getattr(response, 'finish_reason', '알 수 없음')
                return f"❌ Gemini 모델에서 유효한 응답을 받지 못했습니다. finish_reason: {finish_reason}"
        except Exception as e:
            StreamlitLogger.add_log(f"콘텐츠 생성 실패: {str(e)}")
            return f"❌ AI 콘텐츠 생성에 실패했습니다.\n\n오류: {str(e)}\n\n샘플 콘텐츠:\n\n# {title}\n\n{keywords}에 대해 자세히 알아보겠습니다.\n\n## 주요 특징\n- 특징 1: 높은 품질\n- 특징 2: 합리적인 가격  \n- 특징 3: 우수한 서비스\n\n[이미지1]\n\n## 추천 이유\n{keywords}를 추천하는 이유는 다음과 같습니다:\n1. 검증된 품질\n2. 만족도 높은 후기\n3. 지속적인 개선\n\n[이미지2]\n\n많은 분들께 도움이 되었으면 합니다!"

class DataManager:
    """데이터 관리 클래스"""
    
    @staticmethod
    def get_task_statistics():
        """작업 통계 반환"""
        # TODO: 실제 통계 데이터 구현
        return {
            "total_tasks": 12,
            "successful_tasks": 10,
            "failed_tasks": 2,
            "success_rate": 83.3
        }
    
    @staticmethod
    def get_task_history():
        """작업 이력 반환"""
        # TODO: 실제 이력 데이터 구현
        return [
            {
                "시간": "2024-01-20 10:30",
                "플랫폼": "블로그",
                "계정": "user1@naver.com",
                "상태": "성공",
                "제목": "맛집 추천"
            },
            {
                "시간": "2024-01-20 11:15",
                "플랫폼": "카페",
                "계정": "user2@naver.com",
                "상태": "성공",
                "제목": "여행 후기"
            },
            {
                "시간": "2024-01-20 12:00",
                "플랫폼": "블로그",
                "계정": "user3@naver.com",
                "상태": "실패",
                "제목": "제품 리뷰"
            }
        ]

def init_session_state():
    """세션 상태 초기화"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'task_running' not in st.session_state:
        st.session_state.task_running = False
    
    if 'logs' not in st.session_state:
        st.session_state.logs = ["시스템이 초기화되었습니다."]
    
    if 'current_platform' not in st.session_state:
        st.session_state.current_platform = "블로그"