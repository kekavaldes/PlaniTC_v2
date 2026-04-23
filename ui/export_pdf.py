"""
ui/export_pdf.py
Exportación a PDF de toda la planificación del examen TC (PlaniTC_v2).

Lee el estado guardado en st.session_state (ingreso_store, topograma_sets,
exploraciones, reconstrucciones_por_exp, reformaciones_por_rec, inyectora_store,
imagenes_recon_por_id, imagenes_ref_por_id) y arma un PDF A4 con:

    1) Datos del paciente y preparación
    2) Topogramas (1..N sets)
    3) Adquisiciones
    4) Reconstrucciones (con imagen si fue subida)
    5) Reformaciones (con imágenes si fueron subidas)
    6) Inyectora (con visualización SVG → PNG)

Dependencias:
    pip install reportlab
    pip install cairosvg   # opcional: para incrustar la visualización de inyectora

Entrypoint: render_export_pdf()
"""

import io
import re
from datetime import datetime

import streamlit as st
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

# Motor SVG→PDF. Preferimos svglib (Python puro, funciona en Streamlit Cloud
# sin libs del sistema). cairosvg queda como fallback opcional.
try:
    from svglib.svglib import svg2rlg  # type: ignore
    HAS_SVGLIB = True
except Exception:
    HAS_SVGLIB = False

try:
    import cairosvg  # type: ignore
    HAS_CAIROSVG = True
except Exception:
    HAS_CAIROSVG = False

HAS_SVG_ENGINE = HAS_SVGLIB or HAS_CAIROSVG


# ──────────────────────────────────────────────────────────────────────────
# Estilos del PDF
# ──────────────────────────────────────────────────────────────────────────
def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PTitle", parent=ss["Title"],
            fontSize=22, leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4, alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "PH1", parent=ss["Heading1"],
            fontSize=16, leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10, spaceAfter=8, alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "PH2", parent=ss["Heading2"],
            fontSize=13, leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=8, spaceAfter=4, alignment=TA_LEFT,
        ),
        "h3": ParagraphStyle(
            "PH3", parent=ss["Heading3"],
            fontSize=11, leading=14,
            textColor=colors.HexColor("#334155"),
            spaceBefore=4, spaceAfter=2, alignment=TA_LEFT,
        ),
        "normal": ParagraphStyle(
            "PNormal", parent=ss["BodyText"],
            fontSize=9.5, leading=12,
            textColor=colors.HexColor("#0f172a"),
        ),
        "small": ParagraphStyle(
            "PSmall", parent=ss["BodyText"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#64748b"),
        ),
        "caption": ParagraphStyle(
            "PCaption", parent=ss["BodyText"],
            fontSize=8.5, leading=11,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        ),
    }


def _table_style_kv():
    return TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _table_style_grid():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ──────────────────────────────────────────────────────────────────────────
# Helpers generales
# ──────────────────────────────────────────────────────────────────────────
def _v(val, placeholder="—"):
    """Normaliza un valor para mostrarlo en el PDF."""
    if val is None:
        return placeholder
    s = str(val).strip()
    if not s or s.lower() == "seleccionar":
        return placeholder
    return s


def _alumnos_participantes_str():
    """Obtiene los nombres de alumnos participantes desde session_state."""
    return str(st.session_state.get("alumnos_participantes", "") or "").strip()


def _resolved_patient_name():
    """Obtiene el nombre del paciente con fallback al widget activo de Ingreso."""
    ingreso = st.session_state.get("ingreso_store", {}) or {}
    nombre = str(ingreso.get("nombre") or "").strip()
    if nombre:
        return nombre

    # Fallback al widget usado en ui/ingreso.py
    nombre_widget = str(st.session_state.get("nombre_paciente_widget") or "").strip()
    if nombre_widget:
        ingreso = dict(ingreso)
        ingreso["nombre"] = nombre_widget
        st.session_state["ingreso_store"] = ingreso
        return nombre_widget

    # Fallback adicional por si en alguna versión quedó otro nombre de key
    for k in ("nombre_paciente", "nombre_widget", "paciente_nombre"):
        val = str(st.session_state.get(k) or "").strip()
        if val:
            ingreso = dict(ingreso)
            ingreso["nombre"] = val
            st.session_state["ingreso_store"] = ingreso
            return val

    return ""


