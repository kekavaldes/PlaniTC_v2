# 🔥 SOLO TE MUESTRO LO NUEVO + INTEGRACIÓN CLAVE
# (no te repito todo tu archivo porque es largo, esto es plug & play)

# =========================
# INICIALIZACIÓN NUEVA
# =========================
def _init_grupos_topograma():
    if "grupos_topograma" not in st.session_state:
        st.session_state["grupos_topograma"] = []

    if "grupo_topograma_activo" not in st.session_state:
        st.session_state["grupo_topograma_activo"] = 0

    # Crear grupo inicial si no existe
    if len(st.session_state["grupos_topograma"]) == 0:
        st.session_state["grupos_topograma"].append({
            "nombre": "Grupo 1",
            "data": st.session_state.get("topograma_store", {}).copy()
        })


def _guardar_en_grupo_actual():
    idx = st.session_state["grupo_topograma_activo"]
    st.session_state["grupos_topograma"][idx]["data"] = st.session_state.get("topograma_store", {}).copy()


def _cargar_grupo(idx):
    grupo = st.session_state["grupos_topograma"][idx]
    st.session_state["topograma_store"] = grupo["data"].copy()


# =========================
# MODIFICAR render_topograma_panel()
# =========================
def render_topograma_panel():

    _init_grupos_topograma()

    # 🔹 selector de grupo
    nombres = [g["nombre"] for g in st.session_state["grupos_topograma"]]

    col_sel, col_btn = st.columns([2,1])

    with col_sel:
        idx = st.selectbox(
            "Grupo de topogramas",
            range(len(nombres)),
            format_func=lambda i: nombres[i],
            key="selector_grupo_topo"
        )

    with col_btn:
        if st.button("➕ Nuevo grupo"):
            nuevo_idx = len(st.session_state["grupos_topograma"]) + 1
            st.session_state["grupos_topograma"].append({
                "nombre": f"Grupo {nuevo_idx}",
                "data": {}
            })
            st.session_state["grupo_topograma_activo"] = len(st.session_state["grupos_topograma"]) - 1
            st.rerun()

    # 🔹 detectar cambio de grupo
    if idx != st.session_state["grupo_topograma_activo"]:
        st.session_state["grupo_topograma_activo"] = idx
        _cargar_grupo(idx)

    # 🔥 AQUÍ SIGUE TU CÓDIGO ORIGINAL
    # (NO LO CAMBIES)
    store = st.session_state.get("topograma_store", {})

    # ... TODO tu código existente ...

    # 🔥 AL FINAL DEL PANEL
    _guardar_en_grupo_actual()
