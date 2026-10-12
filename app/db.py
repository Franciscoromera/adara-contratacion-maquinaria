# -*- coding: utf-8 -*-
"""Almacenamiento de las solicitudes de contrato (SQLite).

Guarda los datos del formulario, la copia del PDF generado, las evidencias de la
aceptación telemática y el ejemplar firmado que devuelve el cliente.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
PDFS_DIR = DATA_DIR / "pdfs"
FIRMADOS_DIR = DATA_DIR / "firmados"
DB_PATH = DATA_DIR / "contratos.db"

for _d in (DATA_DIR, PDFS_DIR, FIRMADOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS solicitudes (
    id                TEXT PRIMARY KEY,
    numero_contrato   TEXT,
    creado            TEXT NOT NULL,
    estado            TEXT NOT NULL DEFAULT 'aceptado',
    empresa           TEXT,
    cif               TEXT,
    representante     TEXT,
    email             TEXT,
    telefono          TEXT,
    ip                TEXT,
    user_agent        TEXT,
    version_contrato  TEXT,
    datos             TEXT,
    pdf_archivo       TEXT,
    pdf_sha256        TEXT,
    email_enviado     INTEGER DEFAULT 0,
    email_error       TEXT,
    firmado_archivo   TEXT,
    firmado_creado    TEXT,
    notas             TEXT
);
CREATE INDEX IF NOT EXISTS idx_solicitudes_creado ON solicitudes (creado DESC);
"""


def conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH, timeout=20)
    conexion.row_factory = sqlite3.Row
    return conexion


def init() -> None:
    with _lock, conectar() as conexion:
        conexion.executescript(ESQUEMA)


def ahora() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def nuevo_id() -> str:
    return uuid.uuid4().hex[:12]


def crear_solicitud(datos: dict, *, ip: str, user_agent: str, version: str) -> str:
    ident = nuevo_id()
    numero = f"ARR-{datetime.now().strftime('%Y')}-{ident[:6].upper()}"
    with _lock, conectar() as conexion:
        conexion.execute(
            """INSERT INTO solicitudes
               (id, numero_contrato, creado, estado, empresa, cif, representante,
                email, telefono, ip, user_agent, version_contrato, datos)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ident,
                numero,
                ahora(),
                "aceptado",
                datos.get("arr_razon", ""),
                datos.get("arr_cif", ""),
                datos.get("firma_nombre", "") or datos.get("arr_representante", ""),
                datos.get("arr_email", ""),
                datos.get("arr_telefono", ""),
                ip,
                user_agent[:400],
                version,
                json.dumps(datos, ensure_ascii=False),
            ),
        )
    return ident


def guardar_pdf(ident: str, contenido: bytes, sha256: str) -> str:
    archivo = f"{ident}.pdf"
    (PDFS_DIR / archivo).write_bytes(contenido)
    with _lock, conectar() as conexion:
        conexion.execute(
            "UPDATE solicitudes SET pdf_archivo=?, pdf_sha256=? WHERE id=?",
            (archivo, sha256, ident),
        )
    return archivo


def marcar_email(ident: str, ok: bool, error: str = "") -> None:
    with _lock, conectar() as conexion:
        conexion.execute(
            "UPDATE solicitudes SET email_enviado=?, email_error=? WHERE id=?",
            (1 if ok else 0, error[:400], ident),
        )


def guardar_firmado(ident: str, contenido: bytes, nombre: str) -> None:
    seguro = "".join(ch for ch in nombre if ch.isalnum() or ch in "._-") or "firmado.pdf"
    archivo = f"{ident}-FIRMADO-{seguro}"
    (FIRMADOS_DIR / archivo).write_bytes(contenido)
    with _lock, conectar() as conexion:
        conexion.execute(
            "UPDATE solicitudes SET firmado_archivo=?, firmado_creado=?, estado='firmado_recibido' WHERE id=?",
            (archivo, ahora(), ident),
        )


def obtener(ident: str) -> dict | None:
    with conectar() as conexion:
        fila = conexion.execute("SELECT * FROM solicitudes WHERE id=?", (ident,)).fetchone()
    if not fila:
        return None
    datos = dict(fila)
    datos["datos"] = json.loads(datos.get("datos") or "{}")
    return datos


def listar(limite: int = 200) -> list[dict]:
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT id, numero_contrato, creado, estado, empresa, email, version_contrato,"
            " email_enviado, email_error, pdf_archivo, firmado_archivo"
            " FROM solicitudes ORDER BY creado DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [dict(f) for f in filas]


def actualizar_estado(ident: str, estado: str, notas: str = "") -> None:
    with _lock, conectar() as conexion:
        conexion.execute(
            "UPDATE solicitudes SET estado=?, notas=? WHERE id=?", (estado, notas[:2000], ident)
        )