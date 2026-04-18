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

        phase_rows.append(
            f'<g transform="translate(360,{78 + i*68})">'
            f'<rect x="0" y="0" width="72" height="42" rx="4" fill="{color}" opacity="0.95"/>'
            f'<rect x="84" y="0" width="72" height="42" rx="4" fill="{color}" opacity="0.95"/>'
            f'<rect x="168" y="0" width="72" height="42" rx="4" fill="#CFE0EC" opacity="0.95"/>'
            f'<text x="36" y="27" text-anchor="middle" font-size="22" font-weight="800">{caud if sol != "PAUSA" else ""}</text>'
            f'<text x="120" y="27" text-anchor="middle" font-size="22" font-weight="800">{vol if sol != "PAUSA" else ""}</text>'
            f'<text x="204" y="27" text-anchor="middle" font-size="22" font-weight="800">{dur}</text>'
            f'<text x="-10" y="28" text-anchor="end" font-size="18" font-weight="800" fill="{colors["TEXT"]}">{sol}</text>'
            f'</g>'
        )

    def syringe(x, label, ratio, vol, maxv, fill):
        h = 240
        y = 10
        inner_h = int(round(h * ratio))
        inner_y = y + h - inner_h

        return (
            f'<g transform="translate({x},58)">'
            f'<rect x="8" y="12" width="56" height="240" rx="8" fill="{colors["EMPTY"]}" stroke="{colors["OUTLINE"]}" stroke-width="2"/>'
            f'<rect x="8" y="{inner_y}" width="56" height="{max(inner_h,0)}" fill="{fill}"/>'
            f'<text x="36" y="140" text-anchor="middle" font-size="40" font-weight="900">{label}</text>'
            f'<text x="36" y="170" text-anchor="middle" font-size="26" font-weight="800">{vol}</text>'
            f'</g>'
        )

    svg = (
        f'<svg viewBox="0 0 640 420" width="100%">'
        f'{syringe(22, "A", ratio_mc, vol_mc, max_mc, colors["MC"])}'
        f'{syringe(122, "B", ratio_sf, vol_sf, max_sf, colors["SF"])}'

        # 👇 ESTA ES LA PARTE QUE HICE MÁS CHICA
        f'<g transform="translate(22,350)">'
        f'<text x="0" y="-6" font-size="11" fill="{colors["TEXT"]}">Canales de inyección</text>'

        f'<text x="0" y="8" font-size="9" fill="{colors["TEXT"]}">{vol_mc}/{max_mc} mL</text>'
        f'<text x="80" y="8" font-size="9" fill="{colors["TEXT"]}">{vol_sf}/{max_sf} mL</text>'

        f'<g transform="translate(0,18)">'
        f'<rect width="75" height="20" rx="6" fill="#15191E"/>'
        f'<text x="12" y="14" font-size="10">A</text>'
        f'<text x="55" y="14" font-size="10">MC</text>'
        f'</g>'

        f'<g transform="translate(0,42)">'
        f'<rect width="75" height="20" rx="6" fill="#15191E"/>'
        f'<text x="12" y="14" font-size="10">B</text>'
        f'<text x="55" y="14" font-size="10">SF</text>'
        f'</g>'
        f'</g>'

        f'{"".join(phase_rows)}'
        f'</svg>'
    )

    return svg
