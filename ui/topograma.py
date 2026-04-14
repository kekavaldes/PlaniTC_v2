import io
import zipfile
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = BASE_DIR / "data/images/IMAGENES TOPOGRAMA.zip"
EXCEL_PATH = BASE_DIR / "data/excel/imagenes_topograma.xlsx"


REGIONES = {
    "CABEZA": ["CEREBRO", "SPN", "MAXILOFACIAL", "ORBITAS", "OIDOS"],
    "CUELLO": ["CUELLO"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS"],
}


POSICIONES_PACIENTE = ["DECUBITO SUPINO", "DECUBITO PRONO"]
ENTRADAS_PACIENTE = ["CABEZA PRIMERO", "PIES PRIMERO"]
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°"]
POS_EXTREMIDADES = ["brazos arriba", "brazos abajo"]

LONGITUDES_TOPO = [128, 256, 512]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN"]


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


@st.cache_data

def load_excel():
    df = pd.read_excel(EXCEL_PATH)
    df["examen_norm"] = df["examen"].apply(norm)
    df["posicion_norm"] = df["Posición paciente"].apply(norm)
    df["entrada_norm"] = df["entrada del paciente"].apply(norm)
    df["tubo_norm"] = df["Posición tubo"].apply(norm)
    return df


@st.cache_data

def index_zip():
    idx = {}
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        for f in z.namelist():
            name = Path(f).name
            idx[norm(name)] = f
    return idx


def get_image(nombre):
    idx = index_zip()
    key = norm(nombre)
    if key not in idx:
        return None
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        data = z.read(idx[key])
        return Image.open(io.BytesIO(data))



def selectbox_con_placeholder(label, options, key):
    opciones = ["Seleccionar"] + list(options)
    val = st.selectbox(label, opciones, key=key)
    return None if val == "Seleccionar" else val



def render_topograma_panel():
    df = load_excel()

    st.markdown("## 📡 Topograma")

    # -------------------------
    # LAYOUT PRINCIPAL
    # -------------------------
    col1, col2, col3 = st.columns([1, 1, 1.2], gap="large")

    # -------------------------
    # DATOS EXAMEN
    # -------------------------
    with col1:
        st.markdown("### 🧾 Datos del examen")

        region = selectbox_con_placeholder("Región anatómica", REGIONES.keys(), "region")
        examen = selectbox_con_placeholder("Examen", REGIONES.get(region, []), "examen")

        with st.container(border=True):
            st.markdown("##### Vista anatómica")
            st.markdown(
                """
                <div style="height:160px; display:flex; align-items:center; justify-content:center;">
                    <span style="opacity:0.5;">Imagen anatómica</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------
    # POSICIONAMIENTO + PARÁMETROS TOPOGRAMA
    # -------------------------
    with col2:
        st.markdown("### 🛏️ Posicionamiento")

        posicion = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, "pos")
        entrada = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, "entrada")
        tubo = selectbox_con_placeholder("Posición tubo", POS_TUBO, "tubo")
        extremidades = selectbox_con_placeholder("Extremidades", POS_EXTREMIDADES, "ext")

        with st.container(border=True):
            st.markdown("##### Posicionamiento")

            if posicion and entrada and tubo:
                st.success("Posicionamiento definido")
            else:
                st.info("Completa los campos")

        st.markdown("### ⚙️ Parámetros topograma")

        col_p1, col_p2 = st.columns(2, gap="medium")

        with col_p1:
            longitud = selectbox_con_placeholder("Longitud (mm)", LONGITUDES_TOPO, "longitud_topo")
            direccion = selectbox_con_placeholder("Dirección", DIRECCIONES, "direccion_topo")

        with col_p2:
            instruccion = selectbox_con_placeholder(
                "Instrucción de voz",
                INSTRUCCIONES_VOZ,
                "voz_topo",
            )

    # -------------------------
    # TOPOGRAMA
    # -------------------------
    with col3:
        st.markdown("### ✅ Topograma adquirido")

        if st.button("☢️ INICIAR TOPOGRAMA"):
            sel = df[
                (df["examen_norm"] == norm(examen))
                & (df["posicion_norm"] == norm(posicion))
                & (df["entrada_norm"] == norm(entrada))
                & (df["tubo_norm"] == norm(tubo))
            ]

            if not sel.empty:
                nombre = sel.iloc[0]["nombre exacto de la imagen"]
                img = get_image(nombre)

                if img:
                    st.image(img, use_container_width=True)
                    st.success("Topograma adquirido correctamente")
                else:
                    st.error("Imagen no encontrada")
            else:
                st.warning("No hay coincidencia en Excel")

    store = {
        "examen": examen,
        "t1_posicion_paciente": posicion,
        "t1_entrada_paciente": entrada,
        "t1_posicion_tubo": tubo,
        "t1_posicion_extremidades": extremidades,
        "t1_longitud": longitud,
        "t1_direccion": direccion,
        "t1_instruccion_voz": instruccion,
    }

    st.session_state["topograma_store"] = store
    return store