def _kv_table(rows, col_widths=(45 * mm, 120 * mm), sty=None):
    sty = sty or _styles()
    data = [
        [Paragraph(f"<b>{k}</b>", sty["normal"]),
         Paragraph(_v(v), sty["normal"])]
        for k, v in rows
    ]
    t = Table(data, colWidths=col_widths)
    t.setStyle(_table_style_kv())
    return t


def _grid_table(headers, rows, col_widths):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths)
    t.setStyle(_table_style_grid())
    return t


def _pil_bytes_to_flowable(img_bytes, max_w_mm=80, max_h_mm=80):
    """Convierte bytes de imagen a un RLImage escalado manteniendo aspecto."""
    if not img_bytes:
        return None
    try:
        im = PILImage.open(io.BytesIO(img_bytes))
        im.load()
    except Exception:
        return None

    w_px, h_px = im.size
    if w_px <= 0 or h_px <= 0:
        return None

    max_w_pt = max_w_mm * mm
    max_h_pt = max_h_mm * mm
    ratio = min(max_w_pt / w_px, max_h_pt / h_px)
    draw_w = w_px * ratio
    draw_h = h_px * ratio

    buf = io.BytesIO()
    if im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    im.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=draw_w, height=draw_h)




def _snapshot_bytes(snapshot):
    if isinstance(snapshot, dict):
        return snapshot.get("bytes")
    return None

def _extraer_svg(svg_str):
    """Extrae solo el tag <svg>...</svg> si viene envuelto en HTML."""
    if not svg_str:
        return None
    m = re.search(r"<svg[\s\S]*?</svg>", svg_str)
    return m.group(0) if m else svg_str


def _svg_a_drawing(svg_str):
    """SVG → reportlab Drawing (vectorial). Usa svglib. None si falla."""
    if not HAS_SVGLIB:
        return None
    clean = _extraer_svg(svg_str)
    if not clean:
        return None
    try:
        return svg2rlg(io.StringIO(clean))
    except Exception:
        return None


def _svg_a_png_bytes(svg_str, scale=2.0):
    """SVG → PNG bytes. Fallback con cairosvg. None si no disponible."""
    if not HAS_CAIROSVG:
        return None
    clean = _extraer_svg(svg_str)
    if not clean:
        return None
    try:
        return cairosvg.svg2png(bytestring=clean.encode("utf-8"), scale=scale)
    except Exception:
        return None


def _scale_drawing(drawing, max_w_pt, max_h_pt):
    """Escala un Drawing de reportlab para caber en (max_w_pt, max_h_pt)."""
    if drawing is None or drawing.width <= 0 or drawing.height <= 0:
        return drawing
    ratio = min(max_w_pt / drawing.width, max_h_pt / drawing.height)
    drawing.width *= ratio
    drawing.height *= ratio
    drawing.scale(ratio, ratio)
    return drawing


