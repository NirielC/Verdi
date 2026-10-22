# ReVerde: sitio web de reciclaje con el chatbot Verdi, panel de administración y webhook de WhatsApp
import os
import time
import uuid
from datetime import date
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for)
from werkzeug.security import check_password_hash

import cerebro
import db
import reportes
from whatsapp import whatsapp_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'desarrollo')
app.register_blueprint(whatsapp_bp)

NUMERO_WHATSAPP = os.getenv('VONAGE_NUMERO_SANDBOX', '14157386102')

NOMBRES_INTENCION = {
    'saludo': 'Saludo', 'despedida': 'Despedida', 'agradecimiento': 'Agradecimiento', 'identidad': 'Quién es Verdi',
    'ayuda': 'Ayuda / menú', 'lista_materiales': 'Lista de materiales', 'consulta_material': 'Consulta de material',
    'puntos': 'Puntos de recolección', 'puntos_todos': 'Todos los puntos', 'ubicacion': 'Punto más cercano',
    'separacion': 'Separación en casa', 'reutilizar': 'Reutilización', 'reducir': 'Reducir residuos',
    'importancia': 'Por qué reciclar', 'especiales': 'Residuos especiales', 'whatsapp': 'Contacto WhatsApp',
    'estado': 'Cómo está Verdi', 'afirmacion': 'Afirmación', 'negacion': 'Negación', 'frustracion': 'Frustración',
    'no_entendido': 'No entendido',
}

# Se agrega a los CSS y JS (?v=...) para que el navegador no use una versión vieja guardada en caché
VERSION = str(int(time.time()))


@app.context_processor
def variables_globales():
    return {'enlace_whatsapp': f"https://wa.me/{NUMERO_WHATSAPP}?text=Hola%20Verdi",
            'nombres_intencion': NOMBRES_INTENCION, 'version': VERSION}


# ---------------- Sitio público ----------------

@app.route('/')
def index():
    materiales = db.obtener_materiales()
    puntos = db.obtener_puntos()
    return render_template('index.html', materiales=materiales, puntos=puntos,
                           total_consultas=db.total_interacciones(),
                           nombres_materiales={m['clave']: m['nombre'] for m in materiales},
                           colores_materiales={m['clave']: m['color'] for m in materiales})


@app.route('/chat', methods=['POST'])
def chat():
    # Cada visitante tiene un id propio guardado en su sesión (así Verdi recuerda su último material)
    if 'visitante' not in session:
        session['visitante'] = 'web-' + uuid.uuid4().hex[:8]

    datos = request.get_json(silent=True) or {}
    ubicacion = None
    if datos.get('latitud') is not None and datos.get('longitud') is not None:
        ubicacion = (float(datos['latitud']), float(datos['longitud']))
    mensaje = (datos.get('mensaje') or '').strip()[:500]
    if not mensaje and not ubicacion:
        return jsonify({'error': 'Escribe un mensaje.'}), 400

    respuesta = cerebro.responder(mensaje, 'web', session['visitante'], ubicacion)
    if respuesta['imagen']:
        respuesta['imagen'] = url_for('static', filename=respuesta['imagen'])
    return jsonify(respuesta)


# ---------------- Autenticación ----------------

def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login', siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = db.obtener_admin(request.form.get('usuario', '').strip())
        if admin and check_password_hash(admin['password_hash'], request.form.get('password', '')):
            session['admin'] = admin['nombre']
            siguiente = request.args.get('siguiente', '')
            return redirect(siguiente if siguiente.startswith('/admin') else url_for('admin_resumen'))
        flash('Usuario o contraseña incorrectos.')
    return render_template('admin/login.html')


@app.route('/admin/salir')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))


# ---------------- Panel de administración ----------------

def leer_filtros():
    claves = ('canal', 'intencion', 'material', 'estado', 'desde', 'hasta', 'buscar')
    return {k: request.args.get(k, '').strip() for k in claves if request.args.get(k, '').strip()}


@app.route('/admin')
@login_requerido
def admin_resumen():
    return render_template('admin/resumen.html', activo='resumen', resumen=db.resumen_interacciones(),
                           recientes=db.obtener_interacciones({}, limite=6), hoy=date.today())


@app.route('/admin/interacciones')
@login_requerido
def admin_interacciones():
    filtros = leer_filtros()
    return render_template('admin/interacciones.html', activo='interacciones', filtros=filtros,
                           interacciones=db.obtener_interacciones(filtros, limite=300),
                           materiales=db.obtener_materiales())


@app.route('/admin/interacciones/<int:id_interaccion>/revisar', methods=['POST'])
@login_requerido
def revisar_interaccion(id_interaccion):
    db.marcar_revisada(id_interaccion)
    return redirect(request.referrer or url_for('admin_interacciones'))


@app.route('/admin/interacciones/<int:id_interaccion>/eliminar', methods=['POST'])
@login_requerido
def eliminar_interaccion(id_interaccion):
    db.eliminar_interaccion(id_interaccion)
    flash('Interacción eliminada.')
    return redirect(request.referrer or url_for('admin_interacciones'))


@app.route('/admin/reporte.pdf')
@login_requerido
def admin_reporte():
    filtros = leer_filtros()
    pdf = reportes.generar(filtros, db.obtener_interacciones(filtros), db.resumen_interacciones(filtros),
                           NOMBRES_INTENCION, session['admin'])
    nombre = f"reporte_verdi_{date.today():%Y%m%d}.pdf"
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{nombre}"'})


@app.route('/admin/puntos')
@login_requerido
def admin_puntos():
    editar = db.obtener_punto(request.args.get('editar', type=int)) if request.args.get('editar') else None
    return render_template('admin/puntos.html', activo='puntos', puntos=db.obtener_puntos(solo_activos=False),
                           materiales=db.obtener_materiales(), editar=editar)


@app.route('/admin/puntos/guardar', methods=['POST'])
@login_requerido
def guardar_punto():
    f = request.form
    try:
        datos = {'nombre': f['nombre'].strip(), 'direccion': f['direccion'].strip(), 'municipio': f['municipio'].strip(),
                 'latitud': float(f['latitud']), 'longitud': float(f['longitud']),
                 'materiales': ','.join(f.getlist('materiales')), 'horario': f['horario'].strip(),
                 'telefono': f.get('telefono', '').strip()}
    except (KeyError, ValueError):
        flash('Revisa los datos: la latitud y la longitud deben ser números.')
        return redirect(url_for('admin_puntos'))
    if not all([datos['nombre'], datos['direccion'], datos['municipio'], datos['materiales'], datos['horario']]):
        flash('Completa todos los campos y elige al menos un material.')
        return redirect(url_for('admin_puntos'))
    db.guardar_punto(datos, f.get('id', type=int))
    flash('Punto guardado.')
    return redirect(url_for('admin_puntos'))


@app.route('/admin/puntos/<int:id_punto>/estado', methods=['POST'])
@login_requerido
def estado_punto(id_punto):
    db.cambiar_estado_punto(id_punto)
    return redirect(url_for('admin_puntos'))


@app.route('/admin/puntos/<int:id_punto>/eliminar', methods=['POST'])
@login_requerido
def eliminar_punto(id_punto):
    db.eliminar_punto(id_punto)
    flash('Punto eliminado.')
    return redirect(url_for('admin_puntos'))


@app.errorhandler(404)
def no_encontrado(error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
