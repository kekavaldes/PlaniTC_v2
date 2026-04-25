"""
Módulo de Ingreso del paciente para PlaniTC_v2.
"""

from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGEN_INGRESO_PATH = BASE_DIR / "data" / "images" / "portada_ingreso.png"


def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    opciones = ["Seleccionar"] + list(options)
    if value in options:
        idx = opciones.index(value)
    else:
        idx = 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    return None if val == "Seleccionar" else val


def _safe_float(value, default=1.0):
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value, default=70):
    try:
        if value in (None, ""):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _panel_header(emoji: str, titulo: str):
    st.markdown(
        f"""
        <div style="
            background:#1A1A1A;
            border:1px solid #2E2E2E;
            border-radius:10px;
            padding:0.75rem 1rem;
            margin-bottom:0.9rem;
            display:flex;
            align-items:center;
            gap:0.55rem;
            font-weight:600;
            font-size:1rem;
            color:#FFFFFF;
        ">
            <span style="font-size:1.15rem;">{emoji}</span>
            <span>{titulo}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_imagen_ingreso():
    if not IMAGEN_INGRESO_PATH.exists():
        return
    try:
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            st.image(
                str(IMAGEN_INGRESO_PATH),
                use_container_width=False,
                width=380,
            )
    except Exception:
        pass


def _build_store(**kwargs):
    prev = st.session_state.get("ingreso_store", {})
    prev.update(kwargs)
    st.session_state["ingreso_store"] = prev


def _restore_widget_value(key, value):
    """
    Restaura el valor del widget desde ingreso_store cada vez que la pestaña se vuelve a cargar.
    """
    if key not in st.session_state or st.session_state.get(key) in (None, ""):
        st.session_state[key] = value


def _init_session_state():
    store = st.session_state.get("ingreso_store", {})

    _restore_widget_value("nombre_paciente_widget", store.get("nombre", ""))
    _restore_widget_value("edad_widget", _safe_int(store.get("edad", 0), 0))
    _restore_widget_value("edad_unidad_widget", store.get("edad_unidad", "Años"))
    _restore_widget_value("diagnostico_widget", store.get("diagnostico", ""))
    _restore_widget_value("peso_widget", _safe_int(store.get("peso", 70), 70))

    # Campo general de sexo del paciente.
    # Fallback a sexo_clearance para compatibilidad con versiones anteriores.
    sexo_guardado = store.get("sexo_paciente") or store.get("sexo") or store.get("sexo_clearance")
    _restore_widget_value("sexo_paciente_widget", sexo_guardado)

    _restore_widget_value("embarazo_widget", store.get("embarazo"))
    _restore_widget_value("requiere_creatinina_widget", bool(store.get("requiere_creatinina", False)))

    # Se conserva este key por compatibilidad con export_pdf u otros módulos antiguos.
    _restore_widget_value("sexo_clearance_widget", sexo_guardado)

    _restore_widget_value("creatinina_serica_widget", _safe_float(store.get("creatinina_serica", 1.0), 1.0))
    _restore_widget_value("contraste_ev_widget", bool(store.get("contraste_ev", False)))
    _restore_widget_value("vvp_widget", store.get("vvp"))
    _restore_widget_value("metodo_inyeccion_widget", store.get("metodo_inyeccion"))
    _restore_widget_value("cantidad_contraste_widget", store.get("cantidad_contraste"))


def _ir_a_inyectora():
    st.session_state["current_tab"] = "💉  Inyectora"
    st.rerun()


def render_ingreso():
    _init_session_state()

    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        _panel_header("📋", "Datos del Paciente")

        nombre = st.text_input(
            "Nombre del paciente",
            placeholder="Ej: Juan Pérez",
            key="nombre_paciente_widget",
        )

        col_edad_num, col_edad_unidad, col_espacio = st.columns([1, 1, 2])

        with col_edad_num:
            edad = st.number_input(
                "Edad",
                min_value=0,
                max_value=130,
                step=1,
                key="edad_widget",
            )

        with col_edad_unidad:
            edad_unidad = st.selectbox(
                "Unidad",
                ["Años", "Meses"],
                key="edad_unidad_widget",
            )

        diagnostico = st.text_area(
            "Diagnóstico",
            placeholder="Indicación clínica del examen",
            height=100,
            key="diagnostico_widget",
        )

        _render_imagen_ingreso()

    with col_der:
        _panel_header("💉", "Preparación del paciente")

        col_prep_izq, col_prep_der = st.columns(2)

        with col_prep_izq:
            peso = st.number_input(
                "Peso (kg)",
                min_value=0,
                max_value=250,
                key="peso_widget",
            )

            sexo_paciente = selectbox_con_placeholder(
                "Sexo",
                ["Femenino", "Masculino"],
                "sexo_paciente_widget",
                value=st.session_state.get("sexo_paciente_widget"),
            )

            # Mantiene sincronía con el key antiguo usado para clearance/exportación.
            st.session_state["sexo_clearance_widget"] = sexo_paciente

            embarazo = None
            if sexo_paciente == "Femenino":
                embarazo = selectbox_con_placeholder(
                    "¿Embarazo?",
                    ["SI", "NO", "PROBABLE"],
                    "embarazo_widget",
                    value=st.session_state.get("embarazo_widget"),
                )
            else:
                st.session_state["embarazo_widget"] = None

            requiere_creatinina = st.checkbox(
                "¿Requiere creatinina?",
                key="requiere_creatinina_widget",
            )

            creatinina_serica = None
            clearance = None

            if requiere_creatinina:
                creatinina_serica = st.number_input(
                    "Creatinina sérica (mg/dL)",
                    min_value=0.1,
                    max_value=20.0,
                    step=0.1,
                    key="creatinina_serica_widget",
                )

                edad_para_clearance = None
                try:
                    if edad_unidad == "Años":
                        edad_para_clearance = float(edad)
                    elif edad_unidad == "Meses":
                        edad_para_clearance = float(edad) / 12.0
                except Exception:
                    edad_para_clearance = None

                if sexo_paciente is not None and edad_para_clearance is not None:
                    try:
                        clearance = ((140 - float(edad_para_clearance)) * float(peso)) / (72 * float(creatinina_serica))
                        if sexo_paciente == "Femenino":
                            clearance *= 0.85
                        clearance = round(clearance, 1)
                    except Exception:
                        clearance = None

                if clearance is None:
                    st.info("Selecciona sexo e ingresa creatinina para calcular el clearance estimado.")
                else:
                    if clearance >= 60:
                        fondo, borde, texto = "#143d22", "#2ecc71", "#d8ffe5"
                        estado = "Adecuado"
                    elif clearance >= 30:
                        fondo, borde, texto = "#4a3d12", "#f1c40f", "#fff6cc"
                        estado = "Disminución moderada"
                    else:
                        fondo, borde, texto = "#4a1616", "#ff5c5c", "#ffe0e0"
                        estado = "Disminución severa"

                    st.markdown(
                        f"""
                        <div style="margin-top:0.35rem; padding:0.85rem 1rem; border-radius:10px;
                                    background:{fondo}; border:1px solid {borde}; color:{texto};">
                            <div style="font-size:0.9rem; font-weight:600; margin-bottom:0.15rem;">
                                Clearance de creatinina estimado
                            </div>
                            <div style="font-size:1.15rem; font-weight:700;">{clearance} mL/min</div>
                            <div style="font-size:0.82rem; opacity:0.95;">{estado}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with col_prep_der:
            contraste_ev = st.checkbox(
                "¿Se requiere medio de contraste EV?",
                key="contraste_ev_widget",
            )

            vvp = None
            metodo_inyeccion = None
            cantidad_contraste = None

            if contraste_ev:
                vvp = selectbox_con_placeholder(
                    "VVP",
                    ["24G", "22G", "20G", "18G", "CVC"],
                    "vvp_widget",
                    value=st.session_state.get("vvp_widget"),
                )

                metodo_inyeccion = selectbox_con_placeholder(
                    "Método de inyección",
                    ["INYECTORA AUTOMÁTICA", "INYECCIÓN MANUAL"],
                    "metodo_inyeccion_widget",
                    value=st.session_state.get("metodo_inyeccion_widget"),
                )

                if metodo_inyeccion == "INYECCIÓN MANUAL":
                    cantidad_contraste = selectbox_con_placeholder(
                        "Cantidad de medio de contraste",
                        [f"{i} cc" for i in range(10, 151, 10)],
                        "cantidad_contraste_widget",
                        value=st.session_state.get("cantidad_contraste_widget"),
                    )
                else:
                    st.session_state["cantidad_contraste_widget"] = None

                if metodo_inyeccion == "INYECTORA AUTOMÁTICA":
                    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

                    col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
                    with col_btn_2:
                        if st.button(
                            "Parámetros de Inyectora",
                            key="btn_ir_inyectora",
                            use_container_width=True,
                        ):
                            _ir_a_inyectora()
            else:
                st.session_state["vvp_widget"] = None
                st.session_state["metodo_inyeccion_widget"] = None
                st.session_state["cantidad_contraste_widget"] = None

    _build_store(
        nombre=nombre,
        fecha_nacimiento=None,
        edad=edad,
        edad_unidad=edad_unidad,
        diagnostico=diagnostico,
        peso=peso,
        sexo_paciente=sexo_paciente,
        sexo=sexo_paciente,
        embarazo=embarazo if sexo_paciente == "Femenino" else None,
        requiere_creatinina=requiere_creatinina,
        # Compatibilidad con export_pdf actual: mantiene el dato bajo el nombre antiguo.
        sexo_clearance=sexo_paciente if requiere_creatinina else None,
        creatinina_serica=creatinina_serica if requiere_creatinina else None,
        clearance=clearance if requiere_creatinina else None,
        contraste_ev=contraste_ev,
        vvp=vvp if contraste_ev else None,
        metodo_inyeccion=metodo_inyeccion if contraste_ev else None,
        cantidad_contraste=cantidad_contraste if (contraste_ev and metodo_inyeccion == "INYECCIÓN MANUAL") else None,
    )

    return st.session_state["ingreso_store"]
