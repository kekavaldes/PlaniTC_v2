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

DIR_IMAGENES_TOPO_POS = BASE_DIR / "data/images/IMAGENES POSICIONAMIENTO TOPOGRAMA"
ZIP_IMAGENES_TOPO_POS = BASE_DIR / "data/images/IMAGENES POSICIONAMIENTO TOPOGRAMA.zip"
CACHE_IMAGENES_TOPO_POS = BASE_DIR / "_cache_imagenes_topograma"


REGIONES = {
    "CABEZA": ["CEREBRO", "SPN", "MAXILOFACIAL", "ORBITAS", "OIDOS"],
    "CUELLO": ["CUELLO"],
    "COLUMNA": ["CERVICAL", "DORSAL", "LUMBAR"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS", "ABDOMEN-PELVIS", "PIELOTC", "TORAX-ABDOMEN-PELVIS"],
    "EESS": ["HOMBRO", "BRAZO", "CODO", "ANTEBRAZO", "MUÑECA", "MANO"],
    "EEII": ["CADERA", "MUSLO", "RODILLA", "PIERNA", "TOBILLO", "PIE"],
    "ANGIO": [
        "ATC CEREBRO",
        "ATC CUELLO",
        "ATC CEREBRO CUELLO",
        "ATC TORAX",
        "ATC ABDOMEN",
        "ATC ABDOMEN-PELVIS",
        "ATC TORAX-ABDOMEN-PELVIS",
        "ATC EESS DERECHA",
        "ATC EESS IZQUIERDA",
        "ATC EEII",
    ],
}

POSICIONES_PACIENTE = [
    "DECUBITO SUPINO",
    "DECUBITO PRONO",
    "LATERAL DERECHO",
    "LATERAL IZQUIERDO",
]

ENTRADAS_PACIENTE = ["CABEZA PRIMERO", "PIES PRIMERO"]
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]

POS_EXTREMIDADES = [
    "NINGUNA",
    "BRAZOS ARRIBA",
    "BRAZOS ABAJO",
    "ELEVA BRAZO DERECHO",
    "ELEVA BRAZO IZQUIERDO",
    "FLEXION EXTREMIDAD INFERIOR DERECHA",
    "FLEXION EXTREMIDAD INFERIOR IZQUIERDA",
]

INICIO_TOPO_OPCIONES = [
    "SOBRE APICES PULMONARES",
    "SOBRE CUPULAS DIAF.",
    "SOBRE ORBITAS",
    "SOBRE OIDOS",
    "SOBRE SPN",
    "SOBRE MAXILOFACIAL",
    "SOBRE C1",
    "SOBRE D1",
    "SOBRE L1",
    "SOBRE SACRO",
]

FIN_TOPO_OPCIONES = [
    "SOBRE APICES PULMONARES",
    "SOBRE CUPULAS DIAF.",
    "SOBRE ORBITAS",
    "SOBRE OIDOS",
    "SOBRE SPN",
    "SOBRE MAXILOFACIAL",
    "SOBRE C1",
    "SOBRE D1",
    "SOBRE L1",
    "SOBRE SACRO",
]

LONGITUDES_TOPO = [128, 256, 512, 768, 1020, 1560]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("°", "").replace("º", "")
    return " ".join(s.split())


