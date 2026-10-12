# -*- coding: utf-8 -*-
"""Genera el PDF del contrato con datos de ejemplo, para revisar el resultado."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("ARRENDADOR_RAZON", "Adara Excavaciones, S.L.")
os.environ.setdefault("ARRENDADOR_CIF", "B04000000")
os.environ.setdefault("ARRENDADOR_DOMICILIO", "C/ Ejemplo nº 1, 04740 Roquetas de Mar (Almería)")
os.environ.setdefault("ARRENDADOR_REPRESENTANTE", "Nombre Apellido Apellido")
os.environ.setdefault("ARRENDADOR_DNI", "00000000X")
os.environ.setdefault("ARRENDADOR_TELEFONO", "643 175 166")
os.environ.setdefault("ARRENDADOR_EMAIL", "contratos@infoadaraexcavaciones.es")
os.environ.setdefault("ARRENDADOR_IBAN", "ES00 0000 0000 0000 0000 0000")

from app import contrato  # noqa: E402

DATOS = {
    "arr_razon": "Excavaciones López e Hijos, S.L.",
    "arr_tipo": "S.L.",
    "arr_cif": "B04012345",
    "arr_domicilio": "Camino de la Vega nº 22, 04120 Almería",
    "arr_representante": "Manuel López García",
    "arr_dni": "12345678Z",
    "arr_cargo": "Administrador",
    "arr_telefono": "600 111 222",
    "arr_email": "manuel@excavacioneslopez.es",
    "obra_direccion": "Parcela 14 del sector UA-3, junto a la carretera AL-3200",
    "obra_municipio": "Roquetas de Mar (Almería)",
    "obra_ref": "Ref. catastral 04007A002000140000FG",
    "obra_uso": "Excavación y movimiento de tierras para cimentación de nave industrial, "
                "perfilado de taludes y carga de tierras sobrantes sobre camión. Terreno firme de zahorra.",
    "maq1_desc": "Miniexcavadora sobre orugas",
    "maq1_marca": "Kubota U48-4",
    "maq1_serie": "KUB12345 / Matrícula E-1234-BBC",
    "maq1_accesorios": "Cazo 600 mm, cazo de limpieza y martillo hidráulico de 250 kg",
    "maq2_desc": "Dumper giratorio autocargable",
    "maq2_marca": "Ausa DR1001",
    "maq2_serie": "AUS98765",
    "maq2_accesorios": "Con cabina y luces de trabajo",
    "maq_observaciones": "Equipos con marcado CE, ITV en vigor y seguro de circulación vigente. "
                         "Se entregan con el manual del fabricante.",
    "fecha_inicio": "2026-10-20",
    "hora_inicio": "08:00",
    "fecha_fin": "2026-11-20",
    "preaviso_dias": "7",
    "prorroga": "automatica",
    "prorroga_periodo": "1 mes",
    "precio_dia": "260",
    "precio_semana": "1.150",
    "precio_mes": "4.200",
    "precio_hora": "38",
    "minimo_facturacion": "1 semana",
    "transporte_ida": "180",
    "transporte_vuelta": "180",
    "revision_precios": "Revisión anual conforme al IPC",
    "otros_conceptos": "Gestión de residuos: 45 € por servicio de retirada",
    "presupuesto_ref": "Presupuesto nº 2026/118, aceptado por el cliente el 15/10/2026",
    "plazo_pago": "30",
    "iban": "ES91 2100 0418 4502 0005 1332",
    "fianza": "500",
    "fianza_modalidad": "transferencia",
    "interes_demora": "El previsto en el Anexo II del contrato",
    "facturacion": "mensual",
    "rc_entidad": "Mapfre",
    "rc_poliza": "RC-99887766",
    "rc_cobertura": "600.000",
    "seguro_danos": "no",
    "franquicia_pct": "10",
    "franquicia_min": "600",
    "poliza_circulacion": "CIR-11223344",
    "vencimiento_circulacion": "2027-03-31",
    "personas_autorizadas": "Manuel López García (DNI 12345678Z) y Andrés López Ruiz (DNI 87654321Y)",
    "parte_horas": "semanal",
    "residuos": "Los derivados de la retirada de tierras, por cuenta del arrendatario",
    "acceso_inspeccion": "Libre acceso del arrendador en horario de obra, con aviso de una hora",
    "anexo2_observaciones": "El arrendatario dispone de la formación acreditada para el manejo de la "
                            "miniexcavadora y del certificado del martillo hidráulico.",
    "firma_nombre": "Manuel López García",
    "firma_cargo": "Administrador",
    "acepta": "si",
    "acepta_datos": "si",
    "acepta_whatsapp": "si",
}

CFG = {
    "empresa": "Adara Excavaciones",
    "web": "https://contratos.infoadaraexcavaciones.es",
    "email_contacto": os.environ["ARRENDADOR_EMAIL"],
    "telefono_contacto": os.environ["ARRENDADOR_TELEFONO"],
    "contrato_url": "https://contratos.infoadaraexcavaciones.es/",
    "arrendador": {
        "razon": os.environ["ARRENDADOR_RAZON"],
        "cif": os.environ["ARRENDADOR_CIF"],
        "domicilio": os.environ["ARRENDADOR_DOMICILIO"],
        "representante": os.environ["ARRENDADOR_REPRESENTANTE"],
        "dni": os.environ["ARRENDADOR_DNI"],
        "telefono": os.environ["ARRENDADOR_TELEFONO"],
        "email": os.environ["ARRENDADOR_EMAIL"],
        "iban": os.environ["ARRENDADOR_IBAN"],
        "poder": "de fecha 12/03/2024",
    },
}

SOLICITUD = {
    "id": "abc123def456",
    "numero_contrato": "ARR-2026-ABC123",
    "creado": "2026-10-12 15:20:00 +0200",
    "fecha_texto": "12/10/2026",
    "version_contrato": contrato.VERSION_CONTRATO,
    "empresa": DATOS["arr_razon"],
    "cif": DATOS["arr_cif"],
    "email": DATOS["arr_email"],
    "telefono": DATOS["arr_telefono"],
    "aceptante": DATOS["firma_nombre"],
    "ip": "85.84.123.45",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
    "web": CFG["web"],
    "pdf_sha256": "0" * 64,
}

if __name__ == "__main__":
    pdf, sha, html = contrato.generar_pdf(DATOS, CFG, SOLICITUD)
    salida = Path("/tmp/contrato-prueba.pdf")
    salida.write_bytes(pdf)
    Path("/tmp/contrato-prueba.html").write_text(html, encoding="utf-8")
    print("PDF:", salida, len(pdf), "bytes")
    print("SHA256:", sha)