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

# rutas nuevas
EXCEL_TOPOGRAMAS = EXCEL_DIR / "imagenes_topograma.xlsx"
ZIP_TOPOGRAMAS = IMAGES_DIR / "IMAGENES TOPOGRAMA.zip"

DIR_IMAGENES_TOPO_POS = IMAGES_DIR / "IMAGENES POSICIONAMIENTO TOPOGRAMA"
ZIP_IMAGENES_TOPO_POS = IMAGES_DIR / "IMAGENES POSICIONAMIENTO TOPOGRAMA.zip"
CACHE_IMAGENES_TOPO_POS = BASE_DIR / "_cache_imagenes_topograma"


REGIONES = {
    "CABEZA":   ["CEREBRO", "ORBITAS", "OIDOS", "SPN", "MAXILOFACIAL"],
    "CUELLO":   ["CUELLO"],
    "EESS":     ["HOMBRO", "BRAZO", "CODO", "ANTEBRAZO", "MUÑECA", "MANO"],
    "COLUMNA":  ["CERVICAL", "DORSAL", "LUMBAR", "SACROCOXIS"],
    "CUERPO":   ["TORAX", "ABDOMEN", "PELVIS", "ABDOMEN-PELVIS", "TORAX-ABDOMEN-PELVIS"],
    "EEII":     ["CADERA", "MUSLO", "RODILLA", "TOBILLO", "PIE"],
    "ANGIO":    ["ATC CEREBRO", "ATC CUELLO", "ATC CEREBRO CUELLO", "ATC TORAX", "ATC ABDOMEN", "ATC ABDOMEN-PELVIS", "ATC TORAX-ABDOMEN-PELVIS", "EESS DERECHA", "EESS IZQUIERDA", "EEII"],
}

POSICIONES_PACIENTE = [
    "DECUBITO SUPINO",
    "DECUBITO PRONO",
    "DECUBITO LATERAL DERECHO",
    "DECUBITO LATERAL IZQUIERDO",
]

ENTRADAS_PACIENTE = ["CABEZA PRIMERO", "PIES PRIMERO"]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
LONGITUDES_TOPO = [128, 256, 512, 768, 1020, 1560]
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]


def selectbox_con_placeholder(label, options, value=None, key=None, placeholder_text="Seleccionar", **kwargs):
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

    return st.selectbox(
        label,
        opciones_finales,
        index=indice,
        key=key,
        format_func=lambda x: placeholder_text if (x is None or x == placeholder_text) else str(x),
        placeholder=placeholder_text,
        **kwargs,
    )


def _norm_topo_texto(valor):
    if valor is None:
        return ""
    s = str(valor).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("°", "")
    s = s.replace("º", "")
    s = s.replace("-", " ")
    s = s.replace("_", " ")
    s = " ".join(s.split())
    return s


def _norm_topo_examen(txt):
    t = _norm_topo_texto(txt)
    equivalencias = {
        "atc": "angiotc",
        "angio tc": "angiotc",
        "angiografia tc": "angiotc",
        "atc torax abdomen pelvis": "angiotc torax abdomen pelvis",
        "atc abdomen pelvis": "angiotc abdomen pelvis",
    }
    return equivalencias.get(t, t)


def _reparar_nombre_zip(name):
    try:
        return name.encode("cp437").decode("utf-8")
    except Exception:
        return name


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
    except Exception as e:
        st.error(f"Error leyendo Excel de topogramas: {e}")
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
        st.warning("El Excel de topogramas no tiene las columnas esperadas.")
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
        if BASE_DIR.exists():
            fuentes.append(BASE_DIR)
    except Exception:
        pass

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

            interna = CACHE_IMAGENES_TOPO_POS / "IMAGENES POSICIONAMIENTO TOPOGRAMA"
            if interna.exists():
                fuentes.append(interna)
            else:
                fuentes.append(CACHE_IMAGENES_TOPO_POS)
    except Exception:
        pass

    fuentes_limpias = []
    vistos = set()
    for fuente in fuentes:
        try:
            clave = str(fuente.resolve())
        except Exception:
            clave = str(fuente)
        if clave not in vistos:
            vistos.add(clave)
            fuentes_limpias.append(fuente)

    return fuentes_limpias


def normalizar_posicion_topograma(posicion: str) -> str:
    posicion = (posicion or "").strip().lower()
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
    entrada = (entrada or "").strip().lower()
    if "cabeza" in entrada:
        return "cabeza_primero"
    if "pies" in entrada:
        return "pies_primero"
    return ""


def normalizar_tubo_topograma(pos_tubo: str) -> str:
    pos_tubo = (pos_tubo or "").strip().lower()
    if "arriba" in pos_tubo:
        return "arriba"
    if "abajo" in pos_tubo:
        return "abajo"
    if "derecha" in pos_tubo:
        return "derecho"
    if "izquierda" in pos_tubo:
        return "izquierdo"
    return ""


