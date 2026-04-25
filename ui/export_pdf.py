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
import time
import hashlib
from datetime import datetime

import streamlit as st
from PIL import Image as PILImage, ImageDraw, ImageFont

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

from ui.canvas_snapshot import (
    capture_all_snapshots_raw,
    capture_all_ref_states_raw,
    items_for_group,
    combine_png_bytes,
    set_snapshot,
)

from ui.reformaciones import _ensure_image_state

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


def _combine_png_bytes_vertical(items, gap=14, padding=10, bg=(255, 255, 255, 0)):
    """Combina PNGs en una sola imagen vertical para no achicarlas tanto en el PDF."""
    valid = []
    for item in items or []:
        data = item.get("bytes") if isinstance(item, dict) else item
        if not data:
            continue
        try:
            valid.append(PILImage.open(io.BytesIO(data)).convert("RGBA"))
        except Exception:
            continue
    if not valid:
        return None
    max_w = max(im.width for im in valid) + padding * 2
    total_h = sum(im.height for im in valid) + gap * (len(valid) - 1) + padding * 2
    canvas = PILImage.new("RGBA", (max_w, total_h), bg)
    y = padding
    for im in valid:
        x = padding + (max_w - padding * 2 - im.width) // 2
        canvas.alpha_composite(im, (x, y))
        y += im.height + gap
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def _items_for_any_recon_topogram(all_snaps, rec_id):
    """Busca snapshots de topogramas de reconstrucción aunque el nombre exacto del key varíe."""
    if not all_snaps or not rec_id:
        return []
    wanted = []
    rec_id_s = str(rec_id)
    for full_key, data in all_snaps.items():
        k = str(full_key)
        # Los topogramas de reconstrucción se guardan como planitc_snapshot_recon_topo_rect_<rec_id>_topo1/2.
        # Esta búsqueda es deliberadamente más flexible para cubrir variaciones de nombre.
        if not k.startswith("planitc_snapshot_"):
            continue
        kl = k.lower()
        if rec_id_s in k and "recon" in kl and "topo" in kl:
            wanted.append({"item": k, "bytes": data})
    # Orden estable: topo1 antes de topo2, luego el resto.
    def _rank(it):
        kk = str(it.get("item", "")).lower()
        if "topo1" in kk:
            return (0, kk)
        if "topo2" in kk:
            return (1, kk)
        return (2, kk)
    return sorted(wanted, key=_rank)




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
        # No mostrar imagen/canvas en la sección Topogramas.
        # Los límites visuales del usuario se informan en Adquisición y Reconstrucción.
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

        nombre_tipo = (exp.get("nombre") or "").upper()
        if "BOLUS" in nombre_tipo:
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

            rec_id = rec.get("id")
            snap_axial = _snapshot_bytes((plan.get("canvas_snapshots_recon_por_id") or {}).get(rec_id))
            snap_topo = _snapshot_bytes((plan.get("canvas_snapshots_recon_topo_por_id") or {}).get(rec_id))
            img_data = imagenes_rec.get(rec_id)

            img_axial_flow = None
            img_topo_flow = None
            # En el PDF, las imágenes de reconstrucción se muestran a la derecha
            # de la tabla de parámetros, igual que en Adquisición.
            # Se apilan verticalmente para mantener ambas visibles sin ocupar otra página.
            if snap_axial:
                img_axial_flow = _pil_bytes_to_flowable(snap_axial, max_w_mm=58, max_h_mm=58)
            elif img_data and img_data.get("bytes"):
                img_axial_flow = _pil_bytes_to_flowable(img_data["bytes"], max_w_mm=58, max_h_mm=58)
            if snap_topo:
                img_topo_flow = _pil_bytes_to_flowable(snap_topo, max_w_mm=58, max_h_mm=58)

            if img_axial_flow is not None or img_topo_flow is not None:
                imagenes_stack = []
                if img_axial_flow is not None:
                    imagenes_stack.append(Paragraph("<b>Imagen axial / DFOV</b>", sty["small"]))
                    imagenes_stack.append(img_axial_flow)
                if img_axial_flow is not None and img_topo_flow is not None:
                    imagenes_stack.append(Spacer(1, 5))
                if img_topo_flow is not None:
                    imagenes_stack.append(Paragraph("<b>Topograma / límites</b>", sty["small"]))
                    imagenes_stack.append(img_topo_flow)

                bloque_tabla_imagenes = Table(
                    [[params_table, imagenes_stack]],
                    colWidths=(105 * mm, 60 * mm),
                )
                bloque_tabla_imagenes.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                block.append(bloque_tabla_imagenes)
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
        "canvas_snapshots_recon_topo_por_id": dict(st.session_state.get("canvas_snapshots_recon_topo_por_id", {}) or {}),
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




