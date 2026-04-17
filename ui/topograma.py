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

# Imágenes de posicionamiento
DIR_IMAGENES_TOPO_POS = BASE_DIR / "data/images/posicionamiento_topograma"
ZIP_IMAGENES_TOPO_POS = BASE_DIR / "data/images/IMAGENES POSICIONAMIENTO TOPOGRAMA.zip"
CACHE_IMAGENES_TOPO_POS = BASE_DIR / "_cache_imagenes_topograma"

# Imágenes de datos del examen por región anatómica
DIR_DATOS_EXAMEN_TOPO = BASE_DIR / "data/images/datos_examen_topograma"
ZIP_DATOS_EXAMEN_TOPO = BASE_DIR / "data/images/datos_examen_topograma.zip"
CACHE_DATOS_EXAMEN_TOPO = BASE_DIR / "_cache_datos_examen_topograma"

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
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
POS_EXTREMIDADES = ["brazos arriba", "brazos abajo", "eleva brazo derecho", "eleva brazo izquierdo", "flexión extremidad inferior derecha", "flexión extremidad inferior izquierda"]

LONGITUDES_TOPO = [128, 256, 512, 768, 1020, 1560]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]

REFS_TOPO = [
    "VERTEX",
    "GLABELA",
    "ORBITAS",
    "MAXILAR",
    "MENTON",
    "CUELLO",
    "CLAVICULAS",
    "CARINA",
    "CUPULAS DIAFRAGMATICAS",
    "XIFOIDES",
    "CRESTAS ILIACAS",
    "SINFISIS PUBICA",
    "RODILLAS",
    "TOBILLOS",
    "PLANTAS",
]


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _reparar_nombre_zip(name: str) -> str:
    try:
        return name.encode("cp437").decode("utf-8")
    except Exception:
        return name


@st.cache_data
def load_excel():
    if not EXCEL_PATH.exists():
        return pd.DataFrame()
    df = pd.read_excel(EXCEL_PATH)

    cols = {c.lower().strip(): c for c in df.columns}
    examen_col = cols.get("examen")
    posicion_col = cols.get("posición paciente") or cols.get("posicion paciente")
    entrada_col = cols.get("entrada del paciente") or cols.get("entrada")
    tubo_col = cols.get("posición tubo") or cols.get("posicion tubo")
    nombre_col = (
        cols.get("nombre exacto de la imagen")
        or cols.get("nombre imagen")
        or cols.get("nombre_imagen")
    )

    if examen_col:
        df["examen_norm"] = df[examen_col].apply(norm)
    if posicion_col:
        df["posicion_norm"] = df[posicion_col].apply(norm)
    if entrada_col:
        df["entrada_norm"] = df[entrada_col].apply(norm)
    if tubo_col:
        df["tubo_norm"] = df[tubo_col].apply(norm)
    if nombre_col:
        df["nombre_imagen"] = df[nombre_col].astype(str).str.strip()
    return df


@st.cache_data
def index_zip():
    idx = {}
    if not ZIP_PATH.exists():
        return idx
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        for f in z.namelist():
            if f.endswith("/"):
                continue
            fixed = _reparar_nombre_zip(f)
            name = Path(fixed).name
            if name.startswith("._") or name == ".DS_Store":
                continue
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


@st.cache_data
def preparar_fuentes_imagenes_topograma():
    fuentes = []
    if DIR_IMAGENES_TOPO_POS.exists():
        fuentes.append(DIR_IMAGENES_TOPO_POS)

    if ZIP_IMAGENES_TOPO_POS.exists():
        CACHE_IMAGENES_TOPO_POS.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ZIP_IMAGENES_TOPO_POS, "r") as zf:
            for member in zf.namelist():
                if member.endswith("/"):
                    continue
                member_fixed = _reparar_nombre_zip(member)
                base = Path(member_fixed).name
                if base.startswith("._") or base == ".DS_Store" or "__MACOSX" in member:
                    continue
                out = CACHE_IMAGENES_TOPO_POS / base
                if not out.exists():
                    with zf.open(member) as src, open(out, "wb") as dst:
                        dst.write(src.read())
        fuentes.append(CACHE_IMAGENES_TOPO_POS)

    return [f for f in fuentes if f.exists()]