def normalizar_nombre_archivo_topograma(nombre: str) -> str:
    nombre = (nombre or "").lower().strip()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
        "°": "", "º": "", "┬░": "", "decubito ": "",
        "lateral derecho": "lateral_derecho",
        "lateral izquierdo": "lateral_izquierdo",
        "derecha": "derecho",
        "izquierda": "izquierdo",
        "cabeza primero": "cabeza_primero",
        "pies primero": "pies_primero",
    }
    for a, b in reemplazos.items():
        nombre = nombre.replace(a, b)

    import re
    nombre = nombre.replace("__", "_")
    nombre = nombre.replace(" ", "_")
    nombre = re.sub(r"[^a-z0-9_]+", "_", nombre)
    nombre = re.sub(r"_+", "_", nombre).strip("_")

    tokens = [t for t in nombre.split("_") if t]
    filtrados = []
    for t in tokens:
        if t.isdigit():
            continue
        filtrados.append(t)
    nombre = "_".join(filtrados)
    nombre = nombre.replace("arriba_0", "arriba").replace("abajo_180", "abajo")
    return nombre


def obtener_imagen_posicionamiento_topograma(posicion: str, entrada: str, pos_tubo: str):
    entrada_norm = normalizar_entrada_topograma(entrada)
    posicion_norm = normalizar_posicion_topograma(posicion)
    tubo_norm = normalizar_tubo_topograma(pos_tubo)

    if not entrada_norm or not posicion_norm or not tubo_norm:
        return None

    objetivo_norm = normalizar_nombre_archivo_topograma(
        f"topograma_{entrada_norm}_{posicion_norm}_{tubo_norm}"
    )
    extensiones = {".png", ".jpg", ".jpeg", ".webp"}

    for fuente in preparar_fuentes_imagenes_topograma():
        if not fuente.exists():
            continue

        for ruta in fuente.rglob("*"):
            if not ruta.is_file():
                continue
            if ruta.suffix.lower() not in extensiones:
                continue
            nombre_lower = ruta.name.lower()
            if "__macosx" in nombre_lower or ruta.name.startswith("._") or ruta.name == ".DS_Store":
                continue
            if not nombre_lower.startswith("topograma"):
                continue

            stem_norm = normalizar_nombre_archivo_topograma(ruta.stem)
            if stem_norm == objetivo_norm:
                return ruta

    return None


