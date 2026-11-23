# Enfócate

Aplicación web de tareas en español. Cada usuario puede registrarse, iniciar sesión y gestionar de forma privada sus tareas: crearlas, editarlas, marcarlas como completadas y eliminarlas.

## Requisitos

- Python 3.10 o posterior

## Instalación y ejecución

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "reemplaza-esto-por-una-clave-aleatoria"
$env:SESSION_COOKIE_SECURE = "0"
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador. El ajuste `SESSION_COOKIE_SECURE = "0"` es solo para desarrollo local por HTTP. En otros entornos, la cookie usa `Secure` por defecto; si hace falta, configura `SESSION_COOKIE_SECURE = "1"` y sirve la aplicación detrás de HTTPS. La base SQLite se crea automáticamente en `instance/tasks.sqlite`. Para usar otra ubicación, configura la variable `DATABASE`.

Para una ejecución local rápida se genera una clave de sesión aleatoria al iniciar. En despliegues persistentes, define `SECRET_KEY` como una clave aleatoria y secreta, y sirve la aplicación detrás de HTTPS.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```