# ──────────────────────────────────────────────────────────────────────────
# Secciones del PDF
# ──────────────────────────────────────────────────────────────────────────
def _seccion_portada(story, plan, sty):
    ingreso = plan.get("ingreso_store", {}) or {}
    alumnos = (plan.get("alumnos_participantes") or "").strip()

    story.append(Paragraph("Planificación de Examen TC", sty["title"]))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sty["small"],
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Participantes de la actividad", sty["h2"]))
    story.append(_kv_table([
        ("Alumno(s)", alumnos),
    ], sty=sty))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Datos del paciente", sty["h2"]))
    story.append(_kv_table([
        ("Nombre", ingreso.get("nombre")),
        ("Fecha de nacimiento", ingreso.get("fecha_nacimiento")),
        ("Edad", f"{ingreso.get('edad')} años" if ingreso.get("edad") is not None else None),
        ("Peso", f"{ingreso.get('peso')} kg" if ingreso.get("peso") is not None else None),
        ("Diagnóstico", ingreso.get("diagnostico")),
    ], sty=sty))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Preparación", sty["h2"]))
    rows = [
        ("¿Embarazo?", ingreso.get("embarazo")),
        ("¿Requiere creatinina?", "Sí" if ingreso.get("requiere_creatinina") else "No"),
    ]
    if ingreso.get("requiere_creatinina"):
        creat = ingreso.get("creatinina_serica")
        clear = ingreso.get("clearance")
        rows += [
            ("Sexo (clearance)", ingreso.get("sexo_clearance")),
            ("Creatinina sérica", f"{creat} mg/dL" if creat is not None else None),
            ("Clearance estimado", f"{clear} mL/min" if clear is not None else None),
        ]
    rows.append(("¿Contraste EV?", "Sí" if ingreso.get("contraste_ev") else "No"))
    if ingreso.get("contraste_ev"):
        rows += [
            ("VVP", ingreso.get("vvp")),
            ("Método de inyección", ingreso.get("metodo_inyeccion")),
        ]
        if ingreso.get("metodo_inyeccion") == "INYECCIÓN MANUAL":
            rows.append(("Cantidad de contraste", ingreso.get("cantidad_contraste")))

    story.append(_kv_table(rows, sty=sty))


def _seccion_topogramas(story, plan, sty):
    sets = plan.get("topograma_sets") or []
    # Compat: si no hay sets pero sí store, tratarlo como set único
    if not sets:
        store = plan.get("topograma_store") or {}
        if store:
            sets = [store]
    if not sets:
        return

    story.append(PageBreak())
    story.append(Paragraph("Topogramas", sty["h1"]))

    for idx, s in enumerate(sets):
        titulo = s.get("label") or f"Set {idx + 1}"
        story.append(Paragraph(f"{idx + 1}. {titulo}", sty["h2"]))

        story.append(_kv_table([
            ("Región anatómica", s.get("region_anat")),
            ("Examen", s.get("examen")),
            ("Posición paciente", s.get("posicion") or s.get("t1_posicion_paciente")),
            ("Entrada paciente", s.get("entrada") or s.get("t1_entrada_paciente")),
            ("Posición tubo", s.get("t1pt") or s.get("t1_posicion_tubo")),
            ("Posición extremidades", s.get("extremidades")),
        ], sty=sty))
        snap_topo = _snapshot_bytes((plan.get("canvas_snapshots_topo_por_set") or {}).get(idx))
        if snap_topo:
            img_flow = _pil_bytes_to_flowable(snap_topo, max_w_mm=165, max_h_mm=85)
            if img_flow is not None:
                story.append(Spacer(1, 5))
                story.append(img_flow)
        story.append(Spacer(1, 6))

        story.append(Paragraph("Topograma 1", sty["h3"]))
        story.append(_kv_table([
            ("Inicio (referencia)", s.get("t1_ini_ref")),
            ("Fin (referencia)", s.get("t1_fin_ref")),
            ("Centraje inicio", s.get("t1_centraje_inicio")),
            ("Longitud (mm)", s.get("t1l")),
            ("Dirección", s.get("t1dir")),
            ("Instrucción de voz", s.get("t1vz")),
            ("kV / mA", "100 / 40 (fijo)"),
            ("Estado", "Iniciado" if s.get("topograma_iniciado") else "No iniciado"),
        ], sty=sty))

        if s.get("aplica_topo2") or s.get("aplica_topograma_2"):
            story.append(Spacer(1, 6))
            story.append(Paragraph("Topograma 2", sty["h3"]))
            story.append(_kv_table([
                ("Posición paciente", s.get("t2_posicion")),
                ("Entrada paciente", s.get("t2_entrada")),
                ("Posición tubo", s.get("t2pt")),
                ("Posición extremidades", s.get("t2_extremidades")),
                ("Inicio (referencia)", s.get("t2_ini_ref")),
                ("Fin (referencia)", s.get("t2_fin_ref")),
                ("Centraje inicio", s.get("t2_centraje_inicio")),
                ("Longitud (mm)", s.get("t2l")),
                ("Dirección", s.get("t2dir")),
                ("Instrucción de voz", s.get("t2vz")),
                ("Estado", "Iniciado" if s.get("topograma2_iniciado") else "No iniciado"),
            ], sty=sty))

        story.append(Spacer(1, 12))


