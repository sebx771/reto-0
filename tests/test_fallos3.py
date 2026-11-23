import pytest

from app import create_app, get_db


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE": str(tmp_path / "test.sqlite"),
        }
    )


def test_registration_rejects_excessively_long_password(app):
    client = app.test_client()
    client.get("/register")
    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/register",
        data={
            "username": "alice",
            "password": "a" * 257,
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 200
    assert b"La contrase\xc3\xb1a no puede superar" in response.data
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 0


def test_registration_accepts_password_at_maximum_length(app):
    client = app.test_client()
    client.get("/register")
    with client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = client.post(
        "/register",
        data={
            "username": "alice",
            "password": "a" * 256,
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 302
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 1
