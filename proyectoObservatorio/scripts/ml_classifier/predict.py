
import json
import os
import joblib
import pandas as pd

from preprocessing import construir_texto_prediccion

ML_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(ML_DIR, "models")
SUB_MODELS_DIR = os.path.join(MODELS_DIR, "modelos_sub")


PROJECT_ROOT = os.path.abspath(os.path.join(ML_DIR, "..", ".."))
_CATEGORIAS_CANDIDATES = [
    os.path.join(PROJECT_ROOT, "data", "dashboard", "categorias.json"),  
    os.path.join(ML_DIR, "categorias.json"),  
]
CATEGORIAS_PATH = next((p for p in _CATEGORIAS_CANDIDATES if os.path.exists(p)), _CATEGORIAS_CANDIDATES[0])

_vectorizer = None
_modelo_macro = None
_modelos_sub_cache = {}
_categorias = None
_modelo_disponible = None  


def modelo_disponible() -> bool:
    """True si existen los artefactos mínimos para clasificar (vectorizer + modelo macro)."""
    global _modelo_disponible
    if _modelo_disponible is None:
        _modelo_disponible = os.path.exists(
            os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl")
        ) and os.path.exists(os.path.join(MODELS_DIR, "modelo_macro.pkl"))
    return _modelo_disponible


def _cargar_recursos():
    global _vectorizer, _modelo_macro, _categorias
    if _vectorizer is None:
        _vectorizer = joblib.load(os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl"))
    if _modelo_macro is None:
        _modelo_macro = joblib.load(os.path.join(MODELS_DIR, "modelo_macro.pkl"))
    if _categorias is None:
        with open(CATEGORIAS_PATH, "r", encoding="utf-8") as f:
            _categorias = json.load(f)


def _nombre_macro(macro_id: str) -> str:
    for m in _categorias["macrocategorias"]:
        if m["id"] == macro_id:
            return m["nombre"]
    return "Desconocida"


def _nombre_sub(macro_id: str, sub_id: str) -> str:
    for m in _categorias["macrocategorias"]:
        if m["id"] == macro_id:
            for s in m["subcategorias"]:
                if s["id"] == sub_id:
                    return s["nombre"]
    return "Desconocida"


def _primera_subcategoria(macro_id: str) -> tuple[str, str]:
    
    for m in _categorias["macrocategorias"]:
        if m["id"] == macro_id and m["subcategorias"]:
            sub = m["subcategorias"][0]
            return sub["id"], sub["nombre"]
    return "M00-S00", "Sin asignar"


def _a_texto_seguro(valor) -> str:
    
    if valor is None:
        return ""
    if isinstance(valor, float) and pd.isna(valor):
        return ""
    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass
    return str(valor)


def clasificar_proyecto(nombre: str, objetivo: str, resumen: str) -> dict:
    
    _cargar_recursos()

    nombre = _a_texto_seguro(nombre)
    objetivo = _a_texto_seguro(objetivo)
    resumen = _a_texto_seguro(resumen)

    texto_limpio = construir_texto_prediccion(nombre, objetivo, resumen)
    X = _vectorizer.transform([texto_limpio])

    macro_id = _modelo_macro.predict(X)[0]
    if hasattr(_modelo_macro, "predict_proba"):
        proba_macro = max(_modelo_macro.predict_proba(X)[0])
    else:
        proba_macro = None

    sub_model_path = os.path.join(SUB_MODELS_DIR, f"{macro_id}.pkl")
    if os.path.exists(sub_model_path):
        if macro_id not in _modelos_sub_cache:
            _modelos_sub_cache[macro_id] = joblib.load(sub_model_path)
        modelo_sub = _modelos_sub_cache[macro_id]
        sub_id = modelo_sub.predict(X)[0]
        if hasattr(modelo_sub, "predict_proba"):
            proba_sub = max(modelo_sub.predict_proba(X)[0])
        else:
            proba_sub = None
    else:
        sub_id, _ = _primera_subcategoria(macro_id)
        proba_sub = None

    return {
        "macrocategoria_id": macro_id,
        "macrocategoria": _nombre_macro(macro_id),
        "subcategoria_id": sub_id,
        "subcategoria": _nombre_sub(macro_id, sub_id),
        "confianza_macro": round(float(proba_macro), 4) if proba_macro is not None else None,
        "confianza_sub": round(float(proba_sub), 4) if proba_sub is not None else None,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--nombre", default="")
    parser.add_argument("--objetivo", default="")
    parser.add_argument("--resumen", default="")
    args = parser.parse_args()

    resultado = clasificar_proyecto(args.nombre, args.objetivo, args.resumen)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
