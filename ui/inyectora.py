"""
ui/inyectora.py
Módulo de Jeringa Inyectora para PlaniTC_v2.
"""

import streamlit as st


MAX_JERINGA = 180
CAUDAL_OPCIONES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
VVP_GAUGE = [18, 20, 22, 24]


def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    opciones = ["Seleccionar"] + list(options)
    if value in options:
        idx = opciones.index(value)
    else:
        idx = 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    return None if val == "Seleccionar" else val


def _panel_header(emoji: str, titulo: str):
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


def _metric_card(titulo: str, valor: str):
    st.markdown(
        f"""
        <div style="
            background:#1A1A1A;
            border:1px solid #2E2E2E;
            border-radius:12px;
            padding:0.9rem 1rem;
            min-height:90px;
            display:flex;
            flex-direction:column;
            justify-content:center;
        ">
            <div style="
                font-size:0.9rem;
                color:#C9D1D9;
                margin-bottom:0.35rem;
                font-weight:600;
            ">
                {titulo}
            </div>
            <div style="
                font-size:1.45rem;
                color:#FFFFFF;
                font-weight:800;
                line-height:1.1;
            ">
                {valor}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_inyectora_svg(vol_mc, vol_sf, max_mc, max_sf, fases_data, gauge):
    def clamp_ratio(v, m):
        try:
            v = float(v or 0)
            m = float(m or 0)
            if m <= 0:
                return 0.0
            return max(0.0, min(v / m, 1.0))
        except Exception:
            return 0.0

    ratio_mc = clamp_ratio(vol_mc, max_mc)
    ratio_sf = clamp_ratio(vol_sf, max_sf)

    colors = {
        "MC": "#8FD16A",
        "SF": "#63BFEA",
        "PAUSA": "#9BB7CF",
        "TEXT": "#F3F4F6",
        "PANEL": "#A9C5DC",
        "OUTLINE": "#2F3E4C",
        "BODY": "#E7EEF5",
        "EMPTY": "#DCE7F1",
    }

    phase_rows = []
    visible_rows = max(4, min(len(fases_data), 6))

    for i in range(visible_rows):
        f = fases_data[i] if i < len(fases_data) else {
            "solucion": None,
            "volumen": 0,
            "caudal": 0,
            "duracion": 0,
        }

        sol = f.get("solucion", None)
        color = colors.get(sol, "#8EA6BC")
        vol = f.get("volumen", 0)
        dur = f.get("duracion", 0)
        caud = f.get("caudal", 0)

        label = "Pausa" if sol == "PAUSA" else (sol if sol is not None else "—")
        caud_txt = "" if sol in (None, "PAUSA") else caud
        vol_txt = "" if sol in (None, "PAUSA") else vol
        dur_txt = dur if sol is not None else 0
        row_fill = "#111111" if sol == "PAUSA" else color

        phase_rows.append(
            f'<g transform="translate(500,{105 + i*78})">'
            f'<text x="-18" y="32" text-anchor="end" font-size="26" font-weight="700" fill="{colors["TEXT"]}">{label}</text>'
            f
