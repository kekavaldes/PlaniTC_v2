import streamlit as st

from ui.topograma import render_topograma_panel


NOMBRES_EXPLORACION = [
    "Seleccionar",
    "SIN CONTRASTE",
    "ARTERIAL",
    "ANGIOGRÁFICA",
    "BOLUS TEST",
    "BOLUS TRACKING",
    "VENOSA",
    "TARDÍA",
]

TIPOS_EXPLORACION = [
    "HELICOIDAL",
    "SECUENCIAL",
    "VOLUMETRICA",
    "TEST BOLUS",
    "BOLUS TRACKING",
]

MODULACION_CORRIENTE = [
    "SELECCIONAR",
    "NO",
    "CARE DOSE",
    "AUTOMATICA",
]

MAS_OPCIONES = [
    "SELECCIONAR",
    "40",
    "50",
    "80",
    "100",
    "120",
    "150",
    "180",
    "200",
    "220",
    "250",
    "300",
]

INDICE_RUIDO_OPCIONES = [
    "SELECCIONAR",
    "6",
    "8",
    "10",
    "12",
    "14",
    "16",
    "18",
    "20",
]

KV_OPCIONES = [
    "SELECCIONAR",
    "80",
    "100",
    "110",
    "120",
    "130",
    "140",
]

DOBLE_MUESTREO_OPCIONES = [
    "SELECCIONAR",
    "NO",
    "SI",
]

CONFIG_DETECTORES = [
    "SELECCIONAR",
    "16 x 0,6",
    "16 x 1,2",
    "32 x 0,6",
    "32 x 1,2",
    "64 x 0,6",
    "64 x 1,2",
    "80 x 0,6",
    "80 x 1,2",
    "128 x 0,6",
]

GROSOR_PROSPECTIVO_OPCIONES = [
    "SELECCIONAR",
    "0,6",
    "0,75",
    "1",
    "1,2",
    "1,5",
    "2",
    "3",
    "5",
]

SFOV_OPCIONES = [
    "SELECCIONAR",
    "CABEZA",
    "CUELLO",
    "PEQUEÑO",
    "MEDIANO",
    "GRANDE",
    "MAXIMO",
]

INSTRUCCION_VOZ_OPCIONES = [
    "SELECCIONAR",
    "NINGUNA",
    "INSPIRACIÓN",
    "ESPIRACIÓN",
    "NO TRAGAR",
    "VALSALVA",
    "NO RESPIRE",
]

RETARDO_OPCIONES = [
    "SELECCIONAR",
    "0 sg",
    "2 sg",
    "3 sg",
    "4 sg",
    "5 sg",
    "6 sg",
    "8 sg",
    "10 sg",
    "12 sg",
    "15 sg",
    "20 sg",
    "25 sg",
    "30 sg",
]

PITCH_OPCIONES = [
    "SELECCIONAR",
    "0,5",
    "0,6",
    "0,8",
    "1",
    "1,2",
    "1,5",
    "1,8",
]

ROTACION_TUBO_OPCIONES = [
    "SELECCIONAR",
    "0,25 sg.",
    "0,28 sg.",
    "0,33 sg.",
    "0,35 sg.",
    "0,5 sg.",
    "0,75 sg.",
    "1 sg.",
]

PERIODO_TEST_BOLUS = [
    "SELECCIONAR",
    "0,9 sg",
    "1 sg",
    "1,5 sg",
    "2 sg",
]

N_IMAGENES_TEST_BOLUS = [
    "SELECCIONAR",
    "10",
    "15",
    "20",
    "25",
    "30",
]

POSICION_CORTE_TEST_BOLUS = [
    "SELECCIONAR",
    "BOTON AORTICO",
    "BAJO CARINA",
]


def _init_adquisicion_state():
    if "exploraciones" not in st.session_state:
        st.session_state["exploraciones"] = []

    if "exp_activa" not in st.session_state:
        st.session_state["exp_activa"] = "topograma"


