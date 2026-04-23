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
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_navigation():
    if "current_tab" not in st.session_state:
        st.session_state["current_tab"] = "🏠  Inicio"


def go_to_tab(tab_name: str):
    st.session_state["current_tab"] = tab_name


def render_top_navigation():
    current = st.session_state.get("current_tab", "🏠  Inicio")

    cols = st.columns(7)
    labels = [
        "🏠 Inicio",
        "📋 Ingreso",
        "⚡ Adquisición",
        "🧩 Reconstrucción",
        "📐 Reformaciones",
        "💉 Inyectora",
        "📄 Exportar",
    ]

    for col, tab_name, label in zip(cols, TAB_OPTIONS, labels):
        with col:
            tipo = "primary" if current == tab_name else "secondary"
            if st.button(label, key=f"nav_{tab_name}", use_container_width=True, type=tipo):
                go_to_tab(tab_name)
                st.rerun()


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


def image_to_base64(image_path: Path) -> str:
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    suffix = image_path.suffix.lower()
    mime_type = mime_map.get(suffix, "image/png")

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


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
