# -*- coding: utf-8 -*-
"""Contrato resumido: dos páginas de contrato más una de albarán de entrega y devolución.

Usa los mismos datos del formulario y los mismos ayudantes de relleno que el contrato
completo (app/contrato.py). Es autosuficiente: sus condiciones son las únicas aplicables.
"""
from __future__ import annotations

import hashlib

from weasyprint import HTML

from .contrato import BASE, _e, _marcar, _css, eur, fecha, hora, v

VERSION_CONTRATO_CORTO = "1.0-resumido-octubre-2026"

_CSS_CORTO = """
html { font-size: 9.6pt; }
@page { margin: 14mm 15mm 15mm 15mm; }
body { line-height: 1.32; }
h1 { font-size: 13pt; margin: 0 0 2pt; color: #1b4d7a; }
h2.seccion { font-size: 9.6pt; margin: 8pt 0 3pt; padding-bottom: 1pt; }
p { margin: 0 0 3pt; }
.sub { font-size: 8pt; color: #444; margin: 0 0 6pt; }
.tabla-datos { font-size: 8.4pt; margin: 3pt 0 5pt; }
.tabla-datos th, .tabla-datos td { padding: 2.2pt 3.5pt; }
.dos { width: 100%; }
.dos td { width: 50%; vertical-align: top; padding: 0 4pt 0 0; border: 0; }
ol.cond { margin: 0; padding-left: 13pt; }
ol.cond li { margin: 0 0 3.2pt; text-align: justify; }
.tabla-firmas td { padding: 5pt; }
.tabla-firmas .firma-espacio { height: 34pt; }
.acept { font-size: 7.4pt; color: #333; margin-top: 6pt; }
.acept td, .acept th { padding: 1.6pt 3.5pt; }
.linea-manual { border-bottom: 0.6pt solid #555; height: 13pt; margin: 0 0 2pt; }
.cajas { font-size: 8.6pt; text-align: left; }
.arriba { margin-top: 0; }
"""


def _tabla_maquinas(datos: dict) -> str:
    filas = []
    for n in range(1, 5):
        desc = datos.get(f"maq{n}_desc")
        marca = datos.get(f"maq{n}_marca")
        serie = datos.get(f"maq{n}_serie")
        tarifa = datos.get(f"maq{n}_tarifa") or datos.get("precio_dia") if n == 1 else datos.get(f"maq{n}_tarifa")
        if not any(str(x or "").strip() for x in (desc, marca, serie)):
            continue
        filas.append(
            f"<tr><td>{n}</td><td>{v(desc, 14)}</td><td>{v(marca, 12)}</td>"
            f"<td>{v(serie, 12)}</td><td>{eur(tarifa)}</td></tr>"
        )
    if not filas:
        filas.append("<tr><td>1</td>" + "<td>&nbsp;</td>" * 4 + "</tr>")
    return "\n".join(filas)


def _lista_maquinas(datos: dict) -> str:
    nombres = []
    for n in range(1, 5):
        desc = (datos.get(f"maq{n}_desc") or "").strip()
        marca = (datos.get(f"maq{n}_marca") or "").strip()
        serie = (datos.get(f"maq{n}_serie") or "").strip()
        if desc or marca or serie:
            partes = " · ".join(x for x in (desc, marca, serie) if x)
            nombres.append(_e(partes))
    return "<br>".join(nombres) if nombres else v("", 60)


