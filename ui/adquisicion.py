import streamlit as st

from ui.topograma import render_topograma_panel


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
        st.session_state["exp_activa"] = 0


def _topograma_listo(store):
    if not store:
        return False
    return bool(store.get("t1_longitud") and store.get("t1_direccion") and store.get("t1_voz"))


def _crear_exploracion_base(nombre="Sin contraste"):
    return {
        "nombre": nombre,
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


def _asegurar_exploraciones_desde_topograma(store):
    exploraciones = st.session_state["exploraciones"]
    if exploraciones:
        return

    exploraciones.append(
        {
            "nombre": "Topograma",
            "tipo_item": "topograma",
        }
    )

    nombre_inicial = "Sin contraste"
    examen = (store.get("examen") or "").upper()

    if "ATC" in examen or "ANGIO" in examen:
        nombre_inicial = "Fase angiográfica"

    exploraciones.append(_crear_exploracion_base(nombre_inicial))


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
    if actual in options:
        index = options.index(actual)
    else:
        index = 0
    return st.selectbox(label, options, index=index, key=key)


def _render_resumen_topograma(store):
    st.markdown("### 📡 Referencia del Topograma")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**Examen**\n\n{store.get('examen') or '-'}")
    with col2:
        st.info(f"**Posición**\n\n{store.get('posicion_paciente') or '-'}")
    with col3:
        st.info(f"**Entrada**\n\n{store.get('entrada_paciente') or '-'}")
    with col4:
        st.info(f"**Tubo**\n\n{store.get('posicion_tubo') or '-'}")

    aplica_t2 = store.get("aplica_topograma_2", False)

    resumen = []
    if store.get("t1_longitud"):
        resumen.append(
            f"Topograma 1: {store.get('t1_longitud')} mm · {store.get('t1_direccion')} · {store.get('t1_voz')}"
        )

    if aplica_t2 and store.get("t2_longitud"):
        resumen.append(
            f"Topograma 2: {store.get('t2_longitud')} mm · {store.get('t2_direccion')} · {store.get('t2_voz')}"
        )

    if resumen:
        st.success(" | ".join(resumen))
    else:
        st.warning("Aún no hay datos completos de topograma para usar como referencia.")


def _render_lista_exploraciones():
    exploraciones = st.session_state["exploraciones"]

    st.markdown("### 🧾 Exploraciones")

    for i, exp in enumerate(exploraciones):
        nombre = exp.get("nombre", f"Exploración {i}")
        icono = "📡" if exp.get("tipo_item") == "topograma" else "⚙️"
        activo = st.session_state.get("exp_activa", 0) == i
        etiqueta = f"{icono} {nombre}"
        if activo:
            etiqueta = f"➡️ {etiqueta}"

        if st.button(etiqueta, key=f"btn_exp_{i}", use_container_width=True):
            st.session_state["exp_activa"] = i

    st.markdown(" ")

    if st.button("➕ Agregar exploración", key="btn_agregar_exploracion", use_container_width=True):
        n = len([e for e in exploraciones if e.get("tipo_item") == "adquisicion"]) + 1
        exploraciones.append(_crear_exploracion_base(f"Exploración {n}"))
        st.session_state["exp_activa"] = len(exploraciones) - 1
        st.rerun()


def _render_panel_topograma(store):
    st.markdown("### ⚙️ Topograma")
    st.info("Esta exploración corresponde al topograma ya programado.")

    tabla = {
        "Examen": store.get("examen") or "-",
        "Posición paciente": store.get("posicion_paciente") or "-",
        "Entrada": store.get("entrada_paciente") or "-",
        "Posición tubo": store.get("posicion_tubo") or "-",
        "Topograma 1": f"{store.get('t1_longitud') or '-'} · {store.get('t1_direccion') or '-'} · {store.get('t1_voz') or '-'}",
        "Topograma 2": (
            f"{store.get('t2_longitud') or '-'} · {store.get('t2_direccion') or '-'} · {store.get('t2_voz') or '-'}"
            if store.get("aplica_topograma_2")
            else "No aplica"
        ),
    }

    for k, v in tabla.items():
        st.write(f"**{k}:** {v}")


def _render_parametros_bloque_general(exp, idx):
    st.markdown("### ⚙️ Parámetros de adquisición")

    row1 = st.columns(4, gap="medium")
    with row1[0]:
        exp["modulacion_corriente"] = _selectbox_con_indice(
            "Modulación de corriente",
            MODULACION_CORRIENTE,
            exp.get("modulacion_corriente", "SELECCIONAR"),
            key=f"mod_corr_{idx}",
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
        exp["tipo_exploracion"] = _selectbox_con_indice(
            "Tipo exploración",
            TIPOS_EXPLORACION,
            exp.get("tipo_exploracion", "HELICOIDAL"),
            key=f"tipo_exp_{idx}",
        )
    with row2[1]:
        exp["doble_muestreo"] = _selectbox_con_indice(
            "Doble muestreo",
            DOBLE_MUESTREO_OPCIONES,
            exp.get("doble_muestreo", "SELECCIONAR"),
            key=f"doble_{idx}",
        )
    with row2[2]:
        exp["config_detectores"] = _selectbox_con_indice(
            "Configuración detección",
            CONFIG_DETECTORES,
            exp.get("config_detectores", "SELECCIONAR"),
            key=f"config_{idx}",
        )

    exp["cobertura"] = _calcular_cobertura(exp.get("config_detectores"), exp.get("doble_muestreo"))

    with row2[3]:
        st.text_input(
            "Cobertura",
            value=exp.get("cobertura", ""),
            disabled=True,
            key=f"cobertura_{idx}",
        )
    with row2[4]:
        exp["grosor_prospectivo"] = _selectbox_con_indice(
            "Grosor prospectivo",
            GROSOR_PROSPECTIVO_OPCIONES,
            exp.get("grosor_prospectivo", "SELECCIONAR"),
            key=f"grosor_{idx}",
        )
    with row2[5]:
        exp["sfov"] = _selectbox_con_indice(
            "SFOV",
            SFOV_OPCIONES,
            exp.get("sfov", "SELECCIONAR"),
            key=f"sfov_{idx}",
        )

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


def _render_bloque_superior_exploracion(exp, idx, store):
    row0 = st.columns([2, 1], gap="medium")
    with row0[0]:
        exp["nombre"] = st.text_input(
            "Nombre de la exploración",
            value=exp.get("nombre", f"Exploración {idx}"),
            key=f"nombre_exp_{idx}",
        )
    with row0[1]:
        examen = store.get("examen", "")
        sugerido = "HELICOIDAL"
        if "ATC" in examen or "ANGIO" in examen:
            sugerido = "HELICOIDAL"
        exp["tipo_exploracion"] = _selectbox_con_indice(
            "Tipo exploración",
            TIPOS_EXPLORACION,
            exp.get("tipo_exploracion", sugerido),
            key=f"tipo_exp_header_{idx}",
        )


def _render_validaciones(exp, store):
    st.markdown("### 🔎 Validación")

    mensajes = []

    cobertura_texto = exp.get("cobertura", "")
    t1_longitud = store.get("t1_longitud")
    tipo = exp.get("tipo_exploracion")

    if t1_longitud and cobertura_texto:
        try:
            cobertura_valor = float(cobertura_texto.replace(" mm", "").replace(",", "."))
            if cobertura_valor < float(t1_longitud):
                mensajes.append(
                    f"⚠️ La cobertura calculada ({cobertura_texto}) es menor que la longitud del topograma 1 ({t1_longitud} mm)."
                )
        except Exception:
            pass

    if tipo not in ["TEST BOLUS", "BOLUS TRACKING"]:
        if exp.get("instruccion_voz") == "SELECCIONAR":
            mensajes.append("⚠️ Falta definir la instrucción de voz.")
        if exp.get("pitch") in ["1,8"]:
            mensajes.append("⚠️ Pitch alto. Revisa si es adecuado para este estudio.")
        if exp.get("kv") == "SELECCIONAR":
            mensajes.append("⚠️ Falta seleccionar kV.")
        if exp.get("config_detectores") == "SELECCIONAR":
            mensajes.append("⚠️ Falta seleccionar configuración de detectores.")
    else:
        if exp.get("posicion_corte") == "SELECCIONAR":
            mensajes.append("⚠️ Debes definir la posición de corte.")
        if exp.get("n_imagenes") == "SELECCIONAR":
            mensajes.append("⚠️ Debes definir el número de imágenes.")

    if mensajes:
        for msg in mensajes:
            st.warning(msg)
    else:
        st.success("Configuración coherente para continuar.")


def _render_imagen_simulada_placeholder(exp):
    st.markdown("### 🖼️ Imagen simulada")
    tipo = exp.get("tipo_exploracion", "")

    with st.container(border=True):
        if tipo in ["TEST BOLUS", "BOLUS TRACKING"]:
            st.caption("Aquí irá la imagen de posición de corte / ROI en una siguiente etapa.")
        else:
            st.caption("Aquí irá la imagen simulada de la adquisición en una siguiente etapa.")


def _render_panel_exploracion(exp, idx, store):
    st.markdown(f"## ⚙️ {exp.get('nombre', f'Exploración {idx}')}")
    _render_bloque_superior_exploracion(exp, idx, store)
    _render_parametros_bloque_general(exp, idx)

    exp["observaciones"] = st.text_area(
        "Observaciones",
        value=exp.get("observaciones", ""),
        key=f"obs_{idx}",
        height=90,
    )

    _render_validaciones(exp, store)
    _render_imagen_simulada_placeholder(exp)


def render_adquisicion():
    _init_adquisicion_state()

    store = render_topograma_panel()

    st.markdown("---")
    st.markdown("# Adquisición real")

    if not _topograma_listo(store):
        st.warning("Primero debes completar al menos el Topograma 1 para continuar con la adquisición.")
        return

    _render_resumen_topograma(store)
    _asegurar_exploraciones_desde_topograma(store)

    col_lista, col_panel = st.columns([1, 3], gap="large")

    with col_lista:
        _render_lista_exploraciones()

    with col_panel:
        exploraciones = st.session_state["exploraciones"]
        idx = st.session_state.get("exp_activa", 0)

        if idx >= len(exploraciones):
            idx = 0
            st.session_state["exp_activa"] = 0

        exp = exploraciones[idx]

        if exp.get("tipo_item") == "topograma":
            _render_panel_topograma(store)
        else:
            _render_panel_exploracion(exp, idx, store)