def _seccion_adquisiciones(story, plan, sty):
    exps = plan.get("exploraciones") or []
    if not exps:
        return

    story.append(PageBreak())
    story.append(Paragraph("Adquisiciones", sty["h1"]))

    for i, exp in enumerate(exps):
        nombre = exp.get("nombre") or f"Adquisición {i + 1}"
        story.append(Paragraph(f"{i + 1}. {nombre}", sty["h2"]))

        rows = [
            ("Tipo de exploración", exp.get("tipo_exp")),
            ("Modulación de corriente", exp.get("mod_corriente")),
            ("mAs", exp.get("mas_val")),
            ("Índice de ruido", exp.get("ind_ruido")),
            ("Índice de calidad", exp.get("ind_cal")),
            ("Rango mA", exp.get("rango_ma")),
            ("kVp", exp.get("kvp")),
            ("Doble muestreo", exp.get("doble_muestreo")),
            ("Configuración detector", exp.get("conf_det")),
            ("Cobertura tabla", exp.get("cobertura_tabla")),
            ("Grosor prospectivo", exp.get("grosor_prosp")),
            ("SFOV", exp.get("sfov")),
            ("Pitch", exp.get("pitch")),
            ("Rotación tubo (sg)", exp.get("rot_tubo")),
            ("Instrucción de voz", exp.get("voz_adq")),
            ("Retardo (sg)", exp.get("retardo")),
        ]

        tipo = (exp.get("tipo_exp") or "").upper()
        if "BOLUS" in tipo:
            rows += [
                ("Período", exp.get("periodo")),
                ("N° de imágenes", exp.get("n_imagenes")),
                ("Posición de corte", exp.get("posicion_corte")),
                ("Umbral de tracking", exp.get("umbral_tracking")),
            ]

        rows += [
            ("Inicio (referencia)", exp.get("inicio_ref")),
            ("Fin (referencia)", exp.get("fin_ref")),
            ("Inicio (mm)", exp.get("ini_mm")),
            ("Fin (mm)", exp.get("fin_mm")),
        ]
        obs = exp.get("observaciones")
        if obs:
            rows.append(("Observaciones", obs))

        params_table = _kv_table(rows, sty=sty)
        snap_adq = _snapshot_bytes((plan.get("canvas_snapshots_adq_por_exp") or {}).get(exp.get("id")))
        img_flow = _pil_bytes_to_flowable(snap_adq, max_w_mm=75, max_h_mm=75) if snap_adq else None
        if img_flow is not None:
            fila = Table([[params_table, img_flow]], colWidths=(110 * mm, 60 * mm))
            fila.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(fila)
        else:
            story.append(params_table)
        story.append(Spacer(1, 10))


