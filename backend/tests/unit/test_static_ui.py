import json

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

EXPECTED_BRANDING_KEYS = {
    "brand_name": str,
    "logo_url": str,
    "primary_color": str,
    "text_on_primary": str,
    "subtitle": str,
    "welcome_message": str,
    "input_placeholder": str,
    "show_powered_by": bool,
}


def test_branding_json_served_and_valid():
    res = client.get("/ui/branding.json")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    data = res.json()
    for key, typ in EXPECTED_BRANDING_KEYS.items():
        assert key in data, f"missing branding key: {key}"
        assert isinstance(data[key], typ), f"{key} should be {typ.__name__}"


def test_root_redirects_to_ui():
    res = client.get("/", follow_redirects=False)
    assert res.status_code in (301, 302, 307)
    assert res.headers["location"] == "/ui/"


def test_customer_chat_served():
    res = client.get("/ui/")
    assert res.status_code == 200
    body = res.text
    assert 'data-role="customer-chat"' in body
    assert 'id="chat-card"' in body


def test_inspector_served():
    res = client.get("/ui/inspector/")
    assert res.status_code == 200
    body = res.text
    assert 'data-role="inspector"' in body
    assert 'id="lead-info"' in body
