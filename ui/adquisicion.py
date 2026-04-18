
import copy
import uuid

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


def _nuevo_id():
    return f"adq_{uuid.uuid4().hex[:8]}"


def _init_adquisicion_state():
    st.session_state.setdefault("exploraciones", [])
    st.session_state.setdefault("exploraciones_adq", [])
    st.session_state.setdefault("exp_activa", "topograma")


def _crear_exploracion_base():
    return {
        "id": _nuevo_id(),
        "tipo": "adquisicion",
        "tipo_item": "adquisicion",
        "nombre": "Seleccionar",
        "tipo_exploracion": "HELICOIDAL",
        "tipo_exp": "HELICOIDAL",
        "modulacion_corriente": "SELECCIONAR",
        "mod_corriente": "SELECCIONAR",
        "mas": "SELECCIONAR",
        "mas_val": "SELECCIONAR",
        "indice_ruido": "SELECCIONAR",
        "kv": "SELECCIONAR",
        "kvp": "SELECCIONAR",
        "doble_muestreo": "SELECCIONAR",
        "config_detectores": "SELECCIONAR",
        "config_det": "SELECCIONAR",
        "cobertura": "",
        "grosor_prospectivo": "SELECCIONAR",
        "grosor_prosp": "SELECCIONAR",
        "sfov": "SELECCIONAR",
        "instruccion_voz": "SELECCIONAR",
        "voz_adq": "SELECCIONAR",
        "retardo": "SELECCIONAR",
        "pitch": "SELECCIONAR",
        "rotacion_tubo": "SELECCIONAR",
        "periodo": "SELECCIONAR",
        "periodo_bolus": "SELECCIONAR",
        "n_imagenes": "SELECCIONAR",
        "n_imagenes_bolus": "SELECCIONAR",
        "posicion_corte": "SELECCIONAR",
        "umbral_disparo": "",
        "inicio_exploracion": "SELECCIONAR",
        "mm_inicio": 0,
        "fin_exploracion": "SELECCIONAR",
        "mm_fin": 400,
        "observaciones": "",
    }


def _asegurar_exploraciones():
    if not st.session_state["exploraciones"]:
        st.session_state["exploraciones"] = [_crear_exploracion_base()]
    _sincronizar_exploraciones()


def _sincronizar_exploraciones():
    for exp in st.session_state.get("exploraciones", []):
        exp.setdefault("id", _nuevo_id())
        exp["tipo"] = "adquisicion"
        exp["tipo_item"] = "adquisicion"
        _ajustar_tipo_segun_nombre(exp)
        _normalizar_aliases(exp)
    st.session_state["exploraciones_adq"] = [copy.deepcopy(e) for e in st.session_state.get("exploraciones", [])]


def _normalizar_aliases(exp):
    exp["tipo_exp"] = exp.get("tipo_exploracion", "HELICOIDAL")
    exp["mod_corriente"] = exp.get("modulacion_corriente", "SELECCIONAR")
    exp["mas_val"] = exp.get("mas", "SELECCIONAR")
    exp["kvp"] = exp.get("kv", "SELECCIONAR")
    exp["config_det"] = exp.get("config_detectores", "SELECCIONAR")
    exp["grosor_prosp"] = exp.get("grosor_prospectivo", "SELECCIONAR")
    exp["voz_adq"] = exp.get("instruccion_voz", "SELECCIONAR")
    exp["periodo_bolus"] = exp.get("periodo", "SELECCIONAR")
    exp["n_imagenes_bolus"] = exp.get("n_imagenes", "SELECCIONAR")


def _selectbox_con_indice(label, options, value, key, label_visibility="visible", disabled=False):
    opciones = list(options)
    idx = opciones.index(value) if value in opciones else 0
    return st.selectbox(
        label,
        opciones,
        index=idx,
        key=key,
        label_visibility=label_visibility,
        disabled=disabled,
    )


def _calcular_cobertura(config_detectores, doble_muestreo):
    if not config_detectores or config_detectores == "SELECCIONAR":
        return "—"
    texto = str(config_detectores).replace(" ", "").replace(",", ".")
    if "x" not in texto:
        return "—"
    try:
        filas_txt, colim_txt = texto.split("x")
        cobertura = float(filas_txt) * float(colim_txt)
        if doble_muestreo == "SI":
            cobertura *= 2
        if float(cobertura).is_integer():
            return f"{int(cobertura)} mm"
        return f"{round(cobertura, 1)} mm"
    except Exception:
        return "—"