def _pagina_contrato(datos: dict, cfg: dict, solicitud: dict) -> str:
    arr = cfg["arrendador"]
    juzgados = cfg.get("juzgados") or ""
    juzgados_txt = _e(juzgados) if juzgados else v("", 22)
    return f"""
    <h1>CONTRATO DE ALQUILER DE MAQUINARIA</h1>
    <p class="sub">Sin operador y sin combustible · Nº {_e(solicitud.get('numero_contrato'))} ·
    {_e(solicitud.get('fecha_texto'))} · versión resumida {_e(solicitud.get('version_contrato'))}</p>

    <table class="dos"><tr>
      <td>
        <table class="tabla-datos">
          <tr><th colspan="2">ARRENDADOR</th></tr>
          <tr><td colspan="2">{v(arr.get('razon'), 30)}</td></tr>
          <tr><th>CIF</th><td>{v(arr.get('cif'), 12)}</td></tr>
          <tr><th>Representante</th><td>{v(arr.get('representante'), 20)} · DNI {v(arr.get('dni'), 10)}</td></tr>
          <tr><th>Domicilio</th><td>{v(arr.get('domicilio'), 30)}</td></tr>
          <tr><th>Contacto</th><td>{v(arr.get('telefono'), 12)} · {v(arr.get('email'), 20)}</td></tr>
        </table>
      </td>
      <td>
        <table class="tabla-datos">
          <tr><th colspan="2">ARRENDATARIO</th></tr>
          <tr><td colspan="2">{v(datos.get('arr_razon'), 30)}</td></tr>
          <tr><th>CIF/NIF</th><td>{v(datos.get('arr_cif'), 12)}</td></tr>
          <tr><th>Representante</th><td>{v(datos.get('arr_representante'), 20)} · DNI {v(datos.get('arr_dni'), 10)}</td></tr>
          <tr><th>Domicilio</th><td>{v(datos.get('arr_domicilio'), 30)}</td></tr>
          <tr><th>Contacto</th><td>{v(datos.get('arr_telefono'), 12)} · {v(datos.get('arr_email'), 20)}</td></tr>
        </table>
      </td>
    </tr></table>

    <h2 class="seccion">1. Máquina alquilada</h2>
    <table class="tabla-datos">
      <thead><tr><th>Nº</th><th>Máquina</th><th>Marca / modelo</th><th>Serie / matrícula</th><th>Precio por jornada</th></tr></thead>
      <tbody>{_tabla_maquinas(datos)}</tbody>
    </table>
    <p>Accesorios y observaciones: {v(datos.get('maq1_accesorios') or datos.get('maq_observaciones'), 60)}</p>

    <h2 class="seccion">2. Obra, uso y duración</h2>
    <p><strong>Lugar de uso:</strong> {v(datos.get('obra_direccion'), 60)}, {v(datos.get('obra_municipio'), 20)}.<br>
    <strong>Trabajo previsto:</strong> {v(datos.get('obra_uso'), 60)}</p>
    <p><strong>Entrega:</strong> {fecha(datos.get('fecha_inicio'))} a las {hora(datos.get('hora_inicio'))} h ·
    <strong>Devolución prevista:</strong> {fecha(datos.get('fecha_fin'))} ·
    <strong>Prórroga:</strong> {_marcar(datos.get('prorroga') == 'automatica')} automática
    {_marcar(datos.get('prorroga') == 'expresa')} solo por escrito · Preaviso de devolución: {v(datos.get('preaviso_dias'), 4)} días</p>

    <h2 class="seccion">3. Precio y pago (más IVA)</h2>
    <p><strong>Jornada de 8 h:</strong> {eur(datos.get('precio_dia'))} ·
    <strong>Semana:</strong> {eur(datos.get('precio_semana'))} ·
    <strong>Mes:</strong> {eur(datos.get('precio_mes'))} ·
    <strong>Hora adicional:</strong> {eur(datos.get('precio_hora'))}<br>
    <strong>Transporte:</strong> ida {eur(datos.get('transporte_ida'))}, vuelta {eur(datos.get('transporte_vuelta'))} ·
    <strong>Otros conceptos:</strong> {v(datos.get('otros_conceptos'), 22)}<br>
    <strong>Fianza:</strong> {eur(datos.get('fianza'))} ({v(datos.get('fianza_modalidad'), 14)}) ·
    <strong>Pago:</strong> transferencia a {v(datos.get('iban') or arr.get('iban'), 28)} en
    {v(datos.get('plazo_pago') or '30', 4)} días desde la factura</p>

    <h2 class="seccion">4. Condiciones esenciales</h2>
    <ol class="cond">
      <li><strong>Modalidad.</strong> Alquiler sin operador y sin combustible: el arrendador entrega la máquina en
        condiciones de trabajo; el arrendatario la maneja con personal propio habilitado y solo en la obra y para el
        trabajo indicados.</li>
      <li><strong>Jornada y precio.</strong> La jornada es de 8 horas de lunes a viernes; las horas de más se cobran en
        proporción. Los precios no incluyen IVA. La lectura del horómetro anotada en el albarán sirve para facturar.
        Los días de máquina a disposición se cobran aunque no se trabaje (lluvia, falta de permisos, obra parada).</li>
      <li><strong>Entrega y devolución.</strong> Al retirar la máquina y al devolverla se firma el albarán de la última
        página: con esa firma queda formalizada la entrega y el contrato. Se devuelve limpia, con sus accesorios, en el lugar
        y fecha pactados. Si no se devuelve a tiempo, se cobra el precio más un recargo del 25 % por día de retraso.</li>
      <li><strong>Combustible y mantenimiento.</strong> Combustible, lubricantes y AdBlue son por cuenta del arrendatario,
        que hace cada día el mantenimiento básico (niveles, engrase, limpieza). No repara ni modifica la máquina sin
        permiso escrito del arrendador.</li>
      <li><strong>Averías.</strong> El arrendatario avisa de inmediato y lo confirma por escrito en 24 horas. El
        arrendador repara o sustituye la máquina en 2 días hábiles y no cobra el tiempo parado si la avería no es culpa
        del arrendatario. Si es por mal uso o falta de mantenimiento, la reparación y la parada son por cuenta del
        arrendatario.</li>
      <li><strong>Daños, robo y custodia.</strong> El arrendatario responde de los daños, la pérdida y el robo mientras
        tenga la máquina. Debe guardarla en recinto cerrado, con llaves retiradas y bloqueos puestos. Neumáticos, cadenas,
        cuchillas y dientes por uso anormal son por su cuenta. En pérdida total o robo paga el valor de reposición menos un
        10 % por año de antigüedad (descuento máximo del 40 %) y nunca menos de 500 €.</li>
      <li><strong>Prohibido.</strong> Ceder, subarrendar o trasladar la máquina a otra obra sin permiso escrito; dejarla
        manejar a personas no habilitadas; anular dispositivos de seguridad o tocar el horómetro (si se manipula, se
        presume un uso de 10 horas diarias); usarla para otro trabajo o por encima de su capacidad.</li>
      <li><strong>Seguros y multas.</strong> El arrendatario debe tener un seguro de responsabilidad civil que cubra los
        daños a terceros ({v(datos.get('rc_cobertura'), 10)} € mínimo) y entregar copia. Las multas y los daños a terceros
        son suyos; si el arrendador recibe una multa, el arrendatario identifica al conductor en 10 días.</li>
      <li><strong>Pago y fianza.</strong> Pago en el plazo indicado. Si no paga a tiempo, se devengan sin aviso los
        intereses de demora de la Ley 3/2004 y 40 € por factura impagada. La fianza responde de las rentas, los daños y
        los gastos, y se devuelve tras comprobar el estado de la máquina y pagar todo lo debido.</li>
      <li><strong>Resolución.</strong> El arrendador puede resolver el contrato y retirar la máquina, con acceso a la obra,
        si hay impago, uso indebido, cesión o falta de seguro. El arrendatario la devuelve en 24 horas desde el
        requerimiento y paga lo devengado, incluidos los gastos de retirada.</li>
      <li><strong>Datos y jurisdicción.</strong> Los datos personales se tratan para gestionar este contrato conforme al
        RGPD y la LOPDGDD; el arrendador puede comunicar los impagos a ficheros de morosidad cuando la ley lo permita. Se
        aplica la ley española y las partes se someten a los juzgados de {juzgados_txt}. En lo no previsto
        se aplica el Código Civil.</li>
      <li><strong>Firma electrónica y copia firmada.</strong> La aceptación en la web, con fecha, hora y dirección IP,
        queda como prueba. El arrendatario firma también el ejemplar y lo devuelve o firma el albarán al retirar la máquina.</li>
    </ol>
    """


