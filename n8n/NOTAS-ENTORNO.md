# Datos del entorno (VPS de Adara / EasyPanel) — anotados durante el trabajo

## Acceso
- VPS: `ssh root@72.62.29.60` (clave SSH del sandbox en `~/.ssh/id_ed25519`, ya autorizada)
- Hostname: `srv1212578`, Docker Swarm con EasyPanel.

## Servicio de contratación (creado por nosotros)
- Repositorio: https://github.com/Franciscoromera/adara-contratacion-maquinaria
- Carpeta en el VPS: `/opt/contrato-firma` (código en `repo/`, configuración en `.env`)
- Servicio Swarm: `contrato-firma`, red overlay `easypanel`, volumen `contrato-firma-data` montado en `/data`
- Enrutado Traefik: `/etc/easypanel/traefik/config/contrato-firma.yaml` (dominios `firmar.infoadaraexcavaciones.es` y `contrato-firma.pdiuan.easypanel.host`)
- Contraseña del panel: `ugIq0XOVKTauom` (guardada también en `/root/.contrato-firma-claves` del VPS)
- Webhook de n8n configurado en el servicio: `N8N_WEBHOOK_URL=https://n8n.completitud.online/webhook/contrato-aceptado`

## n8n del VPS
- URL: https://n8n.completitud.online · contenedor Swarm `database_n8n` · versión **2.14.0**
- Base de datos: Postgres en el contenedor `database_n8n-db`, base `n8n`, usuario `n8n`.
  - Tablas útiles: `execution_entity` (estados) y `execution_data` (detalle, columna `data`, JSON troceado en una lista).
- Flujo creado: **`Contrato aceptado - aviso WhatsApp y envio por email`**, id `ContrAceptJb4Jsn`, activo.
- Webhook de producción del flujo: `https://n8n.completitud.online/webhook/contrato-aceptado`
- Credencial de correo existente reutilizada: **Gmail** id `qxt8FxbBadrOHZZO` ("Gmail account - franciscocultooutlook"), scopes: gmail.addons, gmail.compose, gmail.labels, gmail.modify, mail.google.com (permite enviar).
- Notas sobre n8n 2.14:
  - El nodo Email (`emailSend`) adjunta con el parámetro `attachments` = nombre de la propiedad binaria.
  - El nodo Gmail (`gmail`, v2.1) adjunta con `options.attachmentsUi.attachmentsBinary` = `[{property: "data"}]`.
  - CLI: `n8n import:workflow --input=...` requiere que el JSON lleve `id`; los cambios sólo surten efecto tras **reiniciar n8n**.
  - El nodo HTTP Request devuelve `json` vacío cuando descarga un fichero: hay que referenciar los datos con `$('Nombre del nodo').first().json`.
  - Ojo al filtrar contenedores: `docker ps -f name=database_n8n` también coge `database_n8n-db`; usar `-f name=database_n8n.1`.

## Evolution API
- URL: `https://evolution-api-evolution-api.pdiuan.easypanel.host` (clave en la variable `EVOLUTION_APIKEY` del servicio n8n)
- Instancias:
  - `Respuesta_Whatsapp_34643175166` → **conectada** (643 175 166, la línea de Adara) → es la que usa el flujo.
  - `Respuesta_Whatsapp_34742068428` → conectada
  - `Respuesta_Whatsapp_34622797949` → desconectada (error 401, hay que volver a vincular el dispositivo)

## Otras cosas detectadas
- En EasyPanel hay un servicio `database_caddy` con el dominio `openclaw.completitud.online` que no existe en DNS: Traefik se queja periódicamente.