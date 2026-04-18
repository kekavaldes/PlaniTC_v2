"""
ui/inyectora.py
Módulo de Jeringa Inyectora para PlaniTC_v2.

Cubre la TAB 4 del simulador:
- Número de fases de inyección (1 a 6)
- Configuración por fase: solución (MC / SF / PAUSA), volumen, caudal, duración
- Visualización SVG de ambas jeringas (A = Medio de Contraste, B = Suero Fisiológico)
- Validaciones: capacidad de jeringas y calibre VVP vs caudal

Entrypoint: render_inyectora()
"""

import streamlit as st


# ─── Constantes del módulo ──────────────────────────────────────────────────
MAX_JERINGA = 180  # mL fijos para ambas jeringas (MC y SF)
CAUDAL_OPCIONES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
VVP_GAUGE = [18, 20, 22, 24]


# ─── Helpers reutilizables ──────────────────────────────────────────────────
def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    """Selectbox con opción 'Seleccionar' al inicio; devuelve None si no hay elección."""
    opciones = ["Seleccionar"] + list(options)
    if value in options:
        idx = opciones.index(value)
    else:
        idx = 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    return None if val == "Seleccionar" else val


def _panel_header(emoji: str, titulo: str):
    """Header tipo banner oscuro, consistente con el resto de la app."""
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


