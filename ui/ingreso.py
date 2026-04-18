"""
ui/ingreso.py
Módulo de Ingreso del paciente para PlaniTC_v2.

Cubre la TAB 1 del simulador:
- Datos del paciente (nombre, fecha de nacimiento, edad calculada, diagnóstico)
- Preparación del paciente (peso, embarazo, creatinina + clearance,
  requerimiento de contraste EV + VVP + método + cantidad).

Entrypoint: render_ingreso()
"""

import base64
from datetime import date
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent

# Imagen opcional de la columna "Datos del Paciente".
# Si el archivo no existe, la sección simplemente no renderiza la imagen.
IMAGEN_INGRESO_PATH = BASE_DIR / "assets" / "portada_ingreso.jpg"


# ─── Helpers reutilizables ──────────────────────────────────────────────────
# NOTA: selectbox_con_placeholder también existe en ui/topograma.py con la
# misma firma. Cuando centralices utilidades en core/utils.py, puedes mover
# esta función allí e importarla desde ambos módulos.
def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    """Selectbox con opción 'Seleccionar' al inicio; devuelve None si no hay elección."""
    opciones = ["Seleccionar"] + list(options)
    if value in options:
        idx = opciones.index(value)
    else:
        idx = 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    return None if val == "Seleccionar" else val


