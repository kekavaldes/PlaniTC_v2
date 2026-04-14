import io
import re
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
CACHE_IMAGENES_TOPO_POS = BASE_DIR / "data/images/_cache_imagenes_topograma"


REGIONES = {
    "CABEZA": ["CEREBRO", "SPN", "MAXILOFACIAL", "ORBITAS", "OIDOS"],
    "CUELLO": ["CUELLO"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS"],
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
    "brazos arriba",
    "brazos abajo",
    "eleva brazo derecho",
    "eleva brazo izquierdo",
    "flexión extremidad inferior derecha",
    "flexión extremidad inferior izquierda",
]
LONGITUDES_TOPO = [128, 256, 512]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN"]


# ---------- helpers ----------
def _norm_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _norm_topo_text(value) -> str:
    text = _norm_text(value)
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
        "°": "", "º": "", "┬░": "", "decubito ": "",
        "lateral derecho": "lateral_derecho",
        "lateral izquierdo": "lateral_izquierdo",
        "derecha": "derecho",
        "izquierda": "izquierdo",
        "cabeza primero": "cabeza_primero",
        "pies primero": "pies_primero",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = text.replace("__", "_")
    text = text.replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    tokens = [t for t in text.split("_") if t and not t.isdigit()]
    text = "_".join(tokens)
    return text.replace("arriba_0", "arriba").replace("abajo_180", "abajo")


def normalizar_posicion_topograma(posicion: str) -> str:
    posicion = _norm_text(posicion)
    if "lateral derecho" in posicion:
        return "lateral_derecho"
    if "lateral izquierdo" in posicion:
        return "lateral_izquierdo"
    if "prono" in posicion:
        return "prono"
    if "supino" in posicion:
        return "supino"
    return ""


def normalizar_entrada_topograma(entrada: str) -> str:
    entrada = _norm_text(entrada)
    if "cabeza" in entrada:
        return "cabeza_primero"
    if "pies" in entrada:
        return "pies_primero"
    return ""


def normalizar_tubo_topograma(pos_tubo: str) -> str:
    pos_tubo = _norm_text(pos_tubo)
    if "arriba" in pos_tubo:
        return "arriba"
    if "abajo" in pos_tubo:
        return "abajo"
    if "derecha" in pos_tubo:
        return "derecho"
    if "izquierda" in pos_tubo:
        return "izquierdo"
    return ""


def selectbox_con_placeholder(label, options, value=None, key=None, placeholder_text="Seleccionar", format_func=None, **kwargs):
    opciones = list(options)
    opciones_sin_placeholder = [
        opt for opt in opciones
        if not ((opt is None) or (isinstance(opt, str) and opt == placeholder_text))
    ]
    opciones_finales = [None] + opciones_sin_placeholder

    if value in opciones_finales and value is not None:
        index = opciones_finales.index(value)
    else:
        index = 0

    if format_func is None:
        format_func = lambda x: placeholder_text if (x is None or x == placeholder_text) else str(x)

    return st.selectbox(
        label,
        opciones_finales,
        index=index,
        key=key,
        format_func=format_func,
        placeholder=placeholder_text,
        **kwargs,
    )


# ---------- data sources ----------
@st.cache_data
def cargar_tabla_topogramas_adquiridos() -> pd.DataFrame:
    if not EXCEL_PATH.exists():
        return pd.DataFrame()

    df = pd.read_excel(EXCEL_PATH)
    cols = {c.lower().strip(): c for c in df.columns}

    examen_col = cols.get("examen")
    pos_col = cols.get("posición paciente") or cols.get("posicion paciente")
    entrada_col = cols.get("entrada del paciente") or cols.get("entrada paciente") or cols.get("entrada")
    tubo_col = cols.get("posición tubo") or cols.get("posicion tubo")
    nombre_col = (
        cols.get("nombre exacto de la imagen")
        or cols.get("nombre_imagen")
        or cols.get("nombre imagen")
    )

    if not all([examen_col, pos_col, entrada_col, tubo_col, nombre_col]):
        return pd.DataFrame()

    work = pd.DataFrame({
        "examen": df[examen_col],
        "posicion": df[pos_col],
        "entrada": df[entrada_col],
        "tubo": df[tubo_col],
        "nombre_imagen": df[nombre_col],
    }).copy()
    work["examen_norm"] = work["examen"].apply(_norm_topo_text)
    work["posicion_norm"] = work["posicion"].apply(_norm_topo_text)
    work["entrada_norm"] = work["entrada"].apply(_norm_topo_text)
    work["pos_tubo_norm"] = work["tubo"].apply(_norm_topo_text)
    return work


def _reparar_nombre_zip(name: str) -> str:
    try:
        return name.encode("cp437").decode("utf-8")
    except Exception:
        return name


@st.cache_data
def cargar_indice_zip_topogramas():
    indice = {}
    if not ZIP_PATH.exists():
        return indice
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/") or "__MACOSX" in name:
                continue
            fixed = _reparar_nombre_zip(name)
            base = Path(fixed).name
            stem = Path(base).stem
            indice[_norm_topo_text(base)] = name
            indice[_norm_topo_text(stem)] = name
    return indice


def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, pos_tubo):
    df = cargar_tabla_topogramas_adquiridos()
    if df.empty:
        return None, "No se pudo leer el Excel de topogramas."

    candidatos = df[
        (df["examen_norm"] == _norm_topo_text(examen))
        & (df["posicion_norm"] == _norm_topo_text(posicion_paciente))
        & (df["entrada_norm"] == _norm_topo_text(entrada))
        & (df["pos_tubo_norm"] == _norm_topo_text(pos_tubo))
    ]

    if candidatos.empty:
        return None, (
            f"Sin coincidencia en Excel para examen='{examen}', posición='{posicion_paciente}', "
            f"entrada='{entrada}', tubo='{pos_tubo}'."
        )

    nombre = str(candidatos.iloc[0]["nombre_imagen"]).strip()
    indice_zip = cargar_indice_zip_topogramas()
    miembro = indice_zip.get(_norm_topo_text(nombre))
    if miembro is None:
        return None, f"La imagen '{nombre}' no está dentro del ZIP."

    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            with zf.open(miembro) as f:
                data = f.read()
        return Image.open(io.BytesIO(data)), None
    except Exception as e:
        return None, f"No se pudo abrir la imagen '{nombre}': {e}"


