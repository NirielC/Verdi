# Conexión a la base de datos MySQL de XAMPP y todas las consultas del sistema
import os

import mariadb
from dotenv import load_dotenv

load_dotenv()


def crear_conexion():
    return mariadb.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        database=os.getenv('DB_NOMBRE', 'reciclaje'),
        user=os.getenv('DB_USUARIO', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
    )


def consultar(sql, parametros=(), uno=False):
    """Ejecuta un SELECT y devuelve diccionarios (uno solo si uno=True)."""
    conexion = crear_conexion()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, parametros)
        return cursor.fetchone() if uno else cursor.fetchall()
    finally:
        conexion.close()


def ejecutar(sql, parametros=()):
    """Ejecuta un INSERT, UPDATE o DELETE y devuelve el id insertado."""
    conexion = crear_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, parametros)
        conexion.commit()  # sin commit no se guarda
        return cursor.lastrowid
    finally:
        conexion.close()


# ---------- Materiales (temas del chatbot) ----------

def obtener_materiales():
    return consultar("SELECT * FROM materiales ORDER BY id")


def obtener_material(clave):
    return consultar("SELECT * FROM materiales WHERE clave = %s", (clave,), uno=True)


# ---------- Puntos de recolección ----------

def obtener_puntos(solo_activos=True):
    sql = "SELECT * FROM puntos_recoleccion"
    if solo_activos:
        sql += " WHERE activo = 1"
    puntos = consultar(sql + " ORDER BY municipio, nombre")
    for punto in puntos:
        punto['latitud'] = float(punto['latitud'])
        punto['longitud'] = float(punto['longitud'])
        punto['lista_materiales'] = punto['materiales'].split(',')
    return puntos


def obtener_punto(id_punto):
    return consultar("SELECT * FROM puntos_recoleccion WHERE id = %s", (id_punto,), uno=True)


def guardar_punto(datos, id_punto=None):
    valores = (datos['nombre'], datos['direccion'], datos['municipio'], datos['latitud'], datos['longitud'],
               datos['materiales'], datos['horario'], datos['telefono'] or None)
    if id_punto:
        ejecutar("""UPDATE puntos_recoleccion SET nombre = %s, direccion = %s, municipio = %s, latitud = %s,
                    longitud = %s, materiales = %s, horario = %s, telefono = %s WHERE id = %s""",
                 valores + (id_punto,))
    else:
        ejecutar("""INSERT INTO puntos_recoleccion (nombre, direccion, municipio, latitud, longitud, materiales, horario, telefono)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", valores)


def cambiar_estado_punto(id_punto):
    ejecutar("UPDATE puntos_recoleccion SET activo = 1 - activo WHERE id = %s", (id_punto,))


def eliminar_punto(id_punto):
    ejecutar("DELETE FROM puntos_recoleccion WHERE id = %s", (id_punto,))


# ---------- Interacciones ----------

def registrar_interaccion(canal, usuario, mensaje, respuesta, intencion, confianza, material):
    ejecutar("""INSERT INTO interacciones (canal, usuario, mensaje, respuesta, intencion, confianza, material_clave)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
             (canal, usuario, mensaje, respuesta, intencion, round(confianza, 2), material))


def _filtros_sql(filtros):
    """Convierte los filtros del panel en un WHERE con parámetros (consulta parametrizada)."""
    condiciones, parametros = [], []
    if filtros.get('canal'):
        condiciones.append("i.canal = %s")
        parametros.append(filtros['canal'])
    if filtros.get('intencion'):
        condiciones.append("i.intencion = %s")
        parametros.append(filtros['intencion'])
    if filtros.get('material'):
        condiciones.append("i.material_clave = %s")
        parametros.append(filtros['material'])
    if filtros.get('estado'):
        condiciones.append("i.estado = %s")
        parametros.append(filtros['estado'])
    if filtros.get('desde'):
        condiciones.append("DATE(i.fecha) >= %s")
        parametros.append(filtros['desde'])
    if filtros.get('hasta'):
        condiciones.append("DATE(i.fecha) <= %s")
        parametros.append(filtros['hasta'])
    if filtros.get('buscar'):
        condiciones.append("(i.mensaje LIKE %s OR i.usuario LIKE %s)")
        parametros += [f"%{filtros['buscar']}%"] * 2
    where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    return where, tuple(parametros)


def obtener_interacciones(filtros, limite=None):
    where, parametros = _filtros_sql(filtros)
    sql = f"""SELECT i.*, m.nombre AS material_nombre FROM interacciones i
              LEFT JOIN materiales m ON m.clave = i.material_clave{where}
              ORDER BY i.fecha DESC, i.id DESC"""
    if limite:
        sql += f" LIMIT {int(limite)}"
    return consultar(sql, parametros)


def resumen_interacciones(filtros=None):
    where, parametros = _filtros_sql(filtros or {})
    base = f"FROM interacciones i{where}"
    y = " AND " if where else " WHERE "
    return {
        'total': consultar(f"SELECT COUNT(*) AS n {base}", parametros, uno=True)['n'],
        'usuarios': consultar(f"SELECT COUNT(DISTINCT i.usuario) AS n {base}", parametros, uno=True)['n'],
        'hoy': consultar(f"SELECT COUNT(*) AS n {base}{y}DATE(i.fecha) = CURDATE()", parametros, uno=True)['n'],
        'sin_entender': consultar(f"SELECT COUNT(*) AS n {base}{y}i.intencion = 'no_entendido'", parametros, uno=True)['n'],
        'nuevas': consultar(f"SELECT COUNT(*) AS n {base}{y}i.estado = 'nueva'", parametros, uno=True)['n'],
        'por_canal': consultar(f"SELECT i.canal, COUNT(*) AS n {base} GROUP BY i.canal", parametros),
        'por_intencion': consultar(f"SELECT i.intencion, COUNT(*) AS n {base} GROUP BY i.intencion ORDER BY n DESC", parametros),
        # El JOIN deja fuera las interacciones sin material
        'por_material': consultar(f"""SELECT m.nombre, m.color, COUNT(*) AS n FROM interacciones i
                                      JOIN materiales m ON m.clave = i.material_clave{where}
                                      GROUP BY m.clave, m.nombre, m.color ORDER BY n DESC""", parametros),
        'por_dia': consultar(f"""SELECT DATE(i.fecha) AS dia, COUNT(*) AS n {base}{y}i.fecha >= CURDATE() - INTERVAL 13 DAY
                                 GROUP BY DATE(i.fecha) ORDER BY dia""", parametros),
    }


def marcar_revisada(id_interaccion):
    ejecutar("UPDATE interacciones SET estado = IF(estado = 'nueva', 'revisada', 'nueva') WHERE id = %s", (id_interaccion,))


def eliminar_interaccion(id_interaccion):
    ejecutar("DELETE FROM interacciones WHERE id = %s", (id_interaccion,))


def total_interacciones():
    return consultar("SELECT COUNT(*) AS n FROM interacciones", uno=True)['n']


# ---------- Administradores ----------

def obtener_admin(usuario):
    return consultar("SELECT * FROM administradores WHERE usuario = %s", (usuario,), uno=True)
