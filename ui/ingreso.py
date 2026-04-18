import base64
from datetime import date
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGEN_INGRESO_PATH = BASE_DIR / "assets" / "portada_ingreso.jpg"


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


def _init_session_state():
    defaults = {
        "embarazo": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_ingreso():
    _init_session_state()

    _panel_header("📋", "Datos del Paciente")

    nombre = st.text_input(
        "Nombre del paciente",
        placeholder="Ej: Juan Pérez",
        key="nombre_paciente_widget",
    )

    col_fn, col_edad = st.columns([1, 1])

    # ───────────── FECHA NACIMIENTO ─────────────
    with col_fn:
        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date.today(),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
            key="fecha_nacimiento",
        )

    edad = calcular_edad(fecha_nacimiento, date.today())

    # ───────────── EDAD (ALINEADA) ─────────────
    with col_edad:
        st.markdown("**Edad**")

        st.markdown(
            f"""
            <div style="
                margin-top:4px;
                background-color:#111111;
                color:white;
                border:1px solid #444;
                border-radius:10px;
                padding:0.72rem 0.9rem;
                height:48px;
                display:flex;
                align-items:center;
                font-size:1.05rem;
            ">
                {edad if edad is not None else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ───────────── DIAGNÓSTICO ─────────────
    st.markdown("### Diagnóstico")

    diagnostico = st.text_area(
        "Indicación clínica del examen",
        height=120,
        key="diagnostico",
    )
