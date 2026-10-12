# -*- coding: utf-8 -*-
"""Envío de correos por SMTP (con el contrato en PDF adjunto)."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr


def configurado() -> bool:
    return bool(os.getenv("SMTP_HOST"))


def _conectar():
    host = os.getenv("SMTP_HOST", "")
    puerto = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER", "")
    clave = os.getenv("SMTP_PASS", "")
    seguro = os.getenv("SMTP_SSL", "auto").lower()  # auto | ssl | starttls | ninguna

    if seguro == "auto":
        seguro = "ssl" if puerto == 465 else "starttls"

    if seguro == "ssl":
        servidor = smtplib.SMTP_SSL(host, puerto, timeout=30, context=ssl.create_default_context())
    else:
        servidor = smtplib.SMTP(host, puerto, timeout=30)
        servidor.ehlo()
        if seguro == "starttls":
            servidor.starttls(context=ssl.create_default_context())
            servidor.ehlo()

    if usuario:
        servidor.login(usuario, clave)
    return servidor


def enviar(
    *,
    para: str,
    asunto: str,
    texto: str,
    html: str | None = None,
    responder_a: str | None = None,
    copia: str | None = None,
    adjuntos: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """adjuntos: lista de (nombre_archivo, contenido_bytes, tipo_mime)."""
    remitente = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "contratos@localhost"
    nombre_remitente = os.getenv("SMTP_FROM_NAME", "")

    mensaje = EmailMessage()
    mensaje["From"] = formataddr((nombre_remitente, remitente)) if nombre_remitente else remitente
    mensaje["To"] = para
    mensaje["Subject"] = asunto
    if responder_a:
        mensaje["Reply-To"] = responder_a
    if copia:
        mensaje["Bcc"] = copia
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    for nombre, contenido, mime in adjuntos or []:
        principal, _, sub = mime.partition("/")
        mensaje.add_attachment(
            contenido, maintype=principal or "application", subtype=sub or "octet-stream", filename=nombre
        )

    servidor = _conectar()
    try:
        servidor.send_message(mensaje)
    finally:
        try:
            servidor.quit()
        except Exception:
            pass