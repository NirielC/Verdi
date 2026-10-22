-- Base de datos de ReVerde (asistente de reciclaje Verdi)
-- Importar en phpMyAdmin o ejecutar en la consola de MySQL de XAMPP:
--   C:\xampp\mysql\bin\mysql.exe -u root < reciclaje.sql
DROP DATABASE IF EXISTS reciclaje;
CREATE DATABASE reciclaje CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE reciclaje;

-- Usuarios que pueden entrar al panel de administración
CREATE TABLE administradores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Temas del chatbot: cada material con sus recomendaciones
CREATE TABLE materiales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clave VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    contenedor VARCHAR(40) NOT NULL,
    color CHAR(7) NOT NULL,
    reciclable TINYINT(1) NOT NULL DEFAULT 1,
    especial TINYINT(1) NOT NULL DEFAULT 0,
    resumen VARCHAR(255) NOT NULL,
    preparar TEXT NOT NULL,
    ejemplos TEXT NOT NULL,
    no_aceptado TEXT NOT NULL,
    reutilizar TEXT NOT NULL,
    imagen VARCHAR(60) NOT NULL
);

-- Puntos de recolección registrados en el sistema
CREATE TABLE puntos_recoleccion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    municipio VARCHAR(60) NOT NULL,
    latitud DECIMAL(9,6) NOT NULL,
    longitud DECIMAL(9,6) NOT NULL,
    materiales VARCHAR(255) NOT NULL,   -- claves separadas por coma: plastico,papel,vidrio
    horario VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cada mensaje que recibe Verdi (web o WhatsApp) y lo que respondió
CREATE TABLE interacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    canal ENUM('web', 'whatsapp') NOT NULL,
    usuario VARCHAR(60) NOT NULL,
    mensaje TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    intencion VARCHAR(40) NOT NULL,
    confianza DECIMAL(5,2) NOT NULL DEFAULT 0,
    material_clave VARCHAR(30) NULL,
    estado ENUM('nueva', 'revisada') NOT NULL DEFAULT 'nueva',
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fecha (fecha),
    INDEX idx_canal (canal),
    FOREIGN KEY (material_clave) REFERENCES materiales(clave) ON DELETE SET NULL
);

-- Usuario: admin / Contraseña: reverde2026 (guardada con hash scrypt de werkzeug)
INSERT INTO administradores (usuario, password_hash, nombre) VALUES
('admin', 'scrypt:32768:8:1$ye2n6EF1L3Hyi7yC$4b26781ea80307e9ae3b1de45d9a1e0d1ed5e4a2b71243358f55e1a46d6e730a9f2e6a843f46f53c224c15736305257e114da4f81c2b9a68fe9429922998a7c2', 'Elías López');

INSERT INTO materiales (clave, nombre, contenedor, color, reciclable, especial, resumen, preparar, ejemplos, no_aceptado, reutilizar, imagen) VALUES
('plastico', 'Plástico', 'amarillo', '#E2B22F', 1, 0,
 'La mayoría de botellas y envases plásticos se reciclan si van limpios y secos.',
 'Enjuágalos, sécalos y aplástalos para que ocupen menos espacio. Las tapas también se reciclan, pero van separadas.',
 'Botellas de agua y gaseosa, envases de champú, bolsas limpias, garrafones.',
 'Duroport con comida, plásticos con grasa, pajillas y cubiertos desechables.',
 'Corta botellas para hacer macetas o regaderas, y usa los garrafones para guardar granos o como compostera.',
 'plastico.png'),
('papel', 'Papel y cartón', 'azul', '#4A7BA6', 1, 0,
 'El papel y el cartón secos y sin grasa se reciclan muy bien.',
 'Desarma y aplana las cajas, y quita cintas y grapas grandes. Si está mojado o tiene grasa, como la caja de pizza, ya no se recicla.',
 'Periódicos, cuadernos, hojas, cajas de cartón, revistas, empaques de cereal.',
 'Servilletas y papel higiénico usados, papel plastificado, cajas de pizza con grasa, tickets de supermercado.',
 'Usa las hojas por los dos lados, convierte las cajas en organizadores y mete el papel picado al compost.',
 'papel.png'),
