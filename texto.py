# Preprocesamiento de texto compartido por el entrenamiento (chatty.py) y el chatbot (cerebro.py)
import string
import unicodedata

import nltk
from nltk.stem import SnowballStemmer

# El lematizador de WordNet solo funciona en inglés; para español usamos el stemmer Snowball,
# que corta las palabras a su raíz ("botellas" -> "botell", "reciclar" -> "recicl")
stemmer = SnowballStemmer('spanish')

# Palabras vacías ("de", "el", "la"...). Quitamos "donde", "como", "quien"... de la lista
# porque en este chatbot sí cambian el sentido ("¿dónde lo llevo?" vs "¿cómo lo reutilizo?", "¿quién eres?")
STOPWORDS = set(nltk.corpus.stopwords.words('spanish')) - {'donde', 'que', 'como', 'no', 'quien', 'eres', 'nada'}


def quitar_tildes(texto):
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


def normalizar(oracion):
    """Minúsculas, sin tildes y sin puntuación (incluye los signos de apertura ¿ ¡)."""
    oracion = quitar_tildes(oracion.lower())
    return ''.join(c for c in oracion if c not in string.punctuation + '¿¡«»')


def preproceso(oracion):
    """Normaliza, tokeniza, quita stopwords y deja la raíz de cada palabra."""
    tokens = nltk.word_tokenize(normalizar(oracion))
    tokens = [stemmer.stem(palabra) for palabra in tokens if palabra not in STOPWORDS]
    return ' '.join(tokens)