def _crear_exploracion_base():
    return {
        "nombre": "Seleccionar",
        "tipo_item": "adquisicion",
        "tipo_exploracion": "HELICOIDAL",
        "modulacion_corriente": "SELECCIONAR",
        "mas": "SELECCIONAR",
        "indice_ruido": "SELECCIONAR",
        "kv": "SELECCIONAR",
        "doble_muestreo": "SELECCIONAR",
        "config_detectores": "SELECCIONAR",
        "cobertura": "",
        "grosor_prospectivo": "SELECCIONAR",
        "sfov": "SELECCIONAR",
        "instruccion_voz": "SELECCIONAR",
        "retardo": "SELECCIONAR",
        "pitch": "SELECCIONAR",
        "rotacion_tubo": "SELECCIONAR",
        "periodo": "SELECCIONAR",
        "n_imagenes": "SELECCIONAR",
        "posicion_corte": "SELECCIONAR",
        "observaciones": "",
    }


def _asegurar_exploraciones():
    if st.session_state["exploraciones"]:
        return
    st.session_state["exploraciones"] = [_crear_exploracion_base()]


def _calcular_cobertura(config_detectores, doble_muestreo):
    if not config_detectores or config_detectores == "SELECCIONAR":
        return ""

    texto = config_detectores.replace(" ", "").replace(",", ".")
    if "x" not in texto:
        return ""

    try:
        filas_txt, colim_txt = texto.split("x")
        filas = float(filas_txt)
        colim = float(colim_txt)
        cobertura = filas * colim

        if doble_muestreo == "SI":
            cobertura *= 2

        if cobertura.is_integer():
            return f"{int(cobertura)} mm"
        return f"{round(cobertura, 1)} mm"
    except Exception:
        return ""


def _selectbox_con_indice(label, options, actual, key):
    index = options.index(actual) if actual in options else 0
    return st.selectbox(label, options, index=index, key=key)


def _topograma_tiene_minimo(store):
    return bool(
        store.get("examen")
        and store.get("t1_posicion_paciente")
        and store.get("t1_entrada_paciente")
        and store.get("t1_posicion_tubo")
    )


def _nombre_visible_exploracion(exp, idx):
    nombre = exp.get("nombre", "Seleccionar")
    if not nombre or nombre == "Seleccionar":
        return f"EXPLORACIÓN {idx + 1}"
    return nombre


def _render_lista_exploraciones():
    st.markdown("### 📋 Exploraciones")

    if st.button("📡 Topograma", key="btn_topograma_sidebar", use_container_width=True):
        st.session_state["exp_activa"] = "topograma"

    st.markdown(
        """
        <div style="height:10px"></div>
        """,
        unsafe_allow_html=True,
    )

    for idx, exp in enumerate(st.session_state["exploraciones"]):
        etiqueta = _nombre_visible_exploracion(exp, idx)
        if st.button(f"⚡ {etiqueta}", key=f"btn_sidebar_exp_{idx}", use_container_width=True):
            st.session_state["exp_activa"] = idx

    st.markdown(" ")
    if st.button("➕ Agregar exploración", key="btn_agregar_exploracion", use_container_width=True):
        st.session_state["exploraciones"].append(_crear_exploracion_base())
        st.session_state["exp_activa"] = len(st.session_state["exploraciones"]) - 1
        st.rerun()

    if isinstance(st.session_state.get("exp_activa"), int):
        idx = st.session_state["exp_activa"]
        if 0 <= idx < len(st.session_state["exploraciones"]):
            col1, col2 = st.columns(2, gap="small")

            with col1:
                if st.button("📄 Duplicar", key="btn_duplicar_exp", use_container_width=True):
                    copia = dict(st.session_state["exploraciones"][idx])
                    st.session_state["exploraciones"].insert(idx + 1, copia)
                    st.session_state["exp_activa"] = idx + 1
                    st.rerun()

            with col2:
                if st.button("🗑️ Eliminar", key="btn_eliminar_exp", use_container_width=True):
                    if len(st.session_state["exploraciones"]) > 1:
                        st.session_state["exploraciones"].pop(idx)
                        st.session_state["exp_activa"] = 0
                        st.rerun()


def _render_resumen_topograma(store):
    st.markdown("### 📡 Resumen de referencia")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info(f"**Examen**\n\n{store.get('examen') or '-'}")
    with c2:
        st.info(f"**Topograma 1**\n\n{store.get('t1_posicion_paciente') or '-'}")
    with c3:
        st.info(f"**Entrada 1**\n\n{store.get('t1_entrada_paciente') or '-'}")
    with c4:
        st.info(f"**Tubo 1**\n\n{store.get('t1_posicion_tubo') or '-'}")

    if store.get("aplica_topograma_2"):
        st.success(
            "Topograma 2 activo: "
            f"{store.get('t2_posicion_paciente') or '-'} · "
            f"{store.get('t2_entrada_paciente') or '-'} · "
            f"{store.get('t2_posicion_tubo') or '-'}"
        )


