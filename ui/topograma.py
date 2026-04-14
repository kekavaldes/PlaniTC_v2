import io
import zipfile
import unicodedata
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


def _norm_topo_texto(txt):
    txt = "" if txt is None else str(txt)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = txt.lower().strip()
    txt = txt.replace("_", " ").replace("-", " ")
    txt = " ".join(txt.split())
    return txt


def _norm_topo_examen(txt):
    t = _norm_topo_texto(txt)
    equivalencias = {
        "atc": "angiotc",
        "angio tc": "angiotc",
        "angio-tc": "angiotc",
        "angiografia tc": "angiotc",
    }
    return equivalencias.get(t, t)


def _reparar_nombre_zip(name):
    try:
        return name.encode("cp437").decode("utf-8")
    except Exception:
        return name


def selectbox_con_placeholder(label, options, value=None, key=None, placeholder_text="Seleccionar", format_func=None, **kwargs):
    opciones = list(options)
    opciones_sin_placeholder = [
        opt for opt in opciones
        if not ((opt is None) or (isinstance(opt, str) and opt == placeholder_text))
    ]
    opciones_finales = [None] + opciones_sin_placeholder

    if value in opciones_finales and value is not None:
        indice = opciones_finales.index(value)
    else:
        indice = 0

    if format_func is None:
        format_func = lambda x: placeholder_text if (x is None or x == placeholder_text) else str(x)

    return st.selectbox(
        label,
        opciones_finales,
        index=indice,
        key=key,
        format_func=format_func,
        placeholder=placeholder_text,
        **kwargs,
    )


def _buscar_archivo_topogramas_excel():
    candidatos = [
        EXCEL_DIR / "imagenes_topograma.xlsx",
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

    try:
        for carpeta in [EXCEL_DIR, BASE_DIR]:
            if carpeta.exists():
                for patron in ["*.xlsx", "*.xls"]:
                    for f in carpeta.glob(patron):
                        nombre = _norm_topo_texto(f.stem)
                        if "topograma" in nombre:
                            return f
    except Exception:
        pass

    return None


@st.cache_data
def cargar_tabla_topogramas_adquiridos():
    excel_path = _buscar_archivo_topogramas_excel()
    if excel_path is None or not excel_path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_path)
    except Exception:
        return pd.DataFrame()

    columnas_norm = {_norm_topo_texto(c): c for c in df.columns}

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
        return pd.DataFrame()

    out = pd.DataFrame({
        "examen": df[col_examen].fillna("").astype(str),
        "posicion_paciente": df[col_posicion].fillna("").astype(str),
        "entrada": df[col_entrada].fillna("").astype(str),
        "pos_tubo": df[col_tubo].fillna("").astype(str),
        "nombre_imagen": df[col_imagen].fillna("").astype(str),
    })

    out["examen_norm"] = out["examen"].apply(_norm_topo_examen)
    out["posicion_norm"] = out["posicion_paciente"].apply(_norm_topo_texto)
    out["entrada_norm"] = out["entrada"].apply(_norm_topo_texto)
    out["pos_tubo_norm"] = out["pos_tubo"].apply(_norm_topo_texto)
    return out


@st.cache_data
def cargar_indice_zip_topogramas():
    indice = {}
    if not ZIP_TOPOGRAMAS.exists():
        return indice

    with zipfile.ZipFile(ZIP_TOPOGRAMAS, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/") or "__MACOSX" in name:
                continue
            name_ok = _reparar_nombre_zip(name)
            base = Path(name_ok).name
            stem = Path(base).stem
            indice[_norm_topo_texto(base)] = name
            indice[_norm_topo_texto(stem)] = name
    return indice


def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, pos_tubo):
    df = cargar_tabla_topogramas_adquiridos()
    if df.empty:
        return None, "No se pudo leer el Excel de topogramas."

    examen_norm = _norm_topo_examen(examen)
    posicion_norm = _norm_topo_texto(posicion_paciente)
    entrada_norm = _norm_topo_texto(entrada)
    tubo_norm = _norm_topo_texto(pos_tubo)

    candidatos = df[
        (df["examen_norm"] == examen_norm) &
        (df["posicion_norm"] == posicion_norm) &
        (df["entrada_norm"] == entrada_norm) &
        (df["pos_tubo_norm"] == tubo_norm)
    ]

    if candidatos.empty:
        return None, (
            f"Sin coincidencia en Excel para examen='{examen}', "
            f"posición='{posicion_paciente}', entrada='{entrada}', tubo='{pos_tubo}'."
        )

    nombre = str(candidatos.iloc[0]["nombre_imagen"]).strip()
    indice_zip = cargar_indice_zip_topogramas()
    miembro = indice_zip.get(_norm_topo_texto(nombre))
    if miembro is None:
        return None, f"La imagen '{nombre}' no está dentro del ZIP."

    try:
        with zipfile.ZipFile(ZIP_TOPOGRAMAS, "r") as zf:
            with zf.open(miembro) as f:
                data = f.read()
        img = Image.open(io.BytesIO(data))
        return img, None
    except Exception as e:
        return None, f"No se pudo abrir la imagen '{nombre}': {e}"


