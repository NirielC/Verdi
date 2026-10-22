# Prueba de Verdi en consola, sin web ni WhatsApp: python probar_terminal.py
# (las pruebas también se guardan en la BD con el canal 'web' y el usuario 'terminal')
import sys

import cerebro

PRUEBAS = ['hola', 'qué puedes hacer', 'dónde tiro una botella de vidrio', 'tengo unas latas de gaseosa',
           'y dónde lo llevo?', 'Ideas para reusar', 'qué hago con el aceite de freír', 'cómo separo la basura en casa',
           'residuos peligrosos', 'mi celular ya no sirve', 'se recicla la caja de pizza', 'papel higiénico',
           'gracias', 'asdf qwerty', 'por qué reciclar', 'dame un consejo', 'tienen whatsapp', 'quién eres',
           'cáscaras de banano', 'Todos los puntos', 'Pilas y baterías', 'cómo hago compost',
           'puedo reciclar ropa vieja', 'dónde reciclo', 'chao']

if __name__ == '__main__':
    if '--auto' in sys.argv:
        for mensaje in PRUEBAS:
            r = cerebro.responder(mensaje, 'web', 'terminal')
            print(f"{mensaje!r:42} -> {r['intencion']:18} | {r['texto'][:55]!r}")
    else:
        print("Escribe un mensaje para Verdi (o 'salir'):")
        while (mensaje := input('Tú: ')).lower() != 'salir':
            r = cerebro.responder(mensaje, 'web', 'terminal')
            print(f"Verdi: {r['texto']}\n  Botones: {r['botones']}\n")
