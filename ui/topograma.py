import streamlit as st
from core.helpers import selectbox_con_placeholder

# Loader temporal
try:
    from data.loaders import obtener_imagen_topograma_adquirido
except:
    def obtener_imagen_topograma_adquirido(*args, **kwargs):
        return None, "Loader de topogramas aún no integrado"


# --- OPCIONES (puedes ajustarlas después con tus listas reales) ---
POSICIONES_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
LONGITUDES = [80, 120, 160, 200, 240, 320, 400]
DIRECCIONES = ["CRÁNEO-CAUDAL", "CAUDAL-CRÁNEO"]
VOZ = ["INSPIRAR", "ESPIRAR", "RESPIRACIÓN SUAVE"]
CENTRAJE = ["SUPERIOR", "MEDIO", "INFERIOR"]

REGIONES = ["CRÁNEO", "CUELLO", "TÓRAX", "ABDOMEN", "PELVIS"]

EXAMENES = {
    "CRÁNEO": ["CRÁNEO S/C", "CRÁNEO C/C"],
    "CUELLO": ["CUELLO S/C", "CUELLO C/C"],
    "TÓRAX": ["TÓRAX S/C", "TÓRAX C/C"],
    "ABDOMEN": ["ABDOMEN S/C", "ABDOMEN C/C"],
    "PELVIS": ["PELVIS S/C", "PELVIS C/C"],
}

POSICION = ["DECÚBITO SUPINO", "PRONO"]
ENTRADA = ["HEAD FIRST", "FEET FIRST"]


# --- STATE ---
def init_state():
    if "topograma_store" not in st.session_state:
        st.session_state["topograma_store"] = {}

    if "topograma_iniciado" not in st.session_state:
        st.session_state["topograma_iniciado"] = False

    if "topograma2_iniciado" not in st.session_state:
        st.session_state["topograma2_iniciado"] = False


# --- BLOQUE TOPOGRAMA ---
def bloque_topograma(prefix, titulo):
    store = st.session_state["topograma_store"]

    st.markdown(f"### {titulo}")

    c1, c2 = st.columns(2)

    with c1:
        pos_tubo = selectbox_con_placeholder(
            "Posición tubo",
            POSICIONES_TUBO,
            value=store.get(f"{prefix}p"),
            key=f"{prefix}_pt",
        )
        store[f"{prefix}p"] = pos_tubo

    with c2:
        longitud = selectbox_con_placeholder(
            "Longitud (mm)",
            LONGITUDES,
            value=store.get(f"{prefix}l"),
            key=f"{prefix}_l",
        )
        store[f"{prefix}l"] = longitud

    c3, c4 = st.columns(2)

    with c3:
        direccion = selectbox_con_placeholder(
            "Dirección",
            DIRECCIONES,
            value=store.get(f"{prefix}dir"),
            key=f"{prefix}_dir",
        )
        store[f"{prefix}dir"] = direccion

    with c4:
        voz = selectbox_con_placeholder(
            "Instrucción de voz",
            VOZ,
            value=store.get(f"{prefix}vz"),
            key=f"{prefix}_voz",
        )
        store[f"{prefix}vz"] = voz

    cent = selectbox_con_placeholder(
        "Centraje inicio",
        CENTRAJE,
        value=store.get(f"{prefix}_centraje_inicio"),
        key=f"{prefix}_centraje",
    )
    store[f"{prefix}_centraje_inicio"] = cent

    completos = all([pos_tubo, longitud, direccion, voz, cent])

    state_key = "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"

    if st.button(f"☢️ INICIAR {titulo}", disabled=not completos, key=f"{prefix}_start"):
        st.session_state[state_key] = True
        st.rerun()

    if st.session_state[state_key]:
        if st.button(f"↺ Repetir {titulo}", key=f"{prefix}_reset"):
            st.session_state[state_key] = False
            st.rerun()


# --- IMAGEN ---
def vista_previa(prefix, titulo):
    store = st.session_state["topograma_store"]

    iniciado = st.session_state.get(
        "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"
    )

    st.markdown(f"### {titulo}")

    if not iniciado:
        st.info("Aún no iniciado")
        return

    img, err = obtener_imagen_topograma_adquirido(
        st.session_state.get("examen_ui"),
        st.session_state.get("posicion_ui"),
        st.session_state.get("entrada_ui"),
        store.get(f"{prefix}p"),
    )

    if img:
        st.image(img)
    else:
        st.warning(err)


# --- MAIN ---
def render_topograma():
    init_state()
    store = st.session_state["topograma_store"]

    st.subheader("Topograma")

    # Datos examen
    col1, col2 = st.columns(2)

    with col1:
        region = selectbox_con_placeholder(
            "Región",
            REGIONES,
            key="region_ui",
        )

    with col2:
        examen = selectbox_con_placeholder(
            "Examen",
            EXAMENES.get(region, []),
            key="examen_ui",
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        posicion = selectbox_con_placeholder(
            "Posición",
            POSICION,
            key="posicion_ui",
        )

    with c2:
        entrada = selectbox_con_placeholder(
            "Entrada",
            ENTRADA,
            key="entrada_ui",
        )

    with c3:
        aplica_t2 = st.checkbox("Agregar Topograma 2", value=store.get("t2", False))
        store["t2"] = aplica_t2

    st.markdown("---")

    left, right = st.columns([1.2, 1])

    with left:
        bloque_topograma("t1", "Topograma 1")

        if aplica_t2:
            bloque_topograma("t2", "Topograma 2")

    with right:
        vista_previa("t1", "Vista previa T1")

        if aplica_t2:
            vista_previa("t2", "Vista previa T2")
