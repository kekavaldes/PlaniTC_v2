import streamlit as st

from ui.adquisicion import render_adquisicion

st.set_page_config(page_title="PlaniTC_v2", layout="wide")


def main():
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
