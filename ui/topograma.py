import io
import zipfile
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

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

REFS_INICIO = {
    "CABEZA": ["VERTEX", "ORBOMEATAL"],
    "CUELLO": ["BASE CRANEO", "C2", "C4"],
    "CUERPO": ["APICES", "SUPRAHEPATICO", "HEPATICO"],
}

REFS_FIN = {
    "CABEZA": ["MAXILAR", "MANDIBULA", "C1", "C4"],
    "CUELLO": ["T1", "T4", "CARINA"],
    "CUERPO": ["PUBIS", "SINFISIS PUBICA", "CRESTAS ILIACAS"],
}


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _safe_get(dct, *keys):
    for k in keys:
        if k in dct:
            return dct[k]
    return None


@st.cache_data
def load_excel():
    if not EXCEL_PATH.exists():
        return pd.DataFrame()

    df = pd.read_excel(EXCEL_PATH)
    cols = {norm(c): c for c in df.columns}

    examen_col = _safe_get(cols, "examen")
    pos_col = _safe_get(cols, "posicion paciente")
    entrada_col = _safe_get(cols, "entrada del paciente", "entrada paciente", "entrada")
    tubo_col = _safe_get(cols, "posicion tubo", "tubo")

    if examen_col:
        df["_examen_norm"] = df[examen_col].apply(norm)
    if pos_col:
        df["_posicion_norm"] = df[pos_col].apply(norm)
    if entrada_col:
        df["_entrada_norm"] = df[entrada_col].apply(norm)
    if tubo_col:
        df["_tubo_norm"] = df[tubo_col].apply(norm)

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
            name = Path(f).name
            key = norm(name)
            idx[key] = f
            stem = norm(Path(name).stem)
            idx.setdefault(stem, f)
    return idx


def get_image_by_name(nombre):
    if not nombre:
        return None
    idx = index_zip()
    candidates = []
    nombre = str(nombre).strip()
    candidates.extend([
        norm(nombre),
        norm(Path(nombre).name),
        norm(Path(nombre).stem),
    ])
    for key in candidates:
        if key in idx:
            with zipfile.ZipFile(ZIP_PATH, "r") as z:
                data = z.read(idx[key])
                img = Image.open(io.BytesIO(data))
                try:
                    return img.convert("RGB")
                except Exception:
                    return img
    return None


def _draw_region_placeholder(region):
    img = Image.new("RGB", (500, 500), "black")
    d = ImageDraw.Draw(img)
    if region == "CABEZA":
        d.ellipse((180, 40, 320, 180), outline="white", width=6)
        d.rectangle((220, 170, 280, 280), outline="white", width=6)
        d.line((250, 280, 250, 380), fill="white", width=6)
        d.line((250, 320, 190, 420), fill="white", width=6)
        d.line((250, 320, 310, 420), fill="white", width=6)
        d.line((250, 220, 170, 290), fill="white", width=6)
        d.line((250, 220, 330, 290), fill="white", width=6)
    elif region == "CUELLO":
        d.ellipse((190, 40, 310, 160), outline="white", width=6)
        d.rectangle((220, 150, 280, 340), outline="white", width=6)
        d.line((250, 340, 250, 440), fill="white", width=6)
    else:
        d.ellipse((190, 35, 310, 155), outline="white", width=6)
        d.rectangle((180, 150, 320, 330), outline="white", width=6)
        d.line((220, 330, 180, 455), fill="white", width=6)
        d.line((280, 330, 320, 455), fill="white", width=6)
        d.line((180, 190, 110, 300), fill="white", width=6)
        d.line((320, 190, 390, 300), fill="white", width=6)
    return img


