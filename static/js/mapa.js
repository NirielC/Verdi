// Mapa de puntos de recolección con Leaflet (mapa abierto, sin API key)
const mapa = L.map('mapa', { scrollWheelZoom: false }).setView([13.70, -89.20], 11);

// Mapa base claro de CARTO con datos de OpenStreetMap: es gratis y no necesita API key
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19
}).addTo(mapa);

const iconoPunto = L.divIcon({ className: '', html: '<div class="marcador"></div>', iconSize: [22, 22], iconAnchor: [11, 22] });
const marcadores = {};
const listaPuntos = document.getElementById('lista-puntos');
const filtroMaterial = document.getElementById('filtro-material');
let miUbicacion = null;

function distanciaKm(lat1, lon1, lat2, lon2) {
    const rad = x => x * Math.PI / 180;
    const a = Math.sin(rad(lat2 - lat1) / 2) ** 2 +
              Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(a));
}

function textoMateriales(punto) {
    return punto.lista_materiales.map(c => MATERIALES[c] || c).join(', ');
}

PUNTOS.forEach(punto => {
    marcadores[punto.id] = L.marker([punto.latitud, punto.longitud], { icon: iconoPunto })
        .addTo(mapa)
        .bindPopup(`<strong>${punto.nombre}</strong><br>${punto.direccion}, ${punto.municipio}<br>${punto.horario}` +
                   `<br><a href="https://www.google.com/maps/dir/?api=1&destination=${punto.latitud},${punto.longitud}" target="_blank" rel="noopener">Cómo llegar</a>`);
});

// Dibuja la lista según el filtro y, si la tenemos, la ubicación del usuario
function pintarLista() {
    const material = filtroMaterial.value;
    let puntos = PUNTOS.filter(p => !material || p.lista_materiales.includes(material));
    if (miUbicacion) {
        puntos = puntos.map(p => ({ ...p, distancia: distanciaKm(miUbicacion[0], miUbicacion[1], p.latitud, p.longitud) }))
                       .sort((a, b) => a.distancia - b.distancia);
    }

    PUNTOS.forEach(p => {
        const visible = puntos.some(v => v.id === p.id);
        if (visible) marcadores[p.id].addTo(mapa); else marcadores[p.id].remove();
    });

    listaPuntos.innerHTML = '';
    if (!puntos.length) {
        listaPuntos.innerHTML = '<li class="punto"><p>Ningún punto recibe ese material todavía. Prueba con «Todos los materiales».</p></li>';
        return;
    }
    puntos.forEach(p => {
        const li = document.createElement('li');
        li.className = 'punto';
        li.tabIndex = 0;
        li.dataset.id = p.id;
        li.innerHTML = `${p.distancia !== undefined ? `<span class="distancia">${p.distancia.toFixed(1)} km</span>` : ''}
            <h3>${p.nombre}</h3>
            <p>${p.direccion}, ${p.municipio}</p>
            <p>${p.horario}</p>
            <div class="punto-materiales" title="Recibe: ${textoMateriales(p)}">
                ${p.lista_materiales.map(c => `<span class="punto-color" style="--color:${COLORES[c] || '#888'}"></span>`).join('')}
            </div>`;
        li.addEventListener('click', () => enfocarPunto(p.id));
        li.addEventListener('keydown', e => { if (e.key === 'Enter') enfocarPunto(p.id); });
        listaPuntos.appendChild(li);
    });
}

// Centra el mapa en un punto (también lo usa el chat de Verdi)
function enfocarPunto(id) {
    const marcador = marcadores[id];
    if (!marcador) return;
    document.getElementById('puntos').scrollIntoView({ behavior: 'smooth' });
    mapa.flyTo(marcador.getLatLng(), 15, { duration: .8 });
    marcador.addTo(mapa).openPopup();
    document.querySelectorAll('.punto').forEach(li => li.classList.toggle('activo', li.dataset.id == id));
}

filtroMaterial.addEventListener('change', pintarLista);

document.getElementById('cerca-de-mi').addEventListener('click', () => {
    if (!navigator.geolocation) return alert('Tu navegador no permite compartir la ubicación.');
    navigator.geolocation.getCurrentPosition(pos => {
        miUbicacion = [pos.coords.latitude, pos.coords.longitude];
        L.circleMarker(miUbicacion, { radius: 8, color: '#fff', weight: 3, fillColor: '#2F80ED', fillOpacity: 1 })
            .addTo(mapa).bindPopup('Estás aquí');
        mapa.flyTo(miUbicacion, 12);
        pintarLista();
    }, () => alert('No pudimos obtener tu ubicación. Revisa el permiso del navegador.'));
});

pintarLista();
