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
            idx[norm(name)] = f
            idx.setdefault(norm(Path(name).stem), f)
    return idx


def get_image_by_name(nombre):
    if not nombre:
        return None
    idx = index_zip()
    candidates = [norm(nombre), norm(Path(str(nombre)).name), norm(Path(str(nombre)).stem)]
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
    color = (210, 210, 215)
    if region == "CABEZA":
        d.ellipse((180, 40, 320, 180), outline=color, width=6)
        d.rectangle((220, 170, 280, 280), outline=color, width=6)
        d.line((250, 280, 250, 380), fill=color, width=6)
        d.line((250, 320, 190, 420), fill=color, width=6)
        d.line((250, 320, 310, 420), fill=color, width=6)
        d.line((250, 220, 170, 290), fill=color, width=6)
        d.line((250, 220, 330, 290), fill=color, width=6)
    elif region == "CUELLO":
        d.ellipse((190, 40, 310, 160), outline=color, width=6)
        d.rectangle((220, 150, 280, 340), outline=color, width=6)
        d.line((250, 340, 250, 440), fill=color, width=6)
    else:
        d.ellipse((190, 35, 310, 155), outline=color, width=6)
        d.rectangle((180, 150, 320, 330), outline=color, width=6)
        d.line((220, 330, 180, 455), fill=color, width=6)
        d.line((280, 330, 320, 455), fill=color, width=6)
        d.line((180, 190, 110, 300), fill=color, width=6)
        d.line((320, 190, 390, 300), fill=color, width=6)
    return img


def _draw_position_placeholder(posicion, entrada, tubo):
    img = Image.new("RGB", (700, 430), (18, 20, 28))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((35, 55, 665, 365), radius=26, outline=(115, 118, 135), width=4)
    d.rounded_rectangle((250, 220, 450, 280), radius=18, outline=(220, 220, 220), width=4)
    d.ellipse((275, 140, 355, 220), outline=(235, 235, 235), width=4)
    d.line((355, 180, 560, 180), fill=(228, 197, 77), width=8)
    d.polygon([(560, 180), (530, 165), (530, 195)], fill=(228, 197, 77))
    d.text((44, 22), f"{posicion or '-'} | {entrada or '-'} | {tubo or '-'}", fill=(235, 235, 235))
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

    defaults = {
        "region": st.session_state.get("region"),
        "examen": st.session_state.get("examen"),
        "posicion": st.session_state.get("posicion"),
        "entrada": st.session_state.get("entrada"),
        "t1pt": st.session_state.get("t1pt"),
        "extremidades": st.session_state.get("extremidades"),
        "t1_inicio_ref": st.session_state.get("t1_inicio_ref"),
        "t1_fin_ref": st.session_state.get("t1_fin_ref"),
        "t1_ini_mm": st.session_state.get("t1_ini_mm", 0),
        "t1_fin_mm": st.session_state.get("t1_fin_mm", 400),
        "t1_centraje_inicio": st.session_state.get("t1_centraje_inicio"),
        "t1l": st.session_state.get("t1l", 256),
        "t1dir": st.session_state.get("t1dir", "CAUDO-CRANEAL"),
        "t1vz": st.session_state.get("t1vz", "NINGUNA"),
        "t1kv": st.session_state.get("t1kv", 100),
        "t1ma": st.session_state.get("t1ma", 40),
        "aplica_topo2": st.session_state.get("aplica_topo2", False),
        "t2_posicion_paciente": st.session_state.get("t2_posicion_paciente"),
        "t2_entrada": st.session_state.get("t2_entrada"),
        "t2pt": st.session_state.get("t2pt"),
        "t2_extremidades": st.session_state.get("t2_extremidades"),
        "t2_inicio_ref": st.session_state.get("t2_inicio_ref"),
        "t2_fin_ref": st.session_state.get("t2_fin_ref"),
        "t2_ini_mm": st.session_state.get("t2_ini_mm", 0),
        "t2_fin_mm": st.session_state.get("t2_fin_mm", 400),
        "t2_centraje_inicio": st.session_state.get("t2_centraje_inicio"),
        "t2l": st.session_state.get("t2l", 256),
        "t2dir": st.session_state.get("t2dir", "CAUDO-CRANEAL"),
        "t2vz": st.session_state.get("t2vz", "NINGUNA"),
        "t2kv": st.session_state.get("t2kv", 100),
        "t2ma": st.session_state.get("t2ma", 40),
    }
    for k, v in defaults.items():
        t.setdefault(k, v)


def _save_store_only(**kwargs):
    t = st.session_state["topograma_store"]
    for k, v in kwargs.items():
        t[k] = v


def _render_section_title(text):
    st.markdown(f"### {text}")


