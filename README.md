# Contratación telemática de arrendamiento de maquinaria

Servicio web que sustituye al contrato en papel: el cliente rellena un formulario, acepta el
contrato, recibe el PDF **ya cumplimentado** en su correo, lo firma y lo devuelve (por correo o
subiéndolo). Todo queda registrado con sus evidencias y consultable desde un panel privado.

Se apoya en el modelo de contrato estándar de arrendamiento de maquinaria de obra pública
**sin operador y sin combustible**, con las condiciones particulares y los anexos.

## Qué hace

| Ruta | Para qué |
|---|---|
| `/` | Formulario público de contratación |
| `POST /solicitar` | Valida, genera el PDF, guarda las evidencias y envía el correo al cliente |
| `/contrato/{id}.pdf?t=...` | Descarga del contrato (enlace firmado, no adivinable) |
| `/firmado/{id}?t=...` | El cliente sube el ejemplar firmado |
| `/panel` | Panel privado: listado, descarga, ejemplar firmado y estado |
| `/healthz` | Comprobación de estado |

El PDF que genera incluye, además del contrato completo: la portada con los datos del
expediente, las partes identificadas, el **Anexo I** (relación de máquinas) y el **Anexo II**
(condiciones particulares) rellenados, los anexos III y IV íntegros y, al final, la
**hoja de aceptación telemática** con fecha, IP, navegador, versión del contrato y huella
SHA-256 del documento.

## Variables de configuración

Todas se pasan por entorno (en EasyPanel, en la sección **Entorno** del servicio).

### Datos de la empresa (arrendador)

| Variable | Ejemplo | Para qué |
|---|---|---|
| `EMPRESA_NOMBRE` | `Adara Excavaciones` | Nombre comercial que aparece en las páginas y correos |
| `ARRENDADOR_RAZON` | `Adara Excavaciones, S.L.` | Razón social en el contrato |
| `ARRENDADOR_CIF` | `B04xxxxxx` | CIF del arrendador |
| `ARRENDADOR_DOMICILIO` | `C/ ..., 04740 Roquetas de Mar (Almería)` | Domicilio social |
| `ARRENDADOR_REPRESENTANTE` | `Nombre Apellidos` | Persona que representa a la sociedad |
| `ARRENDADOR_DNI` | `00000000X` | DNI del representante |
| `ARRENDADOR_TELEFONO` | `643 175 166` | Teléfono de contacto |
| `ARRENDADOR_EMAIL` | `contratos@infoadaraexcavaciones.es` | Correo de contacto y de respuesta (`Reply-To`) |
| `ARRENDADOR_IBAN` | `ES..` | Cuenta para el pago (Anexo II) |
| `ARRENDADOR_PODER` | `de fecha 12/03/2024` | Fecha del poder o nombramiento |
| `CONTRATO_URL` | `https://contratos.infoadaraexcavaciones.es/` | Enlace al contrato completo que cita la casilla |
| `PRIVACIDAD_URL` | `https://adara.../privacidad` | Enlace a la política de privacidad |

### Correo saliente (obligatorio para que el cliente reciba el PDF)

| Variable | Ejemplo |
|---|---|
| `SMTP_HOST` | `smtp.hostinger.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | `contratos@infoadaraexcavaciones.es` |
| `SMTP_PASS` | (contraseña del buzón) |
| `SMTP_SSL` | `auto` (usa SSL en 465 y STARTTLS en 587) |
| `SMTP_FROM` | `contratos@infoadaraexcavaciones.es` |
| `SMTP_FROM_NAME` | `Adara Excavaciones` |
| `COPIA_EMAIL` | Correo oculto que recibe copia de cada contrato |
| `AVISO_FIRMADO_EMAIL` | Correo que avisa cuando un cliente sube el contrato firmado |

Si `SMTP_HOST` está vacío, el servicio sigue funcionando pero no envía correos: en la página de
confirmación se avisa al cliente de que descargue el PDF con el botón.

### Seguridad y base

| Variable | Ejemplo | Para qué |
|---|---|---|
| `SECRET_KEY` | cadena larga aleatoria | Firma los enlaces de descarga y la cookie del panel |
| `PANEL_PASSWORD` | contraseña | Acceso a `/panel` |
| `BASE_URL` | `https://firmar.infoadaraexcavaciones.es` | URL pública (para los enlaces de los correos) |
| `DATA_DIR` | `/data` | Carpeta donde se guardan los PDF y la base de datos |

### Integración con n8n / WhatsApp (opcional)

| Variable | Para qué |
|---|---|
| `N8N_WEBHOOK_URL` | Si se informa, al aceptar un contrato se envía un aviso JSON a ese webhook de n8n (que reutiliza Evolution API para mandar el WhatsApp) |

Carga enviada al webhook:

```json
{
  "tipo": "contrato_aceptado",
  "id": "9382b713f60f",
  "numero_contrato": "ARR-2026-9382B7",
  "empresa": "Excavaciones López e Hijos, S.L.",
  "telefono": "600111222",
  "email": "manuel@excavacioneslopez.es",
  "aceptante": "Manuel López García",
  "pdf": "https://…/contrato/9382b713f60f.pdf?t=…"
}
```

## Despliegue en EasyPanel (VPS)

1. Crear un servicio nuevo en el mismo proyecto (`evolution-api`), por ejemplo
   **`contratofirma`**.
2. **Fuente → Git**: este repositorio, rama `main`.
3. **Dockerfile** → tipo de construcción `Dockerfile`, ruta `Dockerfile`.
4. **Volumen**: montar un volumen persistente en `/data` (guarda los contratos y la base de
   datos; sin él se pierden al reconstruir).
5. **Dominio**: `firmar.infoadaraexcavaciones.es`, puerto **80**, HTTPS activado.
   Requiere un registro DNS `A` de `firmar` apuntando a la IP del VPS.
6. **Entorno**: todas las variables anteriores.
7. **Desplegar**.

## Ejecución local con Docker

```bash
cp .env.example .env      # y rellenar los valores
docker compose up -d --build
# formulario: http://localhost:8082/     panel: http://localhost:8082/panel
```

## Actualizar el texto del contrato

El texto del modelo vive en `assets/contrato_general.md`. Para cambiar una cláusula:

1. Editar ese archivo.
2. Subir la versión en `app/contrato.py` (`VERSION_CONTRATO`, por ejemplo `1.1-noviembre-2026`).
3. Reconstruir el servicio (o pulsar **Desplegar** en EasyPanel).

La versión aparecerá impresa en la portada y en la hoja de aceptación, de modo que siempre se
puede saber qué texto aceptó cada cliente.

## Copias de seguridad

Todo lo importante está en el volumen `/data`:

- `contratos.db` — base de datos con los datos, evidencias y estados.
- `pdfs/` — una copia inmutable del contrato entregado a cada cliente.
- `firmados/` — los ejemplares firmados que suben los clientes.

Basta con copiar esa carpeta. En el VPS, el VPS tiene copia de seguridad automática semanal
configurada en Hostinger.

## Aviso

El contrato es un modelo estándar de uso profesional. Antes de usarlo de forma generalizada
conviene que un asesor jurídico revise el clausulado y, en particular, la cláusula penal y el
tipo de interés de demora pactado.