def _seccion_reconstrucciones(story, plan, sty):
    recons_map = plan.get("reconstrucciones_por_exp") or {}
    imagenes_rec = plan.get("imagenes_recon_por_id") or {}
    exps = plan.get("exploraciones") or []

    if not any(recons_map.get(e.get("id")) for e in exps):
        return

    story.append(PageBreak())
    story.append(Paragraph("Reconstrucciones", sty["h1"]))

    for i_exp, exp in enumerate(exps):
        lista = recons_map.get(exp.get("id"), [])
        if not lista:
            continue

        nombre_exp = exp.get("nombre") or f"Adquisición {i_exp + 1}"
        story.append(Paragraph(nombre_exp, sty["h2"]))

        for j, rec in enumerate(lista):
            nombre_rec = rec.get("nombre") or f"Reconstrucción {j + 1}"
            block = [Paragraph(nombre_rec, sty["h3"])]

            ww = rec.get("ww_val")
            wl = rec.get("wl_val")
            ww_wl = f"{ww} / {wl}" if ww is not None and wl is not None else None

            params_table = _kv_table([
                ("Fase", rec.get("fase_recons")),
                ("Tipo", rec.get("tipo_recons")),
                ("Algoritmo iterativo", rec.get("algoritmo_iter")),
                ("Nivel / %", rec.get("nivel_iter")),
                ("Kernel", rec.get("kernel_sel")),
                ("Grosor", rec.get("grosor_recons")),
                ("Incremento", rec.get("incremento")),
                ("Preset ventana", rec.get("ventana_preset")),
                ("WW / WL", ww_wl),
                ("DFOV", rec.get("dfov")),
                ("Inicio reconstrucción", rec.get("inicio_recons")),
                ("Fin reconstrucción", rec.get("fin_recons")),
            ], col_widths=(40 * mm, 65 * mm), sty=sty)

            snap_rec = _snapshot_bytes((plan.get("canvas_snapshots_recon_por_id") or {}).get(rec.get("id")))
            img_data = imagenes_rec.get(rec.get("id"))
            img_flow = None
            if snap_rec:
                img_flow = _pil_bytes_to_flowable(snap_rec, max_w_mm=55, max_h_mm=55)
            elif img_data and img_data.get("bytes"):
                img_flow = _pil_bytes_to_flowable(img_data["bytes"], max_w_mm=55, max_h_mm=55)

            if img_flow is not None:
                fila = Table(
                    [[params_table, img_flow]],
                    colWidths=(105 * mm, 65 * mm),
                )
                fila.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]))
                block.append(fila)
            else:
                block.append(params_table)

            block.append(Spacer(1, 8))
            story.append(KeepTogether(block))


