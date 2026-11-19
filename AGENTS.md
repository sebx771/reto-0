# AGENTS.md

## Proyecto
Aplicacion web en español para registrar usuarios y gestionar tareas privadas.
Permite crear, editar, completar y eliminar tareas con proteccion CSRF y sesiones.

## Stack
- Framework: Python 3.10+ y Flask 3.1.
- Base de datos: SQLite mediante sqlite3.
- Librerias principales: Werkzeug, Jinja2 y pytest para pruebas.

## Comandos
- Instalar: `python -m pip install -r requirements.txt`
- Ejecutar: `python app.py`
- Pruebas: `python -m pytest -v`
- Estilo: `ruff check .`

## Estructura
- `app.py`: configuracion, rutas, autenticacion, CSRF, validacion y acceso a SQLite.
- `requirements.txt`: declara la dependencia Flask del proyecto.
- `README.md`: requisitos e instrucciones de instalacion, ejecucion y pruebas.
- `.gitignore`: excluye caches, entorno virtual y datos locales de Git.
- `.venv/`: entorno virtual local y sus paquetes instalados.
- `instance/`: contiene la base SQLite generada automaticamente.
- `instance/tasks.sqlite`: datos persistentes de usuarios y tareas.
- `static/`: recursos publicos; aqui se almacenan hojas de estilo.
- `static/style.css`: diseño responsivo de autenticacion y tablero.
- `templates/`: vistas Jinja2 de autenticacion y tareas.
- `templates/base.html`: plantilla base con cabecera, mensajes y pie.
- `templates/login.html`: formulario e interfaz de inicio de sesion.
- `templates/register.html`: formulario e interfaz de registro.
- `templates/tasks.html`: CRUD visual y estado del tablero de tareas.
- `tests/`: pruebas automatizadas del comportamiento de la aplicacion.
- `tests/test_app.py`: registro, sesiones, CRUD, CSRF y aislamiento por usuario.
- `__pycache__/`: caches generados por Python; no editar ni versionar.

## Que no hacer
- No acumular toda la logica en un solo archivo; evitar monolitos.
- No modificar las pruebas para que pasen.
- No escribir claves en el codigo.
- No instalar dependencias sin explicar para que.
- No hacer commit ni push.

## Lecciones aprendidas
