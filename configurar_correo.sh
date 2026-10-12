#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Configura el correo saliente del servicio de contratos (SMTP).
# Pensado para Gmail con "contrasena de aplicacion".
# Uso:  bash /opt/contrato-firma/configurar_correo.sh
# ---------------------------------------------------------------------------
set -u
DIR=/opt/contrato-firma
SERVICIO=contrato-firma

[ -f "$DIR/.env" ] || { echo "No encuentro $DIR/.env"; exit 1; }

echo "=== Configuracion del correo del servicio de contratos ==="
echo
printf "Servidor SMTP [smtp.gmail.com]: "
read -r HOST
HOST=${HOST:-smtp.gmail.com}

printf "Puerto [465]: "
read -r PORT
PORT=${PORT:-465}

printf "Usuario (la direccion completa, ej. micuenta@gmail.com): "
read -r USUARIO
[ -n "$USUARIO" ] || { echo "Hace falta el usuario."; exit 1; }

printf "Direccion que firma los correos [%s]: " "$USUARIO"
read -r DESDE
DESDE=${DESDE:-$USUARIO}

printf "Nombre del remitente [Adara Excavaciones]: "
read -r NOMBRE
NOMBRE=${NOMBRE:-Adara Excavaciones}

printf "Copia oculta de cada contrato en (opcional, enter para ninguna): "
read -r COPIA

printf "Contrasena de aplicacion (no se vera al escribirla): "
read -rs CLAVE
echo
[ -n "$CLAVE" ] || { echo "Hace falta la contrasena de aplicacion."; exit 1; }

# --- guardar en el .env ---
guardar() {
  local clave="$1" valor="$2"
  if grep -q "^${clave}=" "$DIR/.env"; then
    python3 - "$DIR/.env" "$clave" "$valor" <<'PY'
import sys, pathlib
ruta, clave, valor = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(ruta)
lineas = []
for linea in p.read_text(encoding="utf-8").splitlines():
    lineas.append(f"{clave}={valor}" if linea.startswith(clave + "=") else linea)
p.write_text("\n".join(lineas) + "\n", encoding="utf-8")
PY
  else
    printf '%s=%s\n' "$clave" "$valor" >> "$DIR/.env"
  fi
}

guardar SMTP_HOST "$HOST"
guardar SMTP_PORT "$PORT"
guardar SMTP_USER "$USUARIO"
guardar SMTP_PASS "$CLAVE"
guardar SMTP_FROM "$DESDE"
guardar SMTP_FROM_NAME "$NOMBRE"
guardar COPIA_EMAIL "$COPIA"
chmod 600 "$DIR/.env"
echo "  datos guardados en $DIR/.env (permisos solo root)"

# --- aplicar al servicio ---
docker service update --force \
  --env-add "SMTP_HOST=$HOST" \
  --env-add "SMTP_PORT=$PORT" \
  --env-add "SMTP_USER=$USUARIO" \
  --env-add "SMTP_PASS=$CLAVE" \
  --env-add "SMTP_FROM=$DESDE" \
  --env-add "SMTP_FROM_NAME=$NOMBRE" \
  --env-add "COPIA_EMAIL=$COPIA" \
  "$SERVICIO" >/dev/null
echo "  servicio actualizado, esperando a que arranque..."
sleep 35

# --- prueba de envio ---
printf "Enviar un correo de prueba a [%s]: " "$DESDE"
read -r PRUEBA
PRUEBA=${PRUEBA:-$DESDE}
if [ -n "$PRUEBA" ]; then
  SMTP_HOST="$HOST" SMTP_PORT="$PORT" SMTP_USER="$USUARIO" SMTP_PASS="$CLAVE" \
  SMTP_FROM="$DESDE" DESTINO="$PRUEBA" python3 - <<'PY'
import os, smtplib, ssl
from email.message import EmailMessage
host, puerto = os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])
usuario, clave, desde = os.environ["SMTP_USER"], os.environ["SMTP_PASS"], os.environ["SMTP_FROM"]
m = EmailMessage()
m["From"] = desde
m["To"] = os.environ["DESTINO"]
m["Subject"] = "Prueba de correo - Adara Excavaciones"
m.set_content("Prueba de correo del servicio de contratos. Si lees esto, el envio funciona.")
try:
    if puerto == 465:
        s = smtplib.SMTP_SSL(host, puerto, timeout=30, context=ssl.create_default_context())
    else:
        s = smtplib.SMTP(host, puerto, timeout=30)
        s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
    s.login(usuario, clave)
    s.send_message(m)
    s.quit()
    print("  PRUEBA ENVIADA a " + os.environ["DESTINO"])
except Exception as e:
    print("  FALLO AL ENVIAR: " + str(e)[:200])
PY
fi

echo
echo "=== Resumen ==="
curl -s -o /dev/null -w "  web de contratos: %{http_code}\n" https://firmar.infoadaraexcavaciones.es/healthz
echo "  Para comprobar el correo de verdad: rellena un contrato de prueba en la web"
echo "  y mira si te llega el correo con el PDF adjunto."