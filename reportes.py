# Reporte PDF de las interacciones de Verdi (se descarga desde el panel de administración)
import re
from datetime import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

BOSQUE = (29, 68, 48)
SALVIA = (220, 230, 203)
SALVIA_CLARA = (238, 243, 227)
TINTA = (19, 48, 31)
CORAL = (232, 96, 60)


def limpiar(texto):
    """Las fuentes estándar del PDF solo tienen caracteres latinos: quitamos emojis y los * de negrita."""
    texto = re.sub(r'[*_]', '', str(texto or '')).replace('•', '-').replace('→', '->')
    return texto.encode('latin-1', 'ignore').decode('latin-1').strip()


class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(*BOSQUE)
        self.rect(0, 0, self.w, 24, 'F')
        self.set_xy(12, 7)
        self.set_text_color(*SALVIA)
        self.set_font('Helvetica', 'B', 18)
        self.cell(0, 10, 'ReVerde', new_x='LMARGIN')
        self.set_xy(48, 9)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, 'Reporte de interacciones del chatbot Verdi')
        self.set_y(30)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(110, 120, 110)
        self.cell(0, 6, f'Página {self.page_no()} de {{nb}}', align='R')


def tarjeta_numero(pdf, x, y, ancho, valor, etiqueta):
    pdf.set_fill_color(*SALVIA_CLARA)
    pdf.rect(x, y, ancho, 20, 'F')
    pdf.set_xy(x + 4, y + 2)
    pdf.set_text_color(*BOSQUE)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(ancho - 8, 9, str(valor))
    pdf.set_xy(x + 4, y + 11)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(ancho - 8, 6, etiqueta)


def barras(pdf, x, y, ancho, titulo, filas):
    """Gráfico de barras horizontal simple: filas = [(etiqueta, valor, color)]."""
    pdf.set_xy(x, y)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*TINTA)
    pdf.cell(ancho, 7, titulo)
    y += 9
    maximo = max([v for _, v, _ in filas] or [1])
    for etiqueta, valor, color in filas[:6]:
        pdf.set_xy(x, y)
        pdf.set_font('Helvetica', '', 8.5)
        pdf.cell(42, 5, limpiar(etiqueta)[:26])
        pdf.set_fill_color(*color)
        pdf.rect(x + 43, y + 0.8, max(1, (ancho - 58) * valor / maximo), 3.6, 'F')
        pdf.set_xy(x + ancho - 13, y)
        pdf.cell(13, 5, str(valor), align='R')
        y += 6.5
    return y


def hex_a_rgb(color):
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def generar(filtros, interacciones, resumen, nombres_intencion, generado_por):
    pdf = ReportePDF(orientation='L', format='A4')
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(12, 30, 12)
    pdf.add_page()

    # Datos del reporte
    pdf.set_text_color(*TINTA)
    pdf.set_font('Helvetica', '', 9)
    descripcion_filtros = ', '.join(f'{k}: {v}' for k, v in filtros.items()) or 'sin filtros (todas las interacciones)'
    pdf.cell(0, 5, limpiar(f'Generado el {datetime.now():%d/%m/%Y %H:%M} por {generado_por}'), new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 5, limpiar(f'Filtros: {descripcion_filtros}'), new_x='LMARGIN', new_y='NEXT')

    # Resumen en números
    canales = {c['canal']: c['n'] for c in resumen['por_canal']}
    y = pdf.get_y() + 4
    ancho = (pdf.w - 24 - 4 * 4) / 5
    datos = [(resumen['total'], 'Interacciones'), (resumen['usuarios'], 'Usuarios distintos'),
             (canales.get('web', 0), 'Desde la web'), (canales.get('whatsapp', 0), 'Desde WhatsApp'),
             (resumen['sin_entender'], 'Mensajes no entendidos')]
    for i, (valor, etiqueta) in enumerate(datos):
        tarjeta_numero(pdf, 12 + i * (ancho + 4), y, ancho, valor, etiqueta)

    # Gráficos: materiales más consultados e intenciones
    y += 26
    mitad = (pdf.w - 24 - 8) / 2
    fin_1 = barras(pdf, 12, y, mitad, 'Materiales más consultados',
                   [(m['nombre'], m['n'], hex_a_rgb(m['color'])) for m in resumen['por_material']])
    fin_2 = barras(pdf, 12 + mitad + 8, y, mitad, 'Intenciones detectadas',
                   [(nombres_intencion.get(i['intencion'], i['intencion']), i['n'],
                     CORAL if i['intencion'] == 'no_entendido' else BOSQUE) for i in resumen['por_intencion']])
    if not resumen['por_material']:
        pdf.set_xy(12, y + 9)
        pdf.set_font('Helvetica', 'I', 8.5)
        pdf.cell(mitad, 5, 'Todavía no hay consultas sobre materiales.')
    pdf.set_y(max(fin_1, fin_2, y + 16) + 6)

    # Detalle de las interacciones
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, f'Detalle ({len(interacciones)} interacciones)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 7.5)
    pdf.set_fill_color(255, 255, 255)  # las filas sin color de fondo quedan blancas
    encabezado = FontFace(emphasis='BOLD', color=SALVIA, fill_color=BOSQUE)
    with pdf.table(col_widths=(24, 18, 26, 70, 92, 30, 12, 22), headings_style=encabezado,
                   cell_fill_color=SALVIA_CLARA, cell_fill_mode='ROWS', line_height=4.2,
                   borders_layout='NONE', padding=1.4, text_align='LEFT') as tabla:
        tabla.row(['Fecha', 'Canal', 'Usuario', 'Mensaje', 'Respuesta', 'Intención', 'Conf.', 'Material'])
        for i in interacciones:
            tabla.row([f"{i['fecha']:%d/%m/%Y %H:%M}", 'WhatsApp' if i['canal'] == 'whatsapp' else 'Web',
                       limpiar(i['usuario']), limpiar(i['mensaje'])[:160],
                       limpiar(i['respuesta']).replace('\n', ' ')[:200],
                       limpiar(nombres_intencion.get(i['intencion'], i['intencion'])),
                       f"{float(i['confianza']) * 100:.0f}%", limpiar(i['material_nombre'] or '-')])

    return bytes(pdf.output())