def _draw_position_placeholder(posicion, entrada, tubo):
    img = Image.new("RGB", (640, 400), (22, 22, 30))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 60, 600, 340), radius=28, outline=(130, 130, 150), width=4)
    d.rounded_rectangle((220, 220, 420, 280), radius=18, outline=(220, 220, 220), width=4)
    d.ellipse((250, 140, 330, 220), outline=(230, 230, 230), width=4)
    d.line((330, 180, 520, 180), fill=(240, 210, 80), width=8)
    d.polygon([(520, 180), (490, 165), (490, 195)], fill=(240, 210, 80))
    text = f"{posicion or '-'} | {entrada or '-'} | {tubo or '-'}"
    d.text((55, 25), text, fill=(235, 235, 235))
    return img


def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, posicion_tubo):
    df = load_excel()
    if df.empty:
        return None, "No se pudo cargar el Excel de topograma"

    filtros = pd.Series([True] * len(df))
    if "_examen_norm" in df:
        filtros &= df["_examen_norm"] == norm(examen)
    if "_posicion_norm" in df:
        filtros &= df["_posicion_norm"] == norm(posicion_paciente)
    if "_entrada_norm" in df:
        filtros &= df["_entrada_norm"] == norm(entrada)
    if "_tubo_norm" in df:
        filtros &= df["_tubo_norm"] == norm(posicion_tubo)

    sel = df[filtros]
    if sel.empty:
        return None, "No hay coincidencia en Excel"

    row = sel.iloc[0]
    for col in sel.columns:
        ncol = norm(col)
        if "nombre exacto" in ncol or ("imagen" in ncol and "nombre" in ncol):
            img = get_image_by_name(row[col])
            if img is not None:
                return img, None

    for col in sel.columns:
        if "imagen" in norm(col):
            img = get_image_by_name(row[col])
            if img is not None:
                return img, None

    return None, "Imagen no encontrada"


def selectbox_con_placeholder(label, options, value=None, key=None):
    opciones = [None] + list(options)
    index = opciones.index(value) if value in opciones else 0
    return st.selectbox(
        label,
        opciones,
        index=index,
        key=key,
        format_func=lambda x: "Seleccionar" if x is None else str(x),
    )


def _number_with_buttons(label, key, default):
    c1, c2 = st.columns([4, 2], gap="small")
    with c1:
        st.number_input(label, min_value=-2000, max_value=3000, step=1, key=key, value=int(st.session_state.get(key, default)))
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        with m1:
            if st.button("−", key=f"{key}_menos", use_container_width=True):
                st.session_state[key] = int(st.session_state.get(key, default)) - 1
                st.rerun()
        with m2:
            if st.button("+", key=f"{key}_mas", use_container_width=True):
                st.session_state[key] = int(st.session_state.get(key, default)) + 1
                st.rerun()
    return int(st.session_state.get(key, default))


