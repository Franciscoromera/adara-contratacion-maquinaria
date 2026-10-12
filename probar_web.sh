#!/usr/bin/env bash
# Prueba del flujo completo: formulario -> contrato -> panel -> subida del firmado
set -u
B=http://127.0.0.1:8082

echo "== salud =="
curl -s "$B/healthz"; echo

echo "== formulario =="
curl -s -o /dev/null -w "GET /                  %{http_code}\n" "$B/"

echo "== envio del formulario =="
curl -s -o /tmp/resp.html -w "POST /solicitar        %{http_code}\n" -X POST "$B/solicitar" \
  --data-urlencode "arr_razon=Excavaciones López e Hijos, S.L." \
  --data-urlencode "arr_tipo=S.L." \
  --data-urlencode "arr_cif=B04012345" \
  --data-urlencode "arr_domicilio=Camino de la Vega 22, Almería" \
  --data-urlencode "arr_representante=Manuel López García" \
  --data-urlencode "arr_dni=12345678Z" \
  --data-urlencode "arr_cargo=Administrador" \
  --data-urlencode "arr_telefono=600111222" \
  --data-urlencode "arr_email=manuel@excavacioneslopez.es" \
  --data-urlencode "obra_direccion=Parcela 14 del sector UA-3" \
  --data-urlencode "obra_municipio=Roquetas de Mar (Almería)" \
  --data-urlencode "obra_uso=Excavación para cimentación y movimiento de tierras" \
  --data-urlencode "maq1_desc=Miniexcavadora sobre orugas" \
  --data-urlencode "maq1_marca=Kubota U48-4" \
  --data-urlencode "maq1_accesorios=Cazo 600 mm y martillo hidráulico" \
  --data-urlencode "fecha_inicio=2026-10-20" \
  --data-urlencode "hora_inicio=08:00" \
  --data-urlencode "fecha_fin=2026-11-20" \
  --data-urlencode "precio_dia=260" \
  --data-urlencode "precio_mes=4.200" \
  --data-urlencode "plazo_pago=30" \
  --data-urlencode "fianza=500" \
  --data-urlencode "firma_nombre=Manuel López García" \
  --data-urlencode "acepta=si" \
  --data-urlencode "acepta_datos=si"

ID=$(grep -oE '/contrato/[a-f0-9]+\.pdf' /tmp/resp.html | head -1 | sed 's#/contrato/##; s#\.pdf##')
T=$(grep -oE '/contrato/[a-f0-9]+\.pdf\?t=[a-f0-9]+' /tmp/resp.html | head -1 | sed 's#.*t=##')
echo "   expediente: $ID  (token ${T:0:8}…)"
grep -oE "Contrato aceptado correctamente|No hemos podido enviar el correo" /tmp/resp.html | head -1

echo "== descarga del PDF =="
curl -s -o /tmp/descargado.pdf -w "GET contrato.pdf       %{http_code} %{size_download} bytes\n" "$B/contrato/$ID.pdf?t=$T"
curl -s -o /dev/null -w "sin token (debe 403)   %{http_code}\n" "$B/contrato/$ID.pdf"

echo "== panel =="
curl -s -o /dev/null -w "GET /panel (sin clave) %{http_code}\n" "$B/panel"
curl -s -o /dev/null -c /tmp/cookies.txt -w "POST /panel/login      %{http_code}\n" -X POST "$B/panel/login" -d "clave=clave123"
curl -s -o /tmp/panel.html -b /tmp/cookies.txt -w "GET /panel (con clave) %{http_code}\n" "$B/panel"
grep -oE "ARR-2026-[A-Z0-9]+|Excavaciones López[^<]*|aceptado" /tmp/panel.html | sort -u | head -4

echo "== subida del contrato firmado =="
echo "Contrato firmado de prueba" > /tmp/firmado.txt
curl -s -o /tmp/firmado_resp.html -w "POST /firmado          %{http_code}\n" -X POST "$B/firmado/$ID" \
  -F "t=$T" -F "archivo=@/tmp/firmado.txt;type=application/pdf"
grep -oE "Hemos recibido tu contrato firmado" /tmp/firmado_resp.html | head -1
curl -s -b /tmp/cookies.txt -o /dev/null -w "GET firmado (panel)    %{http_code}\n" "$B/panel/firmado/$ID"

echo "== ficheros guardados =="
ls -la /tmp/firma-data /tmp/firma-data/pdfs /tmp/firma-data/firmados 2>/dev/null | grep -vE '^$|total' | tail -8