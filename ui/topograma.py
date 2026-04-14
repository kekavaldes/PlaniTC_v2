import streamlit as st

from core.helpers import selectbox_con_placeholder

try:
    from data.loaders import obtener_imagen_topograma_adquirido
except Exception:
    # Fallback temporal mientras migramos loaders reales
    def obtener_imagen_topograma_adquirido(examen, posicion_paciente, entrada, pos_tubo):
        return None, "Loader de topogramas aún no integrado en data/loaders.py"


POSICIONES_TUBO = [
    "ARRIBA 0°",
    "ABAJO 180°",
    "DERECHA 90°",
    "IZQUIERDA 90°",
]

LONGITUDES_TOPO = [80, 120, 160, 200, 240, 320, 400]
DIRECCIONES = ["CRÁNEO-CAUDAL", "CAUDAL-CRÁNEO"]
INSTRUCCIONES_VOZ = ["INSPIRAR", "ESPIRAR", "RESPIRACIÓN SUAVE"]

POSICIONES_PACIENTE = [
    "DECÚBITO SUPINO",
    "DECÚBITO PRONO",
    "DECÚBITO LATERAL DERECHO",
    "DECÚBITO LATERAL IZQUIERDO",
]

ENTRADAS = [
    "HEAD FIRST",
    "FEET FIRST",
]

REGIONES = [
    "CRÁNEO",
    "CUELLO",
    "TÓRAX",
    "ABDOMEN",
    "PELVIS",
    "COLUMNA",
    "EESS",
    "EEII",
]

EXAMENES_POR_REGION = {
    "CRÁNEO": ["CRÁNEO S/C", "CRÁNEO C/C"],
    "CUELLO": ["CUELLO S/C", "CUELLO C/C", "ATC CUELLO"],
    "TÓRAX": ["TÓRAX S/C", "TÓRAX C/C", "ATC TÓRAX"],
    "ABDOMEN": ["ABDOMEN S/C", "ABDOMEN C/C", "ATC ABDOMEN"],
    "PELVIS": ["PELVIS S/C", "PELVIS C/C"],
    "COLUMNA": ["COLUMNA CERVICAL", "COLUMNA DORSAL", "COLUMNA LUMBAR"],
    "EESS": ["HOMBRO", "BRAZO", "ANTEBRAZO", "MANO"],
    "EEII": ["CADERA", "MUSLO", "RODILLA", "PIERNA", "TOBILLO", "PIE"],
}


def _init_topograma_state():
    defaults = {
        "topograma_iniciado": False,
        "topograma2_iniciado": False,
        "topograma_store": {},
        "region_anatomica_ui": None,
        "examen_ui": None,
        "posicion_ui": None,
        "entrada_ui": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if not isinstance(st.session_state.get("topograma_store"), dict):
        st.session_state["topograma_store"] = {}


def _warning_campos_faltantes(titulo: str, faltantes: list[str]):
    st.markdown(
        f"""
        <div style="
            background:#1A1100;
            border:1px solid #554400;
            border-radius:8px;
            padding:0.6rem 1rem;
            margin-bottom:0.5rem;
            font-size:0.82rem;
            color:#FFAA00;
        ">
            ⚠️ Completa todos los campos de {titulo} antes de iniciar:<br>
            <span style="color:#FF8800;">{'  ·  '.join(faltantes)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_topograma_image(
    *,
    titulo: str,
    examen: str | None,
    posicion: str | None,
    entrada: str | None,
    pos_tubo: str | None,
    iniciado: bool,
):
    st.markdown(
        f"""
        <div style="
            border:1px solid #2A2E39;
            border-radius:12px;
            padding:0.75rem;
            background:#111827;
            min-height:320px;
        ">
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='font-weight:700; color:#E5E7EB; margin-bottom:0.5rem;'>{titulo}</div>",
        unsafe_allow_html=True,
    )

    if not iniciado:
        st.info("Completa los parámetros y presiona iniciar para generar el topograma.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    img, err = obtener_imagen_topograma_adquirido(
        examen or "",
        posicion or "",
        entrada or "",
        pos_tubo or "",
    )

    if img is not None:
        st.image(img, use_container_width=True)
        st.caption("Topograma adquirido")
    else:
        st.warning(err or "No se pudo cargar la imagen del topograma.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_bloque_topograma(prefix: str, titulo: str):
    _tstore = st.session_state["topograma_store"]

    key_pos = f"{prefix}_pos"
    key_long = f"{prefix}_long"
    key_dir = f"{prefix}_dir"
    key_voz = f"{prefix}_voz"

    # Compatibilidad con claves previas de tu archivo original
    map_store = {
        "t1": {"pos": "t1p", "long": "t1l", "dir": "t1dir", "voz": "t1vz"},
        "t2": {"pos": "t2p", "long": "t2l", "dir": "t2dir", "voz": "t2vz"},
    }

    store_keys = map_store[prefix]

    pos_actual = _tstore.get(store_keys["pos"])
    long_actual = _tstore.get(store_keys["long"])
    dir_actual = _tstore.get(store_keys["dir"])
    voz_actual = _tstore.get(store_keys["voz"])

    st.markdown(
        f"<div style='font-size:1rem; font-weight:700; margin-bottom:0.4rem;'>{titulo}</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        pos_tubo = selectbox_con_placeholder(
            "Posición tubo",
            POSICIONES_TUBO,
            value=pos_actual,
            key=key_pos,
        )
        _tstore[store_keys["pos"]] = pos_tubo if pos_tubo else None

    with c2:
        topo_long = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=long_actual,
            key=key_long,
        )
        _tstore[store_keys["long"]] = topo_long if topo_long is not None else None

    c3, c4 = st.columns(2)
    with c3:
        topo_dir = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=dir_actual,
            key=key_dir,
        )
        _tstore[store_keys["dir"]] = topo_dir if topo_dir else None

    with c4:
        topo_voz = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=voz_actual,
            key=key_voz,
        )
        _tstore[store_keys["voz"]] = topo_voz if topo_voz else None

    completos = all([
        pos_tubo is not None,
        topo_long is not None,
        topo_dir is not None,
        topo_voz is not None,
    ])

    if not completos:
        faltantes = []
        if pos_tubo is None:
            faltantes.append("Posición tubo")
        if topo_long is None:
            faltantes.append("Longitud")
        if topo_dir is None:
            faltantes.append("Dirección")
        if topo_voz is None:
            faltantes.append("Instrucción de voz")
        _warning_campos_faltantes(titulo, faltantes)

    btn_key = "btn_iniciar_topo1" if prefix == "t1" else "btn_iniciar_topo2"
    reset_key = "btn_reset_topo1" if prefix == "t1" else "btn_reset_topo2"
    state_key = "topograma_iniciado" if prefix == "t1" else "topograma2_iniciado"

    if st.button(
        f"☢️  INICIAR {titulo.upper()}",
        key=btn_key,
        use_container_width=True,
        disabled=not completos,
    ):
        st.session_state[state_key] = True
        st.rerun()

    if st.session_state.get(state_key, False):
        if st.button(
            f"↺  Repetir {titulo.lower()}",
            key=reset_key,
            use_container_width=True,
        ):
            st.session_state[state_key] = False
            st.rerun()