def _firmas_y_aceptacion(solicitud: dict, datos: dict) -> str:
    return f"""
    <table class="tabla-firmas">
      <tr>
        <td><p class="firma-titulo">EL ARRENDADOR</p><div class="firma-espacio"></div>
            <p class="firma-pie">Firma y sello · Fecha: {v('', 14)}</p></td>
        <td><p class="firma-titulo">EL ARRENDATARIO — {_e(datos.get('firma_nombre'))}</p><div class="firma-espacio"></div>
            <p class="firma-pie">Firma · Fecha: {v('', 14)}</p></td>
      </tr>
    </table>
    <table class="tabla-datos acept">
      <tr><th colspan="4">Aceptación telemática (justificante)</th></tr>
      <tr><th>Aceptado el</th><td>{_e(solicitud.get('creado'))}</td><th>Aceptante</th><td>{_e(solicitud.get('aceptante') or solicitud.get('empresa'))}</td></tr>
      <tr><th>IP</th><td>{_e(solicitud.get('ip'))}</td><th>Versión</th><td>{_e(solicitud.get('version_contrato'))}</td></tr>
      <tr><th>Correo</th><td colspan="3">{_e(solicitud.get('email'))}</td></tr>
      <tr><th>Navegador</th><td colspan="3" class="pequeno">{_e(solicitud.get('user_agent'))}</td></tr>
    </table>
    """


