import streamlit as st
from ui.topograma import render_topograma_panel


def _init_adquisicion_state():
    if "exploraciones_adq" not in st.session_state:
        st.session_state["exploraciones_adq"] = [
            {
                "id": "topo_1",
                "tipo": "topograma",
                "nombre": "Topograma",
            },
            {
                "id": "exp_1",
                "tipo": "adquisicion",
                "nombre": "SIN CONTRASTE",
            },
        ]

    if "exploracion_adq_activa" not in st.session_state:
        st.session_state["exploracion_adq_activa"] = st.session_state["exploraciones_adq"][0]["id"]


def render_adquisicion():
    _init_adquisicion_state()

    st.subheader("Adquisición")

    col_nav, col_det = st.columns([1, 3], gap="large")

    with col_nav:
        st.markdown("### Exploraciones")

        for exp in st.session_state["exploraciones_adq"]:
            etiqueta = "📡 Topograma" if exp["tipo"] == "topograma" else f"⚡ {exp['nombre']}"
            if st.button(etiqueta, key=f"btn_{exp['id']}", use_container_width=True):
                st.session_state["exploracion_adq_activa"] = exp["id"]
                st.rerun()

        st.markdown("---")

        if st.button("＋ Agregar exploración", use_container_width=True):
            idx = sum(1 for e in st.session_state["exploraciones_adq"] if e["tipo"] == "adquisicion") + 1
            nueva = {
                "id": f"exp_{idx}",
                "tipo": "adquisicion",
                "nombre": "SIN CONTRASTE",
            }
            st.session_state["exploraciones_adq"].append(nueva)
            st.session_state["exploracion_adq_activa"] = nueva["id"]
            st.rerun()

    with col_det:
        actual = next(
            (e for e in st.session_state["exploraciones_adq"]
             if e["id"] == st.session_state["exploracion_adq_activa"]),
            None
        )

        if actual is None:
            st.warning("No se pudo cargar la exploración seleccionada.")
            return

        if actual.get("tipo") == "topograma":
            st.markdown("### 📡 Topograma")
            render_topograma_panel()
            return

        st.markdown(f"### ⚡ {actual.get('nombre', 'Exploración')}")

        opciones_nombre = [
            "SIN CONTRASTE",
            "ARTERIAL",
            "ANGIOGRÁFICA",
            "BOLUS TEST",
            "BOLUS TRACKING",
            "VENOSA",
            "TARDÍA",
        ]

        nombre_actual = actual.get("nombre", opciones_nombre[0])
        actual["nombre"] = st.selectbox(
            "Nombre de la exploración",
            opciones_nombre,
            index=opciones_nombre.index(nombre_actual) if nombre_actual in opciones_nombre else 0,
            key=f"nombre_{actual['id']}",
        )

        st.info("Aquí irá el panel completo de parámetros de adquisición.")
