# -*- coding: utf-8 -*-
"""Composición del contrato personalizado y generación del PDF.

Toma el modelo estándar del contrato (assets/contrato_general.md), le inyecta las
condiciones particulares rellenadas desde el formulario y produce un PDF único con
la hoja de aceptación telemática y su justificante de evidencia.
"""
from __future__ import annotations

import hashlib
import html as _html
import re
from datetime import datetime
from pathlib import Path

import markdown
from weasyprint import HTML

BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "assets"

VERSION_CONTRATO = "1.0-octubre-2026"

_MD = (ASSETS / "contrato_general.md").read_text(encoding="utf-8")


def _bloque(inicio: str, fin: str | None) -> str:
    i = _MD.find(inicio)
    if i < 0:
        return ""
    if fin is None:
        return _MD[i:]
    j = _MD.find(fin, i + 1)
    return _MD[i:j] if j > 0 else _MD[i:]


EXPONEN = _bloque("## EXPONEN", "# ESTIPULACIONES")
ESTIPULACIONES = _bloque("# ESTIPULACIONES", "# ANEXO I")
ANEXOS_FINALES = _bloque("# ANEXO III", None)


def _md_a_html(texto: str) -> str:
    return markdown.markdown(texto, extensions=["tables", "sane_lists"])


# --------------------------------------------------------------------------- #
# Utilidades de relleno
# --------------------------------------------------------------------------- #
def v(valor, ancho: int = 30) -> str:
    """Devuelve el valor escapado o una línea de puntos para rellenar a mano."""
    texto = str(valor or "").strip()
    if not texto:
        return '<span class="linea">' + ("_" * ancho) + "</span>"
    return _html.escape(texto)


def _e(valor) -> str:
    """Escapa un valor de texto tolerando None."""
    return _html.escape(str(valor or ""))