def _init_state():
    st.session_state.setdefault("topograma_iniciado", False)
    st.session_state.setdefault("topograma2_iniciado", False)
    st.session_state.setdefault("topograma_store", {})
    t = st.session_state["topograma_store"]

    # básicos
    t.setdefault("region", st.session_state.get("region"))
    t.setdefault("examen", st.session_state.get("examen"))
    t.setdefault("posicion", st.session_state.get("posicion"))
    t.setdefault("entrada", st.session_state.get("entrada"))
    t.setdefault("t1pt", st.session_state.get("t1pt"))
    t.setdefault("extremidades", st.session_state.get("extremidades"))

    # topograma 1
    t.setdefault("t1_inicio_ref", st.session_state.get("t1_inicio_ref", None))
    t.setdefault("t1_fin_ref", st.session_state.get("t1_fin_ref", None))
    t.setdefault("t1_ini_mm", st.session_state.get("t1_ini_mm", 0))
    t.setdefault("t1_fin_mm", st.session_state.get("t1_fin_mm", 400))
    t.setdefault("t1_centraje_inicio", st.session_state.get("t1_centraje_inicio", None))
    t.setdefault("t1l", st.session_state.get("t1l", 256))
    t.setdefault("t1dir", st.session_state.get("t1dir", "CAUDO-CRANEAL"))
    t.setdefault("t1vz", st.session_state.get("t1vz", "NINGUNA"))
    t.setdefault("t1kv", st.session_state.get("t1kv", 100))
    t.setdefault("t1ma", st.session_state.get("t1ma", 40))

    # topograma 2
    t.setdefault("aplica_topo2", st.session_state.get("aplica_topo2", False))
    t.setdefault("t2_posicion_paciente", st.session_state.get("t2_posicion_paciente"))
    t.setdefault("t2_entrada", st.session_state.get("t2_entrada"))
    t.setdefault("t2pt", st.session_state.get("t2pt"))
    t.setdefault("t2_extremidades", st.session_state.get("t2_extremidades"))
    t.setdefault("t2_inicio_ref", st.session_state.get("t2_inicio_ref", None))
    t.setdefault("t2_fin_ref", st.session_state.get("t2_fin_ref", None))
    t.setdefault("t2_ini_mm", st.session_state.get("t2_ini_mm", 0))
    t.setdefault("t2_fin_mm", st.session_state.get("t2_fin_mm", 400))
    t.setdefault("t2_centraje_inicio", st.session_state.get("t2_centraje_inicio", None))
    t.setdefault("t2l", st.session_state.get("t2l", 256))
    t.setdefault("t2dir", st.session_state.get("t2dir", "CAUDO-CRANEAL"))
    t.setdefault("t2vz", st.session_state.get("t2vz", "NINGUNA"))
    t.setdefault("t2kv", st.session_state.get("t2kv", 100))
    t.setdefault("t2ma", st.session_state.get("t2ma", 40))


def _save_store_and_session(**kwargs):
    t = st.session_state["topograma_store"]
    for k, v in kwargs.items():
        st.session_state[k] = v
        t[k] = v


