# test_login.py
import requests

def test_admin_login():
    response = requests.post("http://localhost:5001/api/auth/login",
                           json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    
def test_user_login():
    response = requests.post("http://localhost:5001/api/auth/login",
                           json={"username": "testuser", "password": "test123"})
    assert response.status_code == 200
