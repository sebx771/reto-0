
from app import create_app


def test_csrf_token_rejects_unicode_without_server_error(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": str(tmp_path / "test.sqlite"),
        }
    )
    client = app.test_client()
    client.get("/login")

    response = client.post(
        "/login",
        data={
            "username": "alice",
            "password": "strong-pass-123",
            "csrf_token": "ñ",
        },
    )

    assert response.status_code == 400