def _seccion_reformaciones(story, plan, sty):
    refs_map = plan.get("reformaciones_por_rec") or {}
    imagenes_ref = plan.get("imagenes_ref_por_id") or {}
    recons_map = plan.get("reconstrucciones_por_exp") or {}
    exps = plan.get("exploraciones") or []

    hay = any(
        refs_map.get(r.get("id"))
        for lst in recons_map.values()
        for r in (lst or [])
    )
    if not hay:
        return

    story.append(PageBreak())
    story.append(Paragraph("Reformaciones", sty["h1"]))

    for i_exp, exp in enumerate(exps):
        recons = recons_map.get(exp.get("id"), [])
        if not recons:
            continue
        escribio_exp = False

        for j, rec in enumerate(recons):
            lst = refs_map.get(rec.get("id"), [])
            if not lst:
                continue

            if not escribio_exp:
                nombre_exp = exp.get("nombre") or f"Adquisición {i_exp + 1}"
                story.append(Paragraph(nombre_exp, sty["h2"]))
                escribio_exp = True

            nombre_rec = rec.get("nombre") or f"Reconstrucción {j + 1}"
            story.append(Paragraph(nombre_rec, sty["h3"]))

            for k, ref in enumerate(lst):
                titulo_ref = f"Reformación {k + 1}" + (
                    f" — {ref.get('tipo')}" if ref.get("tipo") else ""
                )
                block = [
                    Paragraph(titulo_ref, sty["h3"]),
                    _kv_table([
                        ("Tipo", ref.get("tipo")),
                        ("Subtipo", ref.get("subtipo")),
                        ("Plano", ref.get("plano")),
                        ("Grosor", ref.get("grosor")),
                        ("Distancia", ref.get("distancia")),
                        ("N° de vistas", ref.get("n_vistas")),
                        ("Ángulo", ref.get("angulo")),
                    ], sty=sty),
                ]

                # Hasta 3 imágenes por reformación (img1..img3)
                snap_ref = (plan.get("canvas_snapshots_ref_por_id") or {}).get(ref.get("id"))
                ref_imgs = imagenes_ref.get(ref.get("id"))
                flows = []
                for key_img in ("img1", "img2", "img3"):
                    sub = None
                    if isinstance(snap_ref, dict):
                        sub = snap_ref.get(key_img)
                    if not (isinstance(sub, dict) and sub.get("bytes")) and isinstance(ref_imgs, dict):
                        sub = ref_imgs.get(key_img)
                    if isinstance(sub, dict) and sub.get("bytes"):
                        flow = _pil_bytes_to_flowable(
                            sub["bytes"], max_w_mm=55, max_h_mm=55
                        )
                        if flow is not None:
                            flows.append(flow)

                if flows:
                    # Grid horizontal de hasta 3 imágenes
                    while len(flows) < 3:
                        flows.append("")
                    fila = Table([flows], colWidths=(60 * mm, 60 * mm, 60 * mm))
                    fila.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ]))
                    block.append(fila)

                block.append(Spacer(1, 8))
                story.append(KeepTogether(block))


def _seccion_inyectora(story, plan, sty):
    iny = plan.get("inyectora_store") or {}
    if not iny:
        return

    story.append(PageBreak())
    story.append(Paragraph("Inyectora", sty["h1"]))

    story.append(_kv_table([
        ("N° de fases", iny.get("n_fases")),
        ("Volumen total MC",
         f"{iny.get('vol_total_mc')} mL" if iny.get("vol_total_mc") is not None else None),
        ("Volumen total SF",
         f"{iny.get('vol_total_sf')} mL" if iny.get("vol_total_sf") is not None else None),
        ("Duración total",
         f"{iny.get('dur_total')} sg" if iny.get("dur_total") is not None else None),
    ], sty=sty))
    story.append(Spacer(1, 10))

    fases = iny.get("fases_data") or []
    if fases:
        header = ["Fase", "Solución", "Volumen (mL)", "Caudal (mL/sg)", "Duración (sg)"]
        rows = []
        for i, f in enumerate(fases):
            sol = f.get("solucion")
            es_pausa = (sol == "PAUSA")
            rows.append([
                str(i + 1),
                _v(sol, "—") if sol else "—",
                "—" if es_pausa else _v(f.get("volumen")),
                "—" if es_pausa else _v(f.get("caudal")),
                _v(f.get("duracion")),
            ])
        story.append(Paragraph("Fases de inyección", sty["h2"]))
        story.append(_grid_table(
            header, rows,
            col_widths=(15 * mm, 35 * mm, 35 * mm, 40 * mm, 35 * mm),
        ))
        story.append(Spacer(1, 10))

    # Visualización: preferir Drawing vectorial (svglib); si no, PNG (cairosvg)
    svg_str = iny.get("svg_snapshot")
    if svg_str:
        story.append(Paragraph("Visualización de la inyectora", sty["h2"]))

        drawing = _svg_a_drawing(svg_str)
        if drawing is not None:
            _scale_drawing(drawing, 160 * mm, 110 * mm)
            story.append(drawing)
        else:
            png = _svg_a_png_bytes(svg_str, scale=2.0)
            if png:
                try:
                    im = PILImage.open(io.BytesIO(png))
                    w_px, h_px = im.size
                    max_w = 160 * mm
                    max_h = 110 * mm
                    ratio = min(max_w / w_px, max_h / h_px)
                    story.append(RLImage(
                        io.BytesIO(png),
                        width=w_px * ratio,
                        height=h_px * ratio,
                    ))
                except Exception:
                    pass
            elif not HAS_SVG_ENGINE:
                story.append(Paragraph(
                    "<i>(Instala <b>svglib</b> para incluir la visualización "
                    "gráfica de la inyectora)</i>",
                    sty["small"],
                ))


