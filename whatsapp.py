# Chatbot de WhatsApp: Vonage llama a /inbound cada vez que alguien le escribe a Verdi.
# Usa el mismo cerebro que la web y traduce la respuesta a mensajes de WhatsApp
# (texto, imagen, botones, lista y ubicación).
from flask import Blueprint, request

import canal
import cerebro

whatsapp_bp = Blueprint('whatsapp', __name__)

# Vonage puede reenviar el mismo mensaje si tardamos en responder: guardamos los últimos ids
mensajes_procesados = set()


def url_publica(ruta_static):
    """WhatsApp descarga las imágenes desde internet, así que usamos la URL del túnel de Cloudflare."""
    return f"https://{request.host}/static/{ruta_static}"


@whatsapp_bp.route('/inbound', methods=['POST'])
def inbound():
    datos = request.get_json(silent=True) or {}
    numero = datos.get('from')
    tipo = datos.get('message_type')
    id_mensaje = datos.get('message_uuid')

    if not numero or id_mensaje in mensajes_procesados:
        return '', 200
    mensajes_procesados.add(id_mensaje)

    texto, ubicacion = '', None
    if tipo == 'text':
        texto = datos.get('text', '')
    elif tipo == 'reply':  # el usuario tocó un botón o una opción de la lista
        texto = datos.get('reply', {}).get('title', '')
    elif tipo == 'location':
        lugar = datos.get('location', {})
        ubicacion = (float(lugar.get('lat')), float(lugar.get('long')))
    else:
        canal.enviar_texto(numero, 'Por ahora entiendo mensajes de texto, botones y ubicaciones. ¿Me lo escribes?')
        return '', 200

    print(f"[WhatsApp] {numero}: {texto or ubicacion}")
    try:
        respuesta = cerebro.responder(texto, 'whatsapp', numero, ubicacion)
        enviar_respuesta(numero, respuesta)
    except Exception as error:
        # Si algo falla, el usuario recibe un mensaje claro y el servidor sigue vivo
        print(f"[ERROR WhatsApp] {error}")
        canal.enviar_texto(numero, 'Tuve un problema procesando tu mensaje. Escribe *menu* para empezar de nuevo.')
    return '', 200


def con_finalizar(botones):
    """Agrega la opción "Finalizar" a cada respuesta. WhatsApp admite 3 botones o una lista de 10 opciones."""
    if len(botones) < 3:
        return botones + ['Finalizar']
    if len(botones) == 3:
        return botones[:2] + ['Finalizar']
    return botones[:9] + ['Finalizar']


def enviar_respuesta(numero, r):
    texto = r['texto']
    if r.get('pedir_ubicacion'):
        texto += '\n\nSi me compartes tu *ubicación* (clip → Ubicación), te digo cuál te queda más cerca.'

    # El punto más cercano va primero como ubicación, para abrirlo directo en el mapa
    if r['intencion'] == 'ubicacion' and r['puntos']:
        p = r['puntos'][0]
        canal.enviar_ubicacion(numero, p['latitud'], p['longitud'], p['nombre'], f"{p['direccion']}, {p['municipio']}")

    # Con imagen: la respuesta va como pie de foto y los botones en un mensaje aparte
    # (WhatsApp limita el pie de foto y el texto de los botones a 1024 caracteres)
    texto_enviado = False
    if r['imagen'] and len(texto) <= 1024:
        texto_enviado = canal.enviar_imagen(numero, url_publica(r['imagen']), texto)

    # Al despedirse no hay botones: la conversación termina ahí
    botones = [] if r['intencion'] == 'despedida' else con_finalizar(r['botones'])
    if botones:
        cuerpo = '¿Qué quieres hacer ahora?' if texto_enviado or len(texto) > 1024 else texto
        if len(texto) > 1024 and not texto_enviado:
            canal.enviar_texto(numero, texto)
        enviado = (canal.enviar_botones(numero, cuerpo, botones) if len(botones) <= 3
                   else canal.enviar_lista(numero, cuerpo, botones, 'Elegir'))
        if not enviado:  # si el sandbox no acepta interactivos, mandamos las opciones como texto
            canal.enviar_texto(numero, cuerpo + '\n\n' + '\n'.join(f'• {b}' for b in botones))
    elif not texto_enviado:
        canal.enviar_texto(numero, texto)


@whatsapp_bp.route('/status', methods=['POST'])
def status():
    # Vonage avisa aquí el estado de los mensajes enviados (entregado, leído...)
    datos = request.get_json(silent=True) or {}
    error = datos.get('error', {})
    print(f"[Estado] {datos.get('to')}: {datos.get('status')} {error.get('title', '')} {error.get('detail', '')}", flush=True)
    return '', 200
