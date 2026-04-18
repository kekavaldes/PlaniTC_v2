import streamlit as st

from ui.ingreso import render_ingreso
from ui.topograma import render_topograma_panel
from ui.adquisicion import render_adquisicion

st.set_page_config(page_title="PlaniTC_v2", layout="wide")


def aplicar_css_global():
    st.markdown(
        """
        <style>
        /* Fondo general */
        .stApp {
            background-color: #0e1117 !important;
            color: white !important;
        }

        html, body, [class*="css"] {
            color: white !important;
        }

        /* Títulos y textos */
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: white !important;
        }

        [data-testid="stMarkdownContainer"] p {
            color: white !important;
        }

        section[data-testid="stSidebar"] * {
            color: white !important;
        }

        /* Select cerrado */
        div[data-baseweb="select"] > div {
            background-color: #111111 !important;
            color: white !important;
            border: 1px solid #444 !important;
            border-radius: 10px !important;
        }

        div[data-baseweb="select"] * {
            color: white !important;
        }

        /* Inputs */
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

        /* Popover / portal del dropdown */
        div[data-baseweb="popover"] {
            background-color: #111111 !important;
            color: white !important;
        }

        div[data-baseweb="popover"] * {
            color: white !important;
        }

        /* Lista de opciones */
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

        /* Variante alternativa según versión */
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

        /* Botones */
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

        /* Checkbox */
        .stCheckbox label {
            color: white !important;
        }

        /* Tabs */
        button[role="tab"] {
            color: white !important;
        }

        /* Alertas */
        .stAlert {
            border-radius: 10px;
        }

        /* Header transparente */
        .stApp > header,
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Espacio arriba */
        .block-container {
            padding-top: 3.5rem !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: transparent;
            border-bottom: 1px solid #2A2A2A;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            color: #BFBFBF !important;
            padding: 0.7rem 1.2rem !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
            border-radius: 8px 8px 0 0;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: #1A1A1A !important;
            color: #FFFFFF !important;
        }

        .stTabs [aria-selected="true"] {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* Ocultar anchors */
        .stApp a.anchor-link,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    aplicar_css_global()

    tabs = st.tabs([
        "🏠  Inicio",
        "📋  Ingreso",
        "🖼️  Topograma",
        "⚡  Adquisición",
        "🧩  Reconstrucción",
        "💉  Inyectora",
    ])

    with tabs[0]:
        st.subheader("Inicio")
        st.info("Pendiente de modularizar")

    with tabs[1]:
        render_ingreso()

    with tabs[2]:
        render_topograma_panel()

    with tabs[3]:
        render_adquisicion()

    with tabs[4]:
        st.subheader("Reconstrucción")
        st.info("Pendiente de modularizar")

    with tabs[5]:
        st.subheader("Inyectora")
        st.info("Pendiente de modularizar")


if __name__ == "__main__":
    main()
