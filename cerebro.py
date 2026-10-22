# Cerebro de Verdi: entiende el mensaje y arma la respuesta.
# Lo usan los dos canales (web y WhatsApp), así ambos chatbots responden exactamente igual.
import json
import math
import os
import pickle
import random
import re
import warnings

import db
from texto import normalizar, preproceso

warnings.filterwarnings('ignore', category=FutureWarning)

# Carpeta del proyecto: así funciona aunque se ejecute desde otra carpeta
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Cargar el modelo entrenado por chatty.py
with open(os.path.join(CARPETA, 'model.pkl'), 'rb') as f:
    vectorizar, le, model = pickle.load(f)

# Cargar las respuestas desde el archivo JSON
with open(os.path.join(CARPETA, 'intenciones.json'), 'r', encoding='utf-8') as file:
    RESPUESTAS = {i['etiqueta']: i['respuestas'] for i in json.load(file)['intenciones']}

CONFIANZA_MINIMA = 0.35

# Detección de entidades: palabras que identifican cada material (sin tildes, en minúsculas).
# Peso 3 = nombre del material o frase exacta; peso 1 = objeto de ejemplo.
PALABRAS_MATERIAL = {
    'plastico': {'plastic': 3, 'pet': 1, 'botella': 1, 'bolsa': 1, 'garrafon': 1, 'envase': 1, 'champu': 1,
                 'pajilla': 1, 'tapon': 1, 'cubeta': 1},
    'papel': {'papel': 3, 'carton': 3, 'periodico': 1, 'cuaderno': 1, 'hoja': 1, 'revista': 1, 'caja': 1,
              'libro': 1, 'folleto': 1},
    'vidrio': {'vidrio': 3, 'botella de vidrio': 4, 'frasco': 2, 'cristal': 2},
    'metal': {'metal': 3, 'lata': 3, 'aluminio': 2, 'hojalata': 2, 'chatarra': 2, 'clavo': 1},
    'organico': {'organic': 3, 'cascara': 2, 'comida': 1, 'fruta': 1, 'verdura': 1, 'cafe': 1, 'huevo': 1,
                 'hoja seca': 4, 'hojas secas': 4, 'grama': 1, 'jardin': 1, 'compost': 2},
    'textil': {'ropa': 3, 'textil': 3, 'camisa': 1, 'camiseta': 1, 'pantalon': 1, 'zapato': 1, 'sabana': 1,
               'toalla': 1, 'tela': 1, 'mochila': 1},
    'electronicos': {'electronic': 3, 'celular': 2, 'telefono': 1, 'computadora': 2, 'laptop': 2, 'cargador': 2,
                     'cable': 1, 'audifono': 1, 'televisor': 1, 'tablet': 1, 'impresora': 1, 'licuadora': 1,
                     'electrodomestico': 2, 'aparato': 1, 'teclado': 1, 'mouse': 1},
    'pilas': {'pila': 3, 'bateria': 3},
    'aceite': {'aceite': 3, 'manteca': 2},
    'medicamentos': {'medicament': 3, 'medicina': 3, 'pastilla': 2, 'jarabe': 2, 'inhalador': 2, 'jeringa': 2},
    'comun': {'duroport': 3, 'panal': 3, 'servilleta': 2, 'colilla': 3, 'cigarro': 2, 'papel higienico': 4,
              'churrito': 2, 'basura comun': 4, 'no reciclable': 4},
}

# Botones del chatbot: el texto del botón es lo que se envía como mensaje
BOTONES_INICIO = ['Clasificar residuo', 'Puntos de acopio', 'Separar en casa']
BOTONES_MATERIAL = ['Dónde llevarlo', 'Ideas para reusar', 'Otro material']
BOTONES_ESPECIALES = ['Electrónicos', 'Pilas y baterías', 'Aceite de cocina', 'Medicamentos']

# Si el mensaje es exactamente el texto de un botón, ya sabemos la intención (confianza 100 %)
ACCIONES = {
    'clasificar residuo': 'lista_materiales', 'otro material': 'lista_materiales',
    'puntos de acopio': 'puntos', 'donde llevarlo': 'puntos', 'todos los puntos': 'puntos_todos',
    'separar en casa': 'separacion', 'ideas para reusar': 'reutilizar', 'menu': 'ayuda',
    'finalizar': 'despedida',
    # Respuestas cortas muy comunes: con una o dos palabras el modelo no tiene suficiente información
    'si': 'afirmacion', 'ok': 'afirmacion', 'okey': 'afirmacion', 'dale': 'afirmacion', 'va': 'afirmacion',
    'claro': 'afirmacion', 'si por favor': 'afirmacion',
    'no': 'negacion', 'no gracias': 'negacion', 'nada': 'negacion', 'nada mas': 'negacion', 'no por ahora': 'negacion',
    'no entiendo': 'frustracion', 'no entiendo nada': 'frustracion', 'no me sirve': 'frustracion',
}