def preparar_fuentes_imagenes_topograma():
    fuentes = []

    try:
        if DIR_IMAGENES_TOPO_POS.exists():
            fuentes.append(DIR_IMAGENES_TOPO_POS)
    except Exception:
        pass

    try:
        if ZIP_IMAGENES_TOPO_POS.exists():
            CACHE_IMAGENES_TOPO_POS.mkdir(parents=True, exist_ok=True)
            marker = CACHE_IMAGENES_TOPO_POS / ".ok"
            if not marker.exists():
                with zipfile.ZipFile(ZIP_IMAGENES_TOPO_POS, "r") as zf:
                    zf.extractall(CACHE_IMAGENES_TOPO_POS)
                marker.write_text("ok", encoding="utf-8")
            fuentes.append(CACHE_IMAGENES_TOPO_POS)
    except Exception:
        pass

    try:
        if BASE_DIR.exists():
            fuentes.append(BASE_DIR)
    except Exception:
        pass

    return fuentes


def cargar_imagen_posicionamiento(nombre_base):
    if not nombre_base:
        return None

    objetivos = [
        _norm_topo_texto(nombre_base),
        _norm_topo_texto(Path(nombre_base).stem),
    ]

    extensiones = [".png", ".jpg", ".jpeg", ".webp"]

    for carpeta in preparar_fuentes_imagenes_topograma():
        try:
            for archivo in carpeta.rglob("*"):
                if not archivo.is_file():
                    continue
                if archivo.suffix.lower() not in extensiones:
                    continue
                stem_norm = _norm_topo_texto(archivo.stem)
                name_norm = _norm_topo_texto(archivo.name)
                if stem_norm in objetivos or name_norm in objetivos:
                    return Image.open(archivo)
        except Exception:
            continue

    return None


def inicializar_estado_topograma():
    if "aplica_topo2" not in st.session_state:
        st.session_state["aplica_topo2"] = False
    if "topograma_iniciado" not in st.session_state:
        st.session_state["topograma_iniciado"] = False
    if "topograma2_iniciado" not in st.session_state:
        st.session_state["topograma2_iniciado"] = False
    if "topograma_store" not in st.session_state or not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}


POSICIONES_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
LONGITUDES_TOPO = [128, 256, 512, 1024]
DIRECCIONES = ["CRÁNEO-CAUDAL", "CAUDAL-CRÁNEO"]
INSTRUCCIONES_VOZ = ["Inspirar y sostener", "Espirar y sostener", "Respiración libre"]


def _refs_para_entrada(entrada):
    entrada = _norm_topo_texto(entrada)
    if "pies" in entrada:
        return ["Pies", "Cabeza"]
    return ["Cabeza", "Pies"]


