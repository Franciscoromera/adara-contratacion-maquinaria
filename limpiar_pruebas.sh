#!/usr/bin/env bash
# Borra los contratos de prueba creados durante la puesta en marcha.
set -e
C=$(docker ps -q -f name=contrato-firma)
docker exec -i "$C" python3 - <<'PY'
import sqlite3
con = sqlite3.connect("/data/contratos.db")
tablas = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("tablas:", tablas)
if "solicitudes" in tablas:
    con.execute("delete from solicitudes")
    con.commit()
    print("solicitudes restantes:", con.execute("select count(*) from solicitudes").fetchone()[0])
PY
docker exec "$C" sh -c 'rm -f /data/pdfs/* /data/firmados/*'
docker exec "$C" sh -c 'ls -la /data/pdfs /data/firmados'
echo "LIMPIADO"