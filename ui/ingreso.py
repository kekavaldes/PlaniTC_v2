import streamlit as st

from ui.ingreso import render_ingreso
from ui.adquisicion import render_adquisicion
from ui.reconstruccion import render_reconstruccion
from ui.inyectora import render_inyectora

st.set_page_config(page_title="PlaniTC_v2", layout="wide")


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
            padding-top: 3.2rem !important;
        }

        .stApp a.anchor-link,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }

        /* Navegación superior */
        .top-nav-wrap {
            display: flex;
            gap: 0.45rem;
            margin-bottom: 1.1rem;
            border-bottom: 1px solid #2A2A2A;
            padding-bottom: 0.25rem;
            flex-wrap: wrap;
        }

        .top-nav-active {
            background: transparent !important;
            color: #FFFFFF !important;
            border: none !important;
            border-bottom: 2px solid #3B82F6 !important;
            border-radius: 0 !important;
            padding: 0.7rem 0.2rem 0.6rem 0.2rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            display: inline-block;
        }

        div[data-testid="stHorizontalBlock"] .stButton button.nav-btn {
            background: transparent !important;
            color: #BFBFBF !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0.7rem 0.2rem 0.6rem 0.2rem !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
        }

        div[data-testid="stHorizontalBlock"] .stButton button.nav-btn:hover {
            color: #FFFFFF !important;
            background: transparent !important;
            border-bottom: 2px solid #666 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_navigation():
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "📋  Ingreso"


def _go_to(tab_name: str):
    st.session_state["active_tab"] = tab_name


def render_navigation():
    tabs = [
        "🏠  Inicio",
        "📋  Ingreso",
        "⚡  Adquisición",
        "🧩  Reconstrucción",
        "💉  Inyectora",
    ]

    cols = st.columns(len(tabs), gap="small")

    for i, tab_name in enumerate(tabs):
        with cols[i]:
            if st.session_state["active_tab"] == tab_name:
                st.markdown(
                    f'<div class="top-nav-active">{tab_name}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(tab_name, key=f"nav_{i}", use_container_width=True):
                    _go_to(tab_name)
                    st.rerun()

    st.markdown(
        """
        <style>
        button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    aplicar_css_global()
    _init_navigation()
    render_navigation()

    active = st.session_state["active_tab"]

    if active == "🏠  Inicio":
        st.subheader("Inicio")
        st.info("Pendiente de modularizar")

    elif active == "📋  Ingreso":
        render_ingreso()

    elif active == "⚡  Adquisición":
        render_adquisicion()

    elif active == "🧩  Reconstrucción":
        render_reconstruccion()

    elif active == "💉  Inyectora":
        render_inyectora()


if __name__ == "__main__":
    main()
