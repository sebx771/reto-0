import hmac
import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get(
            "DATABASE", str(Path(app.instance_path) / "tasks.sqlite")
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_db(error=None):
        database = g.pop("db", None)
        if database is not None:
            database.close()

    with app.app_context():
        database = get_db()
        database.executescript(SCHEMA)
        database.commit()

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.before_request
    def protect_post_requests():
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            session_token = session.get("csrf_token", "")
            if not session_token or not hmac.compare_digest(
                submitted_token, session_token
            ):
                abort(400, description="Token de seguridad inválido.")

    @app.context_processor
    def inject_template_helpers():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]

        return {"csrf_token": csrf_token}

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                flash("Inicia sesión para continuar.", "info")
                return redirect(url_for("login"))
            return view(**kwargs)

        return wrapped_view

    @app.get("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("tasks"))
        return redirect(url_for("login"))

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            error = None

            if not 3 <= len(username) <= 30:
                error = "El usuario debe tener entre 3 y 30 caracteres."
            elif any(character.isspace() for character in username):
                error = "El usuario no puede contener espacios."
            elif len(password) < 8:
                error = "La contraseña debe tener al menos 8 caracteres."

            if error is None:
                try:
                    database = get_db()
                    cursor = database.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    database.commit()
                except sqlite3.IntegrityError:
                    error = "Ese nombre de usuario ya está registrado."
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["username"] = username
                    flash("¡Cuenta creada! Ya puedes organizar tus tareas.", "success")
                    return redirect(url_for("tasks"))

            flash(error, "error")

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Usuario o contraseña incorrectos.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash("Sesión iniciada. ¡A por tus objetivos!", "success")
                return redirect(url_for("tasks"))

        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("Has cerrado sesión.", "info")
        return redirect(url_for("login"))

    @app.get("/tasks")
    @login_required
    def tasks():
        task_list = get_db().execute(
            """
            SELECT id, title, description, completed, created_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY completed ASC, id DESC
            """,
            (session["user_id"],),
        ).fetchall()
        return render_template("tasks.html", tasks=task_list, editing_task=None)

    @app.post("/tasks")
    @login_required
    def create_task():
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        error = validate_task(title, description)

        if error:
            flash(error, "error")
        else:
            database = get_db()
            database.execute(
                "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                (session["user_id"], title, description),
            )
            database.commit()
            flash("Tarea añadida.", "success")
        return redirect(url_for("tasks"))

    @app.route("/tasks/<int:task_id>/edit", methods=("GET", "POST"))
    @login_required
    def edit_task(task_id):
        task = get_user_task(task_id)
        if task is None:
            abort(404)

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            error = validate_task(title, description)

            if error:
                flash(error, "error")
            else:
                database = get_db()
                database.execute(
                    """
                    UPDATE tasks SET title = ?, description = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (title, description, task_id, session["user_id"]),
                )
                database.commit()
                flash("Tarea actualizada.", "success")
                return redirect(url_for("tasks"))

        task_list = get_db().execute(
            """
            SELECT id, title, description, completed, created_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY completed ASC, id DESC
            """,
            (session["user_id"],),
        ).fetchall()
        return render_template("tasks.html", tasks=task_list, editing_task=task)

    @app.post("/tasks/<int:task_id>/toggle")
    @login_required
    def toggle_task(task_id):
        database = get_db()
        cursor = database.execute(
            """
            UPDATE tasks SET completed = 1 - completed
            WHERE id = ? AND user_id = ?
            """,
            (task_id, session["user_id"]),
        )
        database.commit()
        if cursor.rowcount == 0:
            abort(404)
        return redirect(url_for("tasks"))

    @app.post("/tasks/<int:task_id>/delete")
    @login_required
    def delete_task(task_id):
        database = get_db()
        cursor = database.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"]),
        )
        database.commit()
        if cursor.rowcount == 0:
            abort(404)
        flash("Tarea eliminada.", "info")
        return redirect(url_for("tasks"))

    return app


def validate_task(title, description):
    if not title:
        return "El título de la tarea es obligatorio."
    if len(title) > 120:
        return "El título no puede superar los 120 caracteres."
    if len(description) > 1000:
        return "La descripción no puede superar los 1000 caracteres."
    return None


def get_user_task(task_id):
    return get_db().execute(
        """
        SELECT id, title, description, completed, created_at
        FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        (task_id, session["user_id"]),
    ).fetchone()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
