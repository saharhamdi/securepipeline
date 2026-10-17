from app.main import app


def test_health():
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_users_empty():
    client = app.test_client()
    resp = client.get("/users?name=inconnu")
    assert resp.status_code == 200
    assert resp.get_json() == []
