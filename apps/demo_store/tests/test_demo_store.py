import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Gemini Store" in response.text

def test_checkout_no_bug():
    # Make sure env var is not setting bug
    if "BUG_HIDE_CHECKOUT_BUTTON" in os.environ:
        del os.environ["BUG_HIDE_CHECKOUT_BUTTON"]
        
    response = client.get("/checkout")
    assert response.status_code == 200
    assert "Pay $99.00" in response.text
    # Should not have class hidden-button on the button
    assert "hidden-button" not in response.text

def test_checkout_with_bug_query():
    response = client.get("/checkout?bug=true")
    assert response.status_code == 200
    assert "hidden-button" in response.text

def test_checkout_with_bug_env(monkeypatch):
    monkeypatch.setenv("BUG_HIDE_CHECKOUT_BUTTON", "true")
    response = client.get("/checkout")
    assert response.status_code == 200
    assert "hidden-button" in response.text

def test_post_checkout_form():
    response = client.post("/checkout", data={"name": "Alice", "email": "alice@example.com", "card": "123"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Alice" in response.json()["message"]

def test_post_checkout_json():
    response = client.post("/checkout", json={"name": "Bob", "email": "bob@example.com", "card": "456"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Bob" in response.json()["message"]
