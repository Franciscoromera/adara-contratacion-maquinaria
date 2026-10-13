# -*- coding: utf-8 -*-
"""Servicio de contratación telemática.

Flujo:
  1. El cliente rellena el formulario y acepta el contrato.
  2. Se genera el PDF personalizado, se guarda con sus evidencias y se envía por email.
  3. El cliente puede subir el ejemplar firmado.
  4. La empresa consulta todo desde el panel privado.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import contrato, contrato_corto, correo, db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Contratación Adara", docs_url=None, redoc_url=None)

MAX_FIRMADO = 15 * 1024 * 1024


# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
def cfg() -> dict:
    return {
        "empresa": os.getenv("EMPRESA_NOMBRE", "Adara Excavaciones"),
        "web": os.getenv("BASE_URL", ""),
        "contrato_url": os.getenv(
            "CONTRATO_URL", "https://contratos.infoadaraexcavaciones.es/"
        ),
        "email_contacto": os.getenv("ARRENDADOR_EMAIL", ""),
        "telefono_contacto": os.getenv("ARRENDADOR_TELEFONO", ""),
        "juzgados": os.getenv("JUZGADOS", ""),
        "privacidad_url": os.getenv("PRIVACIDAD_URL", ""),
        "arrendador": {
            "razon": os.getenv("ARRENDADOR_RAZON", ""),
            "cif": os.getenv("ARRENDADOR_CIF", ""),
            "domicilio": os.getenv("ARRENDADOR_DOMICILIO", ""),
            "representante": os.getenv("ARRENDADOR_REPRESENTANTE", ""),
            "dni": os.getenv("ARRENDADOR_DNI", ""),
            "telefono": os.getenv("ARRENDADOR_TELEFONO", ""),
            "email": os.getenv("ARRENDADOR_EMAIL", ""),
            "iban": os.getenv("ARRENDADOR_IBAN", ""),
            "poder": os.getenv("ARRENDADOR_PODER", ""),
        },
    }


def secreto() -> bytes:
    return (os.getenv("SECRET_KEY") or "cambia-esta-clave-en-produccion").encode()


def token(ident: str, ambito: str = "cliente") -> str:
    return hmac.new(secreto(), f"{ident}:{ambito}".encode(), hashlib.sha256).hexdigest()[:32]


def token_valido(ident: str, valor: str, ambito: str = "cliente") -> bool:
    return bool(valor) and hmac.compare_digest(token(ident, ambito), valor)


def url_base(request: Request) -> str:
    return (os.getenv("BASE_URL") or str(request.base_url)).rstrip("/")


def plantilla(request: Request, nombre: str, contexto: dict, status: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, nombre, contexto, status_code=status)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _texto(valor: str | None) -> str:
    return (valor or "").strip()


def _faltan(datos: dict) -> list[str]:
    faltan = [etiqueta for clave, etiqueta in CAMPOS_MINIMOS if not _texto(datos.get(clave))]
    if datos.get("acepta") != "si":
        faltan.append("Aceptación del contrato")
    if datos.get("acepta_datos") != "si":
        faltan.append("Consentimiento para el tratamiento de datos")
    return faltan


CAMPOS_MINIMOS = [
    ("arr_razon", "Razón social o nombre del arrendatario"),
    ("arr_cif", "CIF/NIF del arrendatario"),
    ("arr_representante", "Persona que firma"),
    ("arr_email", "Correo electrónico"),
    ("obra_direccion", "Dirección de la obra"),
    ("obra_uso", "Uso previsto de la máquina"),
    ("maq1_desc", "Máquina 1: descripción"),
    ("fecha_inicio", "Fecha de entrega"),
    ("fecha_fin", "Fecha de devolución prevista"),
    ("firma_nombre", "Nombre del aceptante"),
]


def _aviso_n8n(solicitud: dict, pdf_url: str) -> None:
    """Aviso opcional por WhatsApp: llama a un webhook de n8n si está configurado."""
    destino = os.getenv("N8N_WEBHOOK_URL", "").strip()
    if not destino:
        return
    carga = {
        "tipo": "contrato_aceptado",
        "id": solicitud.get("id"),
        "numero_contrato": solicitud.get("numero_contrato"),
        "empresa": solicitud.get("empresa"),
        "telefono": solicitud.get("telefono_cliente") or solicitud.get("telefono"),
        "email": solicitud.get("email"),
        "aceptante": solicitud.get("aceptante"),
        "pdf": pdf_url,
    }
    try:
        peticion = urllib.request.Request(
            destino,
            data=json.dumps(carga).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(peticion, timeout=8).read()
    except Exception:  # noqa: BLE001
        pass


def _correo_al_cliente(solicitud: dict, pdf: bytes, base: str) -> tuple[bool, str]:
    if not correo.configurado():
        return False, "SMTP no configurado"

    ident = solicitud["id"]
    enlace_subir = f"{base}/firmado/{ident}?t={token(ident)}"
    enlace_pdf = f"{base}/contrato/{ident}.pdf?t={token(ident)}"
    empresa = os.getenv("EMPRESA_NOMBRE", "Adara Excavaciones")
    nombre = solicitud.get("aceptante") or ""

    texto = f"""Hola {nombre}:

