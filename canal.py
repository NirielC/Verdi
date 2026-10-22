# Envío de mensajes de WhatsApp por la API de Vonage (sandbox)
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('VONAGE_API_KEY')
API_SECRET = os.getenv('VONAGE_API_SECRET')
NUMERO_BOT = os.getenv('VONAGE_NUMERO_SANDBOX')

URL_SANDBOX = 'https://messages-sandbox.nexmo.com/v1/messages'


def _enviar(numero, contenido):
    """Agrega los datos comunes y envía. Devuelve True si Vonage lo aceptó (202)."""
    datos = {'from': NUMERO_BOT, 'to': numero, 'channel': 'whatsapp', **contenido}
    respuesta = requests.post(URL_SANDBOX, json=datos, auth=(API_KEY, API_SECRET), timeout=10)
    if respuesta.status_code != 202:
        print(f"[ERROR Vonage] {contenido['message_type']} a {numero}: {respuesta.status_code} {respuesta.text}")
        return False
    return True


def enviar_texto(numero, texto):
    return _enviar(numero, {'message_type': 'text', 'text': texto})


def enviar_imagen(numero, url, pie=''):
    return _enviar(numero, {'message_type': 'image', 'image': {'url': url, 'caption': pie}})


def enviar_botones(numero, texto, botones):
    """Botones de respuesta rápida de WhatsApp (máximo 3, títulos de hasta 20 caracteres)."""
    interactivo = {
        'type': 'button',
        'body': {'text': texto},
        'action': {'buttons': [{'type': 'reply', 'reply': {'id': f'b{i}', 'title': b[:20]}}
                               for i, b in enumerate(botones[:3])]},
    }
    return _enviar(numero, {'message_type': 'custom', 'custom': {'type': 'interactive', 'interactive': interactivo}})


def enviar_lista(numero, texto, opciones, boton='Ver opciones'):
    """Lista desplegable de WhatsApp (hasta 10 opciones de 24 caracteres)."""
    interactivo = {
        'type': 'list',
        'body': {'text': texto},
        'action': {'button': boton,
                   'sections': [{'title': 'Opciones',
                                 'rows': [{'id': f'o{i}', 'title': o[:24]} for i, o in enumerate(opciones[:10])]}]},
    }
    return _enviar(numero, {'message_type': 'custom', 'custom': {'type': 'interactive', 'interactive': interactivo}})


def enviar_ubicacion(numero, latitud, longitud, nombre, direccion):
    ubicacion = {'type': 'location',
                 'location': {'latitude': latitud, 'longitude': longitud, 'name': nombre, 'address': direccion}}
    return _enviar(numero, {'message_type': 'custom', 'custom': ubicacion})