@st.cache_data
def preparar_fuentes_datos_examen():
    fuentes = []
    if DIR_DATOS_EXAMEN_TOPO.exists():
        fuentes.append(DIR_DATOS_EXAMEN_TOPO)

    if ZIP_DATOS_EXAMEN_TOPO.exists():
        CACHE_DATOS_EXAMEN_TOPO.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ZIP_DATOS_EXAMEN_TOPO, "r") as zf:
            for member in zf.namelist():
                if member.endswith("/"):
                    continue
                member_fixed = _reparar_nombre_zip(member)
                base = Path(member_fixed).name
                if base.startswith("._") or base == ".DS_Store" or "__MACOSX" in member:
                    continue
                out = CACHE_DATOS_EXAMEN_TOPO / base
                if not out.exists():
                    with zf.open(member) as src, open(out, "wb") as dst:
                        dst.write(src.read())
        fuentes.append(CACHE_DATOS_EXAMEN_TOPO)

    return [f for f in fuentes if f.exists()]


def _normalizar_region_archivo(region: str) -> str:
    nombre = norm(region).upper()
    nombre = nombre.replace("Ñ", "N")
    return nombre


def obtener_imagen_region(region: str):
    if not region:
        return None

    region_norm = _normalizar_region_archivo(region)
    extensiones = {".png", ".jpg", ".jpeg", ".webp"}

    for fuente in preparar_fuentes_datos_examen():
        for ruta in fuente.rglob("*"):
            if not ruta.is_file() or ruta.suffix.lower() not in extensiones:
                continue
            stem_norm = _normalizar_region_archivo(ruta.stem)
            if stem_norm == region_norm:
                return Image.open(ruta)

    return None


def normalizar_entrada_topograma(entrada: str) -> str:
    entrada = norm(entrada)
    if "cabeza" in entrada:
        return "cabeza_primero"
    if "pies" in entrada:
        return "pies_primero"
    return ""


def normalizar_posicion_topograma(posicion: str) -> str:
    posicion = norm(posicion)
    posicion = posicion.replace("decubito ", "")
    posicion = posicion.replace("lateral derecho", "lateral_derecho")
    posicion = posicion.replace("lateral izquierdo", "lateral_izquierdo")
    posicion = posicion.replace(" ", "_")
    return posicion


def normalizar_tubo_topograma(pos_tubo: str) -> str:
    pos_tubo = norm(pos_tubo)
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
    nombre = norm(nombre)
    reemplazos = {
        "°": "",
        "º": "",
        "┬░": "",
        "decubito ": "",
        "lateral derecho": "lateral_derecho",
        "lateral izquierdo": "lateral_izquierdo",
        "derecha": "derecho",
        "izquierda": "izquierdo",
        "cabeza primero": "cabeza_primero",
        "pies primero": "pies_primero",
    }
    for a, b in reemplazos.items():
        nombre = nombre.replace(a, b)
    nombre = nombre.replace("__", "_").replace(" ", "_")
    nombre = re.sub(r"[^a-z0-9_]+", "_", nombre)
    nombre = re.sub(r"_+", "_", nombre).strip("_")
    tokens = [t for t in nombre.split("_") if t and not t.isdigit()]
    nombre = "_".join(tokens)
    nombre = nombre.replace("arriba_0", "arriba").replace("abajo_180", "abajo")
    return nombre


