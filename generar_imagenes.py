# Genera las tarjetas PNG de cada material a partir de su foto (las usan el chat web y WhatsApp).
# Se ejecuta una vez con MySQL encendido: python generar_imagenes.py
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

import db

FUENTES = 'C:/Windows/Fonts/'
TITULO = ImageFont.truetype(FUENTES + 'segoeuib.ttf', 70)
ETIQUETA = ImageFont.truetype(FUENTES + 'segoeuisb.ttf', 34) if os.path.exists(FUENTES + 'segoeuisb.ttf') \
    else ImageFont.truetype(FUENTES + 'segoeuib.ttf', 34)
CUERPO = ImageFont.truetype(FUENTES + 'segoeui.ttf', 36)
MARCA = ImageFont.truetype(FUENTES + 'segoeuib.ttf', 30)

BLANCO = '#FFFFFF'
TINTA = '#17211B'
SUAVE = '#5D6B62'
VERDE = '#1F4D36'
LADO = 1080
ALTO_FOTO = 640

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
FOTOS = os.path.join(STATIC, 'img', 'fotos')
CARPETA = os.path.join(STATIC, 'img', 'materiales')


def etiqueta_contenedor(m):
    if m['especial']:
        return 'Residuo especial: llévalo a un punto de acopio'
    if m['clave'] == 'comun':
        return 'Basura común: no se recicla'
    if m['clave'] == 'textil':
        return 'Dónalo o reutilízalo'
    return f"Contenedor {m['contenedor']}"


def tarjeta(m):
    img = Image.new('RGB', (LADO, LADO), BLANCO)
    foto = Image.open(os.path.join(FOTOS, m['clave'] + '.jpg')).convert('RGB')
    img.paste(ImageOps.fit(foto, (LADO, ALTO_FOTO), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(img)

    # Franja del color del contenedor entre la foto y el texto
    d.rectangle((0, ALTO_FOTO, LADO, ALTO_FOTO + 14), fill=m['color'])

    x = 72
    d.text((x, ALTO_FOTO + 60), m['nombre'], font=TITULO, fill=TINTA)
    d.ellipse((x, ALTO_FOTO + 160, x + 26, ALTO_FOTO + 186), fill=m['color'])
    d.text((x + 42, ALTO_FOTO + 152), etiqueta_contenedor(m), font=ETIQUETA, fill=TINTA)

    y = ALTO_FOTO + 222
    for linea in textwrap.wrap(m['resumen'], 50)[:2]:
        d.text((x, y), linea, font=CUERPO, fill=SUAVE)
        y += 48

    d.text((LADO - x, LADO - 42), 'ReVerde', font=MARCA, fill=VERDE, anchor='rs')
    return img


def guia_separacion(materiales):
    """Imagen de los contenedores de casa, para la intención 'separacion'."""
    img = Image.new('RGB', (LADO, LADO), BLANCO)
    d = ImageDraw.Draw(img)
    x = 72
    d.text((x, 80), 'Separa en casa', font=TITULO, fill=TINTA)
    d.text((x, 175), 'Con cuatro recipientes ya separas casi todo.', font=CUERPO, fill=SUAVE)
    filas = [('plastico', 'Amarillo', 'Plástico y metal, limpios y aplastados'),
             ('papel', 'Azul', 'Papel y cartón, secos y sin grasa'),
             ('vidrio', 'Verde', 'Vidrio, vacío y sin tapa'),
             ('organico', 'Café', 'Restos de comida y jardín'),
             ('electronicos', 'Aparte', 'Pilas, aceite, electrónicos y medicinas'),
             ('comun', 'Negro', 'Lo que no se recicla')]
    y = 270
    for clave, nombre, detalle in filas:
        d.rounded_rectangle((x, y, x + 14, y + 92), radius=7, fill=materiales[clave]['color'])
        d.text((x + 44, y + 4), nombre, font=ETIQUETA, fill=TINTA)
        d.text((x + 44, y + 48), detalle, font=CUERPO, fill=SUAVE)
        y += 120
    d.text((LADO - x, LADO - 42), 'ReVerde', font=MARCA, fill=VERDE, anchor='rs')
    return img


if __name__ == '__main__':
    os.makedirs(CARPETA, exist_ok=True)
    materiales = {m['clave']: m for m in db.obtener_materiales()}
    for material in materiales.values():
        tarjeta(material).save(os.path.join(CARPETA, material['imagen']), optimize=True)
    guia_separacion(materiales).save(os.path.join(STATIC, 'img', 'separacion.png'), optimize=True)
    print(f"Listo: {len(materiales)} tarjetas y la guía de separación.")
