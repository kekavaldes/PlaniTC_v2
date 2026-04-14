import streamlit as st

MAX_JERINGA = 180


def render_inyectora_svg(vol_mc, vol_sf, max_mc, max_sf, fases_data, gauge):
    # Pega aquí tu función original actual casi sin cambios.
    return f"<div style='padding:1rem;border:1px solid #444;border-radius:12px;'>SVG de inyectora placeholder · MC: {vol_mc} · SF: {vol_sf}</div>"


def render_inyectora_tab():
    st.subheader("Inyectora")
    html = render_inyectora_svg(
        vol_mc=80,
        vol_sf=40,
        max_mc=MAX_JERINGA,
        max_sf=MAX_JERINGA,
        fases_data=[],
        gauge="20G",
    )
    st.components.v1.html(html, height=120)
    st.info("Aquí debes mover la función real render_inyectora_svg() desde tu archivo original.")