def obtener_imagen_posicionamiento_topograma(posicion: str, entrada: str, pos_tubo: str):
    if not posicion or not entrada or not pos_tubo:
        return None

    entrada_norm = norm(entrada)
    posicion_norm = norm(posicion)
    tubo_norm = norm(pos_tubo)

    extensiones = {".png", ".jpg", ".jpeg", ".webp"}

    for fuente in preparar_fuentes_imagenes_topograma():
        for ruta in fuente.rglob("*"):
            if not ruta.is_file() or ruta.suffix.lower() not in extensiones:
                continue

            nombre = norm(ruta.stem)

            if (
                entrada_norm in nombre
                and posicion_norm.replace("decubito ", "") in nombre
                and (
                    ("arriba" in tubo_norm and "arriba" in nombre)
                    or ("abajo" in tubo_norm and "abajo" in nombre)
                    or ("derecha" in tubo_norm and "derecha" in nombre)
                    or ("izquierda" in tubo_norm and "izquierda" in nombre)
                )
            ):
                return Image.open(ruta)

    return None


def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, pos_tubo):
    df = load_excel()
    if df.empty:
        return None, "No se pudo leer el Excel de topogramas."
    needed = {"examen_norm", "posicion_norm", "entrada_norm", "tubo_norm", "nombre_imagen"}
    if not needed.issubset(df.columns):
        return None, "El Excel no tiene las columnas esperadas para topograma adquirido."

    candidatos = df[
        (df["examen_norm"] == norm(examen))
        & (df["posicion_norm"] == norm(posicion_paciente))
        & (df["entrada_norm"] == norm(entrada))
        & (df["tubo_norm"] == norm(pos_tubo))
    ]
    if candidatos.empty:
        return None, "No hay coincidencia en Excel para esta combinación."

    nombre = str(candidatos.iloc[0]["nombre_imagen"]).strip()
    img = get_image(nombre)
    if img is None:
        return None, f"La imagen '{nombre}' no está dentro del ZIP de topogramas adquiridos."
    return img, None


def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    opciones = ["Seleccionar"] + list(options)
    if value in options:
        idx = opciones.index(value)
    else:
        idx = 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    return None if val == "Seleccionar" else val


def _build_store(**kwargs):
    prev = st.session_state.get("topograma_store", {})
    prev.update(kwargs)
    st.session_state["topograma_store"] = prev


