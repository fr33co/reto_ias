#!/bin/sh
# Genera .env con secretos aleatorios si no existe.
set -e
[ -f .env ] && { echo ".env ya existe"; exit 0; }
r() { python3 -c "import secrets;print(secrets.token_urlsafe($1))"; }
fernet() { python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"; }
cat > .env <<ENV
POSTGRES_USER=guabina
POSTGRES_PASSWORD=$(r 24)
POSTGRES_DB=reto
JWT_SECRET=$(r 48)
CEDULA_KEYS=$(fernet)
WEB_PORT=8088
ENV
echo ".env generado"