# ─── Lógica clínica (cálculos puros, sin Streamlit) ─────────────────────────
# NOTA: Estos cálculos son candidatos ideales para mover a core/clinico.py
# cuando armes ese módulo, ya que no dependen de la UI.
def calcular_edad(fecha_nacimiento, fecha_referencia=None):
    """Calcula edad exacta en años cumplidos. Devuelve None si no hay fecha válida."""
    try:
        if fecha_nacimiento in (None, ""):
            return None

        if isinstance(fecha_nacimiento, (tuple, list)):
            if not fecha_nacimiento:
                return None
            fecha_nacimiento = fecha_nacimiento[0]

        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento)
        elif hasattr(fecha_nacimiento, "date") and not isinstance(fecha_nacimiento, date):
            fecha_nacimiento = fecha_nacimiento.date()

        if fecha_referencia is None:
            fecha_referencia = date.today()
        elif isinstance(fecha_referencia, str):
            fecha_referencia = date.fromisoformat(fecha_referencia)
        elif hasattr(fecha_referencia, "date") and not isinstance(fecha_referencia, date):
            fecha_referencia = fecha_referencia.date()

        if fecha_nacimiento > fecha_referencia:
            return 0

        edad = fecha_referencia.year - fecha_nacimiento.year
        if (fecha_referencia.month, fecha_referencia.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
            edad -= 1

        return max(0, int(edad))
    except Exception:
        return None


def calc_clearance_cockcroft_gault(edad, peso_kg, creatinina_mg_dl, sexo):
    """Calcula clearance estimado de creatinina por fórmula de Cockcroft-Gault."""
    try:
        if edad is None or peso_kg is None or creatinina_mg_dl is None:
            return None
        if edad < 0 or peso_kg <= 0 or creatinina_mg_dl <= 0:
            return None
        crcl = ((140 - float(edad)) * float(peso_kg)) / (72 * float(creatinina_mg_dl))
        if sexo == "Femenino":
            crcl *= 0.85
        return round(crcl, 1)
    except Exception:
        return None


# ─── Helpers visuales ───────────────────────────────────────────────────────
def _panel_header(emoji: str, titulo: str):
    """Header tipo banner oscuro, consistente con ui/topograma.py."""
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


def _render_clearance_result(clearance):
    """Muestra clearance estimado con semáforo clínico (verde/amarillo/rojo)."""
    if clearance is None:
        st.info("Selecciona sexo e ingresa creatinina para calcular el clearance estimado.")
        return

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


def _render_imagen_ingreso():
    """Muestra la imagen decorativa de la columna izquierda si existe en assets/."""
    if not IMAGEN_INGRESO_PATH.exists():
        return
    try:
        with open(IMAGEN_INGRESO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        mime = "image/jpeg" if IMAGEN_INGRESO_PATH.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:1rem;">
                <img src="data:{mime};base64,{b64}"
                     style="max-width:55%; border-radius:10px; border:1px solid #333;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass


# ─── Persistencia de estado ─────────────────────────────────────────────────
def _build_store(**kwargs):
    """Acumula valores del formulario en st.session_state['ingreso_store']."""
    prev = st.session_state.get("ingreso_store", {})
    prev.update(kwargs)
    st.session_state["ingreso_store"] = prev


def _init_session_state():
    """Inicializa las llaves de session_state que este módulo necesita."""
    defaults = {
        "contraste_ev": False,
        "vvp": None,
        "metodo_inyeccion": None,
        "cantidad_contraste": None,
        "sexo_clearance": None,
        "requiere_creatinina": False,
        "embarazo": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ─── Render principal ───────────────────────────────────────────────────────
def render_ingreso():
    """Entrypoint del módulo: renderiza la TAB 1 (Ingreso) completa."""
    _init_session_state()
    store = st.session_state.get("ingreso_store", {})

    col_izq, col_der = st.columns([1, 1], gap="large")

    # ── Columna izquierda: Datos del Paciente ──
    with col_izq:
        _panel_header("📋", "Datos del Paciente")

        nombre = st.text_input(
            "Nombre del paciente",
            value=store.get("nombre", ""),
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
            st.text_input(
                "Edad",
                value=f"{edad} años" if edad is not None else "",
                disabled=True,
                key="edad_widget",
            )

        diagnostico = st.text_area(
            "Diagnóstico",
            value=store.get("diagnostico", ""),
            placeholder="Indicación clínica del examen",
            height=100,
            key="diagnostico_widget",
        )

        _render_imagen_ingreso()

    # ── Columna derecha: Preparación del paciente ──
    with col_der:
        _panel_header("💉", "Preparación del paciente")

        col_prep_izq, col_prep_der = st.columns(2)

        with col_prep_izq:
            peso = st.number_input(
                "Peso (kg)",
                min_value=0,
                max_value=250,
                value=int(store.get("peso", 70)),
                key="peso_widget",
            )

            embarazo = selectbox_con_placeholder(
                "¿Embarazo?",
                ["SI", "NO", "PROBABLE"],
                "embarazo_widget",
                value=store.get("embarazo"),
            )
            st.session_state["embarazo"] = embarazo

            requiere_creatinina = st.checkbox(
                "¿Requiere creatinina?",
                value=bool(store.get("requiere_creatinina", False)),
                key="requiere_creatinina",
            )

            sexo_clearance = None
            creatinina_serica = None
            clearance = None

            if requiere_creatinina:
                sexo_clearance = selectbox_con_placeholder(
                    "Sexo",
                    ["Femenino", "Masculino"],
                    "sexo_clearance_widget",
                    value=store.get("sexo_clearance"),
                )
                st.session_state["sexo_clearance"] = sexo_clearance

                creatinina_serica = st.number_input(
                    "Creatinina sérica (mg/dL)",
                    min_value=0.1,
                    max_value=20.0,
                    value=float(store.get("creatinina_serica", 1.0)),
                    step=0.1,
                    key="creatinina_serica_widget",
                )

                clearance = calc_clearance_cockcroft_gault(
                    edad, peso, creatinina_serica, sexo_clearance
                )
                _render_clearance_result(clearance)

        with col_prep_der:
            contraste_ev = st.checkbox(
                "¿Se requiere medio de contraste EV?",
                value=bool(store.get("contraste_ev", False)),
                key="contraste_ev",
            )

            vvp = None
            metodo_inyeccion = None
            cantidad_contraste = None

            if contraste_ev:
                vvp = selectbox_con_placeholder(
                    "VVP",
                    ["24G", "22G", "20G", "18G", "CVC"],
                    "vvp_widget",
                    value=store.get("vvp"),
                )
                st.session_state["vvp"] = vvp

                metodo_inyeccion = selectbox_con_placeholder(
                    "Método de inyección",
                    ["INYECTORA AUTOMÁTICA", "INYECCIÓN MANUAL"],
                    "metodo_inyeccion_widget",
                    value=store.get("metodo_inyeccion"),
                )
                st.session_state["metodo_inyeccion"] = metodo_inyeccion

                cantidad_contraste = selectbox_con_placeholder(
                    "Cantidad de medio de contraste",
                    [f"{i} cc" for i in range(10, 151, 10)],
                    "cantidad_contraste_widget",
                    value=store.get("cantidad_contraste"),
                )
                st.session_state["cantidad_contraste"] = cantidad_contraste
            else:
                # Si se desmarca contraste EV, limpiamos los campos dependientes
                st.session_state["vvp"] = None
                st.session_state["metodo_inyeccion"] = None
                st.session_state["cantidad_contraste"] = None

    # ── Persistencia ──
    _build_store(
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento.isoformat() if fecha_nacimiento else None,
        edad=edad,
        diagnostico=diagnostico,
        peso=peso,
        embarazo=embarazo,
        requiere_creatinina=requiere_creatinina,
        sexo_clearance=sexo_clearance,
        creatinina_serica=creatinina_serica,
        clearance=clearance,
        contraste_ev=contraste_ev,
        vvp=vvp,
        metodo_inyeccion=metodo_inyeccion,
        cantidad_contraste=cantidad_contraste,
    )

    return st.session_state["ingreso_store"]
