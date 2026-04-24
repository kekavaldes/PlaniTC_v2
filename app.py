import streamlit as st
from pathlib import Path
import base64

from ui.ingreso import render_ingreso
from ui.adquisicion import render_adquisicion
from ui.reconstruccion import render_reconstruccion
from ui.reformaciones import render_reformaciones
from ui.inyectora import render_inyectora
from ui.export_pdf import render_export_pdf

st.set_page_config(page_title="PlaniTC_v2", layout="wide")

TAB_OPTIONS = [
    "🏠  Inicio",
    "📋  Ingreso",
    "⚡  Adquisición",
    "🧩  Reconstrucción",
    "📐  Reformaciones",
    "💉  Inyectora",
    "📄  Exportar",
]

TAB_LABELS = [
    "🏠 Inicio",
    "📋 Ingreso",
    "⚡ Adquisición",
    "🧩 Reconstrucción",
    "📐 Reformaciones",
    "💉 Inyectora",
    "📄 Exportar",
]


# ──────────────────────────────────────────────────────────────────────────────
# CSS global
# ──────────────────────────────────────────────────────────────────────────────
def aplicar_css_global():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0e1117 !important;
            color: white !important;
        }

        html, body, [class*="css"] {
            color: white !important;
        }

        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: white !important;
        }

        [data-testid="stMarkdownContainer"] p {
            color: white !important;
        }

        section[data-testid="stSidebar"] * {
            color: white !important;
        }

        div[data-baseweb="select"] > div {
            background-color: #111111 !important;
            color: white !important;
            border: 1px solid #444 !important;
            border-radius: 10px !important;
        }

        div[data-baseweb="select"] * {
            color: white !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        input[type="text"],
        input[type="number"],
        textarea {
            background-color: #111111 !important;
            color: white !important;
            border: 1px solid #444 !important;
            border-radius: 10px !important;
            -webkit-text-fill-color: white !important;
        }

        div[data-baseweb="popover"] {
            background-color: #111111 !important;
            color: white !important;
        }

        div[data-baseweb="popover"] * {
            color: white !important;
        }

        ul[role="listbox"] {
            background-color: #111111 !important;
            border: 1px solid #444 !important;
        }

        ul[role="listbox"] li {
            background-color: #111111 !important;
            color: white !important;
        }

        ul[role="listbox"] li:hover,
        ul[role="listbox"] li[aria-selected="true"] {
            background-color: #222222 !important;
            color: white !important;
        }

        div[role="listbox"] {
            background-color: #111111 !important;
            border: 1px solid #444 !important;
            color: white !important;
        }

        div[role="option"] {
            background-color: #111111 !important;
            color: white !important;
        }

        div[role="option"]:hover,
        div[role="option"][aria-selected="true"] {
            background-color: #222222 !important;
            color: white !important;
        }

        .stButton button {
            background-color: #1c1f26 !important;
            color: white !important;
            border: 1px solid #444 !important;
            border-radius: 10px !important;
            min-height: 48px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
        }

        .stButton button:hover {
            background-color: #2a2e36 !important;
            color: white !important;
        }

        .stCheckbox label {
            color: white !important;
        }

        .stAlert {
            border-radius: 10px;
        }

        .stApp > header,
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 0.5rem !important;
        }

        .stApp a.anchor-link,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }

        .portada-wrapper {
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin-top: 0.15rem;
        }

        .portada-wrapper img {
            width: 100%;
            max-height: calc(100vh - 165px);
            object-fit: contain;
            border-radius: 14px;
            display: block;
        }

        /* ─────────────────────────────────────────────────────────────
           Barra superior principal
           Problema corregido: en Reconstrucción/Reformaciones algunos CSS
           internos de esas pestañas reducen la zona útil de los botones.
           Estos selectores con keys nav_0...nav_6 tienen más prioridad y
           dejan toda la tarjeta de cada pestaña como área clickeable.
        ───────────────────────────────────────────────────────────── */
        .st-key-nav_0,
        .st-key-nav_1,
        .st-key-nav_2,
        .st-key-nav_3,
        .st-key-nav_4,
        .st-key-nav_5,
        .st-key-nav_6 {
            width: 100% !important;
        }

        .st-key-nav_0 button,
        .st-key-nav_1 button,
        .st-key-nav_2 button,
        .st-key-nav_3 button,
        .st-key-nav_4 button,
        .st-key-nav_5 button,
        .st-key-nav_6 button {
            width: 100% !important;
            min-height: 3.05rem !important;
            height: 3.05rem !important;
            padding: 0.55rem 0.65rem !important;
            border-radius: 12px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1.15 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            box-sizing: border-box !important;
            pointer-events: auto !important;
            z-index: 50 !important;
            position: relative !important;
        }

        .st-key-nav_0 button p,
        .st-key-nav_1 button p,
        .st-key-nav_2 button p,
        .st-key-nav_3 button p,
        .st-key-nav_4 button p,
        .st-key-nav_5 button p,
        .st-key-nav_6 button p {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            font-size: 0.92rem !important;
            line-height: 1.15 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            color: #ffffff !important;
            pointer-events: none !important;
        }

        /* Separación fija entre la barra principal y el contenido de cada pestaña */
        div[data-testid="stHorizontalBlock"]:has(.st-key-nav_0) {
            margin-bottom: 1rem !important;
            position: relative !important;
            z-index: 40 !important;
        }

        @media (max-width: 1100px) {
            .st-key-nav_0 button p,
            .st-key-nav_1 button p,
            .st-key-nav_2 button p,
            .st-key-nav_3 button p,
            .st-key-nav_4 button p,
            .st-key-nav_5 button p,
            .st-key-nav_6 button p {
                font-size: 0.82rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Navegación principal
# ──────────────────────────────────────────────────────────────────────────────
def init_navigation():
    if "current_tab" not in st.session_state:
        st.session_state["current_tab"] = "🏠  Inicio"


def go_to_tab(tab_name: str):
    st.session_state["current_tab"] = tab_name


def render_top_navigation():
    current = st.session_state.get("current_tab", "🏠  Inicio")

    # Anchos levemente ajustados para que Reconstrucción/Reformaciones no queden apretados.
    cols = st.columns([1, 1, 1.12, 1.28, 1.28, 1, 1], gap="small")

    for idx, (col, tab_name, label) in enumerate(zip(cols, TAB_OPTIONS, TAB_LABELS)):
        with col:
            tipo = "primary" if current == tab_name else "secondary"
            if st.button(
                label,
                key=f"nav_{idx}",
                use_container_width=True,
                type=tipo,
            ):
                go_to_tab(tab_name)
                st.rerun()

    # Espaciado extra para evitar que algún componente posterior se monte sobre la barra.
    st.markdown("<div style='height:0.2rem;'></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Inicio / portada
# ──────────────────────────────────────────────────────────────────────────────
def obtener_ruta_portada():
    posibles_rutas = [
        Path("data/images/PORTADA.png"),
        Path("data/images/PORTADA.jpg"),
        Path("data/images/PORTADA.jpeg"),
        Path("data/images/PORTADA.webp"),
        Path("data/images/PORTADA.PNG"),
        Path("data/images/PORTADA.JPG"),
        Path("data/images/PORTADA.JPEG"),
        Path("data/images/PORTADA.WEBP"),
    ]

    for ruta in posibles_rutas:
        if ruta.exists():
            return ruta

    return None


@st.cache_data(show_spinner=False)
def _cached_image_to_base64(path_str: str, mtime: float) -> str:
    """Lee y codifica la portada. Cachea por (path, mtime) para que un
    cambio en disco invalide la caché automáticamente."""
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    p = Path(path_str)
    suffix = p.suffix.lower()
    mime_type = mime_map.get(suffix, "image/png")
    with open(p, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def image_to_base64(image_path: Path) -> str:
    try:
        mtime = image_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    return _cached_image_to_base64(str(image_path), mtime)


def render_inicio():
    ruta_portada = obtener_ruta_portada()

    if ruta_portada is not None:
        portada_src = image_to_base64(ruta_portada)

        st.markdown(
            f"""
            <div class="portada-wrapper">
                <img src="{portada_src}" alt="Portada PlaniTC">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            "No se encontró la imagen de portada. "
            "Verifica que esté en data/images y que se llame PORTADA "
            "(.png, .jpg, .jpeg o .webp)."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    aplicar_css_global()
    init_navigation()
    render_top_navigation()

    current_tab = st.session_state.get("current_tab", "🏠  Inicio")

    if current_tab == "🏠  Inicio":
        render_inicio()

    elif current_tab == "📋  Ingreso":
        render_ingreso()

    elif current_tab == "⚡  Adquisición":
        render_adquisicion()

    elif current_tab == "🧩  Reconstrucción":
        render_reconstruccion()

    elif current_tab == "📐  Reformaciones":
        render_reformaciones()

    elif current_tab == "💉  Inyectora":
        render_inyectora()

    elif current_tab == "📄  Exportar":
        render_export_pdf()


if __name__ == "__main__":
    main()