('vidrio', 'Vidrio', 'verde', '#3E8B66', 1, 0,
 'El vidrio se puede reciclar una y otra vez sin perder calidad.',
 'Vacía y enjuaga los envases y quítales la tapa. No hace falta quitar la etiqueta.',
 'Botellas de bebidas, frascos de salsa, mermelada y conservas.',
 'Vidrio de ventana, espejos, focos, vasos y platos de cerámica, termómetros.',
 'Los frascos sirven para guardar especias, granos o como vasos y floreros.',
 'vidrio.png'),
('metal', 'Metal y latas', 'gris', '#7F8B91', 1, 0,
 'Las latas de aluminio y de hojalata son de los materiales que más valor tienen al reciclar.',
 'Enjuágalas y aplástalas. Las tapas metálicas de frascos también van aquí.',
 'Latas de gaseosa, de atún, de frijoles o de leche en polvo, tapas metálicas, papel aluminio limpio.',
 'Latas de pintura o aerosoles con residuos: esas van a un punto de residuos especiales.',
 'Las latas limpias sirven de portalápices, macetas pequeñas o moldes para manualidades.',
 'metal.png'),
('organico', 'Orgánico', 'café', '#8A5B38', 1, 0,
 'Los restos de comida y de jardín se convierten en abono si haces compost.',
 'Sepáralos del resto de la basura, no los metas en bolsas plásticas y escúrrelos bien.',
 'Cáscaras de frutas y verduras, restos de café, cascarones de huevo, hojas y grama.',
 'Carne y huesos en el compost de casa (atraen plagas), excremento de mascotas y aceite.',
 'Haz compost: mezcla restos verdes (cáscaras) con secos (hojas, cartón) y en dos o tres meses tendrás abono para tus plantas.',
 'organico.png'),
('textil', 'Ropa y textiles', 'donación', '#76679F', 1, 0,
 'La ropa en buen estado se dona; la que está dañada se convierte en trapos o relleno.',
 'Lávala y sepárala: la que está en buen estado para donar y la dañada para reutilizar.',
 'Ropa, zapatos, sábanas, toallas, mochilas.',
 'Textiles con aceite, pintura o químicos.',
 'Las camisetas viejas sirven como trapos de limpieza o para coser bolsas de tela.',
 'textil.png'),
('electronicos', 'Electrónicos', 'punto especial', '#E8603C', 1, 1,
 'Celulares, cargadores y aparatos tienen metales que contaminan, pero muchas de sus piezas se recuperan.',
 'Borra tus datos, quítale las baterías si se puede y llévalo a un punto que reciba electrónicos. Nunca a la basura común.',
 'Celulares, computadoras, cargadores, cables, audífonos, electrodomésticos pequeños.',
 'No los quemes ni los desarmes en casa.',
 'Si todavía funciona, dónalo o véndelo; si no, en los talleres de reparación aprovechan los repuestos.',
 'electronicos.png'),
('pilas', 'Pilas y baterías', 'punto especial', '#E8603C', 1, 1,
 'Una sola pila puede contaminar miles de litros de agua: nunca va a la basura común.',
 'Guárdalas en un frasco plástico seco y con tapa, y cubre con cinta los polos de las baterías de litio. Llévalas a un punto que las reciba.',
 'Pilas AA y AAA, pilas de botón, baterías de celular, de laptop o de carro.',
 'No las mezcles con el metal reciclable ni las tires al fuego.',
 'Usa pilas recargables: una sola reemplaza cientos de pilas desechables.',
 'pilas.png'),