# Frases para empezar la respuesta de un material, para que no suene siempre igual
APERTURAS = ['Buena pregunta.', 'Te explico.', 'Qué bueno que lo separas.', 'Con gusto te ayudo.', '']

# Recuerda el último material de cada usuario para entender "¿y dónde lo llevo?"
memoria = {}


def detectar_material(mensaje):
    """Busca en el mensaje las palabras de cada material y devuelve la clave con más puntos."""
    texto = normalizar(mensaje)
    puntajes = {}
    for clave, palabras in PALABRAS_MATERIAL.items():
        for palabra, peso in palabras.items():
            # \b = inicio de palabra; \w* permite plurales y variantes ("latas", "electronicos")
            if re.search(r'\b' + palabra + r'\w*', texto):
                puntajes[clave] = puntajes.get(clave, 0) + peso
    if not puntajes:
        return None
    return max(puntajes, key=puntajes.get)


def clasificar(mensaje):
    """Predice la intención con el modelo SVM. Devuelve (etiqueta, confianza)."""
    X = vectorizar.transform([preproceso(mensaje)])
    if X.nnz == 0:  # ninguna palabra conocida
        return 'no_entendido', 0.0
    confianza = model.predict_proba(X)[0]
    indice = confianza.argmax()
    etiqueta = str(le.inverse_transform([indice])[0])
    if confianza[indice] < CONFIANZA_MINIMA:
        return 'no_entendido', float(confianza[indice])
    return etiqueta, float(confianza[indice])


