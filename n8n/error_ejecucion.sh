#!/usr/bin/env bash
# Muestra el error de la ultima ejecucion del flujo de contratos.
set -u
DB=$(docker ps -q -f "name=database_n8n-db.1")
E=$(docker service inspect database_n8n --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}')
P=$(echo "$E" | tr ',' '\n' | grep -oP '(?<=DB_POSTGRESDB_PASSWORD=)[^"]*' | head -1)
ID=${1:-}
if [ -z "$ID" ]; then
  ID=$(docker exec -e PGPASSWORD="$P" "$DB" psql -U n8n -d n8n -t -A \
    -c "select id from execution_entity where \"workflowId\"='ContrAceptJb4Jsn' order by id desc limit 1;" | tr -d '[:space:]')
fi
echo "== ejecucion $ID =="
echo 'select data from execution_data where "executionId" = '"$ID"';' > /tmp/q.sql
docker exec -i -e PGPASSWORD="$P" "$DB" psql -U n8n -d n8n -t -A < /tmp/q.sql > /tmp/exec.txt
echo "bytes: $(wc -c < /tmp/exec.txt)"
python3 - <<'PY'
import re
texto = open('/tmp/exec.txt','rb').read().strip().decode('utf-8','replace')
claves = ["Cannot read", "NodeOperationError", "insufficient", "invalid_grant",
          "Request had", "invalid_request", "Unauthorized", "error 400", "error 401", "error 403"]
vistos = set()
for c in claves:
    for m in re.finditer(re.escape(c), texto):
        frag = texto[max(0, m.start()-180):m.start()+240].replace("\\n", " ")
        if frag[:70] in vistos:
            continue
        vistos.add(frag[:70])
        print("[" + c + "]", frag[:400])
        break
if not vistos:
    print("sin coincidencias; muestra:", texto[:400])
PY