# ─── Renderizado SVG de la jeringa inyectora ────────────────────────────────
def render_inyectora_svg(vol_mc, vol_sf, max_mc, max_sf, fases_data, gauge):
    """Genera el SVG de la inyectora con ambas jeringas y la tabla de fases."""
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
        "OUTLINE": "#2F3E4C",
        "BODY": "#E7EEF5",
        "EMPTY": "#DCE7F1",
    }

    phase_rows = []
    for i, f in enumerate(fases_data[:4]):
        sol = f.get("solucion", "")
        color = colors.get(sol, colors["PAUSA"])
        vol = f.get("volumen", 0)
        dur = f.get("duracion", 0)
        caud = f.get("caudal", "") if sol != "PAUSA" else ""

        box_fill_left = color if sol != "PAUSA" else "#111111"
        box_fill_mid = color if sol != "PAUSA" else "#111111"

        phase_rows.append(
            f'<g transform="translate(360,{78 + i*68})">'
            f'<rect x="0" y="0" width="72" height="42" rx="4" fill="{box_fill_left}" opacity="0.95"/>'
            f'<rect x="84" y="0" width="72" height="42" rx="4" fill="{box_fill_mid}" opacity="0.95"/>'
            f'<rect x="168" y="0" width="72" height="42" rx="4" fill="#CFE0EC" opacity="0.95"/>'
            f'<text x="36" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{caud if sol != "PAUSA" else ""}</text>'
            f'<text x="120" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{vol if sol != "PAUSA" else ""}</text>'
            f'<text x="204" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{dur}</text>'
            f'<text x="-10" y="28" text-anchor="end" font-size="18" font-weight="800" fill="{colors["TEXT"]}">{"Pausa" if sol == "PAUSA" else sol}</text>'
            f'</g>'
        )
    phase_rows_str = "".join(phase_rows)

    def syringe(x, label, ratio, vol, maxv, fill):
        h = 240
        y = 10
        inner_h = int(round(h * ratio))
        inner_y = y + h - inner_h

        try:
            vol_txt = int(vol) if float(vol).is_integer() else vol
            max_txt = int(maxv) if float(maxv).is_integer() else maxv
        except Exception:
            vol_txt = vol
            max_txt = maxv

        return (
            f'<g transform="translate({x},58)">'
            f'<rect x="0" y="0" width="72" height="12" rx="3" fill="{colors["BODY"]}" stroke="{colors["OUTLINE"]}" stroke-width="1.5"/>'
            f'<rect x="8" y="12" width="56" height="240" rx="8" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<rect x="8" y="{inner_y}" width="56" height="{max(inner_h,0)}" fill="{fill}"/>'
            f'<rect x="8" y="120" width="56" height="2" fill="{colors["OUTLINE"]}" opacity="0.75"/>'
            f'<polygon points="30,252 42,252 42,270 46,275 46,282 26,282 26,275 30,270" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<text x="36" y="136" text-anchor="middle" font-size="40" font-weight="900" fill="#11212B">{label}</text>'
            f'<text x="36" y="164" text-anchor="middle" font-size="26" font-weight="800" fill="#11212B">{vol_txt}</text>'
            f'<text x="36" y="304" text-anchor="middle" font-size="18" font-weight="800" fill="{colors["TEXT"]}">{vol_txt} / {max_txt} mL</text>'
            f'</g>'
        )

    svg = (
        f'<div style="background:transparent;padding:0;margin:0;">'
        f'<svg viewBox="0 0 640 430" width="100%" xmlns="http://www.w3.org/2000/svg">'
        f'{syringe(22, "A", ratio_mc, vol_mc, max_mc, colors["MC"])}'
        f'{syringe(122, "B", ratio_sf, vol_sf, max_sf, colors["SF"])}'
        f'<g transform="translate(22,346)">'
        f'<text x="0" y="-12" font-size="18" font-weight="800" fill="{colors["TEXT"]}">Canales de inyección</text>'
        f'<g transform="translate(0,10)">'
        f'<rect x="0" y="0" width="145" height="42" rx="10" fill="#15191E" stroke="#2E3943" stroke-width="1.6"/>'
        f'<rect x="8" y="8" width="32" height="26" rx="7" fill="{colors["MC"]}"/>'
        f'<text x="24" y="27" text-anchor="middle" font-size="18" font-weight="800" fill="#11212B">A</text>'
        f'<line x1="52" y1="21" x2="108" y2="21" stroke="#F6F7FB" stroke-width="3.5" stroke-linecap="round"/>'
        f'<polygon points="108,14 121,21 108,28" fill="#F6F7FB"/>'
        f'<text x="132" y="27" text-anchor="middle" font-size="16" font-weight="800" fill="{colors["TEXT"]}">MC</text>'
        f'</g>'
        f'<g transform="translate(0,60)">'
        f'<rect x="0" y="0" width="145" height="42" rx="10" fill="#15191E" stroke="#2E3943" stroke-width="1.6"/>'
        f'<rect x="8" y="8" width="32" height="26" rx="7" fill="{colors["SF"]}"/>'
        f'<text x="24" y="27" text-anchor="middle" font-size="18" font-weight="800" fill="#11212B">B</text>'
        f'<line x1="52" y1="21" x2="108" y2="21" stroke="#F6F7FB" stroke-width="3.5" stroke-linecap="round"/>'
        f'<polygon points="108,14 121,21 108,28" fill="#F6F7FB"/>'
        f'<text x="132" y="27" text-anchor="middle" font-size="16" font-weight="800" fill="{colors["TEXT"]}">SF</text>'
        f'</g>'
        f'</g>'

        f'<g transform="translate(360,24)">'
        f'<rect x="0" y="0" width="72" height="34" rx="4" fill="#97B8D0"/>'
        f'<rect x="84" y="0" width="72" height="34" rx="4" fill="#97B8D0"/>'
        f'<rect x="168" y="0" width="72" height="34" rx="4" fill="#97B8D0"/>'
        f'<text x="36" y="22" text-anchor="middle" font-size="15" font-weight="800" fill="#F5F7FA">Caudal</text>'
        f'<text x="120" y="22" text-anchor="middle" font-size="15" font-weight="800" fill="#F5F7FA">Volumen</text>'
        f'<text x="204" y="22" text-anchor="middle" font-size="15" font-weight="800" fill="#F5F7FA">Duración</text>'
        f'</g>'

        f'{phase_rows_str}'
        f'</svg></div>'
    )
    return svg


# ─── Persistencia ───────────────────────────────────────────────────────────
def _build_store(**kwargs):
    """Acumula valores del formulario en st.session_state['inyectora_store']."""
    prev = st.session_state.get("inyectora_store", {})
    prev.update(kwargs)
    st.session_state["inyectora_store"] = prev


