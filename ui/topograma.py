import streamlit as st
from core.helpers import selectbox_con_placeholder

# Loader temporal: se conectará después con Excel + ZIP reales
try:
    from data.loaders import obtener_imagen_topograma_adquirido
except Exception:
    def obtener_imagen_topograma_adquirido(*args, **kwargs):
        return None, "Loader de topogramas aún no integrado en data/loaders.py"


# --- OPCIONES FIELES AL ORIGINAL ---
REGIONES = {
    "CABEZA": ["CEREBRO", "ORBITAS", "OIDOS", "SPN", "MAXILOFACIAL"],
    "CUELLO": ["CUELLO"],
    "EESS": ["HOMBRO", "BRAZO", "CODO", "ANTEBRAZO", "MUÑECA", "MANO"],
    "COLUMNA": ["CERVICAL", "DORSAL", "LUMBAR", "SACROCOXIS"],
    "CUERPO": ["TORAX", "ABDOMEN", "PELVIS", "ABDOMEN-PELVIS", "TORAX-ABDOMEN-PELVIS"],
    "EEII": ["CADERA", "MUSLO", "RODILLA", "TOBILLO", "PIE"],
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
DIRECCIONES = ["CAUDO-CRANEAL", "CRANEO-CAUDAL"]
LONGITUDES_TOPO = [128, 256, 512, 768, 1020, 1560]
POS_TUBO = ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"]
INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]

# Este bloque puede ajustarse después si quieres replicar opciones exactas del centraje
CENTRAJE_INICIO = ["SUPERIOR", "MEDIO", "INFERIOR"]


def _init_topograma_state():
    if "topograma_store" not in st.session_state or not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}

    store = st.session_state["topograma_store"]
    defaults = {
        "region_anat": None,
        "examen": None,
        "posicion": None,
        "entrada": None,
        "aplica_topo2": False,
        "t1pt": None,
        "t1l": None,
        "t1dir": None,
        "t1vz": None,
        "t1_centraje_inicio": None,
        "t2pt": None,
        "t2l": None,
        "t2dir": None,
        "t2vz": None,
        "t2_centraje_inicio": None,
    }
    for k, v in defaults.items():
        store.setdefault(k, v)

    st.session_state.setdefault("topograma_iniciado", False)
    st.session_state.setdefault("topograma2_iniciado", False)


def _render_topograma_image(prefix: str, titulo: str, store: dict):
    state_key = "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"
    iniciado = st.session_state.get(state_key, False)

    st.markdown(f"### {titulo}")

    if not iniciado:
        st.info("Completa los parámetros y presiona iniciar para generar el topograma.")
        return

    img, err = obtener_imagen_topograma_adquirido(
        store.get("examen"),
        store.get("posicion"),
        store.get("entrada"),
        store.get(f"{prefix}pt"),
    )

    if img is not None:
        st.image(img, use_container_width=True)
        st.caption(f"Imagen {titulo}")
    else:
        st.warning(err or "No se pudo cargar la imagen del topograma.")


def _bloque_topograma(prefix: str, titulo: str, store: dict):
    st.markdown(f"### {titulo}")

    c1, c2 = st.columns(2)
    with c1:
        pos_tubo = selectbox_con_placeholder(
            "Posición tubo",
            POS_TUBO,
            value=store.get(f"{prefix}pt"),
            key=f"{prefix}pt_ui",
        )
        store[f"{prefix}pt"] = pos_tubo

    with c2:
        longitud = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=store.get(f"{prefix}l"),
            key=f"{prefix}l_ui",
        )
        store[f"{prefix}l"] = longitud

    c3, c4 = st.columns(2)
    with c3:
        direccion = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=store.get(f"{prefix}dir"),
            key=f"{prefix}dir_ui",
        )
        store[f"{prefix}dir"] = direccion

    with c4:
        voz = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=store.get(f"{prefix}vz"),
            key=f"{prefix}vz_ui",
        )
        store[f"{prefix}vz"] = voz

    centraje = selectbox_con_placeholder(
        "Centraje inicio de topograma",
        CENTRAJE_INICIO,
        value=store.get(f"{prefix}_centraje_inicio"),
        key=f"{prefix}_centraje_inicio_ui",
    )
    store[f"{prefix}_centraje_inicio"] = centraje

    completos = all([
        store.get(f"{prefix}pt"),
        store.get(f"{prefix}l"),
        store.get(f"{prefix}dir"),
        store.get(f"{prefix}vz"),
        store.get(f"{prefix}_centraje_inicio"),
    ])

    state_key = "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"

    if st.button(
        f"☢️ INICIAR {titulo.upper()}",
        key=f"{prefix}_start_btn",
        use_container_width=True,
        disabled=not completos,
    ):
        st.session_state[state_key] = True
        st.rerun()

    if st.session_state.get(state_key, False):
        if st.button(
            f"↺ Repetir {titulo.lower()}",
            key=f"{prefix}_reset_btn",
            use_container_width=True,
        ):
            st.session_state[state_key] = False
            st.rerun()


def render_topograma():
    _init_topograma_state()
    store = st.session_state["topograma_store"]

    st.subheader("Topograma")

    st.markdown("### Datos del examen")
    c1, c2 = st.columns(2)

    with c1:
        region_sel = selectbox_con_placeholder(
            "Región anatómica",
            list(REGIONES.keys()),
            value=store.get("region_anat"),
            key="region_anat_ui",
        )

    examenes_region = REGIONES.get(region_sel, []) if region_sel else []

    with c2:
        examen_actual = store.get("examen")
        if examen_actual not in examenes_region:
            examen_actual = None

        examen_sel = selectbox_con_placeholder(
            "Examen",
            examenes_region,
            value=examen_actual,
            key="examen_ui",
        )

    store["region_anat"] = region_sel
    store["examen"] = examen_sel

    c3, c4, c5 = st.columns(3)

    with c3:
        posicion_sel = selectbox_con_placeholder(
            "Posición del paciente",
            POSICIONES_PACIENTE,
            value=store.get("posicion"),
            key="posicion_ui",
        )
        store["posicion"] = posicion_sel

    with c4:
        entrada_sel = selectbox_con_placeholder(
            "Entrada",
            ENTRADAS_PACIENTE,
            value=store.get("entrada"),
            key="entrada_ui",
        )
        store["entrada"] = entrada_sel

    with c5:
        aplica_topo2 = st.checkbox(
            "Agregar Topograma 2",
            value=store.get("aplica_topo2", False),
            key="aplica_topo2_ui",
        )
        store["aplica_topo2"] = aplica_topo2

    st.markdown("---")

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        _bloque_topograma("t1", "Topograma 1", store)

        if aplica_topo2:
            st.markdown("---")
            _bloque_topograma("t2", "Topograma 2", store)

    with right:
        st.markdown("## Vista previa")
        _render_topograma_image("t1", "Imagen Topograma 1", store)

        if aplica_topo2:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            _render_topograma_image("t2", "Imagen Topograma 2", store)

    if st.session_state.get("topograma_iniciado", False):
        st.success("Topograma 1 listo. Ya puedes avanzar a Adquisición.")

    if aplica_topo2 and st.session_state.get("topograma2_iniciado", False):
        st.success("Topograma 2 listo.")