def _ajustar_tipo_segun_nombre(exp):
    nombre = exp.get("nombre", "Seleccionar")

    if nombre == "BOLUS TEST":
        exp["tipo_exploracion"] = "TEST BOLUS"
    elif nombre == "BOLUS TRACKING":
        exp["tipo_exploracion"] = "BOLUS TRACKING"
    elif exp.get("tipo_exploracion") in ["TEST BOLUS", "BOLUS TRACKING"] and nombre not in ["BOLUS TEST", "BOLUS TRACKING"]:
        exp["tipo_exploracion"] = "HELICOIDAL"


def _render_parametros_adquisicion(exp, idx, store):
    titulo = _nombre_visible_exploracion(exp, idx)
    st.markdown(f"## ⚙️ {titulo}")

    row_head = st.columns([2, 1], gap="medium")
    with row_head[0]:
        exp["nombre"] = _selectbox_con_indice(
            "Nombre de la exploración",
            NOMBRES_EXPLORACION,
            exp.get("nombre", "Seleccionar"),
            key=f"nombre_exp_{idx}",
        )

    _ajustar_tipo_segun_nombre(exp)

    with row_head[1]:
        exp["tipo_exploracion"] = _selectbox_con_indice(
            "Tipo exploración",
            TIPOS_EXPLORACION,
            exp.get("tipo_exploracion", "HELICOIDAL"),
            key=f"tipo_exp_{idx}",
        )

    row1 = st.columns(4, gap="medium")
    with row1[0]:
        exp["modulacion_corriente"] = _selectbox_con_indice(
            "Modulación de corriente",
            MODULACION_CORRIENTE,
            exp.get("modulacion_corriente", "SELECCIONAR"),
            key=f"modcorr_{idx}",
        )
    with row1[1]:
        exp["mas"] = _selectbox_con_indice(
            "mAs",
            MAS_OPCIONES,
            exp.get("mas", "SELECCIONAR"),
            key=f"mas_{idx}",
        )
    with row1[2]:
        exp["indice_ruido"] = _selectbox_con_indice(
            "Índice de ruido",
            INDICE_RUIDO_OPCIONES,
            exp.get("indice_ruido", "SELECCIONAR"),
            key=f"ruido_{idx}",
        )
    with row1[3]:
        exp["kv"] = _selectbox_con_indice(
            "kV",
            KV_OPCIONES,
            exp.get("kv", "SELECCIONAR"),
            key=f"kv_{idx}",
        )

    row2 = st.columns(6, gap="medium")
    with row2[0]:
        exp["doble_muestreo"] = _selectbox_con_indice(
            "Doble muestreo",
            DOBLE_MUESTREO_OPCIONES,
            exp.get("doble_muestreo", "SELECCIONAR"),
            key=f"doble_{idx}",
        )
    with row2[1]:
        exp["config_detectores"] = _selectbox_con_indice(
            "Configuración detección",
            CONFIG_DETECTORES,
            exp.get("config_detectores", "SELECCIONAR"),
            key=f"config_{idx}",
        )

    exp["cobertura"] = _calcular_cobertura(exp.get("config_detectores"), exp.get("doble_muestreo"))

    with row2[2]:
        st.text_input(
            "Cobertura",
            value=exp.get("cobertura", ""),
            disabled=True,
            key=f"cobertura_{idx}",
        )
    with row2[3]:
        exp["grosor_prospectivo"] = _selectbox_con_indice(
            "Grosor prospectivo",
            GROSOR_PROSPECTIVO_OPCIONES,
            exp.get("grosor_prospectivo", "SELECCIONAR"),
            key=f"grosor_{idx}",
        )
    with row2[4]:
        exp["sfov"] = _selectbox_con_indice(
            "SFOV",
            SFOV_OPCIONES,
            exp.get("sfov", "SELECCIONAR"),
            key=f"sfov_{idx}",
        )
    with row2[5]:
        st.info(store.get("examen") or "-")

    tipo = exp.get("tipo_exploracion")

    if tipo in ["TEST BOLUS", "BOLUS TRACKING"]:
        row3 = st.columns(3, gap="medium")
        with row3[0]:
            exp["periodo"] = _selectbox_con_indice(
                "Periodo",
                PERIODO_TEST_BOLUS,
                exp.get("periodo", "SELECCIONAR"),
                key=f"periodo_{idx}",
            )
        with row3[1]:
            exp["n_imagenes"] = _selectbox_con_indice(
                "N° de imágenes",
                N_IMAGENES_TEST_BOLUS,
                exp.get("n_imagenes", "SELECCIONAR"),
                key=f"nimg_{idx}",
            )
        with row3[2]:
            exp["posicion_corte"] = _selectbox_con_indice(
                "Posición de corte",
                POSICION_CORTE_TEST_BOLUS,
                exp.get("posicion_corte", "SELECCIONAR"),
                key=f"poscorte_{idx}",
            )
    else:
        row3 = st.columns(4, gap="medium")
        with row3[0]:
            exp["instruccion_voz"] = _selectbox_con_indice(
                "Instrucción de voz",
                INSTRUCCION_VOZ_OPCIONES,
                exp.get("instruccion_voz", "SELECCIONAR"),
                key=f"voz_{idx}",
            )
        with row3[1]:
            exp["retardo"] = _selectbox_con_indice(
                "Retardo",
                RETARDO_OPCIONES,
                exp.get("retardo", "SELECCIONAR"),
                key=f"retardo_{idx}",
            )
        with row3[2]:
            exp["pitch"] = _selectbox_con_indice(
                "Pitch",
                PITCH_OPCIONES,
                exp.get("pitch", "SELECCIONAR"),
                key=f"pitch_{idx}",
            )
        with row3[3]:
            exp["rotacion_tubo"] = _selectbox_con_indice(
                "TPO ROTACION TUBO",
                ROTACION_TUBO_OPCIONES,
                exp.get("rotacion_tubo", "SELECCIONAR"),
                key=f"rot_{idx}",
            )

    exp["observaciones"] = st.text_area(
        "Observaciones",
        value=exp.get("observaciones", ""),
        key=f"obs_{idx}",
        height=100,
    )

    mensajes = []

    if exp.get("nombre") == "Seleccionar":
        mensajes.append("⚠️ Falta seleccionar el nombre de la exploración.")
    if exp.get("kv") == "SELECCIONAR":
        mensajes.append("⚠️ Falta seleccionar kV.")
    if exp.get("config_detectores") == "SELECCIONAR":
        mensajes.append("⚠️ Falta seleccionar configuración de detectores.")
    if tipo not in ["TEST BOLUS", "BOLUS TRACKING"] and exp.get("instruccion_voz") == "SELECCIONAR":
        mensajes.append("⚠️ Falta definir la instrucción de voz.")
    if tipo in ["TEST BOLUS", "BOLUS TRACKING"] and exp.get("posicion_corte") == "SELECCIONAR":
        mensajes.append("⚠️ Falta definir la posición de corte.")

    if mensajes:
        for msg in mensajes:
            st.warning(msg)
    else:
        st.success("Configuración lista para continuar.")

    with st.container(border=True):
        st.markdown("### 🖼️ Imagen simulada")
        st.caption("Aquí irá la imagen simulada de esta adquisición en el siguiente paso.")


def render_adquisicion():
    _init_adquisicion_state()
    _asegurar_exploraciones()

    col_sidebar, col_main = st.columns([1.05, 4.8], gap="large")

    with col_sidebar:
        _render_lista_exploraciones()

    with col_main:
        activa = st.session_state.get("exp_activa", "topograma")

        if activa == "topograma":
            render_topograma_panel()
        else:
            store = st.session_state.get("topograma_store", {})

            if not _topograma_tiene_minimo(store):
                st.warning("Primero debes completar al menos el Topograma 1.")
                render_topograma_panel()
                return

            _render_resumen_topograma(store)

            exploraciones = st.session_state["exploraciones"]
            if not isinstance(activa, int) or activa >= len(exploraciones):
                st.session_state["exp_activa"] = 0
                activa = 0

            exp = exploraciones[activa]
            _render_parametros_adquisicion(exp, activa, store)
