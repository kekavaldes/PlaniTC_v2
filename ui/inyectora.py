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

        sol_label = "Pausa" if sol == "PAUSA" else (sol if sol else "None")

        phase_rows.append(
            f'<g transform="translate(360,{78 + i*68})">'
            f'<rect x="0" y="0" width="72" height="42" rx="4" fill="{box_fill_left}" opacity="0.95"/>'
            f'<rect x="84" y="0" width="72" height="42" rx="4" fill="{box_fill_mid}" opacity="0.95"/>'
            f'<rect x="168" y="0" width="72" height="42" rx="4" fill="#CFE0EC" opacity="0.95"/>'
            f'<text x="36" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{caud if sol != "PAUSA" else ""}</text>'
            f'<text x="120" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{vol if sol != "PAUSA" else ""}</text>'
            f'<text x="204" y="27" text-anchor="middle" font-size="22" font-weight="800" fill="#11212B">{dur}</text>'
            f'<text x="-10" y="28" text-anchor="end" font-size="18" font-weight="800" fill="{colors["TEXT"]}">{sol_label}</text>'
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
        except Exception:
            vol_txt = vol

        return (
            f'<g transform="translate({x},58)">'
            f'<rect x="0" y="0" width="72" height="12" rx="3" fill="{colors["BODY"]}" stroke="{colors["OUTLINE"]}" stroke-width="1.5"/>'
            f'<rect x="8" y="12" width="56" height="240" rx="8" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<rect x="8" y="{inner_y}" width="56" height="{max(inner_h,0)}" fill="{fill}"/>'
            f'<rect x="8" y="120" width="56" height="2" fill="{colors["OUTLINE"]}" opacity="0.75"/>'
            f'<polygon points="30,252 42,252 42,270 46,275 46,282 26,282 26,275 30,270" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<text x="36" y="136" text-anchor="middle" font-size="40" font-weight="900" fill="#11212B">{label}</text>'
            f'<text x="36" y="164" text-anchor="middle" font-size="26" font-weight="800" fill="#11212B">{vol_txt}</text>'
            f'</g>'
        )

    mc_txt = int(vol_mc) if float(vol_mc).is_integer() else vol_mc
    sf_txt = int(vol_sf) if float(vol_sf).is_integer() else vol_sf
    max_mc_txt = int(max_mc) if float(max_mc).is_integer() else max_mc
    max_sf_txt = int(max_sf) if float(max_sf).is_integer() else max_sf

    svg = (
        f'<div style="background:transparent;padding:0;margin:0;">'
        f'<svg viewBox="0 0 640 470" width="100%" xmlns="http://www.w3.org/2000/svg">'
        f'{syringe(22, "A", ratio_mc, vol_mc, max_mc, colors["MC"])}'
        f'{syringe(122, "B", ratio_sf, vol_sf, max_sf, colors["SF"])}'

        # bloque inferior más abajo y más pequeño
        f'<g transform="translate(22,395)">'
        f'<text x="0" y="-10" font-size="10" font-weight="700" fill="{colors["TEXT"]}">Canales de inyección</text>'

        f'<text x="0" y="4" font-size="9" font-weight="700" fill="{colors["TEXT"]}">{mc_txt} / {max_mc_txt} mL</text>'
        f'<text x="88" y="4" font-size="9" font-weight="700" fill="{colors["TEXT"]}">{sf_txt} / {max_sf_txt} mL</text>'

        f'<g transform="translate(0,16)">'
        f'<rect x="0" y="0" width="82" height="22" rx="7" fill="#15191E" stroke="#2E3943" stroke-width="1.2"/>'
        f'<rect x="5" y="4" width="21" height="14" rx="4" fill="{colors["MC"]}"/>'
        f'<text x="15.5" y="15" text-anchor="middle" font-size="10" font-weight="800" fill="#11212B">A</text>'
        f'<line x1="32" y1="11" x2="60" y2="11" stroke="#F6F7FB" stroke-width="2" stroke-linecap="round"/>'
        f'<polygon points="60,6 69,11 60,16" fill="#F6F7FB"/>'
        f'<text x="76" y="15" text-anchor="middle" font-size="10" font-weight="800" fill="{colors["TEXT"]}">MC</text>'
        f'</g>'

        f'<g transform="translate(0,43)">'
        f'<rect x="0" y="0" width="82" height="22" rx="7" fill="#15191E" stroke="#2E3943" stroke-width="1.2"/>'
        f'<rect x="5" y="4" width="21" height="14" rx="4" fill="{colors["SF"]}"/>'
        f'<text x="15.5" y="15" text-anchor="middle" font-size="10" font-weight="800" fill="#11212B">B</text>'
        f'<line x1="32" y1="11" x2="60" y2="11" stroke="#F6F7FB" stroke-width="2" stroke-linecap="round"/>'
        f'<polygon points="60,6 69,11 60,16" fill="#F6F7FB"/>'
        f'<text x="76" y="15" text-anchor="middle" font-size="10" font-weight="800" fill="{colors["TEXT"]}">SF</text>'
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