Adjuntamos el contrato de arrendamiento de maquinaria nº {solicitud['numero_contrato']},
ya cumplimentado con los datos que nos has facilitado y con el contenido que has aceptado.

Para dejarlo formalizado:
  1. Imprime el contrato (o descárgalo aquí: {enlace_pdf}).
  2. Fírmalo y séllalo.
  3. Envíanoslo firmado respondiendo a este correo, o súbelo aquí: {enlace_subir}

Justificante de la aceptación: {solicitud.get('creado')} · versión {solicitud.get('version_contrato')}.

Cualquier duda, respóndenos a este mismo correo.

Un saludo,
{empresa}
"""

    html = f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.55;color:#111">
<p>Hola {nombre}:</p>
<p>Adjuntamos el <strong>contrato de arrendamiento de maquinaria nº {solicitud['numero_contrato']}</strong>,
ya cumplimentado con los datos que nos has facilitado y con el contenido que has aceptado.</p>
<p>Para dejarlo formalizado:</p>
<ol>
  <li>Imprime el contrato (o <a href="{enlace_pdf}">descárgalo aquí</a>).</li>
  <li>Fírmalo y séllalo.</li>
  <li>Envíanoslo firmado respondiendo a este correo, o
      <a href="{enlace_subir}">súbelo desde este enlace</a>.</li>
</ol>
<p style="color:#555;font-size:12px">Justificante de la aceptación: {solicitud.get('creado')} ·
versión {solicitud.get('version_contrato')} · huella {str(solicitud.get('pdf_sha256') or '')[:16]}…</p>
<p>Cualquier duda, respóndenos a este mismo correo.</p>
<p>Un saludo,<br><strong>{empresa}</strong></p>
</div>"""

    try:
        correo.enviar(
            para=solicitud["email"],
            asunto=f"Contrato de arrendamiento de maquinaria nº {solicitud['numero_contrato']}",
            texto=texto,
            html=html,
            responder_a=os.getenv("ARRENDADOR_EMAIL") or None,
            copia=os.getenv("COPIA_EMAIL") or None,
            adjuntos=[
                (f"contrato-arrendamiento-{solicitud['numero_contrato']}.pdf", pdf, "application/pdf")
            ],
        )
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


# --------------------------------------------------------------------------- #
# Web pública
# --------------------------------------------------------------------------- #
@app.on_event("startup")
def _arranque() -> None:
    db.init()


@app.get("/healthz")
def healthz():
    return {"estado": "ok", "hora": datetime.now().isoformat(timespec="seconds")}


@app.get("/", response_class=HTMLResponse)
def formulario(request: Request):
    return plantilla(
        request,
        "form.html",
        {"cfg": cfg(), "version": contrato.VERSION_CONTRATO, "error": None, "datos": {}},
    )


@app.post("/solicitar", response_class=HTMLResponse)
async def solicitar(request: Request):
    formulario_datos = await request.form()
    datos = {k: v.strip() for k, v in formulario_datos.items() if isinstance(v, str)}

    faltan = _faltan(datos)
    if not faltan and datos.get("arr_email", "").lower() != datos.get("arr_email2", "").lower():
        faltan = ["Los dos correos electrónicos no coinciden"]
    if faltan:
        return plantilla(
            request,
            "form.html",
            {
                "cfg": cfg(),
                "version": contrato.VERSION_CONTRATO,
                "error": "Faltan datos obligatorios: " + ", ".join(faltan),
                "datos": datos,
            },
            status=400,
        )

    conf = cfg()
    completo = datos.get("formato") == "completo"
    version = contrato.VERSION_CONTRATO if completo else contrato_corto.VERSION_CONTRATO_CORTO
    generar_pdf = contrato.generar_pdf if completo else contrato_corto.generar_pdf
    ident = db.crear_solicitud(
        datos,
        ip=(request.client.host if request.client else ""),
        user_agent=request.headers.get("user-agent", ""),
        version=version,
    )
    solicitud = db.obtener(ident) or {}
    solicitud["aceptante"] = datos.get("firma_nombre", "")
    solicitud["telefono_cliente"] = datos.get("arr_telefono", "")
    solicitud["fecha_texto"] = datetime.now().strftime("%d/%m/%Y")
    solicitud["web"] = url_base(request)

    pdf, sha, _html = generar_pdf(datos, conf, solicitud)
    solicitud["pdf_sha256"] = sha
    db.guardar_pdf(ident, pdf, sha)

    base = url_base(request)
    ok, error = _correo_al_cliente(solicitud, pdf, base)
    db.marcar_email(ident, ok, error)
    _aviso_n8n(solicitud, f"{base}/contrato/{ident}.pdf?t={token(ident)}")

    return plantilla(
        request,
        "gracias.html",
        {
            "cfg": conf,
            "solicitud": solicitud,
            "t": token(ident),
            "email_ok": ok or (not correo.configurado() and bool(os.getenv("N8N_WEBHOOK_URL"))),
            "email_error": error,
        },
    )