def render_topograma_panel():
    _init_state()
    t = st.session_state["topograma_store"]

    st.markdown("## 📡 Topograma")

    top_c1, top_c2, top_c3 = st.columns([1.05, 1.15, 1.15], gap="large")

    with top_c1:
        with st.container(border=True):
            _render_section_title("🧾 Datos del Examen")
            region = selectbox_con_placeholder("Región anatómica", REGIONES.keys(), value=t.get("region"), key="region")
            examen = selectbox_con_placeholder(
                "Examen",
                REGIONES.get(region, []),
                value=t.get("examen") if t.get("region") == region else None,
                key="examen",
            )
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.image(_draw_region_placeholder(region), use_container_width=True)

    with top_c2:
        with st.container(border=True):
            _render_section_title("🛏️ Posicionamiento del paciente")
            c21, c22 = st.columns(2, gap="medium")
            with c21:
                posicion = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, value=t.get("posicion"), key="posicion")
                t1pt = selectbox_con_placeholder("Posición tubo", POS_TUBO, value=t.get("t1pt"), key="t1pt")
            with c22:
                entrada = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, value=t.get("entrada"), key="entrada")
                extremidades = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, value=t.get("extremidades"), key="extremidades")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.image(_draw_position_placeholder(posicion, entrada, t1pt), use_container_width=True)

    with top_c3:
        with st.container(border=True):
            _render_section_title("✅ Topograma adquirido")
            if st.session_state.get("topograma_iniciado", False):
                img1, err1 = obtener_imagen_topograma_adquirido(examen, posicion, entrada, t1pt)
                if img1 is not None:
                    st.image(img1, use_container_width=True)
                    st.caption(
                        f"Proyección: AP · Tubo: {t1pt or '—'} · {t.get('t1l') or '—'} mm · {t.get('t1kv') or '—'} kV · {t.get('t1ma') or '—'} mA"
                    )
                    st.success("✅ Topograma adquirido correctamente. Continúa a ⚡ Adquisición.")
                else:
                    st.error(err1 or "Imagen no encontrada")
            else:
                st.info("Configura e inicia el topograma")

    _save_store_only(
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

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        _render_section_title("📡 Topograma 1")

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

        _save_store_only(
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

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    campos_t1_ok = all([region, examen, posicion, entrada, t1pt, t1l, t1dir, t1vz])
    if st.button("☢️ INICIAR TOPOGRAMA", key="btn_iniciar_topo1", use_container_width=True, disabled=not campos_t1_ok):
        st.session_state["topograma_iniciado"] = True
        st.rerun()
    if st.button("↺ Repetir topograma", key="btn_reset_topo1", use_container_width=True, disabled=not st.session_state.get("topograma_iniciado", False)):
        st.session_state["topograma_iniciado"] = False
        st.rerun()

    if aplica_topo2:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        cta, ctb = st.columns([1.05, 1.0], gap="large")
        with cta:
            with st.container(border=True):
                _render_section_title("🛏️ Posicionamiento del paciente — Topograma 2")
                c1, c2 = st.columns(2, gap="medium")
                with c1:
                    t2_pos = selectbox_con_placeholder("Posición paciente", POSICIONES_PACIENTE, value=t.get("t2_posicion_paciente"), key="t2_posicion_paciente")
                    t2_pt = selectbox_con_placeholder("Posición tubo", POS_TUBO, value=t.get("t2pt"), key="t2pt")
                with c2:
                    t2_ent = selectbox_con_placeholder("Entrada", ENTRADAS_PACIENTE, value=t.get("t2_entrada"), key="t2_entrada")
                    t2_ext = selectbox_con_placeholder("Posición extremidades", POS_EXTREMIDADES, value=t.get("t2_extremidades"), key="t2_extremidades")
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                st.image(_draw_position_placeholder(t2_pos, t2_ent, t2_pt), use_container_width=True)

        with ctb:
            with st.container(border=True):
                _render_section_title("🖼️ Topograma 2")
                if st.session_state.get("topograma2_iniciado", False):
                    img2, err2 = obtener_imagen_topograma_adquirido(examen, t2_pos, t2_ent, t2_pt)
                    if img2 is not None:
                        st.image(img2, use_container_width=True)
                        st.caption(
                            f"Proyección: AP · Tubo: {t2_pt or '—'} · {t.get('t2l') or '—'} mm · {t.get('t2kv') or '—'} kV · {t.get('t2ma') or '—'} mA"
                        )
                        st.success("✅ Topograma 2 adquirido correctamente.")
                    else:
                        st.error(err2 or "Imagen no encontrada")
                else:
                    st.info("Configura e inicia Topograma 2")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            _render_section_title("📡 Topograma 2")
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

        _save_store_only(
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

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        campos_t2_ok = all([t2_pos, t2_ent, t2_pt, t2l, t2dir, t2vz])
        if st.button("☢️ INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not campos_t2_ok):
            st.session_state["topograma2_iniciado"] = True
            st.rerun()
        if st.button("↺ Repetir topograma 2", key="btn_reset_topo2", use_container_width=True, disabled=not st.session_state.get("topograma2_iniciado", False)):
            st.session_state["topograma2_iniciado"] = False
            st.rerun()

    return st.session_state["topograma_store"]
