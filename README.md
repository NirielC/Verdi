# ReVerde: asistente de reciclaje con el chatbot Verdi

Examen Final de **Diseño de Aplicaciones con Inteligencia Artificial**, tema 9: *Asistente de reciclaje especializado*.
Autor: Elías López. Colegio Español Padre Arrupe, 2026.

ReVerde es un sitio web hecho en Flask que ayuda a clasificar residuos. Incluye a **Verdi**, un chatbot que responde
dudas sobre materiales reciclables, separación en casa, reutilización y residuos especiales, y que ubica los puntos de
recolección registrados en el sistema. El mismo chatbot funciona en la página web y en **WhatsApp**.

## Qué incluye

| Requisito del examen | Dónde está |
|---|---|
| Página principal del tema con el chatbot integrado | `templates/index.html`: buscador, contenedores por material, mapa de puntos, separación en casa y residuos especiales. Verdi va en el panel derecho. |
| Chatbot entrenado | `intenciones.json` (14 intenciones) + `chatty.py` (TF-IDF + SVM) + `cerebro.py` (intención + detección del material con palabras clave) |
| Imágenes y botones interactivos | Tarjetas PNG por material (`generar_imagenes.py`), botones de respuesta rápida, listas y ubicación en WhatsApp |
| Puntos de recolección | Tabla `puntos_recoleccion`, mapa Leaflet en la web, "punto más cercano" con la ubicación del navegador o la que se comparte en WhatsApp |
| Panel de administración con login | `/admin` (usuario y contraseña con hash): resumen, interacciones con filtros, marcar como revisada, eliminar, y CRUD de puntos |
| Reporte PDF | Botón "Descargar reporte PDF" (`reportes.py`, respeta los filtros) |
| Base de datos MySQL (XAMPP) | `reciclaje.sql`; conexión en `db.py` |
| Chatbot de WhatsApp | `whatsapp.py` (webhook `/inbound`) + `canal.py` (envío con Vonage) |
| Redirigir de la web a WhatsApp | Botón "Seguir en WhatsApp" (riel, chat y cuando el usuario lo pide) |

## Estructura

```
ReVerde/
├── app.py               Servidor Flask: página principal, /chat, login y panel de administración
├── whatsapp.py          Webhook de Vonage (/inbound, /status): mismo cerebro, respuesta en formato WhatsApp
├── canal.py             Envío por la API de Vonage: texto, imagen, botones, lista y ubicación
├── cerebro.py           Lógica de Verdi: intención (SVM) + material (palabras clave) + respuesta
├── texto.py             Preprocesamiento: minúsculas, sin tildes, tokens, stopwords y stemmer
├── chatty.py            Entrenamiento del modelo → model.pkl
├── intenciones.json     Patrones y respuestas de cada intención
├── db.py                Conexión a MySQL y todas las consultas (parametrizadas)
├── reportes.py          Reporte PDF con fpdf2
├── generar_imagenes.py  Crea las tarjetas PNG de cada material
├── probar_terminal.py   Prueba de Verdi en la consola
├── reciclaje.sql        Base de datos: tablas y datos iniciales
├── templates/           index.html, 404.html y admin/
└── static/              css/, js/ (chat y mapa) e img/
```

## Base de datos `reciclaje`

- `administradores`: usuarios del panel (contraseña con hash scrypt).
- `materiales`: los temas del chatbot (contenedor, cómo prepararlo, ejemplos, qué no va, ideas para reutilizar, imagen).
- `puntos_recoleccion`: nombre, dirección, municipio, coordenadas, materiales que recibe, horario y si está activo.
- `interacciones`: cada mensaje de la web o WhatsApp con la respuesta, intención, confianza, material y estado (nueva / revisada).

## Instalación

1. Encender **MySQL** en el panel de XAMPP.
2. Importar la base de datos (en phpMyAdmin → Importar → `reciclaje.sql`, o en consola):
   ```bash
   C:\xampp\mysql\bin\mysql.exe -u root < reciclaje.sql
   ```
