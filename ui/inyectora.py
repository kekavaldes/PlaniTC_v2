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
        f = fases_data[i] if i < len(fases_data) else {"solucion": None, "volumen": 0, "caudal": 0, "duracion": 0}
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
            f"""
            <g transform="translate(500,{105 + i*78})">
                <text x="-18" y="32" text-anchor="end" font-size="26" font-weight="700" fill="{colors["TEXT"]}">{label}</text>
                <rect x="0" y="0" width="100" height="54" rx="0" fill="{row_fill}" opacity="0.98"/>
                <rect x="126" y="0" width="100" height="54" rx="0" fill="{row_fill}" opacity="0.98"/>
                <rect x="252" y="0" width="100" height="54" rx="0" fill="#DCE7F1" opacity="0.98"/>
                <text x="50" y="35" text-anchor="middle" font-size="24" font-weight="800" fill="#11212B">{caud_txt}</text>
                <text x="176" y="35" text-anchor="middle" font-size="24" font-weight="800" fill="#11212B">{vol_txt}</text>
                <text x="302" y="35" text-anchor="middle" font-size="24" font-weight="800" fill="#11212B">{dur_txt}</text>
            </g>
            """
        )

    phase_rows_str = "".join(phase_rows)

    def syringe(x, label, ratio, vol, maxv, fill):
        h = 360
        y = 24
        inner_h = int(round(h * ratio))
        inner_y = y + h - inner_h
        try:
            vol_txt = int(vol) if float(vol).is_integer() else vol
            max_txt = int(maxv) if float(maxv).is_integer() else maxv
        except Exception:
            vol_txt = vol
            max_txt = maxv

        return (
            f"""
            <g transform="translate({x},78)">
                <rect x="0" y="0" width="96" height="16" rx="5" fill="{colors["BODY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>
                <rect x="10" y="16" width="76" height="360" rx="12" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="3"/>
                <rect x="10" y="{inner_y}" width="76" height="{max(inner_h,0)}" fill="{fill}"/>
                <rect x="10" y="196" width="76" height="3" fill="{colors["OUTLINE"]}" opacity="0.6"/>
                <polygon points="40,376 56,376 56,404 62,410 62,420 34,420 34,410 40,404" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="3"/>
                <text x="48" y="232" text-anchor="middle" font-size="54" font-weight="800" fill="#11212B">{label}</text>
                <text x="48" y="286" text-anchor="middle" font-size="38" font-weight="800" fill="#11212B">{vol_txt}</text>
                <text x="48" y="454" text-anchor="middle" font-size="24" font-weight="700" fill="{colors["TEXT"]}">{vol_txt} / {max_txt} mL</text>
            </g>
            """
        )

    svg = f"""
    <div style="background:transparent; padding:0; margin:0;">
        <svg viewBox="0 0 930 610" width="100%" xmlns="http://www.w3.org/2000/svg">
            {syringe(30, "A", ratio_mc, vol_mc, max_mc, colors["MC"])}
            {syringe(180, "B", ratio_sf, vol_sf, max_sf, colors["SF"])}

            <g transform="translate(28,522)">
                <text x="0" y="-12" font-size="20" font-weight="700" fill="{colors["TEXT"]}">Canales de inyección</text>

                <g transform="translate(0,10)">
                    <rect x="0" y="0" width="180" height="52" rx="12" fill="#15191E" stroke="#2E3943" stroke-width="2"/>
                    <rect x="12" y="10" width="42" height="32" rx="8" fill="{colors["MC"]}"/>
                    <text x="33" y="32" text-anchor="middle" font-size="24" font-weight="800" fill="#11212B">A</text>
                    <line x1="72" y1="26" x2="126" y2="26" stroke="#F6F7FB" stroke-width="5" stroke-linecap="round"/>
                    <polygon points="126,16 144,26 126,36" fill="#F6F7FB"/>
                    <text x="160" y="33" text-anchor="middle" font-size="18" font-weight="800" fill="{colors["TEXT"]}">MC</text>
                </g>

                <g transform="translate(0,70)">
                    <rect x="0" y="0" width="180" height="52" rx="12" fill="#15191E" stroke="#2E3943" stroke-width="2"/>
                    <rect x="12" y="10" width="42" height="32" rx="8" fill="{colors["SF"]}"/>
                    <text x="33" y="32" text-anchor="middle" font-size="24" font-weight="800" fill="#11212B">B</text>
                    <line x1="72" y1="26" x2="126" y2="26" stroke="#F6F7FB" stroke-width="5" stroke-linecap="round"/>
                    <polygon points="126,16 144,26 126,36" fill="#F6F7FB"/>
                    <text x="160" y="33" text-anchor="middle" font-size="18" font-weight="800" fill="{colors["TEXT"]}">SF</text>
                </g>
            </g>

            <g transform="translate(500,45)">
                <rect x="0" y="0" width="100" height="46" fill="#A9C5DC"/>
                <rect x="126" y="0" width="100" height="46" fill="#A9C5DC"/>
                <rect x="252" y="0" width="100" height="46" fill="#A9C5DC"/>
                <text x="50" y="31" text-anchor="middle" font-size="22" font-weight="800" fill="#F5F7FA">Caudal</text>
                <text x="176" y="31" text-anchor="middle" font-size="22" font-weight="800" fill="#F5F7FA">Volumen</text>
                <text x="302" y="31" text-anchor="middle" font-size="22" font-weight="800" fill="#F5F7FA">Duración</text>
            </g>

            {phase_rows_str}
        </svg>
    </div>
    """
    return svg


