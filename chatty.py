# Entrenamiento del modelo de clasificación de intenciones de Verdi
# Se ejecuta una vez (y cada vez que cambias intenciones.json): python chatty.py
import json
import os
import pickle
import warnings

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC

from texto import preproceso

# Carpeta del proyecto: así funciona aunque se ejecute desde otra carpeta
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Cargar el archivo de intenciones
with open(os.path.join(CARPETA, 'intenciones.json'), 'r', encoding='utf-8') as file:
    data = json.load(file)

# Preparación de los datos: cada patrón es una oración de ejemplo de su etiqueta
oraciones = []
etiquetas = []

for intencion in data['intenciones']:
    for patron in intencion['patrones']:
        oraciones.append(preproceso(patron))
        etiquetas.append(intencion['etiqueta'])

# Vectorizar las oraciones (TF-IDF). ngram_range=(1, 2) también toma pares de palabras ("donde llevo")
vectorizar = TfidfVectorizer(ngram_range=(1, 2))
X = vectorizar.fit_transform(oraciones)

# Codificar las etiquetas (texto -> número)
le = LabelEncoder()
y = le.fit_transform(etiquetas)

# Entrenar el modelo (SVM lineal con probabilidades para saber qué tan seguro está)
# scikit-learn 1.9 avisa que probability=True cambiará en el futuro; por ahora funciona igual que en la guía
warnings.filterwarnings('ignore', category=FutureWarning)
model = SVC(kernel='linear', probability=True, random_state=42)
model.fit(X, y)

# Guardar el modelo y los objetos necesarios
with open(os.path.join(CARPETA, 'model.pkl'), 'wb') as f:
    pickle.dump((vectorizar, le, model), f)

print(f"Modelo entrenado con {len(oraciones)} oraciones y {len(le.classes_)} intenciones.")
