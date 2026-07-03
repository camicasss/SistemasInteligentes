
import re
import unicodedata
import pandas as pd

COLUMNAS_TEXTO = ["nombre", "objetivo", "resumen", "palabras_clave"]

STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "ante", "bajo", "cabe", "con", "contra", "desde", "en", "entre",
    "hacia", "hasta", "para", "por", "según", "sin", "so", "sobre", "tras",
    "y", "o", "u", "e", "ni", "que", "como", "cuando", "donde", "mientras",
    "es", "son", "ser", "fue", "ha", "han", "este", "esta", "estos", "estas",
    "su", "sus", "se", "lo", "le", "les", "mas", "más", "pero", "porque",
    "si", "no", "ya", "muy", "también", "así", "cada", "todo", "toda",
    "todos", "todas", "otro", "otra", "uno", "dos", "proyecto", "estudio",
}


def quitar_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def limpiar_texto(texto: str) -> str:
    """Minúsculas, sin acentos, sin puntuación, sin stopwords básicas."""
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = quitar_acentos(texto)
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    palabras = [p for p in texto.split() if p not in STOPWORDS_ES and len(p) > 1]
    return " ".join(palabras)


def construir_corpus_entrenamiento(df: pd.DataFrame) -> pd.Series:
    
    df = df.copy()
    for col in ["nombre", "objetivo", "resumen", "palabras_clave"]:
        if col not in df.columns:
            df[col] = ""

    texto_combinado = (
        df["nombre"].fillna("") + " " +
        df["objetivo"].fillna("") + " " +
        df["resumen"].fillna("") + " " +
        df["palabras_clave"].fillna("") + " " +
        df["palabras_clave"].fillna("")  # doble peso a palabras clave
    )
    return texto_combinado.apply(limpiar_texto)


def construir_texto_prediccion(nombre: str, objetivo: str, resumen: str) -> str:
    
    texto = f"{nombre or ''} {objetivo or ''} {resumen or ''}"
    return limpiar_texto(texto)


construir_corpus = construir_corpus_entrenamiento


def cargar_dataset(ruta_excel: str, sheet_name=0) -> pd.DataFrame:
    """Carga el Excel y normaliza nombres de columnas a snake_case esperado."""
    df = pd.read_excel(ruta_excel, sheet_name=sheet_name, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df
