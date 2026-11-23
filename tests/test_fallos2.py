import pytest

from app import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": str(tmp_path / "test.sqlite"),
        }
    )


def test_session_cookie_requires_secure_transport(app):
    assert app.config["SESSION_COOKIE_SECURE"] is True
    response = app.test_client().get("/login")
    assert "; Secure" in response.headers["Set-Cookie"]


def test_session_cookie_can_be_disabled_for_local_http(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": str(tmp_path / "local.sqlite"),
            "SESSION_COOKIE_SECURE": False,
        }
    )

    response = app.test_client().get("/login")

    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert "; Secure" not in response.headers["Set-Cookie"]