def _albaran(datos: dict, solicitud: dict) -> str:
    doc = [
        "Ficha técnica / permiso de circulación",
        "ITV en vigor",
        "Seguro obligatorio",
        "Marcado CE / manual",
        "Registro de mantenimiento",
    ]
    cajas = " &nbsp; ".join(f"☐ {d}" for d in doc)
    return f"""
    <div class="salto"></div>
    <h1>ALBARÁN DE ENTREGA Y DEVOLUCIÓN</h1>
    <p class="sub">Forma parte del contrato nº {_e(solicitud.get('numero_contrato'))} · Arrendatario:
    {v(datos.get('arr_razon'), 30)}</p>
    <p><strong>Máquina(s):</strong><br>{_lista_maquinas(datos)}</p>
    <p><strong>Lugar de uso:</strong> {v(datos.get('obra_direccion'), 60)}</p>

    <h2 class="seccion">A) ENTREGA</h2>
    <table class="tabla-datos">
      <tr><th>Fecha y hora</th><td>{fecha(datos.get('fecha_inicio'))} · {hora(datos.get('hora_inicio'))} h</td>
          <th>Horómetro inicial</th><td>{v('', 14)}</td></tr>
      <tr><th>Combustible</th><td>{v('', 14)}</td><th>Entregado por</th><td>{v('', 18)}</td></tr>
      <tr><th>Accesorios entregados</th><td colspan="3">{v(datos.get('maq1_accesorios'), 50)}</td></tr>
    </table>
    <p class="cajas">Documentación entregada: {cajas}</p>
    <p>Estado aparente y observaciones (golpes, fugas, neumáticos, cristales, luces):</p>
    <div class="linea-manual"></div><div class="linea-manual"></div><div class="linea-manual"></div>
    <p class="cajas">☐ El arrendatario recibe la máquina conforme y sin reservas, salvo las anotadas arriba.</p>
    <table class="tabla-firmas"><tr>
      <td><p class="firma-titulo">POR EL ARRENDADOR</p><div class="firma-espacio"></div><p class="firma-pie">Nombre y firma</p></td>
      <td><p class="firma-titulo">POR EL ARRENDATARIO</p><div class="firma-espacio"></div><p class="firma-pie">Nombre y firma</p></td>
    </tr></table>

    <h2 class="seccion">B) DEVOLUCIÓN</h2>
    <table class="tabla-datos">
      <tr><th>Fecha y hora</th><td>{v('', 18)}</td><th>Horómetro final</th><td>{v('', 14)}</td></tr>
      <tr><th>Horas trabajadas</th><td>{v('', 14)}</td><th>Combustible</th><td>{v('', 14)}</td></tr>
      <tr><th>Importe pendiente</th><td>{v('', 14)} €</td><th>Recibido por</th><td>{v('', 18)}</td></tr>
    </table>
    <p>Estado, limpieza, accesorios, documentación y daños apreciados (con valoración provisional):</p>
    <div class="linea-manual"></div><div class="linea-manual"></div><div class="linea-manual"></div>
    <table class="tabla-firmas"><tr>
      <td><p class="firma-titulo">POR EL ARRENDADOR</p><div class="firma-espacio"></div><p class="firma-pie">Nombre y firma</p></td>
      <td><p class="firma-titulo">POR EL ARRENDATARIO</p><div class="firma-espacio"></div><p class="firma-pie">Nombre y firma</p></td>
    </tr></table>
    """


def construir_html(datos: dict, cfg: dict, solicitud: dict) -> str:
    cuerpo = _pagina_contrato(datos, cfg, solicitud) + _firmas_y_aceptacion(solicitud, datos) + _albaran(datos, solicitud)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8">
<title>Contrato {_e(solicitud.get('numero_contrato'))}</title>
<style>{_css(solicitud.get('numero_contrato', ''))}{_CSS_CORTO}</style>
</head>
<body>{cuerpo}</body>
</html>"""


def generar_pdf(datos: dict, cfg: dict, solicitud: dict) -> tuple[bytes, str, str]:
    """Devuelve (pdf_bytes, sha256, html), igual que contrato.generar_pdf."""
    html = construir_html(datos, cfg, solicitud)
    pdf = HTML(string=html, base_url=str(BASE)).write_pdf()
    return pdf, hashlib.sha256(pdf).hexdigest(), html