def render_topograma_panel():
    _init_state()
    t = st.session_state["topograma_store"]

    region = selectbox_con_placeholder("Región anatómica", REGIONES.keys(), value=t.get("region"), key="region")
    examen = selectbox_con_placeholder("Examen", REGIONES.get(region, []), value=t.get("examen") if t.get("region") == region else None, key="examen")

    posicion = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, value=t.get("posicion"), key="posicion")
    entrada = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, value=t.get("entrada"), key="entrada")
    t1pt = selectbox_con_placeholder("Posición tubo", POS_TUBO, value=t.get("t1pt"), key="t1pt")
    extremidades = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, value=t.get("extremidades"), key="extremidades")

    _save_store_and_session(
        region=region,
        examen=examen,
        posicion=posicion,
        entrada=entrada,
        t1pt=t1pt,
        extremidades=extremidades,
        t1_posicion_paciente=posicion,
        t1_entrada_paciente=entrada,
        t1_posicion_tubo=t1pt,
    )

    st.markdown("## 📡 Topograma")

    top_c1, top_c2, top_c3 = st.columns([1.05, 1.15, 1.2], gap="large")

    with top_c1:
        st.markdown("### 🧾 Datos del examen")
        st.image(_draw_region_placeholder(region), use_container_width=True)

    with top_c2:
        st.markdown("### 🛏️ Posicionamiento del paciente")
        c21, c22 = st.columns(2)
        with c21:
            selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, value=posicion, key="_dummy_pos_lock")
            selectbox_con_placeholder("Posición tubo", POS_TUBO, value=t1pt, key="_dummy_tubo_lock")
        with c22:
            selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, value=entrada, key="_dummy_ent_lock")
            selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, value=extremidades, key="_dummy_ext_lock")
        st.image(_draw_position_placeholder(posicion, entrada, t1pt), use_container_width=True)

    with top_c3:
        st.markdown("### ✅ Topograma adquirido")
        img1, err1 = (None, None)
        if st.session_state.get("topograma_iniciado", False):
            img1, err1 = obtener_imagen_topograma_adquirido(examen, posicion, entrada, t1pt)
            if img1 is not None:
                st.image(img1, use_container_width=True)
                st.caption(f"Proyección: AP · Tubo: {t1pt or '—'} · {t.get('t1l') or '—'} mm · {t.get('t1kv') or '—'} kV · {t.get('t1ma') or '—'} mA")
                st.success("✅ Topograma adquirido correctamente. Continúa a ⚡ Adquisición.")
            else:
                st.error(err1 or "Imagen no encontrada")
        else:
            st.info("Completa y luego inicia el topograma")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("### 📡 Topograma 1")

    refs_inicio = REFS_INICIO.get(region or "CUERPO", REFS_INICIO["CUERPO"])
    refs_fin = REFS_FIN.get(region or "CUERPO", REFS_FIN["CUERPO"])

    r1 = st.columns(5, gap="medium")
    with r1[0]:
        t1_inicio_ref = selectbox_con_placeholder("Inicio Topograma 1", refs_inicio, value=t.get("t1_inicio_ref"), key="t1_inicio_ref")
    with r1[1]:
        t1_fin_ref = selectbox_con_placeholder("Fin Topograma 1", refs_fin, value=t.get("t1_fin_ref"), key="t1_fin_ref")
    with r1[2]:
        st.text_input("kV", value=str(t.get("t1kv", 100)), disabled=True, key="_t1kv_show")
    with r1[3]:
        st.text_input("mA", value=str(t.get("t1ma", 40)), disabled=True, key="_t1ma_show")
    with r1[4]:
        t1_centraje_inicio = selectbox_con_placeholder("Centraje inicio de topograma", refs_inicio, value=t.get("t1_centraje_inicio"), key="t1_centraje_inicio")

    r2 = st.columns(5, gap="medium")
    with r2[0]:
        t1_ini_mm = _number_with_buttons("mm inicio Topograma 1", "t1_ini_mm", int(t.get("t1_ini_mm", 0)))
    with r2[1]:
        t1_fin_mm = _number_with_buttons("mm fin Topograma 1", "t1_fin_mm", int(t.get("t1_fin_mm", 400)))
    with r2[2]:
        t1l = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, value=t.get("t1l"), key="t1l")
    with r2[3]:
        t1dir = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, value=t.get("t1dir"), key="t1dir")
    with r2[4]:
        t1vz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, value=t.get("t1vz"), key="t1vz")

    aplica_topo2 = st.checkbox("¿Aplica Topograma 2?", value=bool(t.get("aplica_topo2", False)), key="aplica_topo2")

    _save_store_and_session(
        t1_inicio_ref=t1_inicio_ref,
        t1_fin_ref=t1_fin_ref,
        t1_ini_mm=t1_ini_mm,
        t1_fin_mm=t1_fin_mm,
        t1_centraje_inicio=t1_centraje_inicio,
        t1l=t1l,
        t1dir=t1dir,
        t1vz=t1vz,
        t1kv=100,
        t1ma=40,
        aplica_topo2=aplica_topo2,
    )

    st.markdown("---")

    campos_t1_ok = all([region, examen, posicion, entrada, t1pt, t1l, t1dir, t1vz])
    if st.button("☢️ INICIAR TOPOGRAMA", key="btn_iniciar_topo1", use_container_width=True, disabled=not campos_t1_ok):
        st.session_state["topograma_iniciado"] = True
        st.rerun()
    if st.session_state.get("topograma_iniciado", False):
        if st.button("↺ Repetir topograma", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    if aplica_topo2:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        cta, ctb = st.columns([1.05, 1.0], gap="large")
        with cta:
            st.markdown("### 🛏️ Posicionamiento del paciente — Topograma 2")
            t2_pos = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, value=t.get("t2_posicion_paciente"), key="t2_posicion_paciente")
            t2_ent = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, value=t.get("t2_entrada"), key="t2_entrada")
            t2_pt = selectbox_con_placeholder("Posición tubo", POS_TUBO, value=t.get("t2pt"), key="t2pt")
            t2_ext = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, value=t.get("t2_extremidades"), key="t2_extremidades")
            st.image(_draw_position_placeholder(t2_pos, t2_ent, t2_pt), use_container_width=True)

        with ctb:
            st.markdown("### 🖼️ Topograma 2")
            if st.session_state.get("topograma2_iniciado", False):
                img2, err2 = obtener_imagen_topograma_adquirido(examen, t2_pos, t2_ent, t2_pt)
                if img2 is not None:
                    st.image(img2, use_container_width=True)
                    st.caption(f"Proyección: AP · Tubo: {t.get('t2pt') or '—'} · {t.get('t2l') or '—'} mm · {t.get('t2kv') or '—'} kV · {t.get('t2ma') or '—'} mA")
                    st.success("✅ Topograma 2 adquirido correctamente.")
                else:
                    st.error(err2 or "Imagen no encontrada")
            else:
                st.info("Configura e inicia Topograma 2")

        st.markdown("### 📡 Topograma 2")
        rr1 = st.columns(5, gap="medium")
        with rr1[0]:
            t2_inicio_ref = selectbox_con_placeholder("Inicio Topograma 2", refs_inicio, value=t.get("t2_inicio_ref"), key="t2_inicio_ref")
        with rr1[1]:
            t2_fin_ref = selectbox_con_placeholder("Fin Topograma 2", refs_fin, value=t.get("t2_fin_ref"), key="t2_fin_ref")
        with rr1[2]:
            st.text_input("kV", value=str(t.get("t2kv", 100)), disabled=True, key="_t2kv_show")
        with rr1[3]:
            st.text_input("mA", value=str(t.get("t2ma", 40)), disabled=True, key="_t2ma_show")
        with rr1[4]:
            t2_centraje_inicio = selectbox_con_placeholder("Centraje inicio de topograma", refs_inicio, value=t.get("t2_centraje_inicio"), key="t2_centraje_inicio")

        rr2 = st.columns(5, gap="medium")
        with rr2[0]:
            t2_ini_mm = _number_with_buttons("mm inicio Topograma 2", "t2_ini_mm", int(t.get("t2_ini_mm", 0)))
        with rr2[1]:
            t2_fin_mm = _number_with_buttons("mm fin Topograma 2", "t2_fin_mm", int(t.get("t2_fin_mm", 400)))
        with rr2[2]:
            t2l = selectbox_con_placeholder("Longitud de topograma (mm)", LONGITUDES_TOPO, value=t.get("t2l"), key="t2l")
        with rr2[3]:
            t2dir = selectbox_con_placeholder("Dirección topograma", DIRECCIONES, value=t.get("t2dir"), key="t2dir")
        with rr2[4]:
            t2vz = selectbox_con_placeholder("Instrucción de voz", INSTRUCCIONES_VOZ, value=t.get("t2vz"), key="t2vz")

        _save_store_and_session(
            t2_posicion_paciente=t2_pos,
            t2_entrada=t2_ent,
            t2pt=t2_pt,
            t2_extremidades=t2_ext,
            t2_inicio_ref=t2_inicio_ref,
            t2_fin_ref=t2_fin_ref,
            t2_ini_mm=t2_ini_mm,
            t2_fin_mm=t2_fin_mm,
            t2_centraje_inicio=t2_centraje_inicio,
            t2l=t2l,
            t2dir=t2dir,
            t2vz=t2vz,
            t2kv=100,
            t2ma=40,
        )

        campos_t2_ok = all([t2_pos, t2_ent, t2_pt, t2l, t2dir, t2vz])
        if st.button("☢️ INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not campos_t2_ok):
            st.session_state["topograma2_iniciado"] = True
            st.rerun()
        if st.session_state.get("topograma2_iniciado", False):
            if st.button("↺ Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = False
                st.rerun()

    return st.session_state["topograma_store"]
