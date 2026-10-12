#!/usr/bin/env bash
# Detalle nodo por nodo de la ultima ejecucion del flujo de contratos.
set -u
DB=$(docker ps -q -f "name=database_n8n-db.1")
E=$(docker service inspect database_n8n --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}')
P=$(echo "$E" | tr ',' '\n' | grep -oP '(?<=DB_POSTGRESDB_PASSWORD=)[^"]*' | head -1)
ID=$(docker exec -e PGPASSWORD="$P" "$DB" psql -U n8n -d n8n -t -A \
  -c "select id from execution_entity where \"workflowId\" = 'ContrAceptJb4Jsn' order by id desc limit 1;" 2>/dev/null | tr -d '[:space:]')

docker exec -i -e PGPASSWORD="$P" "$DB" psql -U n8n -d n8n -t -A > /tmp/exec.txt <<SQL
select data from execution_data where "executionId" = $ID;
SQL

echo "ejecucion $ID | bytes: $(wc -c < /tmp/exec.txt)"
python3 - <<'PY'
import json, gzip
raw = open('/tmp/exec.txt','rb').read().strip()
try:
    raw = gzip.decompress(raw)
except Exception:
    pass
d = json.loads(raw.decode('utf-8','replace'))

rd = {}
partes = d if isinstance(d, list) else [d]
for parte in partes:
    if isinstance(parte, dict) and isinstance(parte.get("resultData"), dict):
        rd.update(parte["resultData"].get("runData", {}))

for nombre, runs in rd.items():
    for r in runs:
        err = r.get("error") or {}
        if err:
            print("-", nombre, "-> ERROR:", str(err.get("message") or err.get("description"))[:220])
            continue
        items = (r.get("data", {}).get("main") or [[]])[0]
        extra = ""
        if items:
            j = items[0].get("json", {})
            if isinstance(j, dict):
                resumen = {k: j[k] for k in ("statusCode", "message", "error", "status") if k in j}
                if resumen:
                    extra = " | " + str(resumen)[:220]
        print("-", nombre, "-> ok" + extra)
PY