3. Crear el entorno e instalar dependencias (desde la carpeta `Examen_DAI`):
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r ReVerde\requirements.txt
   ```
4. Copiar `.env.example` como `.env` y poner las credenciales de Vonage.
5. Desde la carpeta `ReVerde`, entrenar el modelo y crear las imágenes (solo la primera vez o si cambia `intenciones.json`):
   ```bash
   python chatty.py
   python generar_imagenes.py
   ```

## Ejecución

```bash
python app.py
```

- Sitio: http://localhost:5000
- Panel: http://localhost:5000/admin, con el usuario **admin** y la contraseña **reverde2026**
- Probar a Verdi sin navegador: `python probar_terminal.py`

### WhatsApp (Vonage sandbox + Cloudflare)

1. Con `app.py` encendido, en otra terminal:
   ```bash
   C:\Users\elsni\Downloads\cloudflared\cloudflared.exe tunnel --url http://localhost:5000
   ```
2. En el dashboard de Vonage → Messages → Sandbox → Webhooks:
   - Inbound: `https://<tu-url>.trycloudflare.com/inbound`
   - Status: `https://<tu-url>.trycloudflare.com/status`
3. Escribir `hola` al número del sandbox (+1 415 738 6102) desde un número aprobado.

> La URL de Cloudflare cambia cada vez que se reinicia el túnel: hay que actualizar los webhooks cuando eso pase.

## Cómo entiende Verdi un mensaje

1. Si el mensaje es el texto de un botón (por ejemplo "Dónde llevarlo"), la intención ya se sabe.
2. Si no, `texto.preproceso()` lo normaliza y el **SVM** predice la intención con su confianza (mínimo 35 %).
3. En paralelo, `detectar_material()` busca palabras clave con expresiones regulares ("lata" → metal, "cargador" → electrónicos).
   Si encuentra un material, la consulta es sobre ese material, salvo que se pidan puntos o ideas para reutilizarlo.
4. Verdi recuerda el último material de cada usuario, por eso entiende "¿y dónde lo llevo?".
5. La respuesta sale de la tabla `materiales` o de `intenciones.json` y se guarda en `interacciones`.

## Mapa y fotos

- El mapa usa **Leaflet** con el mapa base de **CARTO / OpenStreetMap**: es gratuito y **no necesita API key** (Google Maps
  exige una cuenta de facturación con tarjeta). Los enlaces «Cómo llegar» abren Google Maps sin necesidad de clave.
- Las fotos de los materiales (`static/img/fotos/`) son de [Unsplash](https://unsplash.com) y se usan bajo la
  [licencia de Unsplash](https://unsplash.com/license) (uso gratuito, también en proyectos educativos).
- Las tarjetas de WhatsApp (`static/img/materiales/`) se generan a partir de esas fotos con `generar_imagenes.py`.

## Conversación

- Verdi entiende saludos, cómo está, gracias, sí/no, frustración ("no entiendo") y despedidas, además de los temas de reciclaje.
- Las respuestas cambian entre varias versiones para que no suene siempre igual.
- En WhatsApp todas las respuestas incluyen la opción **Finalizar**, que cierra la conversación.
- Al compartir la ubicación, Verdi responde con el punto más cercano (y lo manda como ubicación en WhatsApp) sin volver a pedirla.

## Limitaciones

- El chatbot es de procesamiento de lenguaje clásico (no generativo): entiende los temas con los que fue entrenado.
- La memoria del último material vive en el servidor y se pierde al reiniciarlo (los datos de la BD no).
- El sandbox de Vonage solo responde a números aprobados y dentro de la ventana de 24 horas de WhatsApp.
- Los puntos de recolección son datos de ejemplo para la demostración; se administran desde el panel.
- Los webhooks no verifican la firma de Vonage (mejora futura).
