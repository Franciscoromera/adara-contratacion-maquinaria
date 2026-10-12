# Aviso automático de contratos aceptados (n8n + Evolution API)

Este flujo se dispara cuando un cliente acepta el contrato en la web **https://firmar.infoadaraexcavaciones.es**.
La web avisa a n8n con los datos del contrato, y el flujo hace tres cosas:

1. Envía un **WhatsApp al cliente** desde la línea de Adara (instancia `Respuesta_Whatsapp_34643175166`) con el número de contrato y el enlace para descargarlo y firmarlo.
2. **Envía el contrato en PDF por correo** al cliente, con el PDF adjunto (nodo Gmail, usando la credencial que ya existe en tu n8n).
3. Tiene preparado un **aviso interno por Telegram** (desactivado) para que te llegue un mensaje cada vez que alguien acepta un contrato.

El flujo se llama **«Contrato aceptado - aviso WhatsApp y envio por email»** (id `ContrAceptJb4Jsn`) y ya está importado y activo en tu n8n.

## Lo único que falta

**El correo.** El permiso de la cuenta de Gmail que hay conectada en n8n está caducado, así que el envío por email falla (el resto del flujo sigue funcionando). Tienes dos formas de arreglarlo:

- **Reconectar Gmail (lo más rápido, 1 minuto).** En n8n: *Credenciales → «Gmail account - franciscocultooutlook» → Reconectar*. Los correos saldrán desde esa cuenta de Gmail.
- **Que salgan desde la dirección de la empresa.** Si me pasas la contraseña del buzón `contratos@infoadaraexcavaciones.es` (o de cualquiera que quieras usar), lo configuro para que el correo salga desde esa dirección, con copia oculta para ti si lo quieres.

## Datos útiles

| Cosa | Valor |
| --- | --- |
| URL del webhook (la usa la web) | `https://n8n.completitud.online/webhook/contrato-aceptado` |
| Instancia de Evolution que envía | `Respuesta_Whatsapp_34643175166` |
| Variable en el servicio de contratos | `N8N_WEBHOOK_URL` |
| Flujo en n8n | «Contrato aceptado - aviso WhatsApp y envio por email» |

## Cómo se comporta

- Si el cliente **no deja teléfono**, se salta el WhatsApp y sigue con el correo.
- Si el teléfono viene sin prefijo (por ejemplo `643175166`), el flujo le añade el `34` automáticamente.
- Los nodos de WhatsApp, correo y descarga del PDF están marcados como «continuar en caso de error»: si uno falla, el resto del flujo termina igualmente y no se pierde el aviso.

## Cambiar la instancia de WhatsApp

Los dos nodos de WhatsApp llevan la instancia en la URL. Para usar otra línea, cambia `Respuesta_Whatsapp_34643175166` por el nombre de la instancia deseada. Recuerda que las instancias `Respuesta_Whatsapp_34643175166` y `Respuesta_Whatsapp_34742068428` están conectadas, y `Respuesta_Whatsapp_34622797949` aparece desconectada (hay que volver a vincular el dispositivo con el QR).

## Ficheros

- `flujo-contrato-aceptado.json`: el flujo completo, para importarlo en cualquier n8n.
- `probar_flujo.sh`: envía un aviso de prueba al webhook.
- `ver_ejecuciones.sh` y `error_ejecucion.sh`: consultan el resultado de las últimas ejecuciones en la base de datos de n8n.
- `NOTAS-ENTORNO.md`: datos del VPS, de Evolution y de n8n anotados durante la instalación.