import streamlit as st

from constants import (
    KVP_OPCIONES,
    MA_OPCIONES,
    MODULACION_CORRIENTE,
    N_IMAGENES_BOLUS_OPCIONES,
    PERIODO_BOLUS_OPCIONES,
    POSICIONES_CORTE_BOLUS,
    ROT_TUBO_OPCIONES,
    TIPOS_EXPLORACION,
    TIPO_EXPLORACION_TECNICA,
)
from core.helpers import is_bolus, selectbox_con_placeholder
from core.state import agregar_exploracion, eliminar_exploracion, get_exploracion_activa


def render_sidebar_exploraciones():
    st.markdown("### Exploraciones")

    for exp in st.session_state["exploraciones_adq"]:
        if exp.get("tipo") == "topograma":
            label = "📡 Topograma"
        else:
            label = f"⚡ {exp.get('orden', '')}. {exp.get('nombre', 'SIN CONTRASTE')}"

        if st.button(label, key=f"sel_{exp['id']}", use_container_width=True):
            st.session_state["exploracion_adq_activa"] = exp["id"]

    st.markdown("---")
    if st.button("➕ Agregar exploración", key="add_exp", use_container_width=True):
        agregar_exploracion()
        st.rerun()


def render_panel_topogramas_disponibles():
    st.markdown("#### Topogramas disponibles")
    topo1 = st.session_state.get("topograma_iniciado", False)
    topo2 = st.session_state.get("topograma2_iniciado", False)

    col1, col2 = st.columns(2)
    with col1:
        if topo1:
            st.success("✅ Topograma 1 disponible")
        else:
            st.info("Topograma 1 no iniciado")
    with col2:
        if topo2:
            st.success("✅ Topograma 2 disponible")
        else:
            st.info("Topograma 2 no iniciado")


def render_form_exploracion(exp: dict):
    exp_id = exp["id"]

    exp["nombre"] = selectbox_con_placeholder(
        "Nombre de la exploración",
        TIPOS_EXPLORACION,
        value=exp.get("nombre"),
        key=f"nombre_{exp_id}",
    )

    if is_bolus(exp.get("nombre")):
        col1, col2, col3 = st.columns(3)
        with col1:
            exp["periodo_bolus"] = selectbox_con_placeholder(
                "Periodo",
                PERIODO_BOLUS_OPCIONES,
                value=exp.get("periodo_bolus"),
                key=f"periodo_{exp_id}",
            )
        with col2:
            exp["n_imagenes_bolus"] = selectbox_con_placeholder(
                "N° de imágenes",
                N_IMAGENES_BOLUS_OPCIONES,
                value=exp.get("n_imagenes_bolus"),
                key=f"nimags_{exp_id}",
            )
        with col3:
            exp["posicion_corte"] = selectbox_con_placeholder(
                "Posición de corte",
                POSICIONES_CORTE_BOLUS,
                value=exp.get("posicion_corte"),
                key=f"poscorte_{exp_id}",
            )

        st.number_input("kV bolus", min_value=80, max_value=140, value=int(exp.get("kvp_bolus", 100)), key=f"kvpbol_{exp_id}")
        st.number_input("mAs bolus", min_value=10, max_value=300, value=int(exp.get("mas_bolus", 20)), key=f"masbol_{exp_id}")
    else:
        row1 = st.columns(4)
        with row1[0]:
            exp["mod_corriente"] = selectbox_con_placeholder(
                "Modulación de corriente",
                MODULACION_CORRIENTE,
                value=exp.get("mod_corriente"),
                key=f"modcorr_{exp_id}",
            )
        with row1[1]:
            exp["mas_val"] = selectbox_con_placeholder(
                "mAs",
                MA_OPCIONES,
                value=exp.get("mas_val"),
                key=f"mas_{exp_id}",
            )
        with row1[2]:
            st.text_input("Índice de ruido", value=str(exp.get("ind_ruido") or ""), key=f"iruido_{exp_id}")
        with row1[3]:
            exp["kvp"] = selectbox_con_placeholder(
                "kV",
                KVP_OPCIONES,
                value=exp.get("kvp"),
                key=f"kvp_{exp_id}",
            )

        row2 = st.columns(6)
        with row2[0]:
            exp["tipo_exp"] = selectbox_con_placeholder(
                "Tipo exploración",
                TIPO_EXPLORACION_TECNICA,
                value=exp.get("tipo_exp"),
                key=f"tipoexp_{exp_id}",
            )
        with row2[1]:
            st.text_input("Doble muestreo", value=str(exp.get("doble_muestreo") or ""), key=f"dm_{exp_id}")
        with row2[2]:
            st.text_input("Configuración de detección", value=str(exp.get("conf_det") or ""), key=f"confdet_{exp_id}")
        with row2[3]:
            st.text_input("Cobertura", value="", key=f"cobertura_{exp_id}")
        with row2[4]:
            st.text_input("Grosor prospectivo", value=str(exp.get("grosor_prosp") or ""), key=f"gpros_{exp_id}")
        with row2[5]:
            st.text_input("SFOV", value=str(exp.get("sfov") or ""), key=f"sfov_{exp_id}")

        row3 = st.columns(4)
        with row3[0]:
            st.text_input("Instrucción de voz", value=str(exp.get("voz_adq") or ""), key=f"voz_{exp_id}")
        with row3[1]:
            st.text_input("Retardo", value=str(exp.get("retardo") or ""), key=f"ret_{exp_id}")
        with row3[2]:
            st.text_input("Pitch", value=str(exp.get("pitch") or ""), key=f"pitch_{exp_id}")
        with row3[3]:
            exp["rot_tubo"] = selectbox_con_placeholder(
                "TPO ROTACION TUBO",
                ROT_TUBO_OPCIONES,
                value=exp.get("rot_tubo"),
                key=f"rot_{exp_id}",
            )


def render_adquisicion():
    col_nav, col_main = st.columns([1, 3])

    with col_nav:
        render_sidebar_exploraciones()

    with col_main:
        actual = get_exploracion_activa()
        if actual is None:
            st.warning("No se pudo cargar la exploración seleccionada.")
            return

        if actual.get("tipo") == "topograma":
            st.subheader("📡 Topograma")
            st.info("Aquí puedes mostrar el panel de topograma incrustado dentro de adquisición si quieres mantener ese flujo.")
            render_panel_topogramas_disponibles()
            return

        st.subheader(f"⚡ {actual.get('nombre', 'Exploración')}")
        render_panel_topogramas_disponibles()
        render_form_exploracion(actual)

        st.markdown("---")
        if st.button("🗑️ Eliminar esta exploración", key=f"del_{actual['id']}"):
            eliminar_exploracion(actual["id"])
            st.rerun()

        st.info(
            "Aquí debes migrar la lógica real de store, sincronización, imágenes de topograma y cobertura automática."
        )
