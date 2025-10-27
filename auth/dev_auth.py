"""
개발용 인증 함수 - 테스트/개발 환경에서 사용
"""

def dev_auth(username, password):
    """개발용 인증 함수 - 간단한 테스트 계정"""
    # 개발용 테스트 계정들
    test_accounts = {
        "admin": "admin123",
        "test": "test123", 
        "user": "user123",
        "demo": "demo123"
    }
    
    return username in test_accounts and test_accounts[username] == password

def prod_auth(username, password):
    """실제 프로덕션 인증 함수"""
    import uuid
    import requests
    
    def get_mac_address():
        id = uuid.getnode()
        mac = ':'.join(("%012X" % id)[i:i+2] for i in range(0, 12, 2))
        return mac
    
    try:
        mac = get_mac_address()
        res = requests.post('https://tellurium.ejae8319.workers.dev/api/users/auth', json={
            "project": "네이버자동포스팅-신공간",
            "username": username,
            "password": password,
            "code": mac,
        }, timeout=5)
        return res.ok
    except Exception as e:
        print(f"인증 서버 연결 실패: {e}")
        return False