# topograma FINAL FIX

import io
import zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
from PIL import Image
import unicodedata

BASE_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = BASE_DIR / "data/images/IMAGENES TOPOGRAMA.zip"
EXCEL_PATH = BASE_DIR / "data/excel/imagenes_topograma.xlsx"

def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s

@st.cache_data
def load_excel():
    df = pd.read_excel(EXCEL_PATH)
    return df

@st.cache_data
def index_zip():
    idx = {}
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        for f in z.namelist():
            if "__MACOSX" in f or f.endswith("/"):
                continue
            name = Path(f).name
            idx[norm(name)] = f
            idx[norm(Path(name).stem)] = f
    return idx

def get_image(nombre):
    idx = index_zip()
    key = norm(nombre)
    if key not in idx:
        return None
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        data = z.read(idx[key])
        return Image.open(io.BytesIO(data))

def render_topograma_panel():
    st.title("Topograma FINAL")

    df = load_excel()

    examen = st.selectbox("Examen", df["examen"].dropna().unique())
    posicion = st.selectbox("Posición paciente", df["Posición paciente"].dropna().unique())
    entrada = st.selectbox("Entrada", df["entrada del paciente"].dropna().unique())
    tubo = st.selectbox("Posición tubo", df["Posición tubo"].dropna().unique())

    sel = df[
        (df["examen"] == examen) &
        (df["Posición paciente"] == posicion) &
        (df["entrada del paciente"] == entrada) &
        (df["Posición tubo"] == tubo)
    ]

    if not sel.empty:
        nombre = sel.iloc[0]["nombre exacto de la imagen"]
        img = get_image(nombre)
        if img:
            st.image(img)
        else:
            st.error(f"No se encontró imagen: {nombre}")
