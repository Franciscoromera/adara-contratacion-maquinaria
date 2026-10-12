#!/usr/bin/env bash
# Activa el flujo en n8n y lo prueba con dos avisos de prueba.
set -u
ID=ContrAceptJb4Jsn
WEBHOOK=https://n8n.completitud.online/webhook/contrato-aceptado
PDF_URL=https://contratos.infoadaraexcavaciones.es/contrato-arrendamiento-maquinaria-obras-publicas.pdf
N8N=$(docker ps -q -f "name=database_n8n.1")
DB=$(docker ps -q -f "name=database_n8n-db.1")

echo "== 1. Activar el flujo y reiniciar n8n =="
docker exec "$N8N" n8n update:workflow --id="$ID" --active=true 2>&1 | tail -1
docker service update --force database_n8n >/dev/null
sleep 45
docker service ps database_n8n --format "{{.Name}} {{.CurrentState}}" | head -2

echo "== 2. Prueba A: aviso sin teléfono (no envía WhatsApp a nadie) =="
curl -s -o /dev/null -w "   respuesta del webhook: %{http_code}\n" -X POST "$WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{\"tipo\":\"contrato_aceptado\",\"id\":\"pruebaA\",\"numero_contrato\":\"ARR-2026-PRUEBAA\",\"empresa\":\"Prueba A S.L.\",\"telefono\":\"\",\"email\":\"prueba@example.com\",\"aceptante\":\"Prueba A\",\"pdf\":\"$PDF_URL\"}"
sleep 10

echo "== 3. Prueba B: con teléfono de mentira (comprueba la llamada a Evolution) =="
curl -s -o /dev/null -w "   respuesta del webhook: %{http_code}\n" -X POST "$WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{\"tipo\":\"contrato_aceptado\",\"id\":\"pruebaB\",\"numero_contrato\":\"ARR-2026-PRUEBAB\",\"empresa\":\"Prueba B S.L.\",\"telefono\":\"600000000\",\"email\":\"prueba@example.com\",\"aceptante\":\"Prueba B\",\"pdf\":\"$PDF_URL\"}"
sleep 14

echo "== 4. Ejecuciones registradas =="
E=$(docker service inspect database_n8n --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}')
U=$(echo "$E" | tr "," "\n" | grep -oP '(?<=DB_POSTGRESDB_USER=)[^"]*' | head -1)
P=$(echo "$E" | tr "," "\n" | grep -oP '(?<=DB_POSTGRESDB_PASSWORD=)[^"]*' | head -1)
D=$(echo "$E" | tr "," "\n" | grep -oP '(?<=DB_POSTGRESDB_DATABASE=)[^"]*' | head -1)
docker exec -e PGPASSWORD="$P" "$DB" psql -U "$U" -d "$D" -c \
  "select id, status, to_char(\"startedAt\",'HH24:MI:SS') as hora from execution order by id desc limit 5;" 2>&1 | tail -9

echo "== 5. Avisos en el registro de n8n =="
docker service logs database_n8n --since 2m 2>&1 | grep -iE "error|problem|401|not exist|credential" | tail -8
echo FIN