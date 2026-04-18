"""
ui/inyectora.py
Módulo de Jeringa Inyectora para PlaniTC_v2.

Cubre la TAB 4 del simulador:
- Número de fases de inyección (1 a 6)
- Configuración por fase: solución (MC / SF / PAUSA), volumen, caudal, duración
- Visualización SVG de ambas jeringas (A = Medio de Contraste, B = Suero Fisiológico)
- Resumen del protocolo: volúmenes totales, duración total
- Validaciones: capacidad de jeringas y calibre VVP vs caudal
- Diagrama de fases de colores

Entrypoint: render_inyectora()
"""

import streamlit as st


# ─── Constantes del módulo ──────────────────────────────────────────────────
# NOTA: cuando centralices constantes en constants.py, mueve estas tres allí
# y haz `from constants import MAX_JERINGA, CAUDAL_OPCIONES, VVP_GAUGE`.
MAX_JERINGA = 180  # mL fijos para ambas jeringas (MC y SF)
CAUDAL_OPCIONES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
VVP_GAUGE = [18, 20, 22, 24]


# ─── Helpers reutilizables ──────────────────────────────────────────────────
# NOTA: también existe en ui/ingreso.py y ui/topograma.py. Candidato a core/utils.py.
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
        "PANEL": "#A9C5DC",
        "OUTLINE": "#2F3E4C",
        "BODY": "#E7EEF5",
        "EMPTY": "#DCE7F1",
        "BG": "#7FA5C2",
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
            f'<g transform="translate(390,{85 + i*58})">'
            f'<rect x="0" y="0" width="58" height="34" fill="{box_fill_left}" opacity="0.95"/>'
            f'<rect x="72" y="0" width="58" height="34" fill="{box_fill_mid}" opacity="0.95"/>'
            f'<rect x="144" y="0" width="58" height="34" fill="#CFE0EC" opacity="0.95"/>'
            f'<text x="29" y="23" text-anchor="middle" font-size="18" font-weight="700" fill="#11212B">{caud if sol != "PAUSA" else ""}</text>'
            f'<text x="101" y="23" text-anchor="middle" font-size="18" font-weight="700" fill="#11212B">{vol if sol != "PAUSA" else ""}</text>'
            f'<text x="173" y="23" text-anchor="middle" font-size="18" font-weight="700" fill="#11212B">{dur}</text>'
            f'<text x="-8" y="23" text-anchor="end" font-size="14" font-weight="700" fill="{colors["TEXT"]}">{"Pausa" if sol == "PAUSA" else sol}</text>'
            f'</g>'
        )
    phase_rows_str = "".join(phase_rows)

    def syringe(x, label, ratio, vol, maxv, fill):
        h = 220
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
            f'<g transform="translate({x},60)">'
            f'<rect x="0" y="0" width="64" height="10" rx="3" fill="{colors["BODY"]}" stroke="{colors["OUTLINE"]}" stroke-width="1.5"/>'
            f'<rect x="6" y="10" width="52" height="220" rx="8" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<rect x="6" y="{inner_y}" width="52" height="{max(inner_h,0)}" fill="{fill}"/>'
            f'<rect x="6" y="106" width="52" height="2" fill="{colors["OUTLINE"]}" opacity="0.75"/>'
            f'<polygon points="28,230 36,230 36,246 40,250 40,256 24,256 24,250 28,246" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<text x="32" y="122" text-anchor="middle" font-size="36" font-weight="800" fill="#11212B">{label}</text>'
            f'<text x="32" y="145" text-anchor="middle" font-size="22" font-weight="700" fill="#11212B">{vol_txt}</text>'
            f'<text x="32" y="276" text-anchor="middle" font-size="15" font-weight="700" fill="{colors["TEXT"]}">{vol_txt} / {max_txt} mL</text>'
            f'</g>'
        )

    svg = (
        f'<div style="background:transparent;padding:0;margin:0;">'
        f'<svg viewBox="0 0 620 410" width="100%" xmlns="http://www.w3.org/2000/svg">'
        f'{syringe(25, "A", ratio_mc, vol_mc, max_mc, colors["MC"])}'
        f'{syringe(120, "B", ratio_sf, vol_sf, max_sf, colors["SF"])}'
        f'<g transform="translate(24,332)">'
        f'<text x="0" y="-10" font-size="16" font-weight="700" fill="{colors["TEXT"]}">Canales de inyección</text>'
        f'<g transform="translate(0,8)">'
        f'<rect x="0" y="0" width="134" height="38" rx="10" fill="#15191E" stroke="#2E3943" stroke-width="1.6"/>'
        f'<rect x="8" y="7" width="30" height="24" rx="7" fill="{colors["MC"]}"/>'
        f'<text x="23" y="24" text-anchor="middle" font-size="18" font-weight="800" fill="#11212B">A</text>'
        f'<line x1="50" y1="19" x2="101" y2="19" stroke="#F6F7FB" stroke-width="3" stroke-linecap="round"/>'
        f'<polygon points="101,12 113,19 101,26" fill="#F6F7FB"/>'
        f'<text x="122" y="24" text-anchor="middle" font-size="15" font-weight="800" fill="{colors["TEXT"]}">MC</text>'
        f'</g>'
        f'<g transform="translate(0,58)">'
        f'<rect x="0" y="0" width="134" height="38" rx="10" fill="#15191E" stroke="#2E3943" stroke-width="1.6"/>'
        f'<rect x="8" y="7" width="30" height="24" rx="7" fill="{colors["SF"]}"/>'
        f'<text x="23" y="24" text-anchor="middle" font-size="18" font-weight="800" fill="#11212B">B</text>'
        f'<line x1="50" y1="19" x2="101" y2="19" stroke="#F6F7FB" stroke-width="3" stroke-linecap="round"/>'
        f'<polygon points="101,12 113,19 101,26" fill="#F6F7FB"/>'
        f'<text x="122" y="24" text-anchor="middle" font-size="15" font-weight="800" fill="{colors["TEXT"]}">SF</text>'
        f'</g>'
        f'</g>'
        f'<g transform="translate(392,42)"><rect x="0" y="0" width="58" height="30" fill="#97B8D0"/><rect x="72" y="0" width="58" height="30" fill="#97B8D0"/><rect x="144" y="0" width="58" height="30" fill="#97B8D0"/><text x="29" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="#F5F7FA">Caudal</text><text x="101" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="#F5F7FA">Volumen</text><text x="173" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="#F5F7FA">Duración</text></g>'
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

    top_left, top_right = st.columns([1.05, 1.35], gap="large")

    # ── Columna derecha: Configuración de fases ──
    with top_right:
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
                    # Fase sin solución seleccionada: no contribuye a totales
                    duracion_fase = 0
                    vol = 0
                    caud = 0
                else:
                    col_vol, col_caud = st.columns(2)
                    with col_vol:
                        vol = selectbox_con_placeholder(
                            "Volumen (mL)",
                            list(range(0, 185, 5)),
                            key=f"vol_{i}",
                            value=st.session_state.get(f"vol_{i}_val", 50),
                        )
                    with col_caud:
                        caud = selectbox_con_placeholder(
                            "Caudal (mL/sg)",
                            CAUDAL_OPCIONES,
                            key=f"caud_{i}",
                            value=st.session_state.get(f"caud_{i}_val", CAUDAL_OPCIONES[5]),
                        )

                    # Normalizar a numéricos para el cálculo
                    vol_num = vol if vol is not None else 0
                    caud_num = caud if caud is not None else 0
                    duracion_fase = round(vol_num / caud_num, 1) if caud_num and caud_num > 0 else 0
                    vol = vol_num
                    caud = caud_num

                st.caption(f"Duración: {duracion_fase} sg")
                fases_data.append({
                    "solucion": sol,
                    "volumen": vol,
                    "caudal": caud,
                    "duracion": duracion_fase,
                })

    # ── Cálculos agregados ──
    vol_total_mc = sum(f["volumen"] for f in fases_data if f["solucion"] == "MC")
    vol_total_sf = sum(f["volumen"] for f in fases_data if f["solucion"] == "SF")
    dur_total = sum(f["duracion"] for f in fases_data)

    # VVP actual (si ya estaba seleccionado en esta tab o viene de Ingreso)
    vvp_default = st.session_state.get("vvp_gauge_widget", VVP_GAUGE[1])
    vvp_gauge = vvp_default if vvp_default in VVP_GAUGE else VVP_GAUGE[1]

    # ── Columna izquierda: visualización SVG de la inyectora ──
    with top_left:
        st.markdown(
            render_inyectora_svg(
                vol_total_mc, vol_total_sf, vol_max_mc, vol_max_sf, fases_data, vvp_gauge
            ),
            unsafe_allow_html=True,
        )

    # ── Resumen del protocolo ──
    st.markdown("---")
    _panel_header("📊", "Resumen del Protocolo")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Vol. total MC", f"{vol_total_mc} mL")
        st.metric("Duración total", f"{dur_total} sg")
    with col_m2:
        st.metric("Vol. total SF", f"{vol_total_sf} mL")
        st.metric("Vol. total", f"{vol_total_mc + vol_total_sf} mL")

    st.markdown("**Acceso venoso y capacidades**")
    col_vvp, col_cap = st.columns(2)
    with col_vvp:
        vvp_gauge = selectbox_con_placeholder(
            "VVP (Gauge)",
            VVP_GAUGE,
            key="vvp_gauge_widget",
            value=vvp_gauge,
        )
    with col_cap:
        st.markdown("<div style='height: 0.2rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="padding:0.85rem 1rem; background:#1A1A1A;
                        border:1px solid #2E2E2E; border-radius:10px;">
                <div style="font-size:0.92rem; font-weight:700; margin-bottom:0.35rem; color:#FFFFFF;">
                    Capacidad fija de jeringas
                </div>
                <div style="font-size:1.1rem; font-weight:800; color:#F3F4F6;">
                    {MAX_JERINGA} mL / {MAX_JERINGA} cc
                </div>
                <div style="font-size:0.82rem; color:#C9D1D9;">
                    Aplicada por defecto a medio de contraste y suero.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Validaciones de volumen y caudal ──
    if vol_total_mc > vol_max_mc:
        st.warning(
            f"⚠️ Volumen de contraste ({vol_total_mc} mL) supera la capacidad fija ({vol_max_mc} mL)"
        )
    elif vol_total_mc > 0:
        st.info(
            f"✅ Volumen de contraste dentro del límite ({vol_total_mc}/{vol_max_mc} mL)"
        )

    if vol_total_sf > vol_max_sf:
        st.warning(
            f"⚠️ Volumen de suero ({vol_total_sf} mL) supera la capacidad fija ({vol_max_sf} mL)"
        )

    caudal_alto = any(
        (f["caudal"] or 0) > 3.0 for f in fases_data if f["solucion"] not in (None, "PAUSA")
    )
    if vvp_gauge is not None and vvp_gauge >= 22 and caudal_alto:
        st.warning(
            "⚠️ Calibre VVP puede ser insuficiente para el caudal seleccionado. "
            "Se recomienda VVP 18-20G para caudales altos."
        )

    # ── Diagrama de fases en bloques de colores ──
    st.markdown("**Diagrama de fases:**")
    for i, f in enumerate(fases_data):
        sol = f["solucion"]
        if sol == "MC":
            color, text_color = "#8FD16A", "#11212B"
        elif sol == "SF":
            color, text_color = "#63BFEA", "#11212B"
        elif sol == "PAUSA":
            color, text_color = "#757575", "white"
        else:
            color, text_color = "#2A2A2A", "#BFBFBF"

        sol_label = sol if sol is not None else "—"
        st.markdown(
            f"""
            <div style="background:{color}; color:{text_color}; border-radius:6px;
                        padding:6px 10px; margin:3px 0; font-size:0.85rem; font-weight:700;">
                Fase {i+1} — {sol_label} | {f["volumen"]} mL | {f["caudal"]} mL/sg | {f["duracion"]} sg
            </div>
            """,
            unsafe_allow_html=True,
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