# ──────────────────────────────────────────────────────────────────────────
# Snapshot del plan y generación del PDF
# ──────────────────────────────────────────────────────────────────────────
def _recopilar_plan():
    """Snapshot de todo lo planificado desde session_state."""
    iny_store = dict(st.session_state.get("inyectora_store", {}) or {})

    # Intentamos generar el SVG actual de la inyectora para incrustarlo.
    try:
        from ui.inyectora import render_inyectora_svg, MAX_JERINGA
        fases = iny_store.get("fases_data") or []
        iny_store["svg_snapshot"] = render_inyectora_svg(
            iny_store.get("vol_total_mc", 0),
            iny_store.get("vol_total_sf", 0),
            MAX_JERINGA,
            MAX_JERINGA,
            fases,
        )
    except Exception:
        iny_store["svg_snapshot"] = None

    return {
        "alumnos_participantes": _alumnos_participantes_str(),
        "ingreso_store": dict(st.session_state.get("ingreso_store", {}) or {}),
        "topograma_sets": list(st.session_state.get("topograma_sets", []) or []),
        "topograma_store": dict(st.session_state.get("topograma_store", {}) or {}),
        "exploraciones": list(st.session_state.get("exploraciones", []) or []),
        "reconstrucciones_por_exp": dict(st.session_state.get("reconstrucciones_por_exp", {}) or {}),
        "imagenes_recon_por_id": dict(st.session_state.get("imagenes_recon_por_id", {}) or {}),
        "reformaciones_por_rec": dict(st.session_state.get("reformaciones_por_rec", {}) or {}),
        "imagenes_ref_por_id": dict(st.session_state.get("imagenes_ref_por_id", {}) or {}),
        "canvas_snapshots_topo_por_set": dict(st.session_state.get("canvas_snapshots_topo_por_set", {}) or {}),
        "canvas_snapshots_adq_por_exp": dict(st.session_state.get("canvas_snapshots_adq_por_exp", {}) or {}),
        "canvas_snapshots_recon_por_id": dict(st.session_state.get("canvas_snapshots_recon_por_id", {}) or {}),
        "canvas_snapshots_ref_por_id": dict(st.session_state.get("canvas_snapshots_ref_por_id", {}) or {}),
        "inyectora_store": iny_store,
    }


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawRightString(
        A4[0] - 15 * mm, 10 * mm,
        f"PlaniTC_v2 — Página {doc.page}"
    )
    canvas.restoreState()


def construir_pdf(plan=None) -> bytes:
    """Arma el PDF completo y retorna sus bytes."""
    if plan is None:
        plan = _recopilar_plan()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Planificación TC",
        author="PlaniTC_v2",
    )
    sty = _styles()
    story = []

    _seccion_portada(story, plan, sty)
    _seccion_topogramas(story, plan, sty)
    _seccion_adquisiciones(story, plan, sty)
    _seccion_reconstrucciones(story, plan, sty)
    _seccion_reformaciones(story, plan, sty)
    _seccion_inyectora(story, plan, sty)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────
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


