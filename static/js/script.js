// Chat de Verdi: envía los mensajes a /chat y dibuja la respuesta (texto, imagen, botones y puntos)
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const panelVerdi = document.getElementById('verdi');

const BOTONES_INICIO = ['Clasificar residuo', 'Puntos de acopio', 'Separar en casa'];

// Convierte el formato de WhatsApp (*negrita*) a HTML de forma segura
function formatear(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML.replace(/\*([^*\n]+)\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
}

// Función para agregar un mensaje a la caja de chat
function agregarMensaje(texto, quien) {
    const burbuja = document.createElement('div');
    burbuja.className = `mensaje mensaje-${quien}`;
    burbuja.innerHTML = `<p>${formatear(texto)}</p>`;
    chatBox.appendChild(burbuja);
    chatBox.scrollTop = chatBox.scrollHeight;
    return burbuja;
}

// Botones de respuesta rápida debajo del mensaje de Verdi
function agregarOpciones(botones, extra = []) {
    if (!botones.length && !extra.length) return;
    const contenedor = document.createElement('div');
    contenedor.className = 'opciones';
    botones.forEach(texto => {
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'opcion';
        boton.textContent = texto;
        boton.addEventListener('click', () => enviarMensaje(texto));
        contenedor.appendChild(boton);
    });
    extra.forEach(elemento => contenedor.appendChild(elemento));
    chatBox.appendChild(contenedor);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function mostrarRespuesta(data) {
    const burbuja = agregarMensaje(data.respuesta || data.texto, 'bot');

    if (data.imagen) {
        const img = document.createElement('img');
        img.src = data.imagen;
        img.alt = 'Tarjeta del material';
        img.addEventListener('click', () => window.open(data.imagen, '_blank'));
        img.addEventListener('load', () => { chatBox.scrollTop = chatBox.scrollHeight; });
        burbuja.appendChild(img);
    }

    // Los puntos se pueden tocar para verlos en el mapa
    if (data.puntos && data.puntos.length) {
        const lista = document.createElement('ul');
        lista.className = 'mensaje-puntos';
        data.puntos.forEach(p => {
            const li = document.createElement('li');
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.innerHTML = `<strong>${p.nombre}</strong>${p.municipio}${p.distancia !== null ? ` · ${p.distancia} km` : ''}`;
            boton.addEventListener('click', () => { cerrarPanel(); enfocarPunto(p.id); });
            li.appendChild(boton);
            lista.appendChild(li);
        });
        burbuja.querySelector('p').innerHTML = formatear(data.texto.split('\n')[0]);
        burbuja.appendChild(lista);
    }

    const extra = [];
    if (data.pedir_ubicacion) {
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'opcion';
        boton.textContent = 'Usar mi ubicación';
        boton.addEventListener('click', enviarUbicacion);
        extra.push(boton);
    }
    if (data.whatsapp) {
        const enlace = document.createElement('a');
        enlace.className = 'opcion opcion-whatsapp';
        enlace.href = ENLACE_WHATSAPP;
        enlace.target = '_blank';
        enlace.rel = 'noopener';
        enlace.textContent = 'Seguir en WhatsApp';
        extra.push(enlace);
    }
    agregarOpciones(data.botones || [], extra);
}

// Realiza la solicitud POST al servidor en la ruta '/chat'
function preguntar(cuerpo) {
    const escribiendo = agregarMensaje('', 'bot');
    escribiendo.innerHTML = '<span class="escribiendo" aria-label="Verdi está escribiendo"><span></span><span></span><span></span></span>';

    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo)
    })
    .then(response => response.json())
    .then(data => {
        escribiendo.remove();
        if (data.error) return agregarMensaje(data.error, 'bot');
        mostrarRespuesta(data);
    })
    .catch(error => {
        escribiendo.remove();
        agregarMensaje('No pude conectarme con el servidor. Revisa que Flask esté encendido e inténtalo de nuevo.', 'bot');
        console.error('Error:', error);
    });
}

// Función que se ejecuta al enviar un mensaje (desde el input, un botón o la página)
function enviarMensaje(texto) {
    const mensaje = (texto ?? userInput.value).trim();
    if (mensaje === '') return;
    agregarMensaje(mensaje, 'usuario');
    userInput.value = '';
    preguntar({ mensaje });
}

function enviarUbicacion() {
    if (!navigator.geolocation) return agregarMensaje('Tu navegador no permite compartir la ubicación.', 'bot');
    navigator.geolocation.getCurrentPosition(
        pos => {
            agregarMensaje('Te comparto mi ubicación', 'usuario');
            preguntar({ latitud: pos.coords.latitude, longitud: pos.coords.longitude });
        },
        () => agregarMensaje('No pude obtener tu ubicación. Revisa el permiso del navegador o elige un punto de la lista.', 'bot')
    );
}

// Panel de Verdi en pantallas medianas y celulares
function abrirPanel() { panelVerdi.classList.add('abierto'); userInput.focus(); }
function cerrarPanel() { panelVerdi.classList.remove('abierto'); }
document.getElementById('abrir-verdi').addEventListener('click', abrirPanel);
document.getElementById('verdi-cerrar').addEventListener('click', cerrarPanel);

document.getElementById('chat-form').addEventListener('submit', e => { e.preventDefault(); enviarMensaje(); });

// La página principal le pasa preguntas a Verdi: buscador, sugerencias y contenedores
document.getElementById('buscador').addEventListener('submit', e => {
    e.preventDefault();
    const campo = document.getElementById('buscador-texto');
    if (!campo.value.trim()) return campo.focus();
    abrirPanel();
    enviarMensaje(campo.value);
    campo.value = '';
});
document.querySelectorAll('[data-preguntar]').forEach(boton => {
    boton.addEventListener('click', () => { abrirPanel(); enviarMensaje(boton.dataset.preguntar); });
});

// Saludo inicial (no se guarda en la base de datos porque el usuario todavía no ha escrito)
agregarMensaje('¡Hola! Soy *Verdi*, tu asistente de reciclaje. Cuéntame qué quieres tirar y te digo en qué contenedor va, cómo prepararlo y dónde llevarlo.', 'bot');
agregarOpciones(BOTONES_INICIO);