def preparar_fuentes_imagenes_topograma():
    fuentes = []
    try:
        if DIR_IMAGENES_TOPO_POS.exists():
            fuentes.append(DIR_IMAGENES_TOPO_POS)
        if ZIP_IMAGENES_TOPO_POS.exists():
            CACHE_IMAGENES_TOPO_POS.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(ZIP_IMAGENES_TOPO_POS, "r") as zf:
                zf.extractall(CACHE_IMAGENES_TOPO_POS)
            interna = CACHE_IMAGENES_TOPO_POS / "IMAGENES POSICIONAMIENTO TOPOGRAMA"
            fuentes.append(interna if interna.exists() else CACHE_IMAGENES_TOPO_POS)
    except Exception:
        pass
    limpias = []
    vistos = set()
    for fuente in fuentes:
        clave = str(fuente)
        if clave not in vistos:
            vistos.add(clave)
            limpias.append(fuente)
    return limpias


def obtener_imagen_posicionamiento_topograma(posicion: str, entrada: str, pos_tubo: str):
    entrada_norm = normalizar_entrada_topograma(entrada)
    posicion_norm = normalizar_posicion_topograma(posicion)
    tubo_norm = normalizar_tubo_topograma(pos_tubo)
    if not entrada_norm or not posicion_norm or not tubo_norm:
        return None

    objetivo = _norm_topo_text(f"topograma_{entrada_norm}_{posicion_norm}_{tubo_norm}")
    extensiones = {".png", ".jpg", ".jpeg", ".webp"}

    for fuente in preparar_fuentes_imagenes_topograma():
        if not fuente.exists():
            continue
        for ruta in fuente.rglob("*"):
            if not ruta.is_file() or ruta.suffix.lower() not in extensiones:
                continue
            nombre_lower = ruta.name.lower()
            if "__macosx" in nombre_lower or ruta.name.startswith("._") or ruta.name == ".DS_Store":
                continue
            if not nombre_lower.startswith("topograma"):
                continue
            if _norm_topo_text(ruta.stem) == objetivo:
                return ruta
    return None


# ---------- UI ----------
def _init_topograma_state():
    if "topograma_store" not in st.session_state or not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}
    if "topograma_iniciado" not in st.session_state:
        st.session_state["topograma_iniciado"] = False
    if "topograma2_iniciado" not in st.session_state:
        st.session_state["topograma2_iniciado"] = False


def _render_imagen_posicionamiento(posicion, entrada, tubo, titulo="Posicionamiento"):
    with st.container(border=True):
        st.markdown(f"##### {titulo}")
        ruta = obtener_imagen_posicionamiento_topograma(posicion, entrada, tubo)
        if ruta and ruta.exists():
            st.image(str(ruta), use_container_width=True)
        elif posicion and entrada and tubo:
            st.success("Posicionamiento definido")
        else:
            st.info("Completa los campos")