def render_export_pdf():
    """Entrypoint de la pestaña de exportación a PDF."""
    _panel_header("📄", "Exportar planificación a PDF")

    alumnos_default = _alumnos_participantes_str()
    alumnos_participantes = st.text_area(
        "Nombre del alumno o de los alumnos participantes",
        value=alumnos_default,
        key="alumnos_participantes",
        height=90,
        placeholder="",
        help="Completa aquí el nombre de todos los estudiantes que participaron en la actividad. Este dato se incluirá en la portada del PDF.",
    )

    if not HAS_SVG_ENGINE:
        st.info(
            "Para incluir la visualización gráfica de la inyectora en el PDF, "
            "instala **svglib**: `pip install svglib`. "
            "El PDF se genera igual sin esa imagen."
        )

    # Resumen rápido de lo que se va a exportar
    ingreso = st.session_state.get("ingreso_store", {}) or {}
    patient_name = _resolved_patient_name()
    if patient_name and not ingreso.get("nombre"):
        ingreso = dict(ingreso)
        ingreso["nombre"] = patient_name
        st.session_state["ingreso_store"] = ingreso
    sets_topo = st.session_state.get("topograma_sets", []) or []
    exps = st.session_state.get("exploraciones", []) or []
    recs_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    refs_map = st.session_state.get("reformaciones_por_rec", {}) or {}
    iny = st.session_state.get("inyectora_store", {}) or {}

    n_recons = sum(len(v or []) for v in recs_map.values())
    n_refs = sum(len(v or []) for v in refs_map.values())
    n_snaps = sum(len(v or {}) for v in [st.session_state.get("canvas_snapshots_topo_por_set", {}), st.session_state.get("canvas_snapshots_adq_por_exp", {}), st.session_state.get("canvas_snapshots_recon_por_id", {}), st.session_state.get("canvas_snapshots_ref_por_id", {})])

    col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns(6)
    with col_r1:
        st.metric("Paciente", _v(patient_name, "—"))
    with col_r2:
        st.metric("Topogramas", len(sets_topo))
    with col_r3:
        st.metric("Adquisiciones", len(exps))
    with col_r4:
        st.metric("Reconstrucciones", n_recons)
    with col_r5:
        st.metric("Reformaciones", n_refs)
    with col_r6:
        st.metric("Snapshots", n_snaps)

    faltan = []
    if not str(alumnos_participantes or "").strip():
        faltan.append("Nombre del alumno o de los alumnos participantes")
    if not patient_name:
        faltan.append("Nombre del paciente")
    if not exps:
        faltan.append("Al menos una adquisición")
    if faltan:
        st.warning("⚠️ Antes de exportar, completa: " + ", ".join(faltan))

    exportacion_habilitada = len(faltan) == 0

    st.caption("El PDF incluye de forma estable los parámetros seleccionados. Si las imágenes del canvas no aparecen, el problema no es el nombre del paciente sino la sincronización de snapshots del navegador.")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        generar = st.button(
            "🔨 Generar PDF",
            use_container_width=True,
            type="primary",
            disabled=not exportacion_habilitada,
        )

    # Regenerar solo si se cumplen los requisitos mínimos
    if generar and exportacion_habilitada:
        with st.spinner("Generando PDF…"):
            try:
                st.session_state["_pdf_bytes"] = construir_pdf()
                st.session_state["_pdf_generado_en"] = datetime.now()
            except Exception as e:
                st.session_state["_pdf_bytes"] = None
                st.error(f"No se pudo generar el PDF: {e}")

    pdf_bytes = st.session_state.get("_pdf_bytes")
    if pdf_bytes and exportacion_habilitada:
        nombre = patient_name or ingreso.get("nombre") or "paciente"
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre).strip("_") or "paciente"
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"planiTC_{safe}_{ts}.pdf"

        with col2:
            st.download_button(
                "⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )

        generado_en = st.session_state.get("_pdf_generado_en")
        if generado_en:
            st.caption(
                f"Última generación: {generado_en.strftime('%d/%m/%Y %H:%M:%S')} — "
                f"tamaño: {len(pdf_bytes) / 1024:.1f} KB"
            )

    elif st.session_state.get("_pdf_bytes") and not exportacion_habilitada:
        st.info("Completa los datos mínimos faltantes para habilitar la descarga del PDF.")
