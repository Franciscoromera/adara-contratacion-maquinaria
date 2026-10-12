#!/usr/bin/env bash
# Despliegue permanente del servicio de contratación en el VPS con EasyPanel + Traefik.
# Se ejecuta desde el VPS:  ssh root@IP 'bash -s' < desplegar_vps.sh
set -e

DIR=/opt/contrato-firma
REPO=https://github.com/Franciscoromera/adara-contratacion-maquinaria.git
RED=easypanel
SERVICIO=contrato-firma
DOMINIO_EASYPANEL=contrato-firma.pdiuan.easypanel.host
DOMINIO_FINAL=firmar.infoadaraexcavaciones.es

echo "== 1. Código =="
mkdir -p "$DIR"
cd "$DIR"
if [ -d repo/.git ]; then
  (cd repo && git fetch -q origin main && git reset -q --hard origin/main)
  echo "   repositorio actualizado"
else
  git clone -q "$REPO" repo
  echo "   repositorio clonado"
fi

echo "== 2. Configuración (.env) =="
if [ ! -f .env ]; then
  SECRETO=$(openssl rand -hex 32)
  CLAVE=$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-14)
  cat > .env <<EOF
# --- Empresa arrendadora (revisar con los datos reales) ---
EMPRESA_NOMBRE=Adara Excavaciones
ARRENDADOR_RAZON=Adara Excavaciones, S.L.
ARRENDADOR_CIF=B04XXXXXX
ARRENDADOR_DOMICILIO=C/ Ejemplo nº 1, 04740 Roquetas de Mar (Almería)
ARRENDADOR_REPRESENTANTE=Nombre Apellidos
ARRENDADOR_DNI=00000000X
ARRENDADOR_TELEFONO=643 175 166
ARRENDADOR_EMAIL=contratos@infoadaraexcavaciones.es
ARRENDADOR_IBAN=ES00 0000 0000 0000 0000 0000
ARRENDADOR_PODER=de fecha 12/03/2024
CONTRATO_URL=https://contratos.infoadaraexcavaciones.es/
PRIVACIDAD_URL=
# --- Correo saliente: rellenar para que el cliente reciba el PDF ---
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASS=
SMTP_SSL=auto
SMTP_FROM=
SMTP_FROM_NAME=Adara Excavaciones
COPIA_EMAIL=
AVISO_FIRMADO_EMAIL=
# --- Seguridad ---
SECRET_KEY=$SECRETO
PANEL_PASSWORD=$CLAVE
BASE_URL=
DATA_DIR=/data
# --- Integración con n8n / WhatsApp (opcional) ---
N8N_WEBHOOK_URL=
EOF
  chmod 600 .env
  echo "   .env creado"
else
  echo "   .env ya existía: no se toca"
fi
# se conserva la clave del panel para mostrarla siempre
grep -E '^(PANEL_PASSWORD|SECRET_KEY)=' .env > /root/.contrato-firma-claves 2>/dev/null || true
chmod 600 /root/.contrato-firma-claves 2>/dev/null || true

echo "== 3. Imagen =="
docker build -q -t contrato-firma:1.0 repo/ | tail -1

echo "== 4. Volumen y servicio =="
docker volume create contrato-firma-data >/dev/null
if docker service inspect "$SERVICIO" >/dev/null 2>&1; then
  docker service update --force --image contrato-firma:1.0 --env-file .env "$SERVICIO" >/dev/null
  echo "   servicio actualizado"
else
  docker service create \
    --name "$SERVICIO" \
    --network "$RED" \
    --mount type=volume,src=contrato-firma-data,dst=/data \
    --env-file .env \
    --replicas 1 \
    --restart-condition any \
    --update-order start-first \
    contrato-firma:1.0 >/dev/null
  echo "   servicio creado"
fi

echo "== 5. Enrutado de Traefik =="
cat > /etc/easypanel/traefik/config/contrato-firma.yaml <<'EOF'
# Enrutado del servicio de contratación telemática (gestionado por Manus).
http:
  middlewares:
    contrato-firma-redirect:
      redirectScheme:
        permanent: true
        scheme: https
  routers:
    contrato-firma-http:
      rule: "Host(`contrato-firma.pdiuan.easypanel.host`) && PathPrefix(`/`)"
      entryPoints:
        - http
      middlewares:
        - contrato-firma-redirect
      service: contrato-firma
      priority: 10
    contrato-firma-https:
      rule: "Host(`contrato-firma.pdiuan.easypanel.host`) && PathPrefix(`/`)"
      entryPoints:
        - https
      service: contrato-firma
      priority: 10
      tls:
        certResolver: letsencrypt
    firmar-contratos-http:
      rule: "Host(`firmar.infoadaraexcavaciones.es`) && PathPrefix(`/`)"
      entryPoints:
        - http
      middlewares:
        - contrato-firma-redirect
      service: contrato-firma
      priority: 10
    firmar-contratos-https:
      rule: "Host(`firmar.infoadaraexcavaciones.es`) && PathPrefix(`/`)"
      entryPoints:
        - https
      service: contrato-firma
      priority: 10
      tls:
        certResolver: letsencrypt
  services:
    contrato-firma:
      loadBalancer:
        servers:
          - url: "http://contrato-firma:80"
EOF
echo "   configuración escrita"

echo "== 6. Comprobación =="
sleep 12
docker service ps "$SERVICIO" --format '{{.Name}} {{.CurrentState}}' | head -3
for H in "$DOMINIO_EASYPANEL" "$DOMINIO_FINAL"; do
  printf "   %-40s %s\n" "$H" "$(curl -sk -o /dev/null -w '%{http_code}' --resolve "$H:443:127.0.0.1" --max-time 20 "https://$H/healthz" || echo fallo)"
done
echo "   contraseña del panel: $(grep -oP '(?<=^PANEL_PASSWORD=).*' /root/.contrato-firma-claves 2>/dev/null || echo 'ver /opt/contrato-firma/.env')"
echo "== FIN =="