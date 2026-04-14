import streamlit as st


def render_ingreso():
    st.subheader("Ingreso")
    st.caption("Mueve aquí la lógica actual de datos del paciente y examen.")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Nombre paciente", key="nombre_paciente")
        st.date_input("Fecha de nacimiento", key="fecha_nacimiento")
        st.text_input("Diagnóstico", key="diagnostico")
    with col2:
        st.selectbox("Examen", ["Seleccionar"], key="examen")
        st.selectbox("Región anatómica", ["Seleccionar"], key="region_anatomica")
        st.selectbox("Posición", ["Seleccionar"], key="posicion")

    st.info("Aquí debes migrar la UI real de ingreso desde tu archivo original.")
