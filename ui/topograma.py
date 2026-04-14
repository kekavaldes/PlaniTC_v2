# SOLO reemplaza tu archivo ui/topograma.py por este

# (archivo completo con debug de columnas)

import io
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXCEL_DIR = DATA_DIR / "excel"
IMAGES_DIR = DATA_DIR / "images"

EXCEL_TOPOGRAMAS = EXCEL_DIR / "imagenes_topograma.xlsx"

def _norm_text(v):
    if v is None:
        return ""
    s = str(v).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())

@st.cache_data
def cargar_tabla_topogramas():
    if not EXCEL_TOPOGRAMAS.exists():
        return pd.DataFrame(), "No se encontró el Excel"

    df = pd.read_excel(EXCEL_TOPOGRAMAS)

    columnas_norm = {_norm_text(c): c for c in df.columns}

    def buscar(*nombres):
        for n in nombres:
            if n in columnas_norm:
                return columnas_norm[n]
        return None

    col_examen = buscar("examen")
    col_posicion = buscar("posicion paciente")
    col_entrada = buscar("entrada del paciente")
    col_tubo = buscar("posicion tubo")
    col_imagen = buscar("nombre exacto de la imagen")

    if not all([col_examen, col_posicion, col_entrada, col_tubo, col_imagen]):
        st.error("Columnas detectadas en Excel:")
        st.write(df.columns)

        st.error("Columnas reconocidas:")
        st.write({
            "examen": col_examen,
            "posicion": col_posicion,
            "entrada": col_entrada,
            "tubo": col_tubo,
            "imagen": col_imagen,
        })

        return pd.DataFrame(), "Error columnas"

    return df, None


def render_topograma_panel():
    st.title("Topograma DEBUG")

    df, err = cargar_tabla_topogramas()

    if err:
        st.warning(err)
    else:
        st.success("Excel leído correctamente")
        st.dataframe(df.head())
