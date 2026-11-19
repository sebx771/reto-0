import tempfile
import unittest
from pathlib import Path

from app import create_app


class TaskAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "DATABASE": str(Path(self.temp_dir.name) / "test.sqlite"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def post(self, path, data=None):
        with self.client.session_transaction() as session:
            token = session.get("csrf_token")
        if token is None:
            self.client.get("/login")
            with self.client.session_transaction() as session:
                token = session["csrf_token"]
        return self.client.post(path, data={**(data or {}), "csrf_token": token})

    def register(self, username):
        return self.post(
            "/register", {"username": username, "password": "strong-pass-123"}
        )

    def test_register_login_and_password_is_hashed(self):
        response = self.register("alice")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/tasks")

        with self.app.app_context():
            from app import get_db

            row = get_db().execute(
                "SELECT password_hash FROM users WHERE username = ?", ("alice",)
            ).fetchone()
            self.assertNotEqual(row["password_hash"], "strong-pass-123")

        self.post("/logout")
        response = self.post(
            "/login", {"username": "alice", "password": "strong-pass-123"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/tasks")

    def test_task_crud(self):
        self.register("alice")
        response = self.post(
            "/tasks", {"title": "  Comprar café  ", "description": "  Molido  "}
        )
        self.assertEqual(response.status_code, 302)

        with self.client:
            page = self.client.get("/tasks")
            self.assertIn(b"Comprar caf\xc3\xa9", page.data)
            with self.client.session_transaction() as session:
                user_id = session["user_id"]

        with self.app.app_context():
            from app import get_db

            task_id = get_db().execute(
                "SELECT id FROM tasks WHERE user_id = ?", (user_id,)
            ).fetchone()["id"]

        self.assertEqual(self.post(f"/tasks/{task_id}/toggle").status_code, 302)
        self.assertEqual(
            self.post(
                f"/tasks/{task_id}/edit",
                {"title": "Café listo", "description": "Comprado"},
            ).status_code,
            302,
        )
        with self.client:
            page = self.client.get("/tasks")
            self.assertIn(b"Caf\xc3\xa9 listo", page.data)
            self.assertIn(b"Comprado", page.data)

        self.assertEqual(self.post(f"/tasks/{task_id}/delete").status_code, 302)
        with self.client:
            self.assertNotIn(b"Caf\xc3\xa9 listo", self.client.get("/tasks").data)

    def test_users_cannot_access_each_others_tasks(self):
        self.register("alice")
        self.post("/tasks", {"title": "Privada"})
        with self.app.app_context():
            from app import get_db

            task_id = get_db().execute(
                "SELECT id FROM tasks WHERE title = ?", ("Privada",)
            ).fetchone()["id"]

        self.post("/logout")
        self.register("bob")
        self.assertEqual(self.client.get(f"/tasks/{task_id}/edit").status_code, 404)
        self.assertEqual(self.post(f"/tasks/{task_id}/toggle").status_code, 404)
        self.assertEqual(self.post(f"/tasks/{task_id}/delete").status_code, 404)

        with self.app.app_context():
            from app import get_db

            self.assertEqual(
                get_db().execute(
                    "SELECT COUNT(*) AS count FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()["count"],
                1,
            )

    def test_invalid_csrf_token_is_rejected(self):
        self.register("alice")
        response = self.client.post("/tasks", data={"title": "Sin token"})
        self.assertEqual(response.status_code, 400)

    def test_registration_validation(self):
        response = self.post(
            "/register", {"username": "alice", "password": "short"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"al menos 8 caracteres", response.data)


if __name__ == "__main__":
    unittest.main()