def render_topograma():
    inicializar_estado_topograma()
    _tstore = st.session_state["topograma_store"]

    st.subheader("Topograma")

    examen_actual = st.session_state.get("examen", "")
    posicion_actual = st.session_state.get("posicion", "")
    entrada_actual = st.session_state.get("entrada", "")

    c1, c2 = st.columns([1.2, 1])

    with c1:
        st.markdown("### Datos del examen")
        st.text_input("Examen", value=examen_actual, key="topo_examen_muestra", disabled=True)
        st.text_input("Posición", value=posicion_actual, key="topo_pos_muestra", disabled=True)
        st.text_input("Entrada", value=entrada_actual, key="topo_ent_muestra", disabled=True)

    with c2:
        img_pos = None
        if examen_actual and posicion_actual:
            nombre_base = f"{examen_actual}_{posicion_actual}_{entrada_actual}"
            img_pos = cargar_imagen_posicionamiento(nombre_base)

        if img_pos is not None:
            st.image(img_pos, use_container_width=True)
        else:
            st.info("Aquí aparecerá la imagen de posicionamiento.")

    st.markdown("---")

    st.markdown("### Topograma 1")
    col_t1a, col_t1b, col_t1c = st.columns(3)

    with col_t1a:
        topo1_pos = selectbox_con_placeholder(
            "Posición del tubo",
            POSICIONES_TUBO,
            value=_tstore.get("t1pt"),
            key="t1pt",
        )
        _tstore["t1pt"] = topo1_pos if topo1_pos else None

    with col_t1b:
        refs_inicio = _refs_para_entrada(entrada_actual)
        t1_inicio = selectbox_con_placeholder(
            "Centraje inicio de topograma",
            refs_inicio,
            value=_tstore.get("t1_inicio_ref"),
            key="t1_inicio_ref",
        )
        _tstore["t1_inicio_ref"] = t1_inicio if t1_inicio else None

    with col_t1c:
        topo1_long = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=_tstore.get("t1l"),
            key="t1l",
        )
        _tstore["t1l"] = topo1_long if topo1_long is not None else None

    col_t1d, col_t1e = st.columns(2)
    with col_t1d:
        topo1_dir = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=_tstore.get("t1dir"),
            key="t1dir",
        )
        _tstore["t1dir"] = topo1_dir if topo1_dir else None

    with col_t1e:
        topo1_voz = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=_tstore.get("t1vz"),
            key="t1vz",
        )
        _tstore["t1vz"] = topo1_voz if topo1_voz else None

    completos_t1 = all([topo1_pos is not None, topo1_long is not None, topo1_dir is not None, topo1_voz is not None])

    if st.button("☢️  INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1", use_container_width=True, disabled=not completos_t1):
        st.session_state["topograma_iniciado"] = True

    if st.session_state.get("topograma_iniciado", False):
        if st.button("↺  Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

        img1, err1 = obtener_imagen_topograma_adquirido(
            examen_actual,
            posicion_actual,
            entrada_actual,
            topo1_pos or "",
        )
        if img1 is not None:
            st.image(img1, caption="Topograma 1", use_container_width=True)
        else:
            st.warning(err1 or "No se encontró imagen para Topograma 1.")

    st.markdown("---")
    st.checkbox("Aplicar Topograma 2", key="aplica_topo2")

    if st.session_state.get("aplica_topo2", False):
        st.markdown("### Topograma 2")

        col_t2a, col_t2b, col_t2c = st.columns(3)
        with col_t2a:
            topo2_pos = selectbox_con_placeholder(
                "Posición del tubo",
                POSICIONES_TUBO,
                value=_tstore.get("t2pt"),
                key="t2pt",
            )
            _tstore["t2pt"] = topo2_pos if topo2_pos else None

        with col_t2b:
            refs_inicio_topo2 = _refs_para_entrada(entrada_actual)
            t2_inicio = selectbox_con_placeholder(
                "Centraje inicio de topograma",
                refs_inicio_topo2,
                value=_tstore.get("t2_inicio_ref"),
                key="t2_inicio_ref",
            )
            _tstore["t2_inicio_ref"] = t2_inicio if t2_inicio else None

        with col_t2c:
            topo2_long = selectbox_con_placeholder(
                "Longitud de topograma (mm)",
                LONGITUDES_TOPO,
                value=_tstore.get("t2l"),
                key="t2l",
            )
            _tstore["t2l"] = topo2_long if topo2_long is not None else None

        col_t2d, col_t2e = st.columns(2)
        with col_t2d:
            topo2_dir = selectbox_con_placeholder(
                "Dirección topograma",
                DIRECCIONES,
                value=_tstore.get("t2dir"),
                key="t2dir",
            )
            _tstore["t2dir"] = topo2_dir if topo2_dir else None

        with col_t2e:
            topo2_voz = selectbox_con_placeholder(
                "Instrucción de voz",
                INSTRUCCIONES_VOZ,
                value=_tstore.get("t2vz"),
                key="t2vz",
            )
            _tstore["t2vz"] = topo2_voz if topo2_voz else None

        completos_t2 = all([topo2_pos is not None, topo2_long is not None, topo2_dir is not None, topo2_voz is not None])

        if st.button("☢️  INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not completos_t2):
            st.session_state["topograma2_iniciado"] = True

        if st.session_state.get("topograma2_iniciado", False):
            if st.button("↺  Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = False
                st.rerun()

            img2, err2 = obtener_imagen_topograma_adquirido(
                examen_actual,
                posicion_actual,
                entrada_actual,
                topo2_pos or "",
            )
            if img2 is not None:
                st.image(img2, caption="Topograma 2", use_container_width=True)
            else:
                st.warning(err2 or "No se encontró imagen para Topograma 2.")