def norm_file_name(s):
    s = norm(s)
    s = s.replace("lateral derecho", "lateral_derecho")
    s = s.replace("lateral izquierdo", "lateral_izquierdo")
    s = s.replace("cabeza primero", "cabeza_primero")
    s = s.replace("pies primero", "pies_primero")
    s = s.replace("derecha", "derecho")
    s = s.replace("izquierda", "izquierdo")
    s = s.replace("arriba 0", "arriba")
    s = s.replace("abajo 180", "abajo")
    s = s.replace("decubito ", "")
    s = s.replace(" ", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _init_state():
    defaults = {
        "region_anatomica": None,
        "examen": None,
        "posicion_paciente": None,
        "entrada_paciente": None,
        "posicion_tubo": None,
        "posicion_extremidades": None,
        "t1_inicio": None,
        "t1_fin": None,
        "t1_kv": 100,
        "t1_ma": 40,
        "t1_mm_inicio": 0,
        "t1_mm_fin": 400,
        "t1_longitud": None,
        "t1_direccion": None,
        "t1_voz": None,
        "t1_centraje_inicio": None,
        "aplica_topograma_2": False,
        "topograma_iniciado": False,
        "topograma_store": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}


def selectbox_con_placeholder(label, options, key, placeholder="Seleccionar"):
    opciones = [placeholder] + list(options)
    actual = st.session_state.get(key)
    index = opciones.index(actual) if actual in options else 0
    valor = st.selectbox(label, opciones, index=index, key=f"widget_{key}")
    st.session_state[key] = None if valor == placeholder else valor
    return st.session_state[key]


def number_input_con_stepper(label, key, min_value=0, max_value=4000, step=1):
    current = int(st.session_state.get(key, 0))
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        value = st.number_input(
            label,
            min_value=min_value,
            max_value=max_value,
            step=step,
            value=current,
            key=f"widget_{key}",
            label_visibility="collapsed",
        )
    with c2:
        minus = st.button("−", key=f"minus_{key}", use_container_width=True)
    with c3:
        plus = st.button("+", key=f"plus_{key}", use_container_width=True)

    if minus:
        value = max(min_value, int(value) - step)
    if plus:
        value = min(max_value, int(value) + step)

    st.session_state[key] = int(value)
    return st.session_state[key]


@st.cache_data
def load_excel():
    df = pd.read_excel(EXCEL_PATH)
    # normalizados robustos
    df["examen_norm"] = df["examen"].apply(norm)
    df["posicion_norm"] = df["Posición paciente"].apply(norm)
    df["entrada_norm"] = df["entrada del paciente"].apply(norm)
    df["tubo_norm"] = df["Posición tubo"].apply(norm)
    df["nombre_imagen_norm"] = df["nombre exacto de la imagen"].apply(norm)
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


def obtener_imagen_posicionamiento(posicion, entrada, tubo):
    objetivos = {
        norm_file_name(f"topograma_{entrada}_{posicion}_{tubo}"),
        norm_file_name(f"{entrada}_{posicion}_{tubo}"),
    }
    exts = {".png", ".jpg", ".jpeg", ".webp"}

    fuentes = []
    if DIR_IMAGENES_TOPO_POS.exists():
        fuentes.append(DIR_IMAGENES_TOPO_POS)

    if ZIP_IMAGENES_TOPO_POS.exists():
        CACHE_IMAGENES_TOPO_POS.mkdir(parents=True, exist_ok=True)
        marker = CACHE_IMAGENES_TOPO_POS / ".ok"
        if not marker.exists():
            with zipfile.ZipFile(ZIP_IMAGENES_TOPO_POS, "r") as zf:
                zf.extractall(CACHE_IMAGENES_TOPO_POS)
            marker.write_text("ok", encoding="utf-8")
        interna = CACHE_IMAGENES_TOPO_POS / "IMAGENES POSICIONAMIENTO TOPOGRAMA"
        if interna.exists():
            fuentes.append(interna)
        else:
            fuentes.append(CACHE_IMAGENES_TOPO_POS)

    for fuente in fuentes:
        if not fuente.exists():
            continue
        for ruta in fuente.rglob("*"):
            if not ruta.is_file() or ruta.suffix.lower() not in exts:
                continue
            stem = norm_file_name(ruta.stem)
            if stem in objetivos:
                return ruta
    return None


def render_topograma_panel():
    _init_state()
    store = st.session_state["topograma_store"]
    df = load_excel()

    st.markdown("### 📡 Topograma")
    st.markdown("""
<style>

/* Fondo general */
.stApp {
    background-color: #0e1117;
    color: white;
}

/* Títulos */
h1, h2, h3, h4 {
    color: white !important;
}

/* Cards / contenedores */
div[data-testid="stVerticalBlock"] > div {
    background-color: #1c1f26;
    border-radius: 12px;
    padding: 12px;
}

/* Selectbox */
div[data-baseweb="select"] {
    background-color: #2a2e36 !important;
    color: white !important;
}

/* Inputs */
input {
    background-color: #2a2e36 !important;
    color: white !important;
}

/* Botón principal */
.stButton button {
    background-color: #2a2e36;
    color: white;
    border-radius: 10px;
    border: 1px solid #444;
}

/* Botón hover */
.stButton button:hover {
    background-color: #3a3f4b;
}

/* Mensajes */
.stAlert {
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)
    st.markdown("### 📡 Topograma")

# CSS 1 (el que ya tenías)
st.markdown("""
<style>
...
</style>
""", unsafe_allow_html=True)

# 👇 AQUÍ PEGAS EL NUEVO
st.markdown("""
<style>

/* SELECTBOX */
div[data-baseweb="select"] > div {
    background-color: #1a1d24 !important;
    color: white !important;
    border: 1px solid #444 !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] span {
    color: white !important;
}

div[data-baseweb="popover"] {
    background-color: #1a1d24 !important;
    color: white !important;
}

/* INPUTS */
.stNumberInput input,
.stTextInput input,
input[type="text"],
input[type="number"] {
    background-color: #1a1d24 !important;
    color: white !important;
    border: 1px solid #444 !important;
    border-radius: 10px !important;
    -webkit-text-fill-color: white !important;
}

/* LABELS */
label, .stMarkdown, .stCaption, p, span, div {
    color: white;
}

/* Checkbox */
.stCheckbox label {
    color: white !important;
}

/* Flecha */
svg {
    color: white !important;
    fill: white !important;
}

</style>
""", unsafe_allow_html=True)

    left, middle, right = st.columns([1.15, 1.2, 1.2], gap="large")

    with left:
        st.markdown("#### 🏥 Datos del Examen")
        region = selectbox_con_placeholder("Región anatómica", list(REGIONES.keys()), "region_anatomica")
        examenes = REGIONES.get(region, []) if region else []
        examen = selectbox_con_placeholder("Examen", examenes, "examen")

        with st.container(border=True):
            if region:
                st.markdown(f"**Región seleccionada:** {region}")
            else:
                st.markdown("Selecciona una región anatómica")

    with middle:
        st.markdown("#### 🛏️ Posicionamiento del paciente")
        posicion = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, "posicion_paciente")
        entrada = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, "entrada_paciente")
        tubo = selectbox_con_placeholder("Posición tubo", POS_TUBO, "posicion_tubo")
        extremidades = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, "posicion_extremidades")

        with st.container(border=True):
            st.markdown("Selecciona posición paciente, entrada y posición del tubo para ver la imagen correspondiente.")

    with right:
        st.markdown("#### 🖼️ Topograma")
        ruta_pos = obtener_imagen_posicionamiento(posicion, entrada, tubo) if (posicion and entrada and tubo) else None

        with st.container(border=True):
            if ruta_pos is not None:
                st.image(str(ruta_pos), use_container_width=True)
                st.caption(f"Proyección: AP · Tubo: {tubo}")
            else:
                st.markdown(" ")
                st.markdown("☢️")
                st.caption("Proyección: AP · Tubo:")

    store["region_anatomica"] = region
    store["examen"] = examen
    store["posicion_paciente"] = posicion
    store["entrada_paciente"] = entrada
    store["posicion_tubo"] = tubo
    store["posicion_extremidades"] = extremidades

    st.markdown("---")
    st.markdown("## 📡 Topograma 1")

    row1 = st.columns(5, gap="medium")
    with row1[0]:
        t1_inicio = selectbox_con_placeholder("Inicio Topograma 1", INICIO_TOPO_OPCIONES, "t1_inicio")
    with row1[1]:
        t1_fin = selectbox_con_placeholder("Fin Topograma 1", FIN_TOPO_OPCIONES, "t1_fin")
    with row1[2]:
        st.markdown("kV")
        st.text_input("kV", value="100", disabled=True, label_visibility="collapsed", key="widget_t1_kv")
    with row1[3]:
        st.markdown("mA")
        st.text_input("mA", value="40", disabled=True, label_visibility="collapsed", key="widget_t1_ma")
    with row1[4]:
        t1_centraje = selectbox_con_placeholder("Centraje inicio de topograma", ENTRADAS_PACIENTE, "t1_centraje_inicio")

    row2 = st.columns(5, gap="medium")
    with row2[0]:
        st.markdown("mm inicio Topograma 1")
        t1_mm_inicio = number_input_con_stepper("mm inicio Topograma 1", "t1_mm_inicio")
    with row2[1]:
        st.markdown("mm fin Topograma 1")
        t1_mm_fin = number_input_con_stepper("mm fin Topograma 1", "t1_mm_fin")
    with row2[2]:
        t1_longitud = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, "t1_longitud")
    with row2[3]:
        t1_direccion = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, "t1_direccion")
    with row2[4]:
        t1_voz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, "t1_voz")

    aplica_t2 = st.checkbox("¿Aplica Topograma 2?", key="widget_aplica_topograma_2", value=bool(st.session_state.get("aplica_topograma_2", False)))
    st.session_state["aplica_topograma_2"] = aplica_t2
    store["aplica_topograma_2"] = aplica_t2

    faltantes = []
    if not tubo:
        faltantes.append("Posición tubo")
    if not t1_longitud:
        faltantes.append("Longitud")
    if not t1_direccion:
        faltantes.append("Dirección")
    if not t1_voz:
        faltantes.append("Instrucción de voz")

    if faltantes:
        st.warning("Completa todos los campos antes de iniciar:\n\n" + " · ".join(faltantes))

    completos = all([examen, posicion, entrada, tubo, t1_longitud, t1_direccion, t1_voz])

    if st.button("☢️ INICIAR TOPOGRAMA", key="btn_iniciar_topograma", use_container_width=True, disabled=not completos):
        st.session_state["topograma_iniciado"] = True
        store["t1_inicio"] = t1_inicio
        store["t1_fin"] = t1_fin
        store["t1_centraje_inicio"] = t1_centraje
        store["t1_mm_inicio"] = t1_mm_inicio
        store["t1_mm_fin"] = t1_mm_fin
        store["t1_longitud"] = t1_longitud
        store["t1_direccion"] = t1_direccion
        store["t1_voz"] = t1_voz
        store["t1_kv"] = 100
        store["t1_ma"] = 40

    if st.session_state.get("topograma_iniciado", False):
        st.markdown("---")
        st.markdown("### Topograma 1 adquirido")

        sel = df[
            (df["examen_norm"] == norm(examen)) &
            (df["posicion_norm"] == norm(posicion)) &
            (df["entrada_norm"] == norm(entrada)) &
            (df["tubo_norm"] == norm(tubo))
        ]

        if not sel.empty:
            nombre = sel.iloc[0]["nombre exacto de la imagen"]
            img = get_image(nombre)

            if img:
                st.image(img, width=350)
                st.success("Topograma adquirido")
            else:
                st.error(f"No se encontró imagen: {nombre}")
        else:
            st.warning(
                "No hay coincidencia en el Excel para esta combinación: "
                f"examen='{examen}', posición='{posicion}', entrada='{entrada}', tubo='{tubo}'"
            )

        if st.button("↺ Repetir topograma 1", key="btn_reset_topograma", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    if aplica_t2:
        st.markdown("---")
        st.markdown("## 📡 Topograma 2")
        st.info("Topograma 2 quedará en el siguiente paso con la misma estructura.")
