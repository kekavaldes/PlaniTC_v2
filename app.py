import streamlit as st

from core.state import init_state
from ui.ingreso import render_ingreso
from ui.topograma import render_topograma
from ui.adquisicion import render_adquisicion
from ui.reconstruccion import render_reconstruccion
from ui.inyectora import render_inyectora_tab

st.set_page_config(page_title="PlaniTC", layout="wide")

init_state()

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Inicio",
    "Ingreso",
    "Topograma",
    "Adquisición",
    "Reconstrucción",
    "Inyectora",
])

with tab0:
    st.title("PlaniTC")
    st.caption("Base de refactor modular para tu simulador")
    st.info(
        "Esta versión es una estructura de trabajo para migrar tu app actual por módulos. "
        "No reemplaza todavía todas las funciones del archivo monolítico original."
    )

with tab1:
    render_ingreso()

with tab2:
    render_topograma()

with tab3:
    render_adquisicion()

with tab4:
    render_reconstruccion()

with tab5:
    render_inyectora_tab()
