import streamlit as st
from core.helpers import selectbox_con_placeholder

# --- OPCIONES ORIGINALES ---
REGIONES = {
    "CABEZA": ["CEREBRO", "ORBITAS", "OIDOS", "SPN", "MAXILOFACIAL"],
    "CUELLO": ["CUELLO"],
    "EESS": ["HOMBRO", "BRAZO", "CODO", "ANTEBRAZO", "MUÑECA", "MANO"],
    "COLUMNA": ["CERVICAL", "DORSAL", "LUMBAR", "SACROCOXIS"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS", "ABDOMEN-PELVIS", "TORAX-ABDOMEN-PELVIS"],
    "EEII": ["CADERA", "MUSLO", "RODILLA", "TOBILLO", "PIE"],
    "ANGIO": ["ATC CEREBRO", "ATC CUELLO", "ATC CEREBRO CUELLO", "ATC TORAX", "ATC ABDOMEN", "ATC ABDOMEN-PELVIS", "ATC TORAX-ABDOMEN-PELVIS", "EESS DERECHA", "EESS IZQUIERDA", "EEII"],
}

POSICIONES_PACIENTE = [
    "DECUBITO SUPINO",
    "DECUBITO PRONO",
    "DECUBITO LATERAL DERECHO",
    "DECUBITO LATERAL IZQUIERDO",
]

ENTRADAS_PACIENTE = ["CABEZA PRIMERO", "PIES PRIMERO"]
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
LONGITUDES = [128, 256, 512, 768, 1020, 1560]
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]
CENTRAJE = ["SUPERIOR", "MEDIO", "INFERIOR"]

# --- STATE ---
def init_state():
    if "topograma_store" not in st.session_state:
        st.session_state["topograma_store"] = {}

    if "topograma_iniciado" not in st.session_state:
        st.session_state["topograma_iniciado"] = False

    if "topograma2_iniciado" not in st.session_state:
        st.session_state["topograma2_iniciado"] = False


# --- BLOQUE TOPO ---
def bloque_topo(prefix, titulo):
    store = st.session_state["topograma_store"]

    st.markdown(f"### {titulo}")

    c1, c2 = st.columns(2)

    with c1:
        store[f"{prefix}pt"] = selectbox_con_placeholder(
            "Posición tubo",
            POS_TUBO,
            value=store.get(f"{prefix}pt"),
            key=f"{prefix}_pt_ui",
        )

    with c2:
        store[f"{prefix}l"] = selectbox_con_placeholder(
            "Longitud",
            LONGITUDES,
            value=store.get(f"{prefix}l"),
            key=f"{prefix}_l_ui",
        )

    c3, c4 = st.columns(2)

    with c3:
        store[f"{prefix}dir"] = selectbox_con_placeholder(
            "Dirección",
            DIRECCIONES,
            value=store.get(f"{prefix}dir"),
            key=f"{prefix}_dir_ui",
        )

    with c4:
        store[f"{prefix}vz"] = selectbox_con_placeholder(
            "Instrucción voz",
            VOZ,
            value=store.get(f"{prefix}vz"),
            key=f"{prefix}_vz_ui",
        )

    store[f"{prefix}_centraje_inicio"] = selectbox_con_placeholder(
        "Centraje inicio",
        CENTRAJE,
        value=store.get(f"{prefix}_centraje_inicio"),
        key=f"{prefix}_centraje_ui",
    )

    completo = all([
        store.get(f"{prefix}pt"),
        store.get(f"{prefix}l"),
        store.get(f"{prefix}dir"),
        store.get(f"{prefix}vz"),
        store.get(f"{prefix}_centraje_inicio"),
    ])

    key_state = "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"

    if st.button(f"☢️ INICIAR {titulo}", disabled=not completo, key=f"{prefix}_start"):
        st.session_state[key_state] = True
        st.rerun()

    if st.session_state[key_state]:
        if st.button(f"↺ Repetir {titulo}", key=f"{prefix}_reset"):
            st.session_state[key_state] = False
            st.rerun()


# --- MAIN ---
def render_topograma():
    init_state()
    store = st.session_state["topograma_store"]

    st.subheader("Topograma")

    c1, c2 = st.columns(2)

    with c1:
        region = selectbox_con_placeholder(
            "Región anatómica",
            list(REGIONES.keys()),
            value=store.get("region_anat"),
            key="region_ui",
        )

    examenes = REGIONES.get(region, []) if region else []

    with c2:
        examen = selectbox_con_placeholder(
            "Examen",
            examenes,
            value=store.get("examen") if store.get("examen") in examenes else None,
            key="examen_ui",
        )

    store["region_anat"] = region
    store["examen"] = examen

    c3, c4, c5 = st.columns(3)

    with c3:
        store["posicion"] = selectbox_con_placeholder(
            "Posición",
            POSICIONES_PACIENTE,
            value=store.get("posicion"),
            key="posicion_ui",
        )

    with c4:
        store["entrada"] = selectbox_con_placeholder(
            "Entrada",
            ENTRADAS_PACIENTE,
            value=store.get("entrada"),
            key="entrada_ui",
        )

    with c5:
        store["aplica_topo2"] = st.checkbox(
            "Agregar Topograma 2",
            value=store.get("aplica_topo2", False),
        )

    st.markdown("---")

    left, right = st.columns([1.2, 1])

    with left:
        bloque_topo("t1", "Topograma 1")
        if store.get("aplica_topo2"):
            bloque_topo("t2", "Topograma 2")

    with right:
        st.markdown("### Vista previa")
        if st.session_state["topograma_iniciado"]:
            st.success("Topograma 1 listo")

        if store.get("aplica_topo2") and st.session_state["topograma2_iniciado"]:
            st.success("Topograma 2 listo")