def _ajustar_tipo_segun_nombre(exp):
    nombre = exp.get("nombre", "Seleccionar")
    if nombre == "BOLUS TEST":
        exp["tipo_exploracion"] = "TEST BOLUS"
    elif nombre == "BOLUS TRACKING":
        exp["tipo_exploracion"] = "BOLUS TRACKING"
    elif exp.get("tipo_exploracion") in ["TEST BOLUS", "BOLUS TRACKING"] and nombre not in ["BOLUS TEST", "BOLUS TRACKING"]:
        exp["tipo_exploracion"] = "HELICOIDAL"


def _nombre_visible_exploracion(exp, idx):
    nombre = exp.get("nombre", "Seleccionar")
    return f"EXPLORACIÓN {idx + 1}" if not nombre or nombre == "Seleccionar" else str(nombre)


def _topograma_tiene_minimo(store):
    return bool(
        store.get("examen")
        and store.get("t1_posicion_paciente")
        and store.get("t1_entrada_paciente")
        and store.get("t1_posicion_tubo")
    )


def _render_resumen_topograma(store):
    st.markdown("## 📡 Resumen de referencia")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info(f"**Examen**\n\n{store.get('examen') or '-'}")
    with c2:
        st.info(f"**Topograma 1**\n\n{store.get('t1_posicion_paciente') or '-'}")
    with c3:
        st.info(f"**Entrada 1**\n\n{store.get('t1_entrada_paciente') or '-'}")
    with c4:
        st.info(f"**Tubo 1**\n\n{store.get('t1_posicion_tubo') or '-'}")


def _render_lista_exploraciones():
    st.markdown("## 📋 Exploraciones")

    if st.button("📡 Topograma", key="btn_topograma_sidebar", use_container_width=True):
        st.session_state["exp_activa"] = "topograma"

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    for idx, exp in enumerate(st.session_state["exploraciones"]):
        etiqueta = _nombre_visible_exploracion(exp, idx)
        if st.button(f"⚡ {etiqueta}", key=f"btn_sidebar_exp_{exp['id']}", use_container_width=True):
            st.session_state["exp_activa"] = idx

    st.markdown(" ")
    if st.button("➕ Agregar exploración", key="btn_agregar_exploracion", use_container_width=True):
        st.session_state["exploraciones"].append(_crear_exploracion_base())
        st.session_state["exp_activa"] = len(st.session_state["exploraciones"]) - 1
        _sincronizar_exploraciones()
        st.rerun()

    if isinstance(st.session_state.get("exp_activa"), int):
        idx = st.session_state["exp_activa"]
        if 0 <= idx < len(st.session_state["exploraciones"]):
            col1, col2 = st.columns(2, gap="small")
            with col1:
                if st.button("📄 Duplicar", key="btn_duplicar_exp", use_container_width=True):
                    copia = copy.deepcopy(st.session_state["exploraciones"][idx])
                    copia["id"] = _nuevo_id()
                    st.session_state["exploraciones"].insert(idx + 1, copia)
                    st.session_state["exp_activa"] = idx + 1
                    _sincronizar_exploraciones()
                    st.rerun()
            with col2:
                if st.button("🗑️ Eliminar", key="btn_eliminar_exp", use_container_width=True):
                    if len(st.session_state["exploraciones"]) > 1:
                        st.session_state["exploraciones"].pop(idx)
                        st.session_state["exp_activa"] = 0
                        _sincronizar_exploraciones()
                        st.rerun()


def _render_disabled_text(label, value, key):
    st.text_input(label, value=value, disabled=True, key=key)


def _render_adq_pair(col, label, render_fn):
    with col:
        st.markdown(
            f"<div style='font-size:0.9rem; font-weight:600; margin-bottom:0.3rem;'>{label}</div>",
            unsafe_allow_html=True,
        )
        render_fn()