def _build_store(**kwargs):
    prev = st.session_state.get("inyectora_store", {})
    prev.update(kwargs)
    st.session_state["inyectora_store"] = prev


def render_inyectora():
    vol_max_mc = MAX_JERINGA
    vol_max_sf = MAX_JERINGA

    n_fases_default = int(st.session_state.get("n_fases_iny", 2))
    fases_data = []

    # 3 columnas para imagen + resumen | 2 columnas para parámetros
    left_col, right_col = st.columns([3, 2], gap="large")

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

                    vol_num = vol if vol is not None else 0
                    caud_num = caud if caud is not None else 0
                    duracion_fase = round(vol_num / caud_num, 1) if caud_num and caud_num > 0 else 0
                    vol = vol_num
                    caud = caud_num

                st.caption(f"Duración: {duracion_fase} sg")

                fases_data.append(
                    {
                        "solucion": sol,
                        "volumen": vol,
                        "caudal": caud,
                        "duracion": duracion_fase,
                    }
                )

    vol_total_mc = sum(f["volumen"] for f in fases_data if f["solucion"] == "MC")
    vol_total_sf = sum(f["volumen"] for f in fases_data if f["solucion"] == "SF")
    dur_total = sum(f["duracion"] for f in fases_data)

    vvp_default = st.session_state.get("vvp_gauge_widget", VVP_GAUGE[1])
    vvp_gauge = vvp_default if vvp_default in VVP_GAUGE else VVP_GAUGE[1]

    with left_col:
        st.markdown(
            render_inyectora_svg(
                vol_total_mc,
                vol_total_sf,
                vol_max_mc,
                vol_max_sf,
                fases_data,
                vvp_gauge,
            ),
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

        _panel_header("📊", "Resumen del Protocolo")

        met_col1, met_col2 = st.columns(2)
        with met_col1:
            _metric_card("Vol. total MC", f"{vol_total_mc} mL")
        with met_col2:
            _metric_card("Vol. total SF", f"{vol_total_sf} mL")

        met_col3, met_col4 = st.columns(2)
        with met_col3:
            _metric_card("Duración total", f"{dur_total} sg")
        with met_col4:
            _metric_card("Vol. total", f"{vol_total_mc + vol_total_sf} mL")

        st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)
        st.markdown("**Acceso venoso y capacidades**")

        acc_col1, acc_col2 = st.columns([1, 1.2])

        with acc_col1:
            vvp_gauge = selectbox_con_placeholder(
                "VVP (Gauge)",
                VVP_GAUGE,
                key="vvp_gauge_widget",
                value=vvp_gauge,
            )

        with acc_col2:
            st.markdown("<div style='height:0.2rem;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="
                    padding:0.85rem 1rem;
                    background:#1A1A1A;
                    border:1px solid #2E2E2E;
                    border-radius:10px;
                    min-height:92px;
                ">
                    <div style="
                        font-size:0.92rem;
                        font-weight:700;
                        margin-bottom:0.35rem;
                        color:#FFFFFF;
                    ">
                        Capacidad fija de jeringas
                    </div>
                    <div style="
                        font-size:1.1rem;
                        font-weight:800;
                        color:#F3F4F6;
                    ">
                        {MAX_JERINGA} mL / {MAX_JERINGA} cc
                    </div>
                    <div style="
                        font-size:0.82rem;
                        color:#C9D1D9;
                    ">
                        Aplicada por defecto a medio de contraste y suero.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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

    _build_store(
        n_fases=int(n_fases),
        fases_data=fases_data,
        vol_total_mc=vol_total_mc,
        vol_total_sf=vol_total_sf,
        dur_total=dur_total,
        vvp_gauge=vvp_gauge,
    )

    return st.session_state["inyectora_store"]