def _init_topograma_state():
    if "topograma_store" not in st.session_state or not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}

    defaults = {
        "topograma_iniciado": False,
        "topograma2_iniciado": False,
        "aplica_topo2": False,
        "region_anatomica": None,
        "examen": None,
        "posicion": None,
        "entrada": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_topograma_panel():
    _init_topograma_state()
    _tstore = st.session_state["topograma_store"]

    st.markdown("## Datos del examen")

    col_a, col_b = st.columns(2)
    with col_a:
        region = selectbox_con_placeholder(
            "Región anatómica",
            list(REGIONES.keys()),
            value=st.session_state.get("region_anatomica"),
            key="region_anatomica",
        )
        st.session_state["region_anatomica"] = region

    examenes_region = REGIONES.get(region, []) if region else []
    with col_b:
        examen = selectbox_con_placeholder(
            "Examen",
            examenes_region,
            value=st.session_state.get("examen"),
            key="examen",
        )
        st.session_state["examen"] = examen

    col_c, col_d = st.columns(2)
    with col_c:
        posicion = selectbox_con_placeholder(
            "Posición",
            POSICIONES_PACIENTE,
            value=st.session_state.get("posicion"),
            key="posicion",
        )
        st.session_state["posicion"] = posicion

    with col_d:
        entrada = selectbox_con_placeholder(
            "Entrada",
            ENTRADAS_PACIENTE,
            value=st.session_state.get("entrada"),
            key="entrada",
        )
        st.session_state["entrada"] = entrada

    _tstore["region_anatomica"] = region
    _tstore["examen"] = examen
    _tstore["t1_posicion_paciente"] = posicion
    _tstore["t1_entrada"] = entrada

    st.markdown("---")
    st.markdown("## Topograma 1")

    c1, c2, c3 = st.columns(3)
    with c1:
        topo1_pos = selectbox_con_placeholder(
            "Posición del tubo",
            POS_TUBO,
            value=st.session_state.get("t1pt"),
            key="t1pt",
        )
    with c2:
        topo1_inicio = selectbox_con_placeholder(
            "Centraje inicio de topograma",
            ENTRADAS_PACIENTE,
            value=st.session_state.get("t1_inicio_ref"),
            key="t1_inicio_ref",
        )
    with c3:
        topo1_long = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=st.session_state.get("t1l"),
            key="t1l",
        )

    c4, c5 = st.columns(2)
    with c4:
        topo1_dir = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=st.session_state.get("t1dir"),
            key="t1dir",
        )
    with c5:
        topo1_voz = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=st.session_state.get("t1vz"),
            key="t1vz",
        )

    completos_t1 = all([region, examen, posicion, entrada, topo1_pos, topo1_inicio, topo1_long, topo1_dir, topo1_voz])

    if st.button("☢️  INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1", use_container_width=True, disabled=not completos_t1):
        st.session_state["topograma_iniciado"] = True
        _tstore["t1pt"] = topo1_pos
        _tstore["t1_inicio_ref"] = topo1_inicio
        _tstore["t1l"] = topo1_long
        _tstore["t1dir"] = topo1_dir
        _tstore["t1vz"] = topo1_voz
        _tstore["t1_posicion_paciente"] = posicion
        _tstore["t1_entrada"] = entrada

    if st.session_state.get("topograma_iniciado", False):
        ruta_pos = obtener_imagen_posicionamiento_topograma(posicion or "", entrada or "", topo1_pos or "")
        if ruta_pos is not None:
            st.markdown("### Posicionamiento Topograma 1")
            st.image(str(ruta_pos), width=280)

        st.markdown("### Topograma 1 adquirido")
        img1, err1 = obtener_imagen_topograma_adquirido(
            examen or "",
            posicion or "",
            entrada or "",
            topo1_pos or "",
        )
        if img1 is not None:
            st.image(img1, width=340)
            st.success("Topograma 1 adquirido correctamente.")
        else:
            st.warning(err1 or "No se encontró una imagen de topograma para esta combinación.")

        if st.button("↺ Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    st.markdown("---")
    aplicar_t2 = st.checkbox("Aplicar Topograma 2", key="aplica_topo2")
    _tstore["aplica_topo2"] = aplicar_t2

    if aplicar_t2:
        _tstore["t2_posicion_paciente"] = posicion
        _tstore["t2_entrada"] = entrada

        st.markdown("## Topograma 2")

        d1, d2, d3 = st.columns(3)
        with d1:
            topo2_pos = selectbox_con_placeholder(
                "Posición del tubo",
                POS_TUBO,
                value=st.session_state.get("t2pt"),
                key="t2pt",
            )
        with d2:
            topo2_inicio = selectbox_con_placeholder(
                "Centraje inicio de topograma",
                ENTRADAS_PACIENTE,
                value=st.session_state.get("t2_inicio_ref"),
                key="t2_inicio_ref",
            )
        with d3:
            topo2_long = selectbox_con_placeholder(
                "Longitud de topograma (mm)",
                LONGITUDES_TOPO,
                value=st.session_state.get("t2l"),
                key="t2l",
            )

        d4, d5 = st.columns(2)
        with d4:
            topo2_dir = selectbox_con_placeholder(
                "Dirección topograma",
                DIRECCIONES,
                value=st.session_state.get("t2dir"),
                key="t2dir",
            )
        with d5:
            topo2_voz = selectbox_con_placeholder(
                "Instrucción de voz",
                INSTRUCCIONES_VOZ,
                value=st.session_state.get("t2vz"),
                key="t2vz",
            )

        completos_t2 = all([region, examen, posicion, entrada, topo2_pos, topo2_inicio, topo2_long, topo2_dir, topo2_voz])

        if st.button("☢️  INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not completos_t2):
            st.session_state["topograma2_iniciado"] = True
            _tstore["t2pt"] = topo2_pos
            _tstore["t2_inicio_ref"] = topo2_inicio
            _tstore["t2l"] = topo2_long
            _tstore["t2dir"] = topo2_dir
            _tstore["t2vz"] = topo2_voz
            _tstore["t2_posicion_paciente"] = posicion
            _tstore["t2_entrada"] = entrada

        if st.session_state.get("topograma2_iniciado", False):
            ruta_pos2 = obtener_imagen_posicionamiento_topograma(posicion or "", entrada or "", topo2_pos or "")
            if ruta_pos2 is not None:
                st.markdown("### Posicionamiento Topograma 2")
                st.image(str(ruta_pos2), width=280)

            st.markdown("### Topograma 2 adquirido")
            img2, err2 = obtener_imagen_topograma_adquirido(
                examen or "",
                posicion or "",
                entrada or "",
                topo2_pos or "",
            )
            if img2 is not None:
                st.image(img2, width=340)
                st.success("Topograma 2 adquirido correctamente.")
            else:
                st.warning(err2 or "No se encontró una imagen de topograma para esta combinación.")

            if st.button("↺ Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = False
                st.rerun()