('aceite', 'Aceite de cocina', 'punto especial', '#E8603C', 1, 1,
 'Un litro de aceite usado contamina hasta mil litros de agua si se va por el desagüe.',
 'Déjalo enfriar, cuélalo y guárdalo en una botella plástica bien cerrada. Llévala a un punto que reciba aceite.',
 'Aceite de freír, manteca usada.',
 'Nunca lo tires al lavatrastos, al inodoro ni a la tierra.',
 'Con el aceite usado se fabrica jabón y biodiésel en centros autorizados.',
 'aceite.png'),
('medicamentos', 'Medicamentos', 'punto especial', '#E8603C', 0, 1,
 'Los medicamentos vencidos no se reciclan: necesitan un manejo especial.',
 'Déjalos en su empaque, sin sacarlos del blíster, y llévalos a un punto que los reciba. Las cajas de cartón vacías sí van con el papel.',
 'Pastillas vencidas, jarabes, cremas, inhaladores.',
 'No los tires al inodoro ni a la basura común. Las jeringas van dentro de un envase rígido y cerrado.',
 'Compra solo lo que necesitas y revisa cada cierto tiempo las fechas de vencimiento de tu botiquín.',
 'medicamentos.png'),
('comun', 'Basura común', 'negro', '#3A3F3C', 0, 0,
 'Hay cosas que no se pueden reciclar: lo mejor es usar menos de ellas.',
 'Ponlas en una bolsa bien cerrada para el camión de la basura.',
 'Duroport con comida, pañales, servilletas usadas, colillas, empaques brillantes de churritos.',
 'No mezcles aquí pilas, aceite ni electrónicos.',
 'Lleva tu propio vaso, termo y bolsa de tela para evitar desechables.',
 'comun.png');

INSERT INTO puntos_recoleccion (nombre, direccion, municipio, latitud, longitud, materiales, horario, telefono) VALUES
('Acopio Parque Cuscatlán', 'Calle Rubén Darío y 25 Av. Sur, costado del parque', 'San Salvador', 13.698400, -89.205600, 'plastico,papel,vidrio,metal', 'Lun a sáb, 8:00 a 16:00', '2222-1010'),
('EcoPunto Plaza Merliot', 'Calle Chiltiupán, parqueo norte', 'Santa Tecla', 13.677300, -89.265000, 'plastico,papel,metal,electronicos,pilas', 'Todos los días, 9:00 a 19:00', '2289-2020'),
('Punto Verde Antiguo Cuscatlán', 'Calle La Reforma, frente a la alcaldía', 'Antiguo Cuscatlán', 13.673500, -89.246800, 'plastico,papel,vidrio,metal,textil', 'Lun a vie, 8:00 a 17:00', '2243-3030'),
('Centro de Acopio Soyapango', 'Bulevar del Ejército, km 4', 'Soyapango', 13.710000, -89.139400, 'plastico,papel,vidrio,metal,aceite', 'Lun a sáb, 7:00 a 15:00', '2277-4040'),
('Recolección de Especiales Metrocentro', 'Bulevar Los Héroes, nivel 1, módulo de servicios', 'San Salvador', 13.705900, -89.211900, 'electronicos,pilas,medicamentos,aceite', 'Todos los días, 10:00 a 20:00', '2260-5050'),
('Compostera Comunitaria Mejicanos', 'Colonia Zacamil, junto a la casa comunal', 'Mejicanos', 13.731400, -89.207800, 'organico,papel', 'Mar, jue y sáb, 7:00 a 12:00', NULL),
('Punto Limpio Santa Ana', 'Avenida Independencia Sur, frente al parque Colón', 'Santa Ana', 13.992000, -89.556400, 'plastico,papel,vidrio,metal,pilas', 'Lun a sáb, 8:00 a 16:00', '2440-6060'),
('Acopio San Miguel Centro', '4a Calle Poniente, contiguo al mercado municipal', 'San Miguel', 13.481900, -88.180500, 'plastico,papel,metal,textil,electronicos', 'Lun a vie, 8:00 a 16:00', '2661-7070');