def _render_imagen_region(region: str, alto_px: int = 220):
    img_region = obtener_imagen_region(region)
    if img_region is not None:
        c1, c2, c3 = st.columns([1, 1.15, 1])
        with c2:
            st.image(img_region, use_container_width=True)
    else:
        st.markdown(
            f"""
            <div style="height:{alto_px}px; display:flex; align-items:center; justify-content:center; background:#050505; border-radius:12px;">
                <span style="opacity:0.45;">Imagen anatómica no encontrada</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _panel_header(emoji: str, titulo: str):
    """Header tipo 'banner' oscuro que ocupa el ancho completo de la columna."""
    st.markdown(
        f"""
        <div style="
            background:#1A1A1A;
            border:1px solid #2E2E2E;
            border-radius:10px;
            padding:0.75rem 1rem;
            margin-bottom:0.9rem;
            display:flex;
            align-items:center;
            gap:0.55rem;
            font-weight:600;
            font-size:1rem;
            color:#FFFFFF;
        ">
            <span style="font-size:1.15rem;">{emoji}</span>
            <span>{titulo}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _placeholder_dashed(mensaje: str, alto_px: int = 220):
    """Caja con borde punteado y mensaje centrado (estilo 'Selecciona una región anatómica')."""
    st.markdown(
        f"""
        <div style="
            height:{alto_px}px;
            display:flex;
            align-items:center;
            justify-content:center;
            background:transparent;
            border:1.5px dashed #3A3A3A;
            border-radius:10px;
            padding:1rem;
            text-align:center;
        ">
            <span style="color:#BFBFBF; font-size:0.95rem;">{mensaje}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _placeholder_info(mensaje: str, alto_px: int = 180):
    """Caja destacada (fondo azul oscuro) para mensaje de posicionamiento."""
    st.markdown(
        f"""
        <div style="
            min-height:{alto_px}px;
            display:flex;
            align-items:center;
            justify-content:center;
            background:#0E2A44;
            border:1px solid #164463;
            border-radius:10px;
            padding:1.25rem 1.5rem;
            text-align:center;
        ">
            <span style="color:#FFFFFF; font-size:0.95rem; line-height:1.45;">{mensaje}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _placeholder_topograma(proyeccion: str = "AP", tubo: str = ""):
    """Placeholder central con ícono de radiación y etiqueta 'Proyección: AP · Tubo:'."""
    st.markdown(
        f"""
        <div style="
            height:420px;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            background:transparent;
            border:1px solid #2A2A2A;
            border-radius:10px;
            gap:1.25rem;
        ">
            <div style="
                width:72px;
                height:72px;
                border-radius:50%;
                background:#1C1C1C;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:2rem;
                opacity:0.85;
            ">☢️</div>
            <span style="color:#BFBFBF; font-size:0.9rem;">
                Proyección: {proyeccion} · Tubo: {tubo}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topograma_panel():
    store = st.session_state.get("topograma_store", {})

    col1, col2, col3 = st.columns([1, 1, 1], gap="large")

    with col1:
        _panel_header("🧾", "Datos del Examen")
        region = selectbox_con_placeholder(
            "Región anatómica", list(REGIONES.keys()), "region_widget", value=store.get("region_anat")
        )
        examen = selectbox_con_placeholder(
            "Examen", REGIONES.get(region, []), "examen_widget", value=store.get("examen")
        )

        img_region = obtener_imagen_region(region) if region else None
        if img_region is not None:
            c1, c2, c3 = st.columns([1, 1.15, 1])
            with c2:
                st.image(img_region, use_container_width=True)
        else:
            _placeholder_dashed("Selecciona una región anatómica", alto_px=180)

    with col2:
        _panel_header("🛏️", "Posicionamiento del paciente")
        c2a, c2b = st.columns(2)
        with c2a:
            posicion = selectbox_con_placeholder(
                "Posición paciente", POSICIONES_PACIENTE, "pos_widget", value=store.get("posicion")
            )
        with c2b:
            entrada = selectbox_con_placeholder(
                "Entrada", ENTRADAS_PACIENTE, "entrada_widget", value=store.get("entrada")
            )
        with c2a:
            tubo = selectbox_con_placeholder(
                "Posición tubo", POS_TUBO, "tubo_widget", value=store.get("t1pt")
            )
        with c2b:
            extremidades = selectbox_con_placeholder(
                "Posición extremidades", POS_EXTREMIDADES, "ext_widget", value=store.get("extremidades")
            )

        img_pos = obtener_imagen_posicionamiento_topograma(posicion or "", entrada or "", tubo or "")
        if img_pos is not None:
            st.image(img_pos, use_container_width=True)
        else:
            _placeholder_info(
                "Selecciona posición paciente, entrada y posición del tubo para ver la imagen correspondiente.",
                alto_px=180,
            )

    with col3:
        _panel_header("🖼️", "Topograma")

        if st.session_state.get("topograma_iniciado", False):
            img_topo, err = obtener_imagen_topograma_adquirido(examen or "", posicion or "", entrada or "", tubo or "")
            if img_topo is not None:
                st.image(img_topo, use_container_width=True)
                st.success("Topograma adquirido correctamente. Continúa a ⚡ Adquisición.")
            else:
                st.warning(err or "Imagen no encontrada")
                _placeholder_topograma(proyeccion="AP", tubo=tubo or "")
        else:
            _placeholder_topograma(proyeccion="AP", tubo=tubo or "")

    st.markdown("---")
    st.markdown("### 📡 Topograma 1")
    r1a, r1b, r1c, r1d, r1e = st.columns(5, gap="medium")
    with r1a:
        t1_ini_ref = selectbox_con_placeholder("Inicio Topograma 1", REFS_TOPO, "t1_ini_ref_widget", value=store.get("t1_ini_ref"))
    with r1b:
        t1_fin_ref = selectbox_con_placeholder("Fin Topograma 1", REFS_TOPO, "t1_fin_ref_widget", value=store.get("t1_fin_ref"))
    with r1c:
        st.markdown("<div style='margin-bottom:0.45rem;'>kV</div><div style='background:#1A1A1A;border:1px solid #3A3A3A;border-radius:8px;padding:0.55rem 0.75rem;'>100</div>", unsafe_allow_html=True)
    with r1d:
        st.markdown("<div style='margin-bottom:0.45rem;'>mA</div><div style='background:#1A1A1A;border:1px solid #3A3A3A;border-radius:8px;padding:0.55rem 0.75rem;'>40</div>", unsafe_allow_html=True)
    with r1e:
        t1_centraje_inicio = selectbox_con_placeholder("Centraje inicio de topograma", REFS_TOPO, "t1_centraje_inicio_widget", value=store.get("t1_centraje_inicio"))

    r2a, r2b, r2c = st.columns(3, gap="medium")
    with r2a:
        t1_long = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, "t1l_widget", value=store.get("t1l"))
    with r2b:
        t1_dir = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, "t1dir_widget", value=store.get("t1dir"))
    with r2c:
        t1_voz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, "t1vz_widget", value=store.get("t1vz"))

    aplica_topo2 = st.checkbox("¿Aplica Topograma 2?", value=bool(store.get("aplica_topograma_2") or store.get("aplica_topo2")), key="aplica_topo2_widget")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("☢️ INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1_down", use_container_width=True):
            st.session_state["topograma_iniciado"] = True
    with col_btn2:
        if st.button("↺ Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    t2_region = t2_examen = None
    t2_pos = t2_entrada = t2_tubo = t2_ext = t2_long = t2_dir = t2_voz = None
    t2_ini_ref = t2_fin_ref = t2_centraje_inicio = None

    if aplica_topo2:
        st.markdown("---")
        left_t2, mid_t2, right_t2 = st.columns([1, 1, 1], gap="large")

        with left_t2:
            _panel_header("🧾", "Datos del Examen — Topograma 2")
            t2_region = selectbox_con_placeholder(
                "Región anatómica",
                list(REGIONES.keys()),
                "t2_region_widget",
                value=store.get("t2_region_anat")
            )
            t2_examen = selectbox_con_placeholder(
                "Examen",
                REGIONES.get(t2_region, []),
                "t2_examen_widget",
                value=store.get("t2_examen")
            )

            img_region2 = obtener_imagen_region(t2_region) if t2_region else None
            if img_region2 is not None:
                c1, c2, c3 = st.columns([1, 1.15, 1])
                with c2:
                    st.image(img_region2, use_container_width=True)
            else:
                _placeholder_dashed("Selecciona una región anatómica", alto_px=180)

        with mid_t2:
            _panel_header("🛏️", "Posicionamiento del paciente — Topograma 2")
            a, b = st.columns(2)
            with a:
                t2_pos = selectbox_con_placeholder(
                    "Posición paciente",
                    POSICIONES_PACIENTE,
                    "t2_pos_widget",
                    value=store.get("t2_posicion")
                )
            with b:
                t2_entrada = selectbox_con_placeholder(
                    "Entrada",
                    ENTRADAS_PACIENTE,
                    "t2_entrada_widget",
                    value=store.get("t2_entrada")
                )
            with a:
                t2_tubo = selectbox_con_placeholder(
                    "Posición tubo",
                    POS_TUBO,
                    "t2_tubo_widget",
                    value=store.get("t2pt")
                )
            with b:
                t2_ext = selectbox_con_placeholder(
                    "Posición extremidades",
                    POS_EXTREMIDADES,
                    "t2_ext_widget",
                    value=store.get("t2_extremidades")
                )

            img_pos2 = obtener_imagen_posicionamiento_topograma(t2_pos or "", t2_entrada or "", t2_tubo or "")
            if img_pos2 is not None:
                st.image(img_pos2, use_container_width=True)
            else:
                _placeholder_info(
                    "Selecciona posición paciente, entrada y posición del tubo para ver la imagen correspondiente.",
                    alto_px=180,
                )

        with right_t2:
            _panel_header("🖼️", "Topograma 2")
            if st.session_state.get("topograma2_iniciado", False):
                img_topo2, err2 = obtener_imagen_topograma_adquirido(
                    t2_examen or "",
                    t2_pos or "",
                    t2_entrada or "",
                    t2_tubo or "",
                )
                if img_topo2 is not None:
                    st.image(img_topo2, use_container_width=True)
                    st.success("Topograma 2 adquirido correctamente.")
                else:
                    st.warning(err2 or "Imagen de Topograma 2 no encontrada")
                    _placeholder_topograma(proyeccion="AP", tubo=t2_tubo or "")
            else:
                _placeholder_topograma(proyeccion="AP", tubo=t2_tubo or "")

        st.markdown("### 📡 Parámetros Topograma 2")
        t2a, t2b, t2c, t2d, t2e = st.columns(5, gap="medium")
        with t2a:
            t2_ini_ref = selectbox_con_placeholder("Inicio Topograma 2", REFS_TOPO, "t2_ini_ref_widget", value=store.get("t2_ini_ref"))
        with t2b:
            t2_fin_ref = selectbox_con_placeholder("Fin Topograma 2", REFS_TOPO, "t2_fin_ref_widget", value=store.get("t2_fin_ref"))
        with t2c:
            st.markdown("<div style='margin-bottom:0.45rem;'>kV</div><div style='background:#1A1A1A;border:1px solid #3A3A3A;border-radius:8px;padding:0.55rem 0.75rem;'>100</div>", unsafe_allow_html=True)
        with t2d:
            st.markdown("<div style='margin-bottom:0.45rem;'>mA</div><div style='background:#1A1A1A;border:1px solid #3A3A3A;border-radius:8px;padding:0.55rem 0.75rem;'>40</div>", unsafe_allow_html=True)
        with t2e:
            t2_centraje_inicio = selectbox_con_placeholder("Centraje inicio de topograma", REFS_TOPO, "t2_centraje_inicio_widget", value=store.get("t2_centraje_inicio"))

        t2f, t2g, t2h = st.columns(3, gap="medium")
        with t2f:
            t2_long = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, "t2l_widget", value=store.get("t2l"))
        with t2g:
            t2_dir = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, "t2dir_widget", value=store.get("t2dir"))
        with t2h:
            t2_voz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, "t2vz_widget", value=store.get("t2vz"))

        col_btn3, col_btn4 = st.columns(2)
        with col_btn3:
            if st.button("☢️ INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = True
        with col_btn4:
            if st.button("↺ Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = False
                st.rerun()

    _build_store(
        region_anat=region,
        examen=examen,
        posicion=posicion,
        entrada=entrada,
        extremidades=extremidades,
        t1pt=tubo,
        t1l=t1_long,
        t1dir=t1_dir,
        t1vz=t1_voz,
        t1_ini_ref=t1_ini_ref,
        t1_fin_ref=t1_fin_ref,
        t1_centraje_inicio=t1_centraje_inicio,
        aplica_topograma_2=aplica_topo2,
        aplica_topo2=aplica_topo2,
        t2_region_anat=t2_region,
        t2_examen=t2_examen,
        t2_posicion=t2_pos,
        t2_entrada=t2_entrada,
        t2_extremidades=t2_ext,
        t2pt=t2_tubo,
        t2l=t2_long,
        t2dir=t2_dir,
        t2vz=t2_voz,
        t2_ini_ref=t2_ini_ref,
        t2_fin_ref=t2_fin_ref,
        t2_centraje_inicio=t2_centraje_inicio,
        t1_posicion_paciente=posicion,
        t1_entrada_paciente=entrada,
        t1_posicion_tubo=tubo,
        t2_posicion_paciente=t2_pos,
        t2_entrada_paciente=t2_entrada,
        t2_posicion_tubo=t2_tubo,
    )

    return st.session_state["topograma_store"]