def distancia_km(lat1, lon1, lat2, lon2):
    """Fórmula de Haversine: distancia en km entre dos coordenadas."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nombres_materiales(claves, materiales):
    return ', '.join(materiales[c]['nombre'].lower() for c in claves if c in materiales)


def texto_contenedor(m):
    """Frase corta que dice a dónde va el material."""
    if m['especial']:
        return 'es un residuo especial: no va a la basura común, se lleva a un punto que lo reciba.'
    if m['clave'] == 'comun':
        return 'no se recicla: va a la basura común.'
    if m['clave'] == 'textil':
        return 'se dona si está en buen estado, o se reutiliza.'
    return f"va al contenedor {m['contenedor']}."


def respuesta_material(m):
    apertura = random.choice(APERTURAS)
    texto = (f"{apertura + ' ' if apertura else ''}*{m['nombre']}* {texto_contenedor(m)}\n\n{m['resumen']}\n\n"
             f"*Cómo prepararlo*\n{m['preparar']}\n\n"
             f"*Ejemplos*\n{m['ejemplos']}\n\n"
             f"*Ten en cuenta*\n{m['no_aceptado']}")
    return {'texto': texto, 'imagen': f"img/materiales/{m['imagen']}", 'botones': BOTONES_MATERIAL}


def respuesta_puntos(material, materiales, ubicacion=None):
    puntos = db.obtener_puntos()
    filtro = ''
    if material:
        filtrados = [p for p in puntos if material in p['lista_materiales']]
        if filtrados:
            puntos = filtrados
            filtro = materiales[material]['nombre'].lower()

    que_reciben = f" que reciben *{filtro}*" if filtro else ''
    if ubicacion:
        # Ya tenemos la ubicación: ordenamos por distancia y no la volvemos a pedir
        for p in puntos:
            p['distancia'] = round(distancia_km(ubicacion[0], ubicacion[1], p['latitud'], p['longitud']), 1)
        puntos.sort(key=lambda p: p['distancia'])
        puntos = puntos[:3]
        cercano = puntos[0]
        encabezado = (f"¡Gracias por compartir tu ubicación! El punto más cercano{que_reciben} es "
                      f"*{cercano['nombre']}*, a {cercano['distancia']} km de ti.")
        if len(puntos) > 1:
            encabezado += '\n\nTambién te quedan cerca:'
        lista = puntos[1:]
        botones = ['Otro material']
    else:
        puntos = puntos[:4]
        encabezado = f"Estos son algunos puntos de recolección{que_reciben}:"
        lista = puntos
        botones = ['Todos los puntos'] if filtro else []

    lineas = [encabezado]
    for p in lista:
        distancia = f", a {p['distancia']} km" if 'distancia' in p else ''
        lineas.append(f"\n*{p['nombre']}*{distancia}\n{p['direccion']}, {p['municipio']}\nHorario: {p['horario']}\n"
                      f"Recibe: {nombres_materiales(p['lista_materiales'], materiales)}")
    if ubicacion:
        lineas.append(f"\nHorario de *{cercano['nombre']}*: {cercano['horario']}.")
    return {'texto': '\n'.join(lineas),
            'puntos': [{'id': p['id'], 'nombre': p['nombre'], 'direccion': p['direccion'], 'municipio': p['municipio'],
                        'latitud': p['latitud'], 'longitud': p['longitud'], 'horario': p['horario'],
                        'distancia': p.get('distancia')} for p in puntos],
            'botones': botones,
            'pedir_ubicacion': not ubicacion}


def responder(mensaje, canal, usuario, ubicacion=None):
    """Punto de entrada de los dos canales. Devuelve un diccionario con el texto, la imagen,
    los botones y los puntos, y guarda la interacción en la base de datos."""
    materiales = {m['clave']: m for m in db.obtener_materiales()}
    estado = memoria.setdefault(usuario, {'material': None})

    if ubicacion:
        intencion, confianza, material = 'ubicacion', 1.0, estado['material']
        mensaje = f"Ubicación compartida ({ubicacion[0]:.4f}, {ubicacion[1]:.4f})"
        salida = respuesta_puntos(material, materiales, ubicacion)
    else:
        material = detectar_material(mensaje)
        accion = ACCIONES.get(normalizar(mensaje).strip())
        if accion:
            intencion, confianza = accion, 1.0
        else:
            intencion, confianza = clasificar(mensaje)
            # Si el mensaje nombra un material, es una consulta sobre él (salvo que pida puntos o ideas)
            if material and intencion not in ('puntos', 'reutilizar'):
                intencion = 'consulta_material'
        print(f"[{canal}] Intención: {intencion} ({confianza:.2f}), material: {material}")

        if material:
            estado['material'] = material
        elif intencion in ('puntos', 'reutilizar'):
            material = estado['material']  # usa el último material del que se habló
        elif intencion in ('lista_materiales', 'ayuda', 'saludo', 'separacion', 'puntos_todos', 'despedida'):
            estado['material'] = None

        salida = construir_respuesta(intencion, material or estado['material'], materiales, canal)

    salida.setdefault('imagen', None)
    salida.setdefault('botones', [])
    salida.setdefault('puntos', [])
    salida['intencion'] = intencion

    try:
        db.registrar_interaccion(canal, usuario, mensaje, salida['texto'], intencion, confianza, material)
    except Exception as error:  # si la BD falla, el usuario igual recibe su respuesta
        print(f"[ERROR BD] {error}")
    return salida


def construir_respuesta(intencion, material, materiales, canal):
    # Ropa va al final: en WhatsApp la lista admite 10 opciones y la última se cambia por "Finalizar"
    lista_materiales = [m['nombre'] for m in materiales.values() if m['clave'] not in ('comun', 'textil')]
    lista_materiales.append(materiales['textil']['nombre'])

    if intencion == 'consulta_material':
        if material:
            return respuesta_material(materiales[material])
        return {'texto': random.choice(RESPUESTAS['consulta_material']), 'botones': lista_materiales}

    if intencion in ('puntos', 'puntos_todos'):
        return respuesta_puntos(material if intencion == 'puntos' else None, materiales)

    if intencion == 'reutilizar' and material:
        m = materiales[material]
        return {'texto': f"Me encanta la idea de darle otra vida. *Ideas para reutilizar {m['nombre'].lower()}:*\n\n"
                         f"{m['reutilizar']}",
                'imagen': f"img/materiales/{m['imagen']}", 'botones': ['Dónde llevarlo', 'Otro material']}

    if intencion == 'afirmacion' and material:
        nombre = materiales[material]['nombre'].lower()
        return {'texto': f"¡Perfecto! ¿Quieres saber dónde llevar {nombre} o prefieres ideas para reutilizarlo?",
                'botones': BOTONES_MATERIAL}

    if intencion == 'whatsapp' and canal == 'whatsapp':
        return {'texto': '¡Ya estamos hablando por WhatsApp! Escríbeme el residuo que quieras consultar.',
                'botones': BOTONES_INICIO}

    if intencion == 'no_entendido':
        return {'texto': random.choice([
                    'Mmm, no logré entenderte del todo. ¿Me lo dices de otra forma? Por ejemplo «botella», '
                    '«pilas» o «cáscaras». También puedes elegir una opción.',
                    'Perdona, esa no la entendí. Escríbeme el nombre del objeto que quieres tirar y te digo qué hacer.']),
                'botones': BOTONES_INICIO}

    botones = {
        'saludo': BOTONES_INICIO, 'ayuda': BOTONES_INICIO, 'identidad': BOTONES_INICIO, 'estado': BOTONES_INICIO,
        'afirmacion': BOTONES_INICIO, 'frustracion': ['Clasificar residuo', 'Puntos de acopio'],
        'agradecimiento': ['Otro material'],
        'lista_materiales': lista_materiales, 'reutilizar': lista_materiales,
        'especiales': BOTONES_ESPECIALES, 'separacion': ['Clasificar residuo', 'Puntos de acopio'],
        'reducir': ['Clasificar residuo', 'Separar en casa'], 'importancia': ['Clasificar residuo', 'Separar en casa'],
    }
    salida = {'texto': random.choice(RESPUESTAS[intencion]), 'botones': botones.get(intencion, [])}
    if intencion == 'separacion':
        salida['imagen'] = 'img/separacion.png'
    if intencion == 'whatsapp':
        salida['whatsapp'] = True
    return salida
