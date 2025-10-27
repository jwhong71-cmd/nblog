from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def naver_login(naver_id, naver_pw):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # UI 없이 실행하려면 주석 해제
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(1)
        # 아이디 입력
        id_input = driver.find_element(By.ID, 'id')
        id_input.send_keys(naver_id)
        # 패스워드 입력
        pw_input = driver.find_element(By.ID, 'pw')
        pw_input.send_keys(naver_pw)
        pw_input.send_keys(Keys.RETURN)
        time.sleep(2)
        # 로그인 성공 여부 확인
        if '네이버' in driver.title or 'My' in driver.page_source:
            driver.quit()
            return True
        driver.quit()
        return False
    except Exception as e:
        return f'로그인 오류: {e}'