def _render_imagen_adquirida(examen, posicion, entrada, tubo, topograma_num=1):
    img, err = obtener_imagen_topograma_adquirido(examen, posicion, entrada, tubo)
    if img is not None:
        st.image(img, use_container_width=True)
        st.success(f"Topograma {topograma_num} adquirido correctamente")
    elif st.session_state.get(f"topograma{'' if topograma_num == 1 else '2'}_iniciado", False):
        st.warning(err or "No se encontró la imagen.")


def render_topograma_panel():
    _init_topograma_state()
    _tstore = st.session_state["topograma_store"]

    st.markdown("## 📡 Topograma")

    col1, col2, col3 = st.columns([1, 1, 1.2], gap="large")

    # ----- Datos del examen -----
    with col1:
        st.markdown("### 🧾 Datos del examen")
        region = selectbox_con_placeholder(
            "Región anatómica",
            REGIONES.keys(),
            value=_tstore.get("region"),
            key="region",
        )
        _tstore["region"] = region

        examen = selectbox_con_placeholder(
            "Examen",
            REGIONES.get(region, []),
            value=_tstore.get("examen"),
            key="examen",
        )
        _tstore["examen"] = examen
        st.session_state["examen"] = examen or ""

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

    # ----- Posicionamiento + parámetros topo 1 -----
    with col2:
        st.markdown("### 🛏️ Posicionamiento")
        posicion = selectbox_con_placeholder(
            "Posición paciente", POSICIONES_PACIENTE,
            value=_tstore.get("posicion"), key="pos"
        )
        entrada = selectbox_con_placeholder(
            "Entrada", ENTRADAS_PACIENTE,
            value=_tstore.get("entrada"), key="entrada"
        )
        tubo = selectbox_con_placeholder(
            "Posición tubo", POS_TUBO,
            value=_tstore.get("t1pt"), key="tubo"
        )
        extremidades = selectbox_con_placeholder(
            "Extremidades", POS_EXTREMIDADES,
            value=_tstore.get("extremidades"), key="ext"
        )

        _tstore["posicion"] = posicion
        _tstore["entrada"] = entrada
        _tstore["t1pt"] = tubo
        _tstore["extremidades"] = extremidades
        st.session_state["posicion"] = posicion or ""
        st.session_state["entrada"] = entrada or ""
        st.session_state["t1pt"] = tubo or ""

        _render_imagen_posicionamiento(posicion, entrada, tubo)

        st.markdown("### ⚙️ Parámetros topograma 1")
        p1a, p1b, p1c = st.columns(3)
        with p1a:
            topo1_long = selectbox_con_placeholder(
                "Longitud de topograma (mm)", LONGITUDES_TOPO,
                value=_tstore.get("t1l"), key="t1l"
            )
        with p1b:
            topo1_dir = selectbox_con_placeholder(
                "Dirección topograma", DIRECCIONES,
                value=_tstore.get("t1dir"), key="t1dir"
            )
        with p1c:
            topo1_voz = selectbox_con_placeholder(
                "Instrucción de voz", INSTRUCCIONES_VOZ,
                value=_tstore.get("t1vz"), key="t1vz"
            )

        _tstore["t1l"] = topo1_long
        _tstore["t1dir"] = topo1_dir
        _tstore["t1vz"] = topo1_voz
        _tstore["t1kv"] = 100
        _tstore["t1ma"] = 40
        st.session_state["t1l"] = topo1_long or ""
        st.session_state["t1kv"] = 100
        st.session_state["t1ma"] = 40

        faltantes_t1 = []
        if tubo is None:
            faltantes_t1.append("Posición tubo")
        if topo1_long is None:
            faltantes_t1.append("Longitud")
        if topo1_dir is None:
            faltantes_t1.append("Dirección")
        if topo1_voz is None:
            faltantes_t1.append("Instrucción de voz")

        if faltantes_t1:
            st.markdown(
                f"""
                <div style="background:#1A1100; border:1px solid #554400; border-radius:8px;
                            padding:0.6rem 1rem; margin-bottom:0.5rem; font-size:0.82rem; color:#FFAA00;">
                    ⚠️ Completa todos los campos de Topograma 1 antes de iniciar:<br>
                    <span style="color:#FF8800;">{'  ·  '.join(faltantes_t1)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("☢️  INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1", use_container_width=True, disabled=bool(faltantes_t1)):
            st.session_state["topograma_iniciado"] = True

        if st.session_state.get("topograma_iniciado", False):
            if st.button("↺  Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
                st.session_state["topograma_iniciado"] = False
                st.rerun()

    # ----- Adquirido + Topograma 2 -----
    with col3:
        st.markdown("### ✅ Topograma adquirido")
        if st.session_state.get("topograma_iniciado", False):
            _render_imagen_adquirida(examen, posicion, entrada, tubo, topograma_num=1)
        else:
            st.info("Inicia Topograma 1 para visualizarlo.")

        aplica_topo2 = st.checkbox(
            "Agregar Topograma 2",
            value=bool(_tstore.get("aplica_topo2", False)),
            key="aplica_topo2",
        )
        _tstore["aplica_topo2"] = aplica_topo2

        if aplica_topo2:
            st.markdown("---")
            st.markdown("### 📡 Topograma 2")

            topo2_pos_paciente = selectbox_con_placeholder(
                "Posición paciente", POSICIONES_PACIENTE,
                value=_tstore.get("t2_posicion_paciente"), key="t2_posicion_paciente"
            )
            topo2_entrada = selectbox_con_placeholder(
                "Entrada", ENTRADAS_PACIENTE,
                value=_tstore.get("t2_entrada"), key="t2_entrada"
            )
            topo2_pos = selectbox_con_placeholder(
                "Posición tubo", POS_TUBO,
                value=_tstore.get("t2pt"), key="t2pt"
            )
            topo2_ext = selectbox_con_placeholder(
                "Extremidades", POS_EXTREMIDADES,
                value=_tstore.get("t2_extremidades"), key="t2_ext"
            )

            _tstore["t2_posicion_paciente"] = topo2_pos_paciente
            _tstore["t2_entrada"] = topo2_entrada
            _tstore["t2pt"] = topo2_pos
            _tstore["t2_extremidades"] = topo2_ext

            _render_imagen_posicionamiento(topo2_pos_paciente, topo2_entrada, topo2_pos, titulo="Posicionamiento Topograma 2")

            col_t2d, col_t2e, col_t2f = st.columns(3)
            with col_t2d:
                topo2_long = selectbox_con_placeholder(
                    "Longitud de topograma (mm)", LONGITUDES_TOPO,
                    value=_tstore.get("t2l"), key="t2l"
                )
            with col_t2e:
                topo2_dir = selectbox_con_placeholder(
                    "Dirección topograma", DIRECCIONES,
                    value=_tstore.get("t2dir"), key="t2dir"
                )
            with col_t2f:
                topo2_voz = selectbox_con_placeholder(
                    "Instrucción de voz", INSTRUCCIONES_VOZ,
                    value=_tstore.get("t2vz"), key="t2vz"
                )

            _tstore["t2l"] = topo2_long
            _tstore["t2dir"] = topo2_dir
            _tstore["t2vz"] = topo2_voz
            _tstore["t2kv"] = 100
            _tstore["t2ma"] = 40

            faltantes_t2 = []
            if topo2_pos is None:
                faltantes_t2.append("Posición tubo")
            if topo2_long is None:
                faltantes_t2.append("Longitud")
            if topo2_dir is None:
                faltantes_t2.append("Dirección")
            if topo2_voz is None:
                faltantes_t2.append("Instrucción de voz")

            if faltantes_t2:
                st.markdown(
                    f"""
                    <div style="background:#1A1100; border:1px solid #554400; border-radius:8px;
                                padding:0.6rem 1rem; margin-bottom:0.5rem; font-size:0.82rem; color:#FFAA00;">
                        ⚠️ Completa todos los campos de Topograma 2 antes de iniciar:<br>
                        <span style="color:#FF8800;">{'  ·  '.join(faltantes_t2)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button("☢️  INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=bool(faltantes_t2)):
                st.session_state["topograma2_iniciado"] = True

            if st.session_state.get("topograma2_iniciado", False):
                if st.button("↺  Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                    st.session_state["topograma2_iniciado"] = False
                    st.rerun()
                _render_imagen_adquirida(examen, topo2_pos_paciente, topo2_entrada, topo2_pos, topograma_num=2)

    return {
        "region": region,
        "examen": examen,
        "posicion": posicion,
        "entrada": entrada,
        "t1_posicion_paciente": posicion,
        "t1_entrada_paciente": entrada,
        "t1_posicion_tubo": tubo,
        "t1pt": tubo,
        "t1l": topo1_long,
        "t1dir": topo1_dir,
        "t1vz": topo1_voz,
        "t1kv": 100,
        "t1ma": 40,
        "aplica_topograma_2": aplica_topo2,
        "aplica_topo2": aplica_topo2,
        "t2_posicion_paciente": _tstore.get("t2_posicion_paciente"),
        "t2_entrada": _tstore.get("t2_entrada"),
        "t2pt": _tstore.get("t2pt"),
        "t2l": _tstore.get("t2l"),
        "t2dir": _tstore.get("t2dir"),
        "t2vz": _tstore.get("t2vz"),
        "t2kv": _tstore.get("t2kv"),
        "t2ma": _tstore.get("t2ma"),
    }