@app.get("/contrato/{ident}.pdf")
def descargar_contrato(request: Request, ident: str, t: str = ""):
    registro = db.obtener(ident)
    if not registro or not registro.get("pdf_archivo"):
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    if not token_valido(ident, t) and not panel_autorizado(request):
        raise HTTPException(status_code=403, detail="Enlace no válido")
    archivo = db.PDFS_DIR / registro["pdf_archivo"]
    return Response(
        content=archivo.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{registro["pdf_archivo"]}"'},
    )


@app.get("/firmado/{ident}", response_class=HTMLResponse)
def formulario_firmado(request: Request, ident: str, t: str = ""):
    registro = db.obtener(ident)
    if not registro or not token_valido(ident, t):
        raise HTTPException(status_code=404, detail="Enlace no válido")
    return plantilla(
        request, "firmado.html", {"cfg": cfg(), "solicitud": registro, "t": t, "hecho": False, "error": None}
    )


@app.post("/firmado/{ident}", response_class=HTMLResponse)
async def subir_firmado(
    request: Request, ident: str, archivo: UploadFile = File(...), t: str = Form("")
):
    registro = db.obtener(ident)
    if not registro or not token_valido(ident, t):
        raise HTTPException(status_code=404, detail="Enlace no válido")

    contexto = {"cfg": cfg(), "solicitud": registro, "t": t, "hecho": False, "error": None}
    contenido = await archivo.read()

    if not contenido:
        contexto["error"] = "No has seleccionado ningún archivo."
        return plantilla(request, "firmado.html", contexto, status=400)
    if len(contenido) > MAX_FIRMADO:
        contexto["error"] = "El archivo es demasiado grande (máximo 15 MB)."
        return plantilla(request, "firmado.html", contexto, status=400)

    db.guardar_firmado(ident, contenido, archivo.filename or "firmado.pdf")

    aviso = os.getenv("AVISO_FIRMADO_EMAIL") or os.getenv("ARRENDADOR_EMAIL")
    if aviso and correo.configurado():
        try:
            correo.enviar(
                para=aviso,
                asunto=f"Contrato firmado recibido: {registro['numero_contrato']}",
                texto=(
                    f"El cliente {registro.get('empresa')} ({registro.get('email')}) ha subido el contrato "
                    f"nº {registro['numero_contrato']} firmado.\n\n"
                    f"Puedes descargarlo desde el panel: {url_base(request)}/panel"
                ),
            )
        except Exception:  # noqa: BLE001
            pass

    contexto["hecho"] = True
    return plantilla(request, "firmado.html", contexto)


# --------------------------------------------------------------------------- #
# Panel privado
# --------------------------------------------------------------------------- #
def _cookie_panel() -> str:
    return hmac.new(secreto(), b"panel", hashlib.sha256).hexdigest()


def panel_autorizado(request: Request) -> bool:
    clave = os.getenv("PANEL_PASSWORD", "")
    return bool(clave) and request.cookies.get("panel") == _cookie_panel()


@app.get("/panel", response_class=HTMLResponse)
def panel(request: Request):
    if not panel_autorizado(request):
        return plantilla(request, "panel_login.html", {"cfg": cfg(), "error": None}, status=200)
    return plantilla(
        request,
        "panel.html",
        {"cfg": cfg(), "solicitudes": db.listar(), "token": token},
    )


@app.post("/panel/login")
def panel_login(request: Request, clave: str = Form("")):
    esperada = os.getenv("PANEL_PASSWORD", "")
    if esperada and hmac.compare_digest(clave, esperada):
        respuesta = RedirectResponse("/panel", status_code=303)
        respuesta.set_cookie(
            "panel", _cookie_panel(), httponly=True, samesite="lax", max_age=60 * 60 * 12
        )
        return respuesta
    return plantilla(
        request, "panel_login.html", {"cfg": cfg(), "error": "Contraseña incorrecta."}, status=401
    )


@app.get("/panel/firmado/{ident}")
def panel_firmado(request: Request, ident: str):
    if not panel_autorizado(request):
        raise HTTPException(status_code=403)
    registro = db.obtener(ident)
    if not registro or not registro.get("firmado_archivo"):
        raise HTTPException(status_code=404)
    archivo = db.FIRMADOS_DIR / registro["firmado_archivo"]
    return Response(
        content=archivo.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{registro["firmado_archivo"]}"'},
    )


@app.post("/panel/estado/{ident}")
def panel_estado(request: Request, ident: str, estado: str = Form(""), notas: str = Form("")):
    if not panel_autorizado(request):
        raise HTTPException(status_code=403)
    db.actualizar_estado(ident, estado or "aceptado", notas)
    return RedirectResponse("/panel", status_code=303)