from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_login_page_renders():
    response = client.get("/login")
    assert response.status_code == 200
    assert "LUKA" in response.text
    assert "WhatsApp" in response.text

def test_dashboard_redirects_unauthorized():
    response = client.get("/", follow_redirects=False)
    # The app returns a 401 which the exception handler converts to a 303 redirect to /login
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
