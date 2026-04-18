"""
ui/ingreso.py
Módulo de Ingreso del paciente para PlaniTC_v2.
"""

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
        with open(IMAGEN_INGRESO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:1rem;">
                <img src="data:image/jpeg;base64,{b64}"
                     style="max-width:55%; border-radius:10px; border:1px solid #333;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def _build_store(**kwargs):
    prev = st.session_state.get("ingreso_store", {})
    prev.update(kwargs)
    st.session_state["ingreso_store"] = prev


def render_ingreso():
    store = st.session_state.get("ingreso_store", {})

    col_izq, col_der = st.columns([1, 1], gap="large")

    # ─── IZQUIERDA ───
    with col_izq:
        _panel_header("📋", "Datos del Paciente")

        nombre = st.text_input(
            "Nombre del paciente",
            value=store.get("nombre", ""),
            placeholder="Ej: Juan Pérez",
        )

        col_fn, col_edad = st.columns([1, 1])

        with col_fn:
            fecha_guardada = store.get("fecha_nacimiento")
            fecha_default = date.today()

            try:
                if fecha_guardada:
                    fecha_default = date.fromisoformat(fecha_guardada)
            except Exception:
                pass

            fecha_nacimiento = st.date_input(
                "Fecha de nacimiento",
                value=fecha_default,
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                format="DD/MM/YYYY",
            )

        edad = calcular_edad(fecha_nacimiento)

        # 🔥 CORRECCIÓN AQUÍ (SIN KEY)
        with col_edad:
            st.text_input(
                "Edad",
                value=f"{edad} años" if edad is not None else "",
                disabled=True,
            )

        diagnostico = st.text_area(
            "Diagnóstico",
            value=store.get("diagnostico", ""),
            placeholder="Indicación clínica del examen",
            height=100,
        )

        _render_imagen_ingreso()

    # ─── DERECHA ───
    with col_der:
        _panel_header("💉", "Preparación del paciente")

        col_prep_izq, col_prep_der = st.columns(2)

        with col_prep_izq:
            peso = st.number_input(
                "Peso (kg)",
                min_value=0,
                max_value=250,
                value=_safe_int(store.get("peso", 70)),
            )

            embarazo = selectbox_con_placeholder(
                "¿Embarazo?",
                ["SI", "NO", "PROBABLE"],
                "embarazo_widget",
                value=store.get("embarazo"),
            )

            requiere_creatinina = st.checkbox(
                "¿Requiere creatinina?",
                value=bool(store.get("requiere_creatinina", False)),
            )

            if requiere_creatinina:
                sexo = selectbox_con_placeholder(
                    "Sexo",
                    ["Femenino", "Masculino"],
                    "sexo_widget",
                )

                creatinina = st.number_input(
                    "Creatinina sérica",
                    min_value=0.1,
                    max_value=20.0,
                    value=_safe_float(store.get("creatinina_serica", 1.0)),
                    step=0.1,
                )

        with col_prep_der:
            contraste_ev = st.checkbox(
                "¿Se requiere contraste EV?",
                value=bool(store.get("contraste_ev", False)),
            )

    _build_store(
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento.isoformat(),
        edad=edad,
        diagnostico=diagnostico,
        peso=peso,
        embarazo=embarazo,
        requiere_creatinina=requiere_creatinina,
        contraste_ev=contraste_ev,
    )

    return st.session_state["ingreso_store"]