def eur(valor) -> str:
    """Interpreta el importe en formato español (1.150 o 1150,50) y lo formatea."""
    texto = str(valor or "").strip()
    if not texto:
        return v("", 14)
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not limpio:
        return _html.escape(texto)
    try:
        if "." in limpio and "," in limpio:
            numero = float(limpio.replace(".", "").replace(",", "."))
        elif "," in limpio:
            numero = float(limpio.replace(",", "."))
        elif "." in limpio and len(limpio.split(".")[-1]) == 3:
            numero = float(limpio.replace(".", ""))
        else:
            numero = float(limpio)
    except ValueError:
        return _html.escape(texto)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def fecha(valor: str, largo: bool = False) -> str:
    """Convierte 2026-10-12 en 12/10/2026 (o 12 de octubre de 2026)."""
    texto = (valor or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if not m:
        return v(texto, 18)
    a, me, d = m.groups()
    if largo:
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                 "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{int(d)} de {meses[int(me)]} de {a}"
    return f"{d}/{me}/{a}"


def hora(valor: str) -> str:
    texto = (valor or "").strip()
    return _html.escape(texto) if texto else v("", 8)


def _si_no(valor: str, si: str, no: str, ancho: int = 26) -> str:
    texto = (valor or "").strip().lower()
    if texto in ("si", "sí", "s", "true", "1"):
        return _html.escape(si)
    if texto in ("no", "n", "false", "0"):
        return _html.escape(no)
    return v("", ancho)


def _marcar(condicion) -> str:
    return "☒" if condicion else "☐"


# --------------------------------------------------------------------------- #
# Secciones generadas
# --------------------------------------------------------------------------- #
def _cabecera(solicitud: dict) -> str:
    return f"""
    <div class="portada">
      <div class="portada-etiqueta">Documento contractual</div>
      <h1 class="portada-titulo">CONTRATO DE ARRENDAMIENTO DE MAQUINARIA<br>Y VEHÍCULOS DE OBRA PÚBLICA</h1>
      <div class="portada-sub">Modalidad sin operador y sin combustible · máquina entregada en condiciones de trabajo</div>
      <table class="tabla-resumen">
        <tr><th>Nº de contrato</th><td>{_e(solicitud.get('numero_contrato'))}</td>
            <th>Fecha</th><td>{_e(solicitud.get('fecha_texto'))}</td></tr>
        <tr><th>Arrendatario</th><td>{v(solicitud.get('empresa'), 24)}</td>
            <th>CIF</th><td>{v(solicitud.get('cif'), 14)}</td></tr>
        <tr><th>Email</th><td>{v(solicitud.get('email'), 24)}</td>
            <th>Teléfono</th><td>{v(solicitud.get('telefono'), 14)}</td></tr>
        <tr><th>Versión</th><td>{_e(solicitud.get('version_contrato'))}</td>
            <th>Emitido</th><td>{_e(solicitud.get('creado'))}</td></tr>
      </table>
      <p class="nota">Documento generado electrónicamente a partir de la solicitud aceptada en
      {_e(solicitud.get('web'))}. El ejemplar firmado por ambas partes y las actas de entrega
      y devolución forman parte inseparable de este contrato.</p>
    </div>
    """


def _partes(datos: dict, cfg: dict) -> str:
    arr = cfg["arrendador"]
    tipo = (datos.get("arr_tipo") or "").strip()
    razon = (datos.get("arr_razon") or "").strip()
    if tipo and tipo.lower() not in razon.lower():
        razon = f"{razon} ({tipo})" if razon else tipo
    cargo = (datos.get("arr_cargo") or "").strip()
    facultades = datos.get("arr_facultades") or (f"su condición de {cargo}" if cargo else "")
    return f"""
    <h2 class="seccion">REUNIDOS</h2>
    <p class="etiqueta">DE UNA PARTE — EL ARRENDADOR</p>
    <p>D./Dña. {v(arr.get('representante'), 34)}, mayor de edad, con DNI/NIE nº {v(arr.get('dni'), 12)},
    en nombre y representación de la mercantil {v(arr.get('razon'), 34)} (en lo sucesivo,
    <strong>«el ARRENDADOR»</strong>), con CIF nº {v(arr.get('cif'), 12)} y domicilio social en
    {v(arr.get('domicilio'), 38)}, teléfono {v(arr.get('telefono'), 12)}, correo electrónico
    {v(arr.get('email'), 24)}.</p>
    <p>Actúa en su condición de administrador/representante legal de la sociedad, con facultades
    suficientes según escritura de poder o nombramiento {v(arr.get('poder'), 40)}, que declara vigente.</p>

    <p class="etiqueta">DE OTRA PARTE — EL ARRENDATARIO</p>
    <p>D./Dña. {v(datos.get('arr_representante'), 34)}, mayor de edad, con DNI/NIE nº
    {v(datos.get('arr_dni'), 12)}, en nombre y representación de la mercantil
    {v(razon, 34)}
    (en lo sucesivo, <strong>«el ARRENDATARIO»</strong>), con CIF nº {v(datos.get('arr_cif'), 12)} y
    domicilio social en {v(datos.get('arr_domicilio'), 38)}, teléfono {v(datos.get('arr_telefono'), 12)},
    correo electrónico {v(datos.get('arr_email'), 24)}.</p>
    <p>Actúa con facultades suficientes según {v(facultades, 40)}.</p>
    <p>Ambas partes se reconocen mutuamente la capacidad legal necesaria para contratar y obligarse, y con
    tal carácter, libremente y de buena fe,</p>
    """


def _maquinas(datos: dict) -> str:
    filas = []
    for n in range(1, 5):
        desc = datos.get(f"maq{n}_desc")
        marca = datos.get(f"maq{n}_marca")
        serie = datos.get(f"maq{n}_serie")
        acc = datos.get(f"maq{n}_accesorios")
        valor = datos.get(f"maq{n}_valor")
        tarifa = datos.get(f"maq{n}_tarifa")
        if not any(str(x or "").strip() for x in (desc, marca, serie, acc, valor, tarifa)):
            if n == 1:
                filas.append("<tr><td>1</td>" + "<td>&nbsp;</td>" * 7 + "</tr>")
            continue
        filas.append(
            "<tr>"
            f"<td>{n}</td>"
            f"<td>{v(desc, 10)}</td>"
            f"<td>{v(marca, 10)}</td>"
            f"<td>{v(serie, 10)}</td>"
            f"<td>{v(datos.get(f'maq{n}_horometro'), 8)}</td>"
            f"<td>{v(acc, 10)}</td>"
            f"<td>{eur(valor)}</td>"
            f"<td>{eur(tarifa)}</td>"
            "</tr>"
        )
    if len(filas) < 2:
        filas.append("<tr><td>2</td>" + "<td>&nbsp;</td>" * 7 + "</tr>")
    return "\n".join(filas)


def _anexo_i(datos: dict) -> str:
    return f"""
    <h2 class="seccion">ANEXO I. RELACIÓN DE MAQUINARIA Y VEHÍCULOS ARRENDADOS</h2>
    <table class="tabla-datos">
      <thead>
        <tr><th>Nº</th><th>Descripción y tipo de máquina</th><th>Marca / Modelo</th>
        <th>Nº serie / Matrícula</th><th>Horómetro</th><th>Accesorios</th>
        <th>Valor reposición</th><th>Tarifa</th></tr>
      </thead>
      <tbody>
      {_maquinas(datos)}
      </tbody>
    </table>
    <p><strong>Observaciones</strong> (accesorios, equipamiento, limitaciones del equipo, estado de desgaste,
    marcado CE, ITV en vigor, seguro):</p>
    <p class="relleno">{v(datos.get('maq_observaciones'), 120)}</p>
    """


def _anexo_ii(datos: dict, cfg: dict) -> str:
    arr = cfg["arrendador"]
    propietario = datos.get("maq_propiedad") or arr.get("razon")
    obj = v(propietario, 40) if propietario else "el ARRENDADOR"
    seguro_danos = (datos.get("seguro_danos") or "").strip()
    if seguro_danos == "arrendador":
        txt_seguro = (
            "☒ contratado por el ARRENDADOR (prima repercutida: "
            + v(datos.get("prima_pct"), 6)
            + " % del precio) &nbsp;&nbsp; ☐ no contratado"
        )
    elif seguro_danos == "no":
        txt_seguro = "☐ contratado por el ARRENDADOR &nbsp;&nbsp; ☒ no contratado"
    else:
        txt_seguro = "☐ contratado por el ARRENDADOR &nbsp;&nbsp; ☐ no contratado"
    return f"""
    <h2 class="seccion">ANEXO II. CONDICIONES PARTICULARES</h2>

    <p class="num">1. Partes</p>
    <ul>
      <li>ARRENDADOR: {v(arr.get('razon'), 40)} — CIF: {v(arr.get('cif'), 14)}</li>
      <li>ARRENDATARIO: {v(datos.get('arr_razon'), 40)} — CIF: {v(datos.get('arr_cif'), 14)}</li>
    </ul>

    <p class="num">2. Obra o emplazamiento de uso</p>
    <p class="relleno">{v(datos.get('obra_direccion'), 120)}<br>
    Término municipal: {v(datos.get('obra_municipio'), 40)}
    {(' · ' + _html.escape(datos.get('obra_ref'))) if datos.get('obra_ref') else ''}</p>

    <p class="num">3. Uso autorizado de la maquinaria</p>
    <p class="relleno">{v(datos.get('obra_uso'), 120)}</p>

    <p class="num">4. Duración</p>
    <ul>
      <li>Fecha de entrega: {fecha(datos.get('fecha_inicio'))} &nbsp;·&nbsp; Hora: {hora(datos.get('hora_inicio'))}</li>
      <li>Fecha de devolución prevista: {fecha(datos.get('fecha_fin'))}</li>
      <li>Prórroga: {_marcar(datos.get('prorroga') == 'automatica')} automática por períodos de
          {v(datos.get('prorroga_periodo'), 14)} &nbsp;&nbsp; {_marcar(datos.get('prorroga') == 'expresa')} expresa por escrito</li>
      <li>Preaviso de devolución: {v(datos.get('preaviso_dias'), 8)} días naturales</li>
    </ul>

    <p class="num">5. Precio</p>
    <ul>
      <li>Precio por día laborable (8 h): {eur(datos.get('precio_dia'))} + IVA</li>
      <li>Precio por semana (5 días / 40 h): {eur(datos.get('precio_semana'))} + IVA</li>
      <li>Precio por mes (21 días / 168 h): {eur(datos.get('precio_mes'))} + IVA</li>
      <li>Precio por hora adicional: {eur(datos.get('precio_hora'))} + IVA</li>
      <li>Duración mínima de facturación: {v(datos.get('minimo_facturacion'), 24)}</li>
      <li>Revisión de precios: {v(datos.get('revision_precios'), 46)}</li>
      <li>Transporte ida: {eur(datos.get('transporte_ida'))} + IVA — Transporte vuelta: {eur(datos.get('transporte_vuelta'))} + IVA</li>
      <li>Otros conceptos: {v(datos.get('otros_conceptos'), 60)}</li>
      <li>Presupuesto o tarifa aceptada por el ARRENDATARIO: {v(datos.get('presupuesto_ref'), 40)}</li>
    </ul>

    <p class="num">6. Pago y garantía</p>
    <ul>
      <li>Plazo de pago: {v(datos.get('plazo_pago'), 8)} días naturales desde la fecha de factura</li>
      <li>Cuenta bancaria del ARRENDADOR (IBAN): {v(datos.get('iban') or arr.get('iban'), 34)}</li>
      <li>Fianza o garantía: {eur(datos.get('fianza'))}, en la modalidad de {v(datos.get('fianza_modalidad'), 30)}</li>
      <li>Tipo de interés de demora pactado: {v(datos.get('interes_demora'), 30)}</li>
      <li>Periodicidad de facturación: {_marcar(datos.get('facturacion') == 'mensual')} mensual
          {_marcar(datos.get('facturacion') == 'final')} al final del arrendamiento
          {_marcar(datos.get('facturacion') == 'otra')} otra: {v(datos.get('facturacion_otra'), 20)}</li>
    </ul>

    <p class="num">7. Seguros</p>
    <ul>
      <li>RC de explotación del ARRENDATARIO: entidad {v(datos.get('rc_entidad'), 24)}, póliza nº
          {v(datos.get('rc_poliza'), 16)}, cobertura {eur(datos.get('rc_cobertura'))}</li>
      <li>Seguro de daños propios de la máquina:
          {txt_seguro}</li>
      <li>Franquicia a cargo del ARRENDATARIO: {v(datos.get('franquicia_pct'), 6)} % del siniestro, mínimo {eur(datos.get('franquicia_min'))}</li>
      <li>Seguro obligatorio de circulación (equipos matriculados): póliza nº {v(datos.get('poliza_circulacion'), 16)},
          vencimiento {fecha(datos.get('vencimiento_circulacion'))}</li>
    </ul>

    <p class="num">8. Obligaciones accesorias</p>
    <ul>
      <li>Personas autorizadas por el ARRENDATARIO para el uso de la máquina: {v(datos.get('personas_autorizadas'), 46)}</li>
      <li>Parte de horas: {_marcar(datos.get('parte_horas') == 'semanal')} semanal
          {_marcar(datos.get('parte_horas') == 'mensual')} mensual
          {_marcar(datos.get('parte_horas') == 'otro')} otro: {v(datos.get('parte_horas_otro'), 18)}</li>
      <li>Gastos de gestión de residuos: {v(datos.get('residuos'), 30)}</li>
      <li>Régimen de acceso e inspección: {v(datos.get('acceso_inspeccion'), 46)}</li>
    </ul>

    <p class="num">9. Observaciones</p>
    <p class="relleno">{v(datos.get('anexo2_observaciones'), 120)}</p>

    <p class="num">10. Titularidad y cargas</p>
    <p class="relleno">Se hace constar que la maquinaria relacionada en el Anexo I es propiedad de {obj} y que
    sobre ella no existen cargas, embargos ni limitaciones que impidan su arrendamiento, salvo las que se
    indican a continuación: {v(datos.get('cargas'), 60)}</p>
    """


def _certificado(solicitud: dict) -> str:
    return f"""
    <div class="salto"></div>
    <h2 class="seccion">HOJA DE ACEPTACIÓN TELEMÁTICA Y JUSTIFICANTE</h2>
    <p>El presente ejemplar ha sido generado automáticamente como consecuencia de la aceptación del contrato
    por el ARRENDATARIO a través del formulario telemático de contratación. Se deja constancia de los
    siguientes extremos, a efectos probatorios:</p>
    <table class="tabla-datos">
      <tr><th>Nº de contrato</th><td>{_e(solicitud.get('numero_contrato'))}</td></tr>
      <tr><th>Versión del contrato aceptada</th><td>{_e(solicitud.get('version_contrato'))}</td></tr>
      <tr><th>Fecha y hora de la aceptación</th><td>{_e(solicitud.get('creado'))}</td></tr>
      <tr><th>Aceptante</th><td>{_html.escape(solicitud.get('aceptante','') or solicitud.get('empresa',''))}</td></tr>
      <tr><th>Correo electrónico declarado</th><td>{_e(solicitud.get('email'))}</td></tr>
      <tr><th>Dirección IP</th><td>{_e(solicitud.get('ip'))}</td></tr>
      <tr><th>Navegador / dispositivo</th><td class="pequeno">{_e(solicitud.get('user_agent'))}</td></tr>
      <tr><th>Huella del documento (SHA-256)</th><td class="pequeno mono">{_e(solicitud.get('pdf_sha256'))}</td></tr>
    </table>
    <p class="declaracion">El ARRENDATARIO declara haber leído íntegramente este contrato, comprender su
    contenido y aceptarlo libremente, comprometiéndose a firmar el ejemplar en papel y a devolverlo firmado
    al ARRENDADOR, quedando este ejemplar electrónico como prueba de la aceptación y del contenido aceptado.</p>
    <table class="tabla-firmas">
      <tr>
        <td>
          <p class="firma-titulo">EL ARRENDADOR</p>
          <div class="firma-espacio"></div>
          <p class="firma-pie">Firma y sello<br>{v('', 26)}</p>
        </td>
        <td>
          <p class="firma-titulo">EL ARRENDATARIO</p>
          <div class="firma-espacio"></div>
          <p class="firma-pie">Firma<br>{v('', 26)}</p>
        </td>
      </tr>
    </table>
    """


_CSS_PLANTILLA = """
@page {
  size: A4;
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center {
    content: "Contrato __NUMERO__ · página " counter(page) " de " counter(pages);
    font-family: "DejaVu Sans", Arial, sans-serif; font-size: 7.5pt; color: #666;
  }
}
html { font-size: 10pt; }
body { font-family: "DejaVu Serif", Georgia, "Times New Roman", serif; color: #111; line-height: 1.42; }
h1, h2, h3, th, .etiqueta, .num { font-family: "DejaVu Sans", Arial, Helvetica, sans-serif; }
h1 { font-size: 15pt; margin: 0 0 8pt; }
h2 { font-size: 11.5pt; margin: 14pt 0 6pt; }
h2.seccion { border-bottom: 1.2pt solid #1b4d7a; padding-bottom: 2pt; color: #1b4d7a;
  string-set: numero ""; }
h3 { font-size: 10pt; margin: 10pt 0 4pt; }
p { margin: 0 0 6pt; text-align: justify; }
ul { margin: 0 0 7pt 0; padding-left: 14pt; }
li { margin: 0 0 3pt; text-align: justify; }
strong { font-weight: bold; }
table { border-collapse: collapse; width: 100%; }
.tabla-datos { font-size: 8.6pt; font-family: "DejaVu Sans", Arial, sans-serif; margin: 6pt 0 8pt; }
.tabla-datos th, .tabla-datos td { border: 0.6pt solid #7a7a7a; padding: 3.5pt 4pt; vertical-align: top; text-align: left; }
.tabla-datos thead th, .tabla-datos tr > th { background: #eef3f8; font-weight: bold; }
.tabla-firmas { margin-top: 14pt; font-size: 9pt; }
.tabla-firmas td { border: 0.6pt solid #7a7a7a; padding: 8pt; width: 50%; vertical-align: top; }
.firma-espacio { height: 55pt; }
.firma-titulo { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 8.5pt; font-weight: bold; margin: 0 0 4pt; }
.firma-pie { font-size: 8pt; color: #444; margin: 4pt 0 0; text-align: left; }
.portada { text-align: center; border: 1.4pt solid #1b4d7a; padding: 18pt 14pt; margin-bottom: 14pt; }
.portada-etiqueta { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 8pt; letter-spacing: 1.6pt;
  text-transform: uppercase; color: #1b4d7a; }
.portada-titulo { font-size: 14.5pt; line-height: 1.3; margin: 8pt 0 6pt; }
.portada-sub { font-size: 9.5pt; color: #333; margin-bottom: 12pt; }
.tabla-resumen { font-size: 8.6pt; font-family: "DejaVu Sans", Arial, sans-serif; text-align: left; margin-top: 6pt; }
.tabla-resumen th { background: #eef3f8; border: 0.6pt solid #7a7a7a; padding: 3.5pt 4pt; width: 16%; }
.tabla-resumen td { border: 0.6pt solid #7a7a7a; padding: 3.5pt 4pt; }
.nota { font-size: 7.8pt; color: #555; margin-top: 10pt; text-align: justify; }
.etiqueta { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 9pt; font-weight: bold; margin: 10pt 0 4pt; }
.num { font-size: 9.2pt; font-weight: bold; margin: 9pt 0 3pt; }
.relleno { text-align: left; }
.linea { color: #555; letter-spacing: 0.4pt; }
.salto { page-break-before: always; }
.declaracion { font-size: 9pt; border-left: 2.5pt solid #1b4d7a; padding: 6pt 8pt; background: #f6f9fc; }
.pequeno { font-size: 7.6pt; }
.mono { font-family: "DejaVu Sans Mono", monospace; word-break: break-all; }
table th { font-weight: bold; }
"""


def _css(numero: str = "") -> str:
    return _CSS_PLANTILLA.replace("__NUMERO__", numero or "")


def construir_html(datos: dict, cfg: dict, solicitud: dict) -> str:
    cuerpo = "\n".join(
        [
            _cabecera(solicitud),
            _partes(datos, cfg),
            _md_a_html(EXPONEN),
            _md_a_html(ESTIPULACIONES),
            '<div class="salto"></div>',
            _anexo_i(datos),
            '<div class="salto"></div>',
            _anexo_ii(datos, cfg),
            '<div class="salto"></div>',
            _md_a_html(ANEXOS_FINALES),
            _certificado(solicitud),
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8">
<title>Contrato {_e(solicitud.get('numero_contrato'))}</title>
<style>{_css(solicitud.get('numero_contrato',''))}</style>
</head>
<body>{cuerpo}</body>
</html>"""


def generar_pdf(datos: dict, cfg: dict, solicitud: dict) -> tuple[bytes, str, str]:
    """Devuelve (pdf_bytes, sha256, html)."""
    html = construir_html(datos, cfg, solicitud)
    pdf = HTML(string=html, base_url=str(BASE)).write_pdf()
    return pdf, hashlib.sha256(pdf).hexdigest(), html
