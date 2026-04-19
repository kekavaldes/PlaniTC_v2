"""
ui/ingreso.py
Módulo de Ingreso del paciente para PlaniTC_v2.
"""

from datetime import date
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


def calcular_edad(fecha_nacimiento, fecha_referencia=None):
    try:
        if fecha_nacimiento in (None, ""):
            return None

        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento)

        if fecha_referencia is None:
            fecha_referencia = date.today()

        edad = fecha_referencia.year - fecha_nacimiento.year
        if (fecha_referencia.month, fecha_referencia.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
            edad -= 1

        return max(0, int(edad))
    except Exception:
        return None


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


def _init_session_state():
    store = st.session_state.get("ingreso_store", {})

    widget_defaults = {
        "nombre_paciente_widget": store.get("nombre", ""),
        "fecha_nacimiento": date.fromisoformat(store["fecha_nacimiento"]) if store.get("fecha_nacimiento") else date.today(),
        "diagnostico_widget": store.get("diagnostico", ""),
        "peso_widget": _safe_int(store.get("peso", 70), 70),
        "embarazo_widget": store.get("embarazo"),
        "requiere_creatinina_widget": bool(store.get("requiere_creatinina", False)),
        "sexo_clearance_widget": store.get("sexo_clearance"),
        "creatinina_serica_widget": _safe_float(store.get("creatinina_serica", 1.0), 1.0),
        "contraste_ev_widget": bool(store.get("contraste_ev", False)),
        "vvp_widget": store.get("vvp"),
        "metodo_inyeccion_widget": store.get("metodo_inyeccion"),
        "cantidad_contraste_widget": store.get("cantidad_contraste"),
    }

    for key, value in widget_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _ir_a_inyectora():
    st.session_state["current_tab"] = "💉  Inyectora"
    st.rerun()


def render_ingreso():
    _init_session_state()
    store = st.session_state.get("ingreso_store", {})

    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        _panel_header("📋", "Datos del Paciente")

        nombre = st.text_input(
            "Nombre del paciente",
            placeholder="Ej: Juan Pérez",
            key="nombre_paciente_widget",
        )

        col_fn, col_edad = st.columns([1, 1])

        with col_fn:
            fecha_nacimiento = st.date_input(
                "Fecha de nacimiento",
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                format="DD/MM/YYYY",
                key="fecha_nacimiento",
            )

        edad = calcular_edad(fecha_nacimiento, date.today())

        with col_edad:
            st.markdown(
                f"""
                <div style="margin-bottom:0.35rem;">
                    <label style="font-size:0.875rem; font-weight:400; color:white;">Edad</label>
                </div>
                <div style="
                    background-color:#111111;
                    color:white;
                    border:1px solid #444;
                    border-radius:10px;
                    padding:0.72rem 0.9rem;
                    min-height:24px;
                    display:flex;
                    align-items:center;
                    font-size:1.05rem;
                    font-weight:500;
                    height:42px;
                    box-sizing:border-box;
                ">
                    {f"{edad} años" if edad is not None else ""}
                </div>
                """,
                unsafe_allow_html=True,
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

            embarazo = selectbox_con_placeholder(
                "¿Embarazo?",
                ["SI", "NO", "PROBABLE"],
                "embarazo_widget",
                value=st.session_state.get("embarazo_widget"),
            )

            requiere_creatinina = st.checkbox(
                "¿Requiere creatinina?",
                key="requiere_creatinina_widget",
            )

            sexo_clearance = None
            creatinina_serica = None
            clearance = None

            if requiere_creatinina:
                sexo_clearance = selectbox_con_placeholder(
                    "Sexo",
                    ["Femenino", "Masculino"],
                    "sexo_clearance_widget",
                    value=st.session_state.get("sexo_clearance_widget"),
                )

                creatinina_serica = st.number_input(
                    "Creatinina sérica (mg/dL)",
                    min_value=0.1,
                    max_value=20.0,
                    step=0.1,
                    key="creatinina_serica_widget",
                )

                if sexo_clearance is not None and edad is not None:
                    try:
                        clearance = ((140 - float(edad)) * float(peso)) / (72 * float(creatinina_serica))
                        if sexo_clearance == "Femenino":
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

                cantidad_contraste = selectbox_con_placeholder(
                    "Cantidad de medio de contraste",
                    [f"{i} cc" for i in range(10, 151, 10)],
                    "cantidad_contraste_widget",
                    value=st.session_state.get("cantidad_contraste_widget"),
                )

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

    _build_store(
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento.isoformat() if fecha_nacimiento else None,
        edad=edad,
        diagnostico=diagnostico,
        peso=peso,
        embarazo=embarazo,
        requiere_creatinina=requiere_creatinina,
        sexo_clearance=sexo_clearance if requiere_creatinina else None,
        creatinina_serica=creatinina_serica if requiere_creatinina else None,
        clearance=clearance if requiere_creatinina else None,
        contraste_ev=contraste_ev,
        vvp=vvp if contraste_ev else None,
        metodo_inyeccion=metodo_inyeccion if contraste_ev else None,
        cantidad_contraste=cantidad_contraste if contraste_ev else None,
    )

    return st.session_state["ingreso_store"]