# ─── Render principal ───────────────────────────────────────────────────────
def render_inyectora():
    """Entrypoint del módulo: renderiza la TAB 4 (Jeringa Inyectora) completa."""
    vol_max_mc = MAX_JERINGA
    vol_max_sf = MAX_JERINGA

    n_fases_default = int(st.session_state.get("n_fases_iny", 2))
    fases_data = []

    # VVP actual
    vvp_default = st.session_state.get("vvp_gauge_widget", VVP_GAUGE[1])
    vvp_gauge = vvp_default if vvp_default in VVP_GAUGE else VVP_GAUGE[1]

    # Layout principal: izquierda más grande para la visualización
    left_col, right_col = st.columns([1.45, 1.0], gap="large")

    # ── Columna derecha: configuración de fases ──
    with right_col:
        _panel_header("💉", "Fases de inyección")

        n_fases = st.number_input(
            "Número de fases",
            min_value=1,
            max_value=6,
            value=n_fases_default,
            key="n_fases_iny",
        )

        for i in range(int(n_fases)):
            with st.expander(f"Fase {i+1}", expanded=(i == 0)):
                form_col, empty_col = st.columns([1, 1])

                with form_col:
                    sol = selectbox_con_placeholder(
                        "Solución",
                        ["MC", "SF", "PAUSA"],
                        key=f"sol_{i}",
                        value=st.session_state.get(f"sol_{i}"),
                    )

                    if sol == "PAUSA":
                        duracion_fase = st.number_input(
                            "Duración (sg)",
                            min_value=2,
                            max_value=30,
                            value=int(st.session_state.get(f"dur_pause_{i}", 10)),
                            step=1,
                            key=f"dur_pause_{i}",
                        )
                        vol = 0
                        caud = 0

                    elif sol is None:
                        duracion_fase = 0
                        vol = 0
                        caud = 0

                    else:
                        vol = selectbox_con_placeholder(
                            "Volumen (mL)",
                            list(range(0, 185, 5)),
                            key=f"vol_{i}",
                            value=st.session_state.get(f"vol_{i}_val", 50),
                        )

                        caud = selectbox_con_placeholder(
                            "Caudal (mL/sg)",
                            CAUDAL_OPCIONES,
                            key=f"caud_{i}",
                            value=st.session_state.get(f"caud_{i}_val", CAUDAL_OPCIONES[5]),
                        )

                        vol_num = vol if vol is not None else 0
                        caud_num = caud if caud is not None else 0
                        duracion_fase = round(vol_num / caud_num, 1) if caud_num and caud_num > 0 else 0
                        vol = vol_num
                        caud = caud_num

                    st.caption(f"Duración: {duracion_fase} sg")

                with empty_col:
                    st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

                fases_data.append({
                    "solucion": sol,
                    "volumen": vol,
                    "caudal": caud,
                    "duracion": duracion_fase,
                })

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        vvp_gauge = selectbox_con_placeholder(
            "VVP (Gauge)",
            VVP_GAUGE,
            key="vvp_gauge_widget",
            value=vvp_gauge,
        )

    # ── Cálculos agregados ──
    vol_total_mc = sum(f["volumen"] for f in fases_data if f["solucion"] == "MC")
    vol_total_sf = sum(f["volumen"] for f in fases_data if f["solucion"] == "SF")
    dur_total = sum(f["duracion"] for f in fases_data)

    caudal_alto = any(
        (f["caudal"] or 0) > 3.0 for f in fases_data if f["solucion"] not in (None, "PAUSA")
    )

    # ── Columna izquierda: visualización SVG de la inyectora ──
    with left_col:
        _panel_header("🧴", "Llenado de la Inyectora")
        st.markdown(
            render_inyectora_svg(
                vol_total_mc, vol_total_sf, vol_max_mc, vol_max_sf, fases_data, vvp_gauge
            ),
            unsafe_allow_html=True,
        )

        if vol_total_mc > vol_max_mc:
            st.warning(
                f"⚠️ Volumen de contraste ({vol_total_mc} mL) supera la capacidad fija ({vol_max_mc} mL)"
            )

        if vol_total_sf > vol_max_sf:
            st.warning(
                f"⚠️ Volumen de suero ({vol_total_sf} mL) supera la capacidad fija ({vol_max_sf} mL)"
            )

        if vvp_gauge is not None and vvp_gauge >= 22 and caudal_alto:
            st.warning(
                "⚠️ Calibre VVP puede ser insuficiente para el caudal seleccionado. "
                "Se recomienda VVP 18-20G para caudales altos."
            )

    # ── Persistencia ──
    _build_store(
        n_fases=int(n_fases),
        fases_data=fases_data,
        vol_total_mc=vol_total_mc,
        vol_total_sf=vol_total_sf,
        dur_total=dur_total,
        vvp_gauge=vvp_gauge,
    )

    return st.session_state["inyectora_store"]