def _render_parametros_normales(exp, idx, store):
    row1_icon, row1_body = st.columns([0.12, 1], gap="small")
    with row1_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:0.8rem;'>☢️</div>", unsafe_allow_html=True)
    with row1_body:
        c1, c2, c3, c4 = st.columns(4, gap="small")
        _render_adq_pair(c1, "MODULACIÓN CORRIENTE", lambda: exp.__setitem__("modulacion_corriente", _selectbox_con_indice("", MODULACION_CORRIENTE, exp.get("modulacion_corriente", "SELECCIONAR"), key=f"modcorr_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c2, "MAS", lambda: exp.__setitem__("mas", _selectbox_con_indice("", MAS_OPCIONES, exp.get("mas", "SELECCIONAR"), key=f"mas_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c3, "ÍNDICE DE RUIDO", lambda: exp.__setitem__("indice_ruido", _selectbox_con_indice("", INDICE_RUIDO_OPCIONES, exp.get("indice_ruido", "SELECCIONAR"), key=f"ruido_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c4, "KV", lambda: exp.__setitem__("kv", _selectbox_con_indice("", KV_OPCIONES, exp.get("kv", "SELECCIONAR"), key=f"kv_{idx}", label_visibility="collapsed")))

    row2_icon, row2_body = st.columns([0.12, 1], gap="small")
    with row2_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:0.8rem;'>⚙️</div>", unsafe_allow_html=True)
    with row2_body:
        c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
        _render_adq_pair(c1, "TIPO EXPLORACIÓN", lambda: exp.__setitem__("tipo_exploracion", _selectbox_con_indice("", TIPOS_EXPLORACION, exp.get("tipo_exploracion", "HELICOIDAL"), key=f"tipo_exp_{idx}", label_visibility="collapsed")))
        if exp.get("tipo_exploracion") == "HELICOIDAL":
            _render_adq_pair(c2, "DOBLE MUESTREO", lambda: exp.__setitem__("doble_muestreo", _selectbox_con_indice("", DOBLE_MUESTREO_OPCIONES, exp.get("doble_muestreo", "SELECCIONAR"), key=f"doble_{idx}", label_visibility="collapsed")))
        else:
            exp["doble_muestreo"] = "NO"
            _render_adq_pair(c2, "DOBLE MUESTREO", lambda: _render_disabled_text("", "No aplica", key=f"doble_na_{idx}"))
        _render_adq_pair(c3, "CONF. DETECCIÓN", lambda: exp.__setitem__("config_detectores", _selectbox_con_indice("", CONFIG_DETECTORES, exp.get("config_detectores", "SELECCIONAR"), key=f"config_{idx}", label_visibility="collapsed")))
        exp["cobertura"] = _calcular_cobertura(exp.get("config_detectores"), exp.get("doble_muestreo"))
        _render_adq_pair(c4, "COBERTURA", lambda: _render_disabled_text("", exp.get("cobertura", "—"), key=f"cobertura_{idx}"))
        _render_adq_pair(c5, "GROSOR PROSP.", lambda: exp.__setitem__("grosor_prospectivo", _selectbox_con_indice("", GROSOR_PROSPECTIVO_OPCIONES, exp.get("grosor_prospectivo", "SELECCIONAR"), key=f"grosor_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c6, "SFOV", lambda: exp.__setitem__("sfov", _selectbox_con_indice("", SFOV_OPCIONES, exp.get("sfov", "SELECCIONAR"), key=f"sfov_{idx}", label_visibility="collapsed")))

    row3_icon, row3_body = st.columns([0.12, 1], gap="small")
    with row3_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:0.8rem;'>🕒</div>", unsafe_allow_html=True)
    with row3_body:
        c1, c2, c3, c4 = st.columns(4, gap="small")
        _render_adq_pair(c1, "INSTRUCCIÓN DE VOZ", lambda: exp.__setitem__("instruccion_voz", _selectbox_con_indice("", INSTRUCCION_VOZ_OPCIONES, exp.get("instruccion_voz", "SELECCIONAR"), key=f"voz_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c2, "RETARDO", lambda: exp.__setitem__("retardo", _selectbox_con_indice("", RETARDO_OPCIONES, exp.get("retardo", "SELECCIONAR"), key=f"retardo_{idx}", label_visibility="collapsed")))
        if exp.get("tipo_exploracion") == "HELICOIDAL":
            _render_adq_pair(c3, "PITCH", lambda: exp.__setitem__("pitch", _selectbox_con_indice("", PITCH_OPCIONES, exp.get("pitch", "SELECCIONAR"), key=f"pitch_{idx}", label_visibility="collapsed")))
        else:
            exp["pitch"] = "1"
            _render_adq_pair(c3, "PITCH", lambda: _render_disabled_text("", "No aplica", key=f"pitch_na_{idx}"))
        _render_adq_pair(c4, "TPO ROTACION TUBO", lambda: exp.__setitem__("rotacion_tubo", _selectbox_con_indice("", ROTACION_TUBO_OPCIONES, exp.get("rotacion_tubo", "SELECCIONAR"), key=f"rot_{idx}", label_visibility="collapsed")))

    row4_icon, row4_body = st.columns([0.12, 1], gap="small")
    with row4_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:0.8rem;'>📏</div>", unsafe_allow_html=True)
    with row4_body:
        c1, c2, c3, c4 = st.columns([1.2, 0.8, 1.2, 0.8], gap="small")
        referencias = [
            "VERTEX", "GLABELA", "ORBITAS", "MAXILAR", "MENTON", "CUELLO",
            "CLAVICULAS", "CARINA", "CUPULAS DIAFRAGMATICAS", "XIFOIDES",
            "CRESTAS ILIACAS", "SINFISIS PUBICA", "RODILLAS", "TOBILLOS", "PLANTAS"
        ]
        _render_adq_pair(c1, "INICIO EXPLORACIÓN", lambda: exp.__setitem__("inicio_exploracion", _selectbox_con_indice("", ["SELECCIONAR"] + referencias, exp.get("inicio_exploracion", "SELECCIONAR"), key=f"inicio_ref_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c2, "MM INICIO", lambda: exp.__setitem__("mm_inicio", st.number_input("", min_value=-1000, max_value=2000, value=int(exp.get("mm_inicio", 0)), step=1, key=f"mm_inicio_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c3, "FIN EXPLORACIÓN", lambda: exp.__setitem__("fin_exploracion", _selectbox_con_indice("", ["SELECCIONAR"] + referencias, exp.get("fin_exploracion", "SELECCIONAR"), key=f"fin_ref_{idx}", label_visibility="collapsed")))
        _render_adq_pair(c4, "MM FIN", lambda: exp.__setitem__("mm_fin", st.number_input("", min_value=-1000, max_value=2000, value=int(exp.get("mm_fin", 400)), step=1, key=f"mm_fin_{idx}", label_visibility="collapsed")))

    with st.container():
        exp["observaciones"] = st.text_area(
            "Observaciones",
            value=exp.get("observaciones", ""),
            key=f"obs_{idx}",
            height=100,
        )


def _render_parametros_bolus(exp, idx):
    exp["kv"] = "100"
    exp["mas"] = "20"

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### ⚙️ Parámetros de Bolus")
        exp["periodo"] = _selectbox_con_indice("Periodo", PERIODO_TEST_BOLUS, exp.get("periodo", "SELECCIONAR"), key=f"periodo_{idx}")
        exp["n_imagenes"] = _selectbox_con_indice("N° de imágenes", N_IMAGENES_TEST_BOLUS, exp.get("n_imagenes", "SELECCIONAR"), key=f"nimg_{idx}")
        exp["posicion_corte"] = _selectbox_con_indice("Posición de corte", POSICION_CORTE_TEST_BOLUS, exp.get("posicion_corte", "SELECCIONAR"), key=f"poscorte_{idx}")
        if exp.get("tipo_exploracion") == "BOLUS TRACKING":
            exp["umbral_disparo"] = st.text_input("Umbral de disparo (UH)", value=exp.get("umbral_disparo", ""), key=f"umbral_{idx}")
    with col2:
        st.markdown("### 🔧 Configuración fija")
        st.text_input("kV", value="100", key=f"kv_bolus_{idx}", disabled=True)
        st.text_input("mAs", value="20", key=f"mas_bolus_{idx}", disabled=True)
        st.info("En Test bolus y Bolus tracking estos valores quedan fijos.")

    with st.container():
        exp["observaciones"] = st.text_area(
            "Observaciones",
            value=exp.get("observaciones", ""),
            key=f"obs_{idx}",
            height=100,
        )


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
            disabled=exp.get("nombre") in ["BOLUS TEST", "BOLUS TRACKING"],
        )

    es_bolus = exp.get("tipo_exploracion") in ["TEST BOLUS", "BOLUS TRACKING"]
    if es_bolus:
        _render_parametros_bolus(exp, idx)
    else:
        _render_parametros_normales(exp, idx, store)

    mensajes = []
    if exp.get("nombre") == "Seleccionar":
        mensajes.append("⚠️ Falta seleccionar el nombre de la exploración.")
    if es_bolus:
        if exp.get("posicion_corte") == "SELECCIONAR":
            mensajes.append("⚠️ Falta definir la posición de corte.")
    else:
        if exp.get("kv") == "SELECCIONAR":
            mensajes.append("⚠️ Falta seleccionar kV.")
        if exp.get("config_detectores") == "SELECCIONAR":
            mensajes.append("⚠️ Falta seleccionar configuración de detectores.")
        if exp.get("instruccion_voz") == "SELECCIONAR":
            mensajes.append("⚠️ Falta definir la instrucción de voz.")

    _normalizar_aliases(exp)
    _sincronizar_exploraciones()

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
            return

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
