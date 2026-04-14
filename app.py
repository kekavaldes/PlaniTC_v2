import streamlit as st

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
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    aplicar_css_global()

    st.title("PlaniTC_v2")

    tabs = st.tabs([
        "Inicio",
        "Ingreso",
        "Adquisición",
        "Reconstrucción",
        "Inyectora",
    ])

    with tabs[0]:
        st.subheader("Inicio")
        st.info("Pendiente de modularizar")

    with tabs[1]:
        st.subheader("Ingreso")
        st.info("Pendiente de modularizar")

    with tabs[2]:
        render_adquisicion()

    with tabs[3]:
        st.subheader("Reconstrucción")
        st.info("Pendiente de modularizar")

    with tabs[4]:
        st.subheader("Inyectora")
        st.info("Pendiente de modularizar")


if __name__ == "__main__":
    main()
