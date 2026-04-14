import streamlit as st

from constants import DIRECCIONES, INSTRUCCIONES_VOZ, LONGITUDES_TOPO, POSICIONES_TUBO
from core.helpers import selectbox_con_placeholder


def render_bloque_topograma(prefix: str, titulo: str, iniciado_key: str):
    st.markdown(f"### {titulo}")

    col1, col2 = st.columns(2)
    with col1:
        pos = selectbox_con_placeholder(
            "Posición tubo",
            POSICIONES_TUBO,
            key=f"{prefix}_pos_tubo",
        )
        longi = selectbox_con_placeholder(
            "Longitud de topograma (mm)",
            LONGITUDES_TOPO,
            key=f"{prefix}_longitud",
        )
    with col2:
        dire = selectbox_con_placeholder(
            "Dirección topograma",
            DIRECCIONES,
            key=f"{prefix}_direccion",
        )
        voz = selectbox_con_placeholder(
            "Instrucción de voz",
            INSTRUCCIONES_VOZ,
            key=f"{prefix}_voz",
        )

    completos = all([pos is not None, longi is not None, dire is not None, voz is not None])

    if not completos:
        faltan = []
        if pos is None:
            faltan.append("Posición tubo")
        if longi is None:
            faltan.append("Longitud")
        if dire is None:
            faltan.append("Dirección")
        if voz is None:
            faltan.append("Instrucción de voz")
        st.warning("Completa antes de iniciar: " + " · ".join(faltan))

    if st.button(f"☢️ INICIAR {titulo.upper()}", key=f"btn_{prefix}", disabled=not completos, use_container_width=True):
        st.session_state[iniciado_key] = True

    if st.session_state.get(iniciado_key, False):
        st.success(f"{titulo} iniciado")
        if st.button(f"↺ Repetir {titulo.lower()}", key=f"reset_{prefix}", use_container_width=True):
            st.session_state[iniciado_key] = False
            st.rerun()


def render_topograma():
    st.subheader("Topograma")
    col1, col2 = st.columns(2)
    with col1:
        render_bloque_topograma("topo1", "Topograma 1", "topograma_iniciado")
    with col2:
        render_bloque_topograma("topo2", "Topograma 2", "topograma2_iniciado")

    st.info(
        "Aquí debes migrar la lógica real de imágenes, stores y validaciones de topograma "
        "desde tu archivo original."
    )
