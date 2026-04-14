
import streamlit as st
from core.helpers import selectbox_con_placeholder

try:
    from data.loaders import obtener_imagen_topograma_adquirido
except Exception:
    def obtener_imagen_topograma_adquirido(*args, **kwargs):
        return None, "Loader de topogramas aún no integrado"

# Opciones fieles al archivo original
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

# Valores usados por el original para centro/referencia
REFS_INICIO_TOPO = ["SUPERIOR", "CENTRO", "INFERIOR"]


def _init_topograma_state():
    defaults = {
        "topograma_store": {},
        "topograma_iniciado": False,
        "topograma2_iniciado": False,
        # claves globales históricas del original
        "region_anat": None,
        "examen": None,
        "posicion": None,
        "entrada": None,
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
        if k not in st.session_state:
            st.session_state[k] = v
    if not isinstance(st.session_state.get("topograma_store"), dict):
        st.session_state["topograma_store"] = {}


def _sync_global_to_store():
    t = st.session_state["topograma_store"]
    # topograma 1
    t["region_anat"] = st.session_state.get("region_anat")
    t["examen"] = st.session_state.get("examen")
    t["posicion"] = st.session_state.get("posicion")
    t["entrada"] = st.session_state.get("entrada")
    t["t1pt"] = st.session_state.get("t1pt")
    t["t1l"] = st.session_state.get("t1l")
    t["t1dir"] = st.session_state.get("t1dir")
    t["t1vz"] = st.session_state.get("t1vz")
    t["t1_centraje_inicio"] = st.session_state.get("t1_centraje_inicio")
    # topograma 2
    t["aplica_topo2"] = bool(t.get("aplica_topo2", False))
    t["t2pt"] = st.session_state.get("t2pt")
    t["t2l"] = st.session_state.get("t2l")
    t["t2dir"] = st.session_state.get("t2dir")
    t["t2vz"] = st.session_state.get("t2vz")
    t["t2_centraje_inicio"] = st.session_state.get("t2_centraje_inicio")
    # compatibilidad con adquisición
    t["t2_posicion_paciente"] = st.session_state.get("posicion")
    t["t2_entrada"] = st.session_state.get("entrada")


def _warning_campos_faltantes(titulo: str, faltantes: list[str]):
    st.markdown(f"""
    <div style="background:#1A1100; border:1px solid #554400; border-radius:8px;
                padding:0.6rem 1rem; margin-bottom:0.5rem; font-size:0.82rem; color:#FFAA00;">
        ⚠️ Completa todos los campos de {titulo} antes de iniciar:<br>
        <span style="color:#FF8800;">{'  ·  '.join(faltantes)}</span>
    </div>
    """, unsafe_allow_html=True)


def _render_preview_topo(prefix: str, titulo: str):
    store = st.session_state["topograma_store"]
    iniciado = st.session_state.get("topograma_iniciado" if prefix == "t1" else "topograma2_iniciado", False)
    pos_tubo = store.get(f"{prefix}pt") or st.session_state.get(f"{prefix}pt")
    posicion = store.get("posicion") or st.session_state.get("posicion", "")
    entrada = store.get("entrada") or st.session_state.get("entrada", "")
    examen = store.get("examen") or st.session_state.get("examen", "")

    st.markdown(f"### {titulo}")

    if not iniciado:
        st.info("Completa los parámetros y presiona iniciar para generar el topograma.")
        return

    img, err = obtener_imagen_topograma_adquirido(
        examen,
        posicion if prefix == "t1" else (store.get("t2_posicion_paciente") or posicion),
        entrada if prefix == "t1" else (store.get("t2_entrada") or entrada),
        pos_tubo or "",
    )
    if img is not None:
        st.image(img, use_container_width=True)
        subt = f"Tubo: {pos_tubo or '—'} · {store.get(f'{prefix}l') or st.session_state.get(f'{prefix}l', '—')} mm"
        st.caption(subt)
    else:
        st.warning(err or "No se encontró una imagen de topograma para esta combinación.")


def _bloque_topograma_1():
    st.markdown("### Parámetros Topograma 1")
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state["t1pt"] = selectbox_con_placeholder(
            "Posición tubo",
            POS_TUBO,
            value=st.session_state.get("t1pt"),
            key="t1pt",
        )
    with col_b:
        st.session_state["t1_centraje_inicio"] = selectbox_con_placeholder(
            "Centraje inicio de topograma",
            REFS_INICIO_TOPO,
            value=st.session_state.get("t1_centraje_inicio"),
            key="t1_centraje_inicio",
        )

    col_c, col_d, col_e = st.columns(3)
    with col_c:
        st.session_state["t1l"] = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=st.session_state.get("t1l"),
            key="t1l",
        )
    with col_d:
        st.session_state["t1dir"] = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=st.session_state.get("t1dir"),
            key="t1dir",
        )
    with col_e:
        st.session_state["t1vz"] = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=st.session_state.get("t1vz"),
            key="t1vz",
        )

    completos = all([
        st.session_state.get("t1pt") is not None,
        st.session_state.get("t1l") is not None,
        st.session_state.get("t1dir") is not None,
        st.session_state.get("t1vz") is not None,
    ])
    if not completos:
        faltantes = []
        if st.session_state.get("t1pt") is None: faltantes.append("Posición tubo")
        if st.session_state.get("t1l") is None: faltantes.append("Longitud")
        if st.session_state.get("t1dir") is None: faltantes.append("Dirección")
        if st.session_state.get("t1vz") is None: faltantes.append("Instrucción de voz")
        _warning_campos_faltantes("Topograma 1", faltantes)

    if st.button("☢️  INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1", use_container_width=True, disabled=not completos):
        st.session_state["topograma_iniciado"] = True
        _sync_global_to_store()
        st.rerun()

    if st.session_state.get("topograma_iniciado", False):
        if st.button("↺  Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()


def _bloque_topograma_2():
    st.markdown("### Parámetros Topograma 2")
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state["t2pt"] = selectbox_con_placeholder(
            "Posición tubo",
            POS_TUBO,
            value=st.session_state.get("t2pt"),
            key="t2pt",
        )
    with col_b:
        st.session_state["t2_centraje_inicio"] = selectbox_con_placeholder(
            "Centraje inicio de topograma",
            REFS_INICIO_TOPO,
            value=st.session_state.get("t2_centraje_inicio"),
            key="t2_centraje_inicio",
        )

    col_c, col_d, col_e = st.columns(3)
    with col_c:
        st.session_state["t2l"] = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            value=st.session_state.get("t2l"),
            key="t2l",
        )
    with col_d:
        st.session_state["t2dir"] = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            value=st.session_state.get("t2dir"),
            key="t2dir",
        )
    with col_e:
        st.session_state["t2vz"] = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            value=st.session_state.get("t2vz"),
            key="t2vz",
        )

    completos = all([
        st.session_state.get("t2pt") is not None,
        st.session_state.get("t2l") is not None,
        st.session_state.get("t2dir") is not None,
        st.session_state.get("t2vz") is not None,
    ])
    if not completos:
        faltantes = []
        if st.session_state.get("t2pt") is None: faltantes.append("Posición tubo")
        if st.session_state.get("t2l") is None: faltantes.append("Longitud")
        if st.session_state.get("t2dir") is None: faltantes.append("Dirección")
        if st.session_state.get("t2vz") is None: faltantes.append("Instrucción de voz")
        _warning_campos_faltantes("Topograma 2", faltantes)

    if st.button("☢️  INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not completos):
        st.session_state["topograma2_iniciado"] = True
        _sync_global_to_store()
        st.rerun()

    if st.session_state.get("topograma2_iniciado", False):
        if st.button("↺  Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
            st.session_state["topograma2_iniciado"] = False
            st.rerun()


def render_topograma():
    _init_topograma_state()

    st.subheader("Topograma")

    st.markdown("### Datos del examen")
    col1, col2 = st.columns(2)
    regiones_lista = list(REGIONES.keys())

    with col1:
        st.session_state["region_anat"] = selectbox_con_placeholder(
            "Región anatómica",
            regiones_lista,
            value=st.session_state.get("region_anat"),
            key="region_anat_widget",
        )

    examenes_region = REGIONES.get(st.session_state.get("region_anat"), [])

    with col2:
        examen_actual = st.session_state.get("examen")
        st.session_state["examen"] = selectbox_con_placeholder(
            "Examen",
            examenes_region,
            value=examen_actual if examen_actual in examenes_region else None,
            key="examen_widget",
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        st.session_state["posicion"] = selectbox_con_placeholder(
            "Posición del paciente",
            POSICIONES_PACIENTE,
            value=st.session_state.get("posicion"),
            key="posicion_widget",
        )
    with col4:
        st.session_state["entrada"] = selectbox_con_placeholder(
            "Entrada",
            ENTRADAS_PACIENTE,
            value=st.session_state.get("entrada"),
            key="entrada_widget",
        )
    with col5:
        aplica_topo2 = st.checkbox(
            "Agregar Topograma 2",
            value=st.session_state["topograma_store"].get("aplica_topo2", False),
            key="aplica_topo2_widget",
        )
        st.session_state["topograma_store"]["aplica_topo2"] = aplica_topo2

    _sync_global_to_store()

    st.markdown("---")
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        _bloque_topograma_1()
        if aplica_topo2:
            st.markdown("---")
            _bloque_topograma_2()

    with right:
        _render_preview_topo("t1", "Vista previa Topograma 1")
        if aplica_topo2:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            _render_preview_topo("t2", "Vista previa Topograma 2")

    if st.session_state.get("topograma_iniciado", False):
        st.success("Topograma 1 listo. Ya puedes avanzar a Adquisición.")
    if aplica_topo2 and st.session_state.get("topograma2_iniciado", False):
        st.success("Topograma 2 listo.")