def _overlay_ref_text_on_png(png_bytes, ref_state):
    """Agrega al PNG del canvas los textos de referencia anatómica guardados por JS."""
    if not png_bytes or not isinstance(ref_state, dict):
        return png_bytes
    refs = ref_state.get("refs") or []
    if not isinstance(refs, list):
        return png_bytes
    try:
        im = PILImage.open(io.BytesIO(png_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(im, "RGBA")
        w, h = im.size
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(14, int(min(w, h) * 0.030)))
            font_num = ImageFont.truetype("DejaVuSans-Bold.ttf", max(12, int(min(w, h) * 0.024)))
        except Exception:
            font = ImageFont.load_default()
            font_num = ImageFont.load_default()

        for idx, ref in enumerate(refs[:3], start=1):
            if not isinstance(ref, dict) or not ref.get("enabled"):
                continue
            text = str(ref.get("text") or "").strip()
            if not text:
                continue
            tx = float(ref.get("tx", 0.18) or 0.18)
            ty = float(ref.get("ty", 0.12) or 0.12)
            x = max(0, min(int(tx * w), w - 10))
            y = max(0, min(int(ty * h), h - 10))

            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x = max(8, int(w * 0.012))
            pad_y = max(5, int(h * 0.008))
            r = max(11, int(min(w, h) * 0.025))
            gap = max(5, int(w * 0.008))
            box_w = min(tw + pad_x * 2, max(60, w - x - (2 * r + gap) - 8))
            box_h = th + pad_y * 2
            cx = max(r + 2, min(x + r, w - r - 2))
            cy = max(r + 2, min(y + box_h // 2, h - r - 2))
            box_x = max(2, min(cx + r + gap, w - box_w - 2))
            box_y = max(2, min(cy - box_h // 2, h - box_h - 2))

            badge_color = (0, 210, 255, 255)
            border_color = (0, 210, 255, 255)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=badge_color)
            nb = draw.textbbox((0, 0), str(idx), font=font_num)
            draw.text((cx - (nb[2]-nb[0]) / 2, cy - (nb[3]-nb[1]) / 2 - 1), str(idx), font=font_num, fill=(5, 16, 24, 255))
            try:
                draw.rounded_rectangle((box_x, box_y, box_x + box_w, box_y + box_h), radius=max(6, int(min(w, h) * 0.012)), fill=(0,0,0,185), outline=border_color, width=max(2, int(min(w, h) * 0.003)))
            except Exception:
                draw.rectangle((box_x, box_y, box_x + box_w, box_y + box_h), fill=(0,0,0,185), outline=border_color)
            draw.text((box_x + pad_x, box_y + pad_y - bbox[1]), text, font=font, fill=(255,255,255,255))
        out = io.BytesIO()
        im.convert("RGB").save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return png_bytes

# ──────────────────────────────────────────────────────────────────────────
# Auto-captura de canvas al generar el PDF
# ──────────────────────────────────────────────────────────────────────────
def _ingest_canvas_snapshots(all_snaps: dict, all_ref_states: dict | None = None) -> dict:
    """A partir del dict masivo {planitc_snapshot_xxx: bytes}, distribuye
    los snapshots en los 4 stores de session_state que consume el PDF:
      - canvas_snapshots_adq_por_exp  → por exp_id
      - canvas_snapshots_topo_por_set → por índice de set de topograma
      - canvas_snapshots_recon_por_id → por rec_id
      - canvas_snapshots_ref_por_id   → por ref_id (dict {img1, img2, img3})

    Devuelve un diccionario con el conteo de snapshots distribuidos por
    sección (para feedback al usuario).
    """
    conteo = {"adq": 0, "topo": 0, "recon": 0, "ref": 0}
    all_ref_states = all_ref_states or {}
    if not all_snaps:
        return conteo

    # ADQUISICIÓN + TOPOGRAMAS (comparten snapshot por exploración)
    exps = st.session_state.get("exploraciones", []) or []
    for exp in exps:
        exp_id = exp.get("id")
        if not exp_id:
            continue
        # Probamos los patrones conocidos de group_key usados en adquisicion.py.
        # Ojo: items_for_group(exp_id) también captura exp_id_topo1, exp_id_topo2
        # y exp_id_roi_corte porque comparten prefijo. En bolus esos canvas se
        # renderizan separados, por eso se usan solo las claves explícitas para
        # evitar que el PDF repita los topogramas y la imagen de posición de corte.
        nombre_exp = (exp.get("nombre") or "").upper()
        if "BOLUS" in nombre_exp:
            candidate_groups = [
                f"{exp_id}_topo1",
                f"{exp_id}_topo2",
                f"{exp_id}_roi_corte",
            ]
        else:
            candidate_groups = [exp_id]

        items = []
        seen_hashes = set()
        for gk in candidate_groups:
            for item in items_for_group(all_snaps, gk):
                data = item.get("bytes")
                if not data:
                    continue
                h = hashlib.md5(data).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                items.append(item)

        if items:
            combinado = combine_png_bytes(items)
            if combinado:
                set_snapshot("canvas_snapshots_adq_por_exp", exp_id, combinado)
                conteo["adq"] += 1
                topo_idx = exp.get("topo_set_idx")
                if topo_idx is not None:
                    set_snapshot(
                        "canvas_snapshots_topo_por_set",
                        topo_idx,
                        combinado,
                        extra={"exp_id": exp_id},
                    )
                    conteo["topo"] += 1

    # RECONSTRUCCIONES
    # Se guardan por separado:
    #   - axial/DFOV: recon_square_<rec_id>
    #   - topograma/límites: recon_topo_rect_<rec_id>_topo1/topo2
    # Esto permite que en el PDF aparezcan ambas imágenes, una sobre la otra,
    # sin achicarlas demasiado.
    recons_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    for recs in recons_map.values():
        for rec in (recs or []):
            rec_id = rec.get("id")
            if not rec_id:
                continue

            axial_items = items_for_group(all_snaps, f"recon_square_{rec_id}")
            if axial_items:
                combinado_axial = combine_png_bytes(axial_items)
                if combinado_axial:
                    set_snapshot("canvas_snapshots_recon_por_id", rec_id, combinado_axial)
                    conteo["recon"] += 1

            topo_items = []
            topo_items.extend(items_for_group(all_snaps, f"recon_topo_rect_{rec_id}_topo1"))
            topo_items.extend(items_for_group(all_snaps, f"recon_topo_rect_{rec_id}_topo2"))
            if not topo_items:
                topo_items = _items_for_any_recon_topogram(all_snaps, rec_id)
            if topo_items:
                combinado_topo = _combine_png_bytes_vertical(topo_items)
                if combinado_topo:
                    set_snapshot("canvas_snapshots_recon_topo_por_id", rec_id, combinado_topo)
                    conteo["recon"] += 1

    # REFORMACIONES (3 imágenes por reformación, con sig dentro del group_key)
    refs_map = st.session_state.get("reformaciones_por_rec", {}) or {}
    imagenes_ref = st.session_state.get("imagenes_ref_por_id", {}) or {}
    for refs in refs_map.values():
        for ref in (refs or []):
            ref_id = ref.get("id")
            if not ref_id:
                continue
            img_state = imagenes_ref.get(ref_id, {}) if isinstance(imagenes_ref, dict) else {}
            snaps = {}
            for img_idx in (1, 2, 3):
                img_data = img_state.get(f"img{img_idx}") if isinstance(img_state, dict) else None
                if not img_data or not img_data.get("bytes"):
                    continue
                sig = img_data.get("sig") or hashlib.md5(img_data["bytes"]).hexdigest()[:10]
                group_key = f"{ref_id}_img{img_idx}_{sig}"
                items = items_for_group(all_snaps, group_key)
                if items:
                    ref_state = all_ref_states.get(f"planitc_ref_{group_key}") if isinstance(all_ref_states, dict) else None
                    png_bytes = _overlay_ref_text_on_png(items[0]["bytes"], ref_state)
                    snaps[f"img{img_idx}"] = {"bytes": png_bytes}
            if snaps:
                store = st.session_state.setdefault("canvas_snapshots_ref_por_id", {})
                store[ref_id] = snaps
                conteo["ref"] += 1

    return conteo


def _contar_canvas_snapshots_guardados() -> int:
    """Cuenta snapshots ya distribuidos en st.session_state."""
    total = 0
    total += len(st.session_state.get("canvas_snapshots_topo_por_set", {}) or {})
    total += len(st.session_state.get("canvas_snapshots_adq_por_exp", {}) or {})
    total += len(st.session_state.get("canvas_snapshots_recon_por_id", {}) or {})
    total += len(st.session_state.get("canvas_snapshots_recon_topo_por_id", {}) or {})

    refs = st.session_state.get("canvas_snapshots_ref_por_id", {}) or {}
    for value in refs.values():
        if isinstance(value, dict):
            total += len(value)
        elif value:
            total += 1
    return total


def _finalizar_captura_y_generar_pdf(js_key: str) -> bool:
    """Lee los snapshots persistidos en el navegador, los guarda en session_state
    y genera el PDF. Retorna True si terminó; False si el navegador aún no responde.
    """
    all_snaps = capture_all_snapshots_raw(js_key=js_key)
    all_ref_states = capture_all_ref_states_raw(js_key=f"{js_key}_ref_states")
    if all_snaps is None or all_ref_states is None:
        st.info("Capturando los canvas guardados antes de generar el PDF...")
        return False

    conteo = _ingest_canvas_snapshots(all_snaps or {}, all_ref_states or {})
    st.session_state["_pdf_ultimo_conteo_snapshots"] = conteo
    st.session_state["_pdf_ultimo_total_raw_snapshots"] = len(all_snaps or {})

    try:
        st.session_state["_pdf_bytes"] = construir_pdf()
        st.session_state["_pdf_generado_en"] = datetime.now()
        st.session_state["_pdf_error"] = None
    except Exception as e:
        st.session_state["_pdf_bytes"] = None
        st.session_state["_pdf_error"] = str(e)

    st.session_state.pop("_pdf_capture_js_key", None)
    return True


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
        st.metric("Paciente", _v(ingreso.get("nombre"), "—"))
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
    if not ingreso.get("nombre"):
        faltan.append("Nombre del paciente")
    if not exps:
        faltan.append("Al menos una adquisición")
    if faltan:
        st.warning("⚠️ Antes de exportar, completa: " + ", ".join(faltan))

    exportacion_habilitada = len(faltan) == 0

    # ── Captura automática pendiente desde el navegador ───────────────────────
    pending_js_key = st.session_state.get("_pdf_capture_js_key")
    if pending_js_key and exportacion_habilitada:
        terminado = _finalizar_captura_y_generar_pdf(pending_js_key)
        if not terminado:
            st.stop()
        st.rerun()

    # ── Captura de canvas automática ────────────────────────────────────────
    st.markdown("---")
    st.caption("Los canvas se capturan automáticamente desde el navegador al generar el PDF.")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        generar = st.button(
            "🔨 Generar PDF",
            use_container_width=True,
            type="primary",
            disabled=not exportacion_habilitada,
        )

    # ── Generación del PDF ─────────────────────────────────────────────────────
    if generar and exportacion_habilitada:
        # Dos pasos: primero se fuerza una lectura JS del navegador; en el rerun
        # siguiente se ingieren los snapshots y recién ahí se arma el PDF.
        st.session_state["_pdf_bytes"] = None
        st.session_state["_pdf_error"] = None
        st.session_state["_pdf_capture_js_key"] = f"pdf_snaps_{time.time_ns()}"
        st.rerun()

    if st.session_state.get("_pdf_error"):
        st.error(f"No se pudo generar el PDF: {st.session_state.get('_pdf_error')}")

    pdf_bytes = st.session_state.get("_pdf_bytes")
    if pdf_bytes and exportacion_habilitada:
        nombre = ingreso.get("nombre") or "paciente"
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
        
        # Botón para finalizar examen y limpiar todo
        if st.button(
            "🏁 Finalizar Examen",
            use_container_width=True,
            type="secondary",
            help="Limpia todos los datos del protocolo actual para comenzar un nuevo examen"
        ):
            # Confirmar antes de limpiar
            st.session_state["_confirmar_finalizar"] = True
            st.rerun()
        
        # Modal de confirmación
        if st.session_state.get("_confirmar_finalizar"):
            st.warning("⚠️ **¿Estás seguro?** Esto borrará TODOS los datos del protocolo actual (topogramas, exploraciones, reconstrucciones, reformaciones).")
            col_si, col_no = st.columns(2)
            with col_si:
                if st.button("✅ Sí, finalizar examen", use_container_width=True, type="primary"):
                    # Limpiar todo el session_state excepto las configuraciones del usuario
                    keys_to_keep = {"nombre_alumno", "alumnos_participantes"}
                    keys_to_delete = [k for k in st.session_state.keys() if k not in keys_to_keep]
                    for key in keys_to_delete:
                        del st.session_state[key]
                    st.success("✅ Examen finalizado. Todos los datos han sido eliminados.")
                    st.rerun()
            with col_no:
                if st.button("❌ Cancelar", use_container_width=True):
                    del st.session_state["_confirmar_finalizar"]
                    st.rerun()

        generado_en = st.session_state.get("_pdf_generado_en")
        if generado_en:
            # Contar snapshots incluidos, tanto automáticos como manuales.
            snap_count = _contar_canvas_snapshots_guardados()
            raw_count = st.session_state.get("_pdf_ultimo_total_raw_snapshots", 0)

            detalle = ""
            if snap_count > 0:
                detalle = f" — {snap_count} snapshot(s) de canvas incluidos"
            elif raw_count == 0:
                detalle = " — sin snapshots de canvas detectados"
            
            st.caption(
                f"✅ PDF generado: {generado_en.strftime('%d/%m/%Y %H:%M:%S')} — "
                f"tamaño: {len(pdf_bytes) / 1024:.1f} KB{detalle}"
            )

    elif st.session_state.get("_pdf_bytes") and not exportacion_habilitada:
        st.info("Completa primero el nombre del alumno o de los alumnos participantes para habilitar la descarga del PDF.")
