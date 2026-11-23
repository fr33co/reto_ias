"""WSGI entry point used by gunicorn (`wsgi:app`) and the Flask CLI (`--app wsgi`)."""
from app import create_app

app = create_app()
