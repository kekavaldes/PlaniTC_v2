import streamlit as st


def _init_topograma_state():
    if "topograma_store" not in st.session_state or not isinstance(st.session_state["topograma_store"], dict):
        st.session_state["topograma_store"] = {}

    if "topograma_iniciado" not in st.session_state:
        st.session_state["topograma_iniciado"] = False

    if "topograma2_iniciado" not in st.session_state:
        st.session_state["topograma2_iniciado"] = False

    if "aplica_topo2" not in st.session_state:
        st.session_state["aplica_topo2"] = False


def _selectbox_placeholder(label, options, key):
    opciones = ["Seleccionar"] + list(options)
    valor_actual = st.session_state.get(key, "Seleccionar")
    if valor_actual not in opciones:
        valor_actual = "Seleccionar"

    valor = st.selectbox(label, opciones, index=opciones.index(valor_actual), key=f"widget_{key}")
    st.session_state[key] = valor
    return None if valor == "Seleccionar" else valor


def render_topograma_panel():
    _init_topograma_state()
    store = st.session_state["topograma_store"]

    posicion = st.session_state.get("posicion", "")
    entrada = st.session_state.get("entrada", "")
    examen = st.session_state.get("examen", "")

    store["posicion"] = posicion
    store["entrada"] = entrada
    store["examen"] = examen

    st.markdown("#### Datos del examen")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Examen", value=examen, disabled=True)
    with c2:
        st.text_input("Posición", value=posicion, disabled=True)
    with c3:
        st.text_input("Entrada", value=entrada, disabled=True)

    st.markdown("---")
    st.markdown("## Topograma 1")

    a, b, c = st.columns(3)
    with a:
        topo1_pos = _selectbox_placeholder(
            "Posición del tubo",
            ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"],
            "t1pt",
        )
    with b:
        topo1_inicio = _selectbox_placeholder(
            "Centraje inicio de topograma",
            ["Cabeza", "Pies"],
            "t1_inicio_ref",
        )
    with c:
        topo1_long = _selectbox_placeholder(
            "Longitud de topograma (mm)",
            [128, 256, 512, 1024],
            "t1l",
        )

    d, e = st.columns(2)
    with d:
        topo1_dir = _selectbox_placeholder(
            "Dirección topograma",
            ["CRÁNEO-CAUDAL", "CAUDAL-CRÁNEO"],
            "t1dir",
        )
    with e:
        topo1_voz = _selectbox_placeholder(
            "Instrucción de voz",
            ["Inspirar y sostener", "Espirar y sostener", "Respiración libre"],
            "t1vz",
        )

    completos_t1 = all([topo1_pos, topo1_inicio, topo1_long, topo1_dir, topo1_voz])

    if st.button("☢️  INICIAR TOPOGRAMA 1", key="btn_iniciar_topo1", use_container_width=True, disabled=not completos_t1):
        st.session_state["topograma_iniciado"] = True
        store["t1pt"] = topo1_pos
        store["t1_inicio_ref"] = topo1_inicio
        store["t1l"] = topo1_long
        store["t1dir"] = topo1_dir
        store["t1vz"] = topo1_voz

    if st.session_state.get("topograma_iniciado"):
        st.success("Topograma 1 iniciado.")
        if st.button("↺ Repetir topograma 1", key="btn_reset_topo1", use_container_width=True):
            st.session_state["topograma_iniciado"] = False
            st.rerun()

    st.markdown("---")
    aplicar_t2 = st.checkbox("Aplicar Topograma 2", key="aplica_topo2")
    store["aplica_topo2"] = aplicar_t2

    if aplicar_t2:
        st.markdown("## Topograma 2")

        a2, b2, c2 = st.columns(3)
        with a2:
            topo2_pos = _selectbox_placeholder(
                "Posición del tubo",
                ["ARRIBA 0°", "ABAJO 180°", "DERECHA 90°", "IZQUIERDA 90°"],
                "t2pt",
            )
        with b2:
            topo2_inicio = _selectbox_placeholder(
                "Centraje inicio de topograma",
                ["Cabeza", "Pies"],
                "t2_inicio_ref",
            )
        with c2:
            topo2_long = _selectbox_placeholder(
                "Longitud de topograma (mm)",
                [128, 256, 512, 1024],
                "t2l",
            )

        d2, e2 = st.columns(2)
        with d2:
            topo2_dir = _selectbox_placeholder(
                "Dirección topograma",
                ["CRÁNEO-CAUDAL", "CAUDAL-CRÁNEO"],
                "t2dir",
            )
        with e2:
            topo2_voz = _selectbox_placeholder(
                "Instrucción de voz",
                ["Inspirar y sostener", "Espirar y sostener", "Respiración libre"],
                "t2vz",
            )

        completos_t2 = all([topo2_pos, topo2_inicio, topo2_long, topo2_dir, topo2_voz])

        if st.button("☢️  INICIAR TOPOGRAMA 2", key="btn_iniciar_topo2", use_container_width=True, disabled=not completos_t2):
            st.session_state["topograma2_iniciado"] = True
            store["t2pt"] = topo2_pos
            store["t2_inicio_ref"] = topo2_inicio
            store["t2l"] = topo2_long
            store["t2dir"] = topo2_dir
            store["t2vz"] = topo2_voz

        if st.session_state.get("topograma2_iniciado"):
            st.success("Topograma 2 iniciado.")
            if st.button("↺ Repetir topograma 2", key="btn_reset_topo2", use_container_width=True):
                st.session_state["topograma2_iniciado"] = False
                st.rerun()
