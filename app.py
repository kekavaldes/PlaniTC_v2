import streamlit as st

from ui.ingreso import render_ingreso
from ui.adquisicion import render_adquisicion
from ui.reconstruccion import render_reconstruccion
from ui.inyectora import render_inyectora

st.set_page_config(page_title="PlaniTC_v2", layout="wide")

TAB_OPTIONS = [
    "🏠  Inicio",
    "📋  Ingreso",
    "⚡  Adquisición",
    "🧩  Reconstrucción",
    "💉  Inyectora",
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
            padding-top: 3rem !important;
        }

        div[role="radiogroup"] {
            display: flex !important;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }

        div[role="radiogroup"] label {
            background: transparent !important;
            border: 1px solid #2A2A2A !important;
            border-radius: 10px !important;
            padding: 0.5rem 0.9rem !important;
            color: #BFBFBF !important;
        }

        div[role="radiogroup"] label:hover {
            background: #1A1A1A !important;
            color: #FFFFFF !important;
            border-color: #444 !important;
        }

        .stApp a.anchor-link,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_navigation():
    if "current_tab" not in st.session_state:
        st.session_state["current_tab"] = "🏠  Inicio"

    if "main_navigation_radio" not in st.session_state:
        st.session_state["main_navigation_radio"] = st.session_state["current_tab"]


def sync_tab_from_radio():
    st.session_state["current_tab"] = st.session_state["main_navigation_radio"]


def render_top_navigation():
    # mantener siempre sincronizados ambos estados antes de dibujar
    st.session_state["main_navigation_radio"] = st.session_state["current_tab"]

    st.radio(
        "Navegación",
        TAB_OPTIONS,
        key="main_navigation_radio",
        horizontal=True,
        label_visibility="collapsed",
        on_change=sync_tab_from_radio,
    )


def main():
    aplicar_css_global()
    init_navigation()
    render_top_navigation()

    current_tab = st.session_state.get("current_tab", "🏠  Inicio")

    if current_tab == "🏠  Inicio":
        st.subheader("Inicio")
        st.info("Pendiente de modularizar")

    elif current_tab == "📋  Ingreso":
        render_ingreso()

    elif current_tab == "⚡  Adquisición":
        render_adquisicion()

    elif current_tab == "🧩  Reconstrucción":
        render_reconstruccion()

    elif current_tab == "💉  Inyectora":
        render_inyectora()


if __name__ == "__main__":
    main()
