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
ZIP_TOPOGRAMAS = IMAGES_DIR / "IMAGENES TOPOGRAMA.zip"

DIR_IMAGENES_TOPO_POS = IMAGES_DIR / "IMAGENES POSICIONAMIENTO TOPOGRAMA"
ZIP_IMAGENES_TOPO_POS = IMAGES_DIR / "IMAGENES POSICIONAMIENTO TOPOGRAMA.zip"
CACHE_IMAGENES_TOPO_POS = BASE_DIR / "_cache_imagenes_topograma"

REGIONES = {
    "CABEZA": ["CEREBRO", "ORBITAS", "OIDOS", "SPN", "MAXILOFACIAL"],
    "CUELLO": ["CUELLO"],
    "EESS": ["HOMBRO", "BRAZO", "CODO", "ANTEBRAZO", "MUÑECA", "MANO"],
    "COLUMNA": ["CERVICAL", "DORSAL", "LUMBAR", "SACROCOXIS"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS", "ABDOMEN-PELVIS", "TORAX-ABDOMEN-PELVIS"],
    "EEII": ["CADERA", "MUSLO", "RODILLA", "PIERNA", "TOBILLO", "PIE"],
    "ANGIO": [
        "ATC CEREBRO",
        "ATC CUELLO",
        "ATC CEREBRO CUELLO",
        "ATC TORAX",
        "ATC ABDOMEN",
        "ATC ABDOMEN-PELVIS",
        "ATC TORAX-ABDOMEN-PELVIS",
        "EESS DERECHA",
        "EESS IZQUIERDA",
        "EEII",
    ],
}

POSICIONES_PACIENTE = [
    "DECUBITO SUPINO",
    "DECUBITO PRONO",
    "DECUBITO LATERAL DERECHO",
    "DECUBITO LATERAL IZQUIERDO",
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


def _init_topograma_state():
    defaults = {
        "topograma_store": {},
        "topograma_iniciado": False,
        "topograma2_iniciado": False,
        "aplica_topo2": False,
        "region_anatomica": None,
        "examen": None,
        "posicion": None,
        "entrada": None,
        "pos_tubo": None,
        "pos_extremidades": None,
        "t1_inicio": None,
        "t1_fin": None,
        "t1_kv": 100,
        "t1_ma": 40,
        "t1_mm_inicio": 0,
        "t1_mm_fin": 400,
        "t1_longitud": None,
        "t1_dir": None,
        "t1_voz": None,
        "t1_inicio_ref": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}


def selectbox_con_placeholder(label, options, state_key, placeholder_text="Seleccionar", **kwargs):
    opciones = [placeholder_text] + list(options)
    actual = st.session_state.get(state_key)
    if actual is None or actual not in options:
        index = 0
    else:
        index = opciones.index(actual)

    valor = st.selectbox(label, opciones, index=index, key=f"widget_{state_key}", **kwargs)
    st.session_state[state_key] = None if valor == placeholder_text else valor
    return st.session_state[state_key]


def numero_con_botones(label, state_key, default=0, min_value=0, max_value=4000, step=1):
    current = int(st.session_state.get(state_key, default))
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        valor = st.number_input(
            label,
            min_value=min_value,
            max_value=max_value,
            step=step,
            value=current,
            key=f"widget_{state_key}",
        )
    with c2:
        menos = st.button("−", key=f"minus_{state_key}", use_container_width=True)
    with c3:
        mas = st.button("+", key=f"plus_{state_key}", use_container_width=True)

    if menos:
        valor = max(min_value, int(valor) - step)
    if mas:
        valor = min(max_value, int(valor) + step)

    st.session_state[state_key] = int(valor)
    return st.session_state[state_key]


def _norm_text(v):
    if v is None:
        return ""
    s = str(v).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("°", "").replace("º", "")
    s = s.replace("-", " ").replace("_", " ")
    s = " ".join(s.split())
    return s


def _norm_file_name(v):
    s = _norm_text(v)
    s = s.replace("decubito ", "")
    s = s.replace("lateral derecho", "lateral_derecho")
    s = s.replace("lateral izquierdo", "lateral_izquierdo")
    s = s.replace("cabeza primero", "cabeza_primero")
    s = s.replace("pies primero", "pies_primero")
    s = s.replace("derecha", "derecho")
    s = s.replace("izquierda", "izquierdo")
    s = s.replace("arriba 0", "arriba")
    s = s.replace("abajo 180", "abajo")
    s = s.replace(" ", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _buscar_archivo_topogramas_excel():
    candidatos = [
        EXCEL_TOPOGRAMAS,
        EXCEL_DIR / "Imagenes_topograma.xlsx",
        EXCEL_DIR / "IMAGENES_TOPOGRAMA.xlsx",
        EXCEL_DIR / "topogramas.xlsx",
        BASE_DIR / "imagenes topograma.xlsx",
        BASE_DIR / "Imagenes topograma.xlsx",
        BASE_DIR / "IMAGENES TOPOGRAMA.xlsx",
        BASE_DIR / "imagenes_topograma.xlsx",
        BASE_DIR / "topogramas.xlsx",
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


@st.cache_data
def cargar_tabla_topogramas():
    excel_path = _buscar_archivo_topogramas_excel()
    if excel_path is None or not excel_path.exists():
        return pd.DataFrame(), "No se encontró el Excel de topogramas."

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        return pd.DataFrame(), f"Error leyendo Excel de topogramas: {e}"

    columnas_norm = {_norm_text(c): c for c in df.columns}

    def buscar_columna(*nombres):
        for nombre in nombres:
            if nombre in columnas_norm:
                return columnas_norm[nombre]
        return None

    col_examen = buscar_columna("examen", "tipo examen", "estudio", "exploracion")
    col_posicion = buscar_columna("posicion", "posicion paciente", "posicion_paciente")
    col_entrada = buscar_columna("entrada")
    col_tubo = buscar_columna("posicion tubo", "posicion_tubo", "tubo", "pos tubo")
    col_imagen = buscar_columna("imagen", "nombre imagen", "nombre_imagen", "archivo", "archivo imagen")

    if not all([col_examen, col_posicion, col_entrada, col_tubo, col_imagen]):
        return pd.DataFrame(), "El Excel no tiene las columnas esperadas."

    out = pd.DataFrame({
        "examen": df[col_examen].fillna("").astype(str),
        "posicion_paciente": df[col_posicion].fillna("").astype(str),
        "entrada": df[col_entrada].fillna("").astype(str),
        "pos_tubo": df[col_tubo].fillna("").astype(str),
        "nombre_imagen": df[col_imagen].fillna("").astype(str),
    })

    out["examen_norm"] = out["examen"].apply(_norm_text)
    out["posicion_norm"] = out["posicion_paciente"].apply(_norm_text)
    out["entrada_norm"] = out["entrada"].apply(_norm_text)
    out["pos_tubo_norm"] = out["pos_tubo"].apply(_norm_text)
    return out, None


@st.cache_data
def cargar_indice_zip_topogramas():
    indice = {}
    if not ZIP_TOPOGRAMAS.exists():
        return indice

    with zipfile.ZipFile(ZIP_TOPOGRAMAS, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/") or "__MACOSX" in name:
                continue
            try:
                name_ok = name.encode("cp437").decode("utf-8")
            except Exception:
                name_ok = name
            base = Path(name_ok).name
            stem = Path(base).stem
            indice[_norm_text(base)] = name
            indice[_norm_text(stem)] = name
    return indice


def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, pos_tubo):
    df, err = cargar_tabla_topogramas()
    if df.empty:
        return None, err or "No se pudo leer el Excel de topogramas."

    candidatos = df[
        (df["examen_norm"] == _norm_text(examen)) &
        (df["posicion_norm"] == _norm_text(posicion_paciente)) &
        (df["entrada_norm"] == _norm_text(entrada)) &
        (df["pos_tubo_norm"] == _norm_text(pos_tubo))
    ]

    if candidatos.empty:
        return None, (
            f"Sin coincidencia en Excel para examen='{examen}', "
            f"posición='{posicion_paciente}', entrada='{entrada}', tubo='{pos_tubo}'."
        )

    nombre = str(candidatos.iloc[0]["nombre_imagen"]).strip()
    indice_zip = cargar_indice_zip_topogramas()
    miembro = indice_zip.get(_norm_text(nombre))

    if miembro is None:
        return None, f"La imagen '{nombre}' no está dentro del ZIP."

    try:
        with zipfile.ZipFile(ZIP_TOPOGRAMAS, "r") as zf:
            with zf.open(miembro) as f:
                data = f.read()
        return Image.open(io.BytesIO(data)), None
    except Exception as e:
        return None, f"No se pudo abrir la imagen '{nombre}': {e}"


def preparar_fuentes_posicionamiento():
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

    if BASE_DIR.exists():
        fuentes.append(BASE_DIR)

    return fuentes


def obtener_imagen_posicionamiento(posicion, entrada, pos_tubo):
    objetivo = _norm_file_name(f"topograma_{entrada}_{posicion}_{pos_tubo}")
    extensiones = {".png", ".jpg", ".jpeg", ".webp"}

    for fuente in preparar_fuentes_posicionamiento():
        if not fuente.exists():
            continue
        for ruta in fuente.rglob("*"):
            if not ruta.is_file():
                continue
            if ruta.suffix.lower() not in extensiones:
                continue
            if not ruta.name.lower().startswith("topograma"):
                continue
            stem_norm = _norm_file_name(ruta.stem)
            if stem_norm == objetivo:
                return ruta
    return None


def render_topograma_panel():
    _init_topograma_state()
    store = st.session_state["topograma_store"]

    st.markdown("### 📡 Topograma")

    c_exam, c_pos, c_img = st.columns([1.2, 1.3, 1.3], gap="large")

    with c_exam:
        st.markdown("#### 🏥 Datos del Examen")
        region = selectbox_con_placeholder("Región anatómica", list(REGIONES.keys()), "region_anatomica")
        examenes = REGIONES.get(region, []) if region else []
        examen = selectbox_con_placeholder("Examen", examenes, "examen")

        with st.container(border=True):
            if region:
                st.markdown(f"**Región seleccionada:** {region}")
            else:
                st.markdown("Selecciona una región anatómica")

    with c_pos:
        st.markdown("#### 🛏️ Posicionamiento del paciente")
        posicion = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, "posicion")
        entrada = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, "entrada")
        pos_tubo = selectbox_con_placeholder("Posición tubo", POS_TUBO, "pos_tubo")
        pos_ext = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, "pos_extremidades")

        with st.container(border=True):
            st.markdown("Selecciona posición paciente, entrada y posición del tubo para ver la imagen correspondiente.")

    with c_img:
        st.markdown("#### 🖼️ Topograma")
        ruta_pos = obtener_imagen_posicionamiento(posicion, entrada, pos_tubo) if (posicion and entrada and pos_tubo) else None
        with st.container(border=True):
            if ruta_pos is not None:
                st.image(str(ruta_pos), use_container_width=True)
                st.caption(f"Proyección: AP · Tubo: {pos_tubo}")
            else:
                st.markdown(" ")
                st.markdown("☢️")
                st.caption("Proyección: AP · Tubo:")

    store["region_anatomica"] = region
    store["examen"] = examen
    store["posicion"] = posicion
    store["entrada"] = entrada
    store["pos_tubo"] = pos_tubo
    store["pos_extremidades"] = pos_ext

    st.markdown("---")
    st.markdown("## 📡 Topograma 1")

    f1, f2, f3, f4, f5 = st.columns(5, gap="medium")
    with f1:
        t1_inicio = selectbox_con_placeholder("Inicio Topograma 1", INICIO_TOPO_OPCIONES, "t1_inicio")
    with f2:
        t1_fin = selectbox_con_placeholder("Fin Topograma 1", FIN_TOPO_OPCIONES, "t1_fin")
    with f3:
        st.markdown("kV")
        st.text_input("kV", value="100", disabled=True, label_visibility="collapsed", key="widget_kv_display")
    with f4:
        st.markdown("mA")
        st.text_input("mA", value="40", disabled=True, label_visibility="collapsed", key="widget_ma_display")
    with f5:
        t1_inicio_ref = selectbox_con_placeholder("Centraje inicio de topograma", ENTRADAS_PACIENTE, "t1_inicio_ref")

    g1, g2, g3, g4, g5 = st.columns(5, gap="medium")
    with g1:
        mm_inicio = numero_con_botones("mm inicio Topograma 1", "t1_mm_inicio", default=0)
    with g2:
        mm_fin = numero_con_botones("mm fin Topograma 1", "t1_mm_fin", default=400)
    with g3:
        t1_longitud = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, "t1_longitud")
    with g4:
        t1_dir = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, "t1_dir")
    with g5:
        t1_voz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, "t1_voz")

    aplicar_t2 = st.checkbox("¿Aplica Topograma 2?", key="widget_aplica_topo2", value=bool(st.session_state.get("aplica_topo2", False)))
    st.session_state["aplica_topo2"] = aplicar_t2
    store["aplica_topo2"] = aplicar_t2

    faltantes = []
    if not pos_tubo:
        faltantes.append("Posición tubo")
    if not t1_longitud:
        faltantes.append("Longitud")
    if not t1_dir:
        faltantes.append("Dirección")
    if not t1_voz:
        faltantes.append("Instrucción de voz")

    if faltantes:
        st.warning("Completa todos los campos antes de iniciar:\n\n" + " · ".join(faltantes))

    completos_t1 = all([region, examen, posicion, entrada, pos_tubo, t1_longitud, t1_dir, t1_voz])

    if st.button("☢️ INICIAR TOPOGRAMA", key="btn_iniciar_topo1", use_container_width=True, disabled=not completos_t1):
        st.session_state["topograma_iniciado"] = True
        store["t1_inicio"] = t1_inicio
        store["t1_fin"] = t1_fin
        store["t1_inicio_ref"] = t1_inicio_ref
        store["t1_mm_inicio"] = mm_inicio
        store["t1_mm_fin"] = mm_fin
        store["t1_longitud"] = t1_longitud
        store["t1_dir"] = t1_dir
        store["t1_voz"] = t1_voz
        store["t1_kv"] = 100
        store["t1_ma"] = 40
        store["t1_posicion_paciente"] = posicion
        store["t1_entrada"] = entrada
        store["t1pt"] = pos_tubo

    if st.session_state.get("topograma_iniciado", False):
        st.markdown("---")
        st.markdown("### Topograma 1 adquirido")
        img1, err1 = obtener_imagen_topograma_adquirido(examen or "", posicion or "", entrada or "", pos_tubo or "")
        if img1 is not None:
            st.image(img1, width=360)
            st.success("Topograma 1 adquirido correctamente.")
        else:
            st.info(err1 or "No se encontró una imagen de topograma para esta combinación.")

        if st.button("↺ Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    if aplicar_t2:
        st.markdown("---")
        st.markdown("## 📡 Topograma 2")
        st.info("En el siguiente paso te dejo Topograma 2 con la misma estructura del original.")
