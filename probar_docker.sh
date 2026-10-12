#!/usr/bin/env bash
# Construye la imagen y prueba el servicio dentro del contenedor
set -u
cd /home/ubuntu/firma

echo "== build =="
sudo docker build --network=host -t contrato-firma:1.0 . 2>&1 | tail -3

echo "== arranque =="
sudo docker rm -f firma-test >/dev/null 2>&1
sudo docker run -d --name firma-test --network=host \
  -e DATA_DIR=/data -e SECRET_KEY=prueba-docker -e PANEL_PASSWORD=clave123 \
  -e BASE_URL=http://127.0.0.1:8085 -e EMPRESA_NOMBRE="Adara Excavaciones" \
  contrato-firma:1.0 uvicorn app.main:app --host 0.0.0.0 --port 8085 >/dev/null
sleep 14

echo "== comprobaciones =="
curl -s -o /dev/null -w "healthz            %{http_code}\n" http://127.0.0.1:8085/healthz
curl -s -o /dev/null -w "formulario         %{http_code}\n" http://127.0.0.1:8085/
curl -s -o /tmp/docker_resp.html -w "envio formulario   %{http_code}\n" -X POST http://127.0.0.1:8085/solicitar \
  --data-urlencode "arr_razon=Excavaciones Prueba, S.L." \
  --data-urlencode "arr_cif=B04000001" \
  --data-urlencode "arr_representante=Ana Pérez Ruiz" \
  --data-urlencode "arr_email=ana@prueba.es" \
  --data-urlencode "obra_direccion=Camino de la Vega 5" \
  --data-urlencode "obra_uso=Movimiento de tierras" \
  --data-urlencode "maq1_desc=Retrocargadora" \
  --data-urlencode "fecha_inicio=2026-10-25" \
  --data-urlencode "fecha_fin=2026-11-25" \
  --data-urlencode "firma_nombre=Ana Pérez Ruiz" \
  --data-urlencode "acepta=si" --data-urlencode "acepta_datos=si"

grep -oE "Contrato aceptado correctamente|ARR-2026-[A-Z0-9]+" /tmp/docker_resp.html | sort -u | head -3

ID=$(grep -oE '/contrato/[a-f0-9]+\.pdf' /tmp/docker_resp.html | head -1 | sed 's#/contrato/##; s#\.pdf##')
T=$(grep -oE '/contrato/[a-f0-9]+\.pdf\?t=[a-f0-9]+' /tmp/docker_resp.html | head -1 | sed 's#.*t=##')
curl -s -o /tmp/docker_descarga.pdf -w "descarga del PDF   %{http_code} %{size_download} bytes\n" "http://127.0.0.1:8085/contrato/$ID.pdf?t=$T"
pdfinfo /tmp/docker_descarga.pdf 2>/dev/null | grep -i pages

echo "== panel y ficheros dentro del contenedor =="
curl -s -o /dev/null -w "panel              %{http_code}\n" http://127.0.0.1:8085/panel
sudo docker exec firma-test ls -la /data /data/pdfs 2>/dev/null | tail -8
echo "== registro del contenedor =="
sudo docker logs firma-test 2>&1 | tail -5