def render_topograma():
    _init_topograma_state()
    _tstore = st.session_state["topograma_store"]

    st.subheader("Topograma")

    st.markdown("### Datos del examen")
    a1, a2 = st.columns([1, 1])

    with a1:
        region = selectbox_con_placeholder(
            "Región anatómica",
            REGIONES,
            value=st.session_state.get("region_anatomica_ui"),
            key="region_anatomica_ui",
        )

    examenes = EXAMENES_POR_REGION.get(region, []) if region else []

    with a2:
        examen_actual = st.session_state.get("examen_ui")
        examen = selectbox_con_placeholder(
            "Examen",
            examenes,
            value=examen_actual if examen_actual in examenes else None,
            key="examen_ui",
        )

    b1, b2, b3 = st.columns(3)
    with b1:
        posicion = selectbox_con_placeholder(
            "Posición del paciente",
            POSICIONES_PACIENTE,
            value=st.session_state.get("posicion_ui"),
            key="posicion_ui",
        )

    with b2:
        entrada = selectbox_con_placeholder(
            "Entrada",
            ENTRADAS,
            value=st.session_state.get("entrada_ui"),
            key="entrada_ui",
        )

    with b3:
        aplica_topo2 = st.checkbox(
            "Agregar Topograma 2",
            value=_tstore.get("aplica_topo2", False),
            key="aplica_topo2_ui",
        )
        _tstore["aplica_topo2"] = aplica_topo2

    st.markdown("---")

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        _render_bloque_topograma("t1", "Topograma 1")

        if aplica_topo2:
            st.markdown("---")
            _render_bloque_topograma("t2", "Topograma 2")

    with right:
        st.markdown("### Vista previa")
        _render_topograma_image(
            titulo="Imagen Topograma 1",
            examen=st.session_state.get("examen_ui"),
            posicion=st.session_state.get("posicion_ui"),
            entrada=st.session_state.get("entrada_ui"),
            pos_tubo=_tstore.get("t1p"),
            iniciado=st.session_state.get("topograma_iniciado", False),
        )

        if aplica_topo2:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            _render_topograma_image(
                titulo="Imagen Topograma 2",
                examen=st.session_state.get("examen_ui"),
                posicion=st.session_state.get("posicion_ui"),
                entrada=st.session_state.get("entrada_ui"),
                pos_tubo=_tstore.get("t2p"),
                iniciado=st.session_state.get("topograma2_iniciado", False),
            )

    if st.session_state.get("topograma_iniciado", False):
        st.success("Topograma 1 listo. Ya puedes avanzar a Adquisición.")

    if aplica_topo2 and st.session_state.get("topograma2_iniciado", False):
        st.success("Topograma 2 listo.")
