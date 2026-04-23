"""
ui/adquisicion.py
Módulo de Adquisición para PlaniTC_v2.

Cubre la TAB 2 del simulador. Reemplaza a `adquisicion-3.py` con:
- Eliminación del "Resumen de referencia" (tarjetas azules de arriba).
- Visualización de los topogramas 1/2 con caja DFOV arrastrable / redimensionable
  (canvas HTML interactivo), igual que en el PlaniTC original.
- Lógica de parámetros igual al PlaniTC original:
  * MODULACION_CORRIENTE dinámica: "MANUAL" → mAs, "AUTO mA" → Rango mA + Índice ruido,
    "CARE DOSE 4D" → mAs REF + Índice calidad.
  * CONF. DETECCIÓN con opciones según tipo_exp + doble_muestreo.
  * COBERTURA calculada por tabla (COBERTURA_TABLA), no por fórmula.
  * Métricas de dosis al final (CTDIvol, duración, ruido estimado).

Entrypoint: render_adquisicion()

NOTA: este archivo es grande (~1200 líneas) porque incluye el canvas JS
interactivo (~570 líneas). Cuando tengas `core/canvas.py`, mover allí:
  - POSICIONES_Y, get_y_position, get_y_position_with_offset
  - _pil_to_b64_jpeg
  - render_topogramas_independientes_interactivos
"""

import io
import json
import math
import uuid
import base64
from pathlib import Path

import streamlit as st
from PIL import Image

from ui.canvas_snapshot import capture_canvas_group, combine_png_bytes, set_snapshot

from ui.topograma import (
    obtener_imagen_topograma_adquirido,
    render_topograma_panel,
    _init_topograma_sets,
    _agregar_set_topograma,
    _eliminar_set_topograma,
    _next_order,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_POSICION_CORTE_BOLUS = BASE_DIR / "data" / "images" / "posicion_corte_bolus"


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES DE ADQUISICIÓN (del PlaniTC original)
# ═══════════════════════════════════════════════════════════════════════════
NOMBRES_EXPLORACION = [
    "SIN CONTRASTE",
    "ARTERIAL",
    "ANGIOGRÁFICA",
    "BOLUS TEST",
    "BOLUS TRACKING",
    "VENOSA",
    "TARDÍA",
]

TIPOS_EXPLORACION = ["HELICOIDAL", "SECUENCIAL CONTIGUO", "SECUENCIAL ESPACIADO"]

MODULACION_CORRIENTE = ["MANUAL", "AUTO mA", "CARE DOSE 4D"]

KVP_OPCIONES = [70, 80, 90, 100, 110, 120, 140]

MAS_OPCIONES = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]

RANGO_MA = ["30 - 400", "40 - 300", "60 - 500", "130 - 400", "140 - 500"]

INDICE_RUIDO = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

INDICE_CALIDAD = [80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300]

CONF_DETECTORES = [
    "8 x 1,25 mm", "16 x 0,625 mm", "32 x 0.6 mm",
    "32 x 0,625 mm", "32 x 1,2 mm", "32 x 1,25 mm",
    "64 x 0,6 mm", "64 x 0,625 mm",
]

SFOV_OPCIONES = ["SMALL (200 mm)", "HEAD (300 mm)", "LARGE (500 mm)"]

PITCH_OPCIONES = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]

ROT_TUBO = [0.3, 0.5, 0.7, 1.0]

GROSOR_PROSP = [0.6, 0.625, 1.0, 1.2, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0]

INSTRUCCIONES_VOZ = ["NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]

RETARDOS = ["2 sg", "3 sg", "4 sg", "5 sg", "6 sg"]

# Específicas de BOLUS
PERIODO_TEST_BOLUS = ["0,9 sg", "1 sg", "1,5 sg", "2 sg"]
N_IMAGENES_TEST_BOLUS = ["10", "15", "20", "25", "30"]
POSICION_CORTE_BOLUS = ["ANGULO MANDIBULAR (SEGM. C1 CAROTIDA)", "BOTON AORTICO", "BAJO CARINA", "CUPULAS DIAFRAGMATICAS", "L5-S1 (BIFURCACION AORTO-ILIACA)"]
UMBRAL_TRACKING = ["80 UH", "100 UH", "120 UH", "150 UH", "180 UH"]

# Cobertura por tabla (no por fórmula)
COBERTURA_TABLA = {
    "SECUENCIAL CONTIGUO": {
        "8 x 1,25 mm": "10",
        "16 x 0,625 mm": "10",
        "32 x 0.6 mm": "19,2",
        "32 x 0,625 mm": "20",
        "32 x 1,2 mm": "38,4",
        "32 x 1,25 mm": "40",
        "64 x 0,6 mm": "38,4",
        "64 x 0,625 mm": "40",
    },
    "HELICOIDAL": {
        "8 x 1,25 mm": "10",
        "16 x 0,625 mm": "10",
        "32 x 0.6 mm": "19,2",
        "32 x 0,625 mm": "20",
        "32 x 1,2 mm": "38,4",
        "32 x 1,25 mm": "40",
        "64 x 0,6 mm": "38,4",
        "64 x 0,625 mm": "40",
    },
    "DOBLE MUESTREO": {
        "16 x 0,625 mm": "5",
        "32 x 0.6 mm": "9,6",
        "32 x 0,625 mm": "10",
        "64 x 0,6 mm": "19,2",
    },
    "SECUENCIAL ESPACIADO": {
        "1 x 1,25 mm": "1,25 - 20 mm",
        "2 x 0,625 mm": "1,25 - 10 mm",
    }
}

CONF_DETECTORES_POR_TIPO = {
    "SECUENCIAL CONTIGUO": list(COBERTURA_TABLA["SECUENCIAL CONTIGUO"].keys()),
    "HELICOIDAL": list(COBERTURA_TABLA["HELICOIDAL"].keys()),
    "SECUENCIAL ESPACIADO": list(COBERTURA_TABLA["SECUENCIAL ESPACIADO"].keys()),
}

CONF_DETECTORES_DOBLE_MUESTREO = list(COBERTURA_TABLA["DOBLE MUESTREO"].keys())

# Referencias anatómicas por grupo (inicio y fin de exploración)
REFS_INICIO = {
    "CABEZA":  ["VERTEX", "SOBRE SENO FRONTAL", "TECHO ORBITARIO", "CAE",
                "PISO ORBITARIO", "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR",
                "BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO"],
    "CUELLO":  ["TECHO ORBITARIO", "CAE", "ARCO AÓRTICO"],
    "EESS":    ["SOBRE ART. ACROMIOCLAV.", "BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO",
                "TERCIO PROXIMAL RADIO-CUBITO", "TERCIO PROXIMAL MTC", "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["CAE", "SOBRE BASE DE CRÁNEO", "C6-C7", "T1-T2", "T11-T12", "L1-L2", "L4-L5", "S1-S2"],
    "CUERPO":  ["SOBRE ÁPICES PULMONARES", "SOBRE CÚPULAS DIAF.", "ARCO AÓRTICO",
                "BAJO ANGULOS COSTOFR.", "L5-S1"],
    "EEII":    ["EIAS", "TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR",
                "TERCIO PROXIMAL TIBIA-PERONÉ", "TERCIO DISTAL TIBIA-PERONÉ",
                "BAJO CALCÁNEO", "HASTA COMPLETAR ORTEJOS"],
    "ANGIO":   ["SOBRE ÁPICES PULMONARES", "ARCO AÓRTICO", "SOBRE CÚPULAS DIAF.",
                "BAJO ANGULOS COSTOFR.", "L5-S1", "COMPLETAR FALANGE DISTAL"],
}

REFS_FIN = {
    "CABEZA":  ["BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO", "PISO ORBITARIO",
                "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR"],
    "CUELLO":  ["CAE", "ARCO AÓRTICO", "MENTON"],
    "EESS":    ["BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO", "TERCIO PROXIMAL MTC",
                "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["SOBRE BASE DE CRÁNEO", "T1-T2", "T11-T12", "L4-L5", "S1-S2",
                "1 CM BAJO COXIS", "L5-S1"],
    "CUERPO":  ["SOBRE CÚPULAS DIAF.", "BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA"],
    "EEII":    ["TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR",
                "TERCIO PROXIMAL TIBIA-PERONÉ", "BAJO CALCÁNEO",
                "HASTA COMPLETAR ORTEJOS", "COMPLETAR ORTEJOS"],
    "ANGIO":   ["BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA",
                "COMPLETAR FALANGE DISTAL", "COMPLETAR ORTEJOS"],
}

# Posiciones Y relativas para el recuadro DFOV (0=arriba, 1=abajo)
POSICIONES_Y = {
    "VERTEX":                   0.05,
    "SOBRE SENO FRONTAL":       0.12,
    "TECHO ORBITARIO":          0.22,
    "CAE":                      0.35,
    "PISO ORBITARIO":           0.28,
    "SOBRE REGION PETROSA":     0.38,
    "ARCADA DENTARIA SUPERIOR": 0.42,
    "BAJO BASE DE CRÁNEO":      0.48,
    "MENTON":                   0.55,
    "ARCO AÓRTICO":             0.85,
    "SOBRE ÁPICES PULMONARES":  0.05,
    "SOBRE CÚPULAS DIAF.":      0.22,
    "BAJO ANGULOS COSTOFR.":    0.38,
    "L5-S1":                    0.72,
    "BAJO PELVIS OSEA":         0.88,
    "SOBRE CRESTA ILIACA":      0.65,
    "L4-L5":                    0.68,
    "L1-L2":                    0.55,
    "T11-T12":                  0.40,
    "T1-T2":                    0.18,
    "C6-C7":                    0.10,
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE NEGOCIO (cálculos, tablas)
# ═══════════════════════════════════════════════════════════════════════════
def obtener_opciones_conf_det(tipo_exp, doble_muestreo):
    """Devuelve la lista de configuraciones de detectores válida para el tipo actual."""
    if tipo_exp == "HELICOIDAL" and doble_muestreo == "SI":
        return CONF_DETECTORES_DOBLE_MUESTREO
    return CONF_DETECTORES_POR_TIPO.get(tipo_exp, CONF_DETECTORES)


def obtener_cobertura_tabla(tipo_exp, conf_det, doble_muestreo):
    """Devuelve la cobertura en mm según la tabla (no se calcula por fórmula)."""
    if not tipo_exp or not conf_det:
        return "—"
    tabla = "DOBLE MUESTREO" if tipo_exp == "HELICOIDAL" and doble_muestreo == "SI" else tipo_exp
    return COBERTURA_TABLA.get(tabla, {}).get(conf_det, "—")


def calcular_cobertura_helical(conf_det, pitch):
    """Cobertura en mm/rotación para exploración helicoidal."""
    try:
        partes = conf_det.replace(",", ".").split("x")
        n_det = int(partes[0].strip())
        ancho = float(partes[1].strip().replace(" mm", ""))
        return round(n_det * ancho * float(pitch), 2)
    except Exception:
        return "—"


def calcular_duracion(inicio_mm, fin_mm, cobertura_rot, rot_tubo):
    """Duración estimada del scan en segundos."""
    try:
        longitud = abs(float(fin_mm) - float(inicio_mm))
        if cobertura_rot and float(cobertura_rot) > 0 and float(rot_tubo) > 0:
            return round(longitud / float(cobertura_rot) * float(rot_tubo), 1)
        return "—"
    except Exception:
        return "—"


def estimar_dosis_ctdi(kvp, mas, conf_det):
    """Estimación simplificada de CTDIvol en mGy."""
    try:
        partes = conf_det.replace(",", ".").split("x")
        n_det = int(partes[0].strip())
        ancho = float(partes[1].strip().replace(" mm", ""))
        col = n_det * ancho
        base = (float(mas) / 200) * ((float(kvp) / 120) ** 2) * (col / 20) * 8
        return round(base, 1)
    except Exception:
        return "—"


def nivel_ruido_estimado(mas, kvp, grosor_mm):
    """Nivel relativo de ruido (menor es mejor)."""
    try:
        return round(100 / math.sqrt(float(mas)) * (120 / float(kvp)) * (1 / math.sqrt(float(grosor_mm))), 1)
    except Exception:
        return "—"


def get_y_position(ref):
    """Posición Y (0-1) en el topograma para una referencia anatómica."""
    return POSICIONES_Y.get(ref, 0.5)


def get_y_position_with_offset(ref, offset_mm=0, total_mm=600):
    """Combina referencia anatómica + desplazamiento en mm para ubicar la línea."""
    try:
        offset_mm = float(offset_mm or 0)
    except Exception:
        offset_mm = 0.0
    base = get_y_position(ref)
    y = base + (offset_mm / float(total_mm))
    return max(0.01, min(0.99, y))


# ═══════════════════════════════════════════════════════════════════════════
# CONVERSIÓN DE IMAGEN PIL A BASE64 (para canvas HTML)
# ═══════════════════════════════════════════════════════════════════════════
def _pil_to_b64_jpeg(img, max_width=900):
    """Convierte una imagen PIL a base64 JPEG para usarla en canvas HTML."""
    if img is None:
        return None
    try:
        im = img.copy()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        if max_width and im.width > max_width:
            ratio = max_width / float(im.width)
            im = im.resize((int(im.width * ratio), int(im.height * ratio)))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=92)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# CANVAS HTML INTERACTIVO PARA TOPOGRAMAS (DFOV / línea de corte / ROI)
# Copiado verbatim del PlaniTC original.
# ═══════════════════════════════════════════════════════════════════════════
def render_topogramas_independientes_interactivos(
    topos,
    width=760,
    modo="rect",
    storage_key=None,
    color="#00D2FF",
    show_labels=False,
    roi_label="ROI",
    canvas_css_width=None,
    canvas_css_height=None,
    canvas_width=None,
    canvas_height=None,
):
    """
    Renderiza uno o más canvas interactivos.
    modo="rect"  -> rectángulo movible y redimensionable (DFOV)
    modo="line"  -> línea horizontal única movible (corte de bolus)
    modo="roi"   -> círculo movible y redimensionable para ROI
    """
    if not topos:
        return None

    if modo == "roi":
        default_canvas_css_width = 360
        default_canvas_css_height = 500
        default_canvas_width = 520
        default_canvas_height = 760
    else:
        default_canvas_css_width = 227 if len(topos) > 1 else 307
        default_canvas_css_height = 333 if len(topos) > 1 else 387
        default_canvas_width = 420
        default_canvas_height = 640

    canvas_css_width = canvas_css_width or default_canvas_css_width
    canvas_css_height = canvas_css_height or default_canvas_css_height
    canvas_width = canvas_width or default_canvas_width
    canvas_height = canvas_height or default_canvas_height
    min_col_width = canvas_css_width

    cols_html = []
    topo_payload = []

    for i, topo in enumerate(topos):
        img_b64 = topo.get("img_b64")
        if not img_b64:
            continue

        titulo = topo.get("titulo", f"Topograma {i+1}")
        subtitulo = topo.get("subtitulo", "")
        inicio_ref = topo.get("inicio_ref", "—")
        fin_ref = topo.get("fin_ref", "—")
        inicio_mm = topo.get("inicio_mm", 0)
        fin_mm = topo.get("fin_mm", 0)
        y_ini = topo.get("y_ini", get_y_position_with_offset(inicio_ref, inicio_mm))
        y_fin = topo.get("y_fin", get_y_position_with_offset(fin_ref, fin_mm))

        y1 = max(0.05, min(y_ini, y_fin))
        y2 = min(0.95, max(y_ini, y_fin))
        rect_h = max(0.10, y2 - y1)
        rect_y = max(0.02, min(0.98 - rect_h, y1))
        rect_x = 0.22
        rect_w = 0.56
        line_y = (y1 + y2) / 2.0
        circle_x = 0.50
        circle_y = 0.50
        circle_r = 0.12

        labels_html = ""
        if show_labels:
            labels_html = f'''
          <div style="margin-top:4px; font-size:13px; color:#fff; text-align:center; line-height:1.45;">
            Campo: <b id="lblSizeInd{i}">—</b>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Centro: <b id="lblCenterInd{i}">—</b>
            <br>
            Alto aprox.: <b id="lblHeightInd{i}">—</b> mm
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Ancho aprox.: <b id="lblWidthInd{i}">—</b> %
          </div>
            '''

        cols_html.append(f'''
        <div style="flex:0 0 {canvas_css_width}px; width:{canvas_css_width}px; min-width:{min_col_width}px; max-width:{canvas_css_width}px;">
          <div style="font-size:16px;font-weight:700;color:#fff;margin:0 0 6px 0;text-align:center;">{titulo}</div>
          <canvas id="topoCanvasInd{i}" data-planitc-snapshot-item="{i}" width="{canvas_width}" height="{canvas_height}"
            style="width:{canvas_css_width}px; height:{canvas_css_height}px; cursor:grab; border:1px solid #444; border-radius:8px; background:#000; display:block; margin:0 auto; touch-action:none;"></canvas>
          <button type="button" onclick="downloadCanvasInd({i}, {json.dumps(titulo)})"
            style="margin-top:8px; background:#1f2937; color:#fff; border:1px solid #4b5563; border-radius:10px; padding:8px 12px; font-size:12px; font-weight:700; cursor:pointer;">Descargar PNG</button>
          <div style="margin-top:6px; font-size:12px; color:#ccc; text-align:center; min-height:32px;">{subtitulo}</div>
          {labels_html}
        </div>
        ''')

        topo_payload.append({
            "img_b64": img_b64,
            "rect_x": rect_x,
            "rect_y": rect_y,
            "rect_w": rect_w,
            "rect_h": rect_h,
            "line_y": line_y,
            "circle_x": circle_x,
            "circle_y": circle_y,
            "circle_r": circle_r,
        })

    if not cols_html:
        return None

    help_text = {
        "rect": "Arrastra el recuadro para moverlo. Usa cualquiera de sus bordes o esquinas para cambiar su tamaño.",
        "line": "Arrastra la línea para ubicar el corte de planificación.",
        "roi": "Arrastra el círculo para mover el ROI. Usa el control lateral para ajustar su tamaño.",
    }.get(modo, "")

    html = f'''
<div data-planitc-snapshot-group="{storage_key or ''}" style="text-align:center; margin:0 0 0 0;">
  <div style="display:inline-block; font-size:11px; color:#aaa; margin-bottom:2px;">
    {help_text}
  </div>
  <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:flex-start; justify-content:center; margin-bottom:0;">
    {''.join(cols_html)}
  </div>
</div>
<script>
(function() {{
  var topoData = {json.dumps(topo_payload)};
  var modo = {json.dumps(modo)};
  var baseStorageKey = {json.dumps(storage_key or '')};
  var strokeColor = {json.dumps(color)};
  var showLabels = {json.dumps(show_labels)};
  var roiLabel = {json.dumps(roi_label)};

  function rgbaFromHex(hex, alpha) {{
    if (!hex || typeof hex !== 'string') return 'rgba(0,210,255,' + alpha + ')';
    var h = hex.replace('#','');
    if (h.length === 3) h = h.split('').map(function(c) {{ return c + c; }}).join('');
    if (h.length !== 6) return 'rgba(0,210,255,' + alpha + ')';
    var r = parseInt(h.substring(0,2), 16);
    var g = parseInt(h.substring(2,4), 16);
    var b = parseInt(h.substring(4,6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }}

  function downloadCanvasInd(idx, title) {{
    try {{
      var canvas = document.getElementById('topoCanvasInd' + idx);
      if (!canvas) return;
      var a = document.createElement('a');
      var safe = String(title || ('topograma_' + (idx + 1))).replace(/[^a-zA-Z0-9_-]+/g, '_');
      a.href = canvas.toDataURL('image/png');
      a.download = safe + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }} catch (e) {{}}
  }}
  window.downloadCanvasInd = downloadCanvasInd;

  topoData.forEach(function(data, idx) {{
    var canvas = document.getElementById('topoCanvasInd' + idx);
    if (!canvas) return;

    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var storageKey = baseStorageKey ? ('planitc_' + baseStorageKey + '_' + modo + '_' + idx) : '';
    var snapshotKey = baseStorageKey ? ('planitc_snapshot_' + baseStorageKey + '_' + idx) : '';

    var rectState = {{ x: data.rect_x, y: data.rect_y, w: data.rect_w, h: data.rect_h }};
    var lineState = {{ y: data.line_y }};
    var circleState = {{ x: data.circle_x, y: data.circle_y, r: data.circle_r }};

    try {{
      if (storageKey) {{
        var saved = localStorage.getItem(storageKey);
        if (saved) {{
          var parsed = JSON.parse(saved);
          if (modo === 'rect' && parsed && parsed.rectState) rectState = parsed.rectState;
          if (modo === 'line' && parsed && parsed.lineState) lineState = parsed.lineState;
          if (modo === 'roi' && parsed && parsed.circleState) circleState = parsed.circleState;
        }}
      }}
    }} catch (e) {{}}

    var dragMode = null;
    var dragOffsetX = 0;
    var dragOffsetY = 0;
    var handleSize = 6;
    var minW = 0.12;
    var minH = 0.10;
    var minR = modo === 'roi' ? 0.004 : 0.05;
    var roiMoveHitMinPx = 18;
    var roiHandleHitExtraPx = 12;
    var roiVisualMinPx = 10;
    var img = new Image();
    img.src = 'data:image/jpeg;base64,' + data.img_b64;

    function saveState() {{
      try {{
        if (storageKey) {{
          localStorage.setItem(storageKey, JSON.stringify({{
            rectState: rectState,
            lineState: lineState,
            circleState: circleState
          }}));
        }}
        if (snapshotKey) {{
          localStorage.setItem(snapshotKey, canvas.toDataURL('image/png'));
        }}
      }} catch (e) {{}}
    }}

    function clampRect() {{
      rectState.w = Math.max(minW, Math.min(0.92, rectState.w));
      rectState.h = Math.max(minH, Math.min(0.92, rectState.h));
      rectState.x = Math.max(0.02, Math.min(0.98 - rectState.w, rectState.x));
      rectState.y = Math.max(0.02, Math.min(0.98 - rectState.h, rectState.y));
    }}

    function clampLine() {{
      lineState.y = Math.max(0.03, Math.min(0.97, lineState.y));
    }}

    function clampCircle() {{
      circleState.r = Math.max(minR, Math.min(0.35, circleState.r));
      circleState.x = Math.max(circleState.r + 0.02, Math.min(0.98 - circleState.r, circleState.x));
      circleState.y = Math.max(circleState.r + 0.02, Math.min(0.98 - circleState.r, circleState.y));
    }}

    function getRectPx() {{
      return {{ x: rectState.x * W, y: rectState.y * H, w: rectState.w * W, h: rectState.h * H }};
    }}

    function getLinePx() {{
      return {{ y: lineState.y * H }};
    }}

    function getCirclePx() {{
      return {{ x: circleState.x * W, y: circleState.y * H, r: circleState.r * Math.min(W, H) }};
    }}

    function getRectResizeMode(mx, my, rp) {{
      var edgeHit = Math.max(12, handleSize + 4);
      var onLeft = Math.abs(mx - rp.x) <= edgeHit && my >= rp.y - edgeHit && my <= rp.y + rp.h + edgeHit;
      var onRight = Math.abs(mx - (rp.x + rp.w)) <= edgeHit && my >= rp.y - edgeHit && my <= rp.y + rp.h + edgeHit;
      var onTop = Math.abs(my - rp.y) <= edgeHit && mx >= rp.x - edgeHit && mx <= rp.x + rp.w + edgeHit;
      var onBottom = Math.abs(my - (rp.y + rp.h)) <= edgeHit && mx >= rp.x - edgeHit && mx <= rp.x + rp.w + edgeHit;

      if (onLeft && onTop) return 'resize-rect-nw';
      if (onRight && onTop) return 'resize-rect-ne';
      if (onLeft && onBottom) return 'resize-rect-sw';
      if (onRight && onBottom) return 'resize-rect-se';
      if (onLeft) return 'resize-rect-w';
      if (onRight) return 'resize-rect-e';
      if (onTop) return 'resize-rect-n';
      if (onBottom) return 'resize-rect-s';
      return null;
    }}

    function isInsideRect(mx, my, rp) {{
      return mx >= rp.x && mx <= rp.x + rp.w && my >= rp.y && my <= rp.y + rp.h;
    }}

    function isOnLine(my, lp) {{
      return Math.abs(my - lp.y) <= 14;
    }}

    function isInsideCircle(mx, my, cp) {{
      var dx = mx - cp.x;
      var dy = my - cp.y;
      var hitRadius = Math.max(cp.r, roiMoveHitMinPx);
      return Math.sqrt(dx*dx + dy*dy) <= hitRadius;
    }}

    function isOnCircleHandle(mx, my, cp) {{
      var dx = mx - cp.x;
      var dy = my - cp.y;
      var dist = Math.sqrt(dx*dx + dy*dy);
      var visualRadius = Math.max(cp.r, roiVisualMinPx);
      var edgeTolerance = Math.max(10, roiHandleHitExtraPx);
      return Math.abs(dist - visualRadius) <= edgeTolerance;
    }}

    function updateLabels() {{
      if (!showLabels) return;
      var lblSize = document.getElementById('lblSizeInd' + idx);
      var lblCenter = document.getElementById('lblCenterInd' + idx);
      var lblHeight = document.getElementById('lblHeightInd' + idx);
      var lblWidth = document.getElementById('lblWidthInd' + idx);
      if (!lblSize || !lblCenter || !lblHeight || !lblWidth) return;

      if (modo === 'rect') {{
        var centerX = Math.round((rectState.x + rectState.w / 2) * 100);
        var centerY = Math.round((rectState.y + rectState.h / 2) * 100);
        var widthPct = Math.round(rectState.w * 100);
        var heightMm = Math.round(rectState.h * 600);
        lblSize.textContent = widthPct + '% × ' + Math.round(rectState.h * 100) + '%';
        lblCenter.textContent = 'X ' + centerX + '% · Y ' + centerY + '%';
        lblHeight.textContent = heightMm;
        lblWidth.textContent = widthPct;
      }} else if (modo === 'line') {{
        lblSize.textContent = 'Corte único';
        lblCenter.textContent = 'Y ' + Math.round(lineState.y * 100) + '%';
        lblHeight.textContent = '—';
        lblWidth.textContent = '—';
      }} else if (modo === 'roi') {{
        lblSize.textContent = 'ROI';
        lblCenter.textContent = 'X ' + Math.round(circleState.x * 100) + '% · Y ' + Math.round(circleState.y * 100) + '%';
        lblHeight.textContent = Math.round(circleState.r * 2 * 600);
        lblWidth.textContent = Math.round((circleState.r * 2) * 100);
      }}
    }}

    function drawBaseImage() {{
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, W, H);
      if (img.width && img.height) {{
        var scale = Math.min(W / img.width, H / img.height);
        var drawW = img.width * scale;
        var drawH = img.height * scale;
        var dx = (W - drawW) / 2;
        var dy = (H - drawH) / 2;
        ctx.drawImage(img, dx, dy, drawW, drawH);
      }}
    }}

    function drawRect() {{
      clampRect();
      var rp = getRectPx();
      ctx.fillStyle = rgbaFromHex(strokeColor, 0.14);
      ctx.fillRect(rp.x, rp.y, rp.w, rp.h);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 6]);
      ctx.strokeRect(rp.x, rp.y, rp.w, rp.h);
      ctx.setLineDash([]);
      ctx.fillStyle = strokeColor;
      ctx.font = 'bold 12px sans-serif';
    }}

    function drawLine() {{
      clampLine();
      var lp = getLinePx();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(28, lp.y);
      ctx.lineTo(W - 28, lp.y);
      ctx.stroke();
      ctx.fillStyle = strokeColor;
      ctx.font = 'bold 12px sans-serif';
      ctx.fillText('CORTE', 28, Math.max(18, lp.y - 10));
    }}

    function drawCircle() {{
      clampCircle();
      var cp = getCirclePx();
      var visualRadius = Math.max(cp.r, roiVisualMinPx);
      ctx.fillStyle = rgbaFromHex(strokeColor, 0.18);
      ctx.beginPath();
      ctx.arc(cp.x, cp.y, visualRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(cp.x, cp.y, visualRadius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = strokeColor;
      ctx.beginPath();
      ctx.arc(cp.x + visualRadius, cp.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = strokeColor;
      ctx.font = 'bold 12px sans-serif';
      ctx.fillText(roiLabel, Math.max(10, cp.x - visualRadius), Math.max(18, cp.y - visualRadius - 8));
    }}

    function draw() {{
      drawBaseImage();
      if (modo === 'line') drawLine();
      else if (modo === 'roi') drawCircle();
      else drawRect();
      updateLabels();
      saveState();
    }}

    function getMousePos(e) {{
      var rect = canvas.getBoundingClientRect();
      var scaleX = W / rect.width;
      var scaleY = H / rect.height;
      return {{ x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY }};
    }}

    function updateCursor(mx, my) {{
      if (modo === 'line') {{
        var lp = getLinePx();
        canvas.style.cursor = isOnLine(my, lp) ? 'ns-resize' : 'default';
        return;
      }}
      if (modo === 'roi') {{
        var cp = getCirclePx();
        if (isOnCircleHandle(mx, my, cp)) canvas.style.cursor = 'nwse-resize';
        else if (isInsideCircle(mx, my, cp)) canvas.style.cursor = 'grab';
        else canvas.style.cursor = 'default';
        return;
      }}
      var rp = getRectPx();
      var resizeMode = getRectResizeMode(mx, my, rp);
      if (resizeMode === 'resize-rect-n' || resizeMode === 'resize-rect-s') canvas.style.cursor = 'ns-resize';
      else if (resizeMode === 'resize-rect-e' || resizeMode === 'resize-rect-w') canvas.style.cursor = 'ew-resize';
      else if (resizeMode === 'resize-rect-ne' || resizeMode === 'resize-rect-sw') canvas.style.cursor = 'nesw-resize';
      else if (resizeMode === 'resize-rect-nw' || resizeMode === 'resize-rect-se') canvas.style.cursor = 'nwse-resize';
      else if (isInsideRect(mx, my, rp)) canvas.style.cursor = 'grab';
      else canvas.style.cursor = 'default';
    }}

    canvas.addEventListener('mousedown', function(e) {{
      var pos = getMousePos(e);
      if (modo === 'line') {{
        var lp = getLinePx();
        if (isOnLine(pos.y, lp)) dragMode = 'move-line';
        return;
      }}
      if (modo === 'roi') {{
        var cp = getCirclePx();
        if (isOnCircleHandle(pos.x, pos.y, cp)) {{
          dragMode = 'resize-circle';
        }} else if (isInsideCircle(pos.x, pos.y, cp)) {{
          dragMode = 'move-circle';
          dragOffsetX = pos.x - cp.x;
          dragOffsetY = pos.y - cp.y;
          canvas.style.cursor = 'grabbing';
        }}
        return;
      }}
      var rp = getRectPx();
      var rectResizeMode = getRectResizeMode(pos.x, pos.y, rp);
      if (rectResizeMode) {{
        dragMode = rectResizeMode;
        if (rectResizeMode === 'resize-rect-n' || rectResizeMode === 'resize-rect-s') canvas.style.cursor = 'ns-resize';
        else if (rectResizeMode === 'resize-rect-e' || rectResizeMode === 'resize-rect-w') canvas.style.cursor = 'ew-resize';
        else if (rectResizeMode === 'resize-rect-ne' || rectResizeMode === 'resize-rect-sw') canvas.style.cursor = 'nesw-resize';
        else canvas.style.cursor = 'nwse-resize';
      }} else if (isInsideRect(pos.x, pos.y, rp)) {{
        dragMode = 'move-rect';
        dragOffsetX = pos.x - rp.x;
        dragOffsetY = pos.y - rp.y;
        canvas.style.cursor = 'grabbing';
      }}
    }});

    canvas.addEventListener('mousemove', function(e) {{
      var pos = getMousePos(e);
      updateCursor(pos.x, pos.y);
      if (!dragMode) return;

      if (dragMode === 'move-line') {{
        lineState.y = pos.y / H;
        clampLine();
      }} else if (dragMode === 'move-circle') {{
        circleState.x = (pos.x - dragOffsetX) / W;
        circleState.y = (pos.y - dragOffsetY) / H;
        clampCircle();
      }} else if (dragMode === 'resize-circle') {{
        var cp = getCirclePx();
        var dx = pos.x - cp.x;
        var dy = pos.y - cp.y;
        circleState.r = Math.max(minR, Math.sqrt(dx*dx + dy*dy) / Math.min(W, H));
        clampCircle();
      }} else if (dragMode === 'move-rect') {{
        rectState.x = (pos.x - dragOffsetX) / W;
        rectState.y = (pos.y - dragOffsetY) / H;
        clampRect();
      }} else if (dragMode && dragMode.indexOf('resize-rect') === 0) {{
        var left = rectState.x;
        var top = rectState.y;
        var right = rectState.x + rectState.w;
        var bottom = rectState.y + rectState.h;
        var px = pos.x / W;
        var py = pos.y / H;

        if (dragMode === 'resize-rect-e' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-se') right = px;
        if (dragMode === 'resize-rect-w' || dragMode === 'resize-rect-nw' || dragMode === 'resize-rect-sw') left = px;
        if (dragMode === 'resize-rect-s' || dragMode === 'resize-rect-se' || dragMode === 'resize-rect-sw') bottom = py;
        if (dragMode === 'resize-rect-n' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-nw') top = py;

        if (right - left < minW) {{
          if (dragMode === 'resize-rect-w' || dragMode === 'resize-rect-nw' || dragMode === 'resize-rect-sw') left = right - minW;
          else right = left + minW;
        }}
        if (bottom - top < minH) {{
          if (dragMode === 'resize-rect-n' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-nw') top = bottom - minH;
          else bottom = top + minH;
        }}

        rectState.x = left;
        rectState.y = top;
        rectState.w = right - left;
        rectState.h = bottom - top;
        clampRect();
      }}
      draw();
    }});

    function endDrag() {{
      dragMode = null;
      canvas.style.cursor = 'grab';
      saveState();
    }}

    canvas.addEventListener('mouseup', endDrag);
    canvas.addEventListener('mouseleave', endDrag);
    canvas.addEventListener('touchstart', function(e) {{
      e.preventDefault();
      var t = e.touches[0];
      var pos = getMousePos(t);
      if (modo === 'line') {{
        var lp = getLinePx();
        if (isOnLine(pos.y, lp)) dragMode = 'move-line';
        return;
      }}
      if (modo === 'roi') {{
        var cp = getCirclePx();
        if (isOnCircleHandle(pos.x, pos.y, cp)) {{
          dragMode = 'resize-circle';
        }} else if (isInsideCircle(pos.x, pos.y, cp)) {{
          dragMode = 'move-circle';
          dragOffsetX = pos.x - cp.x;
          dragOffsetY = pos.y - cp.y;
        }}
        return;
      }}
      var rp = getRectPx();
      var rectResizeMode = getRectResizeMode(pos.x, pos.y, rp);
      if (rectResizeMode) {{
        dragMode = rectResizeMode;
      }} else if (isInsideRect(pos.x, pos.y, rp)) {{
        dragMode = 'move-rect';
        dragOffsetX = pos.x - rp.x;
        dragOffsetY = pos.y - rp.y;
      }}
    }}, {{passive:false}});

    canvas.addEventListener('touchmove', function(e) {{
      e.preventDefault();
      if (!dragMode) return;
      var t = e.touches[0];
      var pos = getMousePos(t);
      if (dragMode === 'move-line') {{
        lineState.y = pos.y / H;
        clampLine();
      }} else if (dragMode === 'move-circle') {{
        circleState.x = (pos.x - dragOffsetX) / W;
        circleState.y = (pos.y - dragOffsetY) / H;
        clampCircle();
      }} else if (dragMode === 'resize-circle') {{
        var cp = getCirclePx();
        var dx = pos.x - cp.x;
        var dy = pos.y - cp.y;
        circleState.r = Math.max(minR, Math.sqrt(dx*dx + dy*dy) / Math.min(W, H));
        clampCircle();
      }} else if (dragMode === 'move-rect') {{
        rectState.x = (pos.x - dragOffsetX) / W;
        rectState.y = (pos.y - dragOffsetY) / H;
        clampRect();
      }} else if (dragMode && dragMode.indexOf('resize-rect') === 0) {{
        var left = rectState.x;
        var top = rectState.y;
        var right = rectState.x + rectState.w;
        var bottom = rectState.y + rectState.h;
        var px = pos.x / W;
        var py = pos.y / H;

        if (dragMode === 'resize-rect-e' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-se') right = px;
        if (dragMode === 'resize-rect-w' || dragMode === 'resize-rect-nw' || dragMode === 'resize-rect-sw') left = px;
        if (dragMode === 'resize-rect-s' || dragMode === 'resize-rect-se' || dragMode === 'resize-rect-sw') bottom = py;
        if (dragMode === 'resize-rect-n' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-nw') top = py;

        if (right - left < minW) {{
          if (dragMode === 'resize-rect-w' || dragMode === 'resize-rect-nw' || dragMode === 'resize-rect-sw') left = right - minW;
          else right = left + minW;
        }}
        if (bottom - top < minH) {{
          if (dragMode === 'resize-rect-n' || dragMode === 'resize-rect-ne' || dragMode === 'resize-rect-nw') top = bottom - minH;
          else bottom = top + minH;
        }}

        rectState.x = left;
        rectState.y = top;
        rectState.w = right - left;
        rectState.h = bottom - top;
        clampRect();
      }}
      draw();
    }}, {{passive:false}});

    canvas.addEventListener('touchend', endDrag);
    img.onload = function() {{ draw(); }};
    if (img.complete) draw();
  }});
}})();
</script>
'''
    return html


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE UI
# ═══════════════════════════════════════════════════════════════════════════
def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible", disabled=False, format_func=None):
    """Selectbox con 'Seleccionar' al inicio; devuelve None si no hay selección."""
    opciones = ["Seleccionar"] + list(options)
    if value in options and value is not None:
        idx = opciones.index(value)
    else:
        idx = 0
    if format_func is None:
        def _fmt(x):
            return "Seleccionar" if x == "Seleccionar" else str(x)
        format_func = _fmt
    val = st.selectbox(
        label,
        opciones,
        index=idx,
        key=key,
        label_visibility=label_visibility,
        disabled=disabled,
        format_func=format_func,
    )
    return None if val == "Seleccionar" else val


def _number(label, value, key, min_value=0, max_value=4000, step=10, disabled=False):
    try:
        value = int(value)
    except Exception:
        value = min_value
    return st.number_input(
        label, min_value=min_value, max_value=max_value,
        step=step, value=value, key=key,
        label_visibility="collapsed", disabled=disabled,
    )


def _text_disabled(label, value, key):
    st.text_input(label, value=str(value), disabled=True, key=key, label_visibility="collapsed")


def _adq_pair(col, etiqueta, render_fn):
    """Renderiza una etiqueta arriba + un widget debajo dentro de una columna."""
    with col:
        st.markdown(f"**{etiqueta}**")
        render_fn()


# ═══════════════════════════════════════════════════════════════════════════
# ESTADO: exploraciones
# ═══════════════════════════════════════════════════════════════════════════
def _new_id() -> str:
    return f"exp_{uuid.uuid4().hex[:8]}"


def _crear_exploracion_base(topo_set_idx=None):
    if topo_set_idx is None:
        topo_set_idx = st.session_state.get("topograma_set_activo", 0)
    return {
        "id": _new_id(),
        "topo_set_idx": topo_set_idx,
        "order": _next_order(),
        "nombre": None,
        "tipo_exp": None,
        "mod_corriente": "MANUAL",
        "mas_val": None,
        "ind_ruido": None,
        "ind_cal": None,
        "rango_ma": None,
        "kvp": None,
        "doble_muestreo": "NO",
        "conf_det": None,
        "cobertura_tabla": "—",
        "grosor_prosp": None,
        "sfov": None,
        "voz_adq": None,
        "retardo": None,
        "pitch": None,
        "rot_tubo": None,
        "inicio_ref": None,
        "ini_mm": 0,
        "fin_ref": None,
        "fin_mm": 400,
        "observaciones": "",
        # BOLUS
        "periodo": None,
        "n_imagenes": None,
        "posicion_corte": None,
        "umbral_tracking": None,
    }


def _init_state():
    # IMPORTANTE: primero inicializamos los sets de topograma. Así el
    # topograma legacy recibe su `order` antes de que creemos la primera
    # exploración por defecto, y queda correctamente ANTES de ella en
    # el sidebar cronológico.
    _init_topograma_sets()
    st.session_state.setdefault("exploraciones", [])
    st.session_state.setdefault("exp_activa", "topograma")
    if not st.session_state["exploraciones"]:
        st.session_state["exploraciones"] = [_crear_exploracion_base()]


def _get_set_exp(exp) -> dict:
    """Devuelve el dict del set de topograma asociado a una exploración.
    Fallback: topograma_store legado."""
    sets = st.session_state.get("topograma_sets")
    if sets:
        idx = exp.get("topo_set_idx", 0) if exp else 0
        if 0 <= idx < len(sets):
            return sets[idx]
    return st.session_state.get("topograma_store", {}) or {}


def _get_region_label(exp) -> str:
    """Obtiene el nombre del examen/región asociado a una exploración."""
    store = _get_set_exp(exp)
    return (store.get("examen") or store.get("region_anat") or store.get("region") or "").strip()


def _region_grupo(exp=None):
    """Determina el grupo anatómico para REFS_INICIO/REFS_FIN a partir del
    topograma de la exploración. Si no se pasa exp, cae al store legado."""
    if exp is not None:
        store = _get_set_exp(exp)
    else:
        store = st.session_state.get("topograma_store", {}) or {}
    region = (store.get("region_anat") or store.get("region") or st.session_state.get("region_anat", "") or "").upper()
    examen = (store.get("examen") or st.session_state.get("examen", "") or "").upper()
    if "ANGIO" in region or examen.startswith("ATC"):
        return "ANGIO"
    for key in REFS_INICIO:
        if key in region:
            return key
    return "CUERPO"



EXPLORACION_COLORS = [
    "#00D2FF",  # cian
    "#FFB000",  # ámbar
    "#7CFF6B",  # verde
    "#FF5CA8",  # fucsia
    "#A78BFA",  # violeta
    "#FF7A59",  # naranja
    "#5EEAD4",  # turquesa
    "#FACC15",  # amarillo
]


def _color_exploracion(exp):
    """Devuelve un color fijo para cada exploración según su posición actual."""
    exploraciones = st.session_state.get("exploraciones", [])
    try:
        idx = next(i for i, e in enumerate(exploraciones) if e.get("id") == exp.get("id"))
    except Exception:
        idx = 0
    return EXPLORACION_COLORS[idx % len(EXPLORACION_COLORS)]



def _ajustar_por_nombre(exp):
    """Reglas automáticas al cambiar el nombre de la exploración."""
    nombre = exp.get("nombre")
    if nombre in ("BOLUS TEST", "BOLUS TRACKING"):
        exp["tipo_exp"] = "SECUENCIAL CONTIGUO"
        exp["mas_val"] = 20
        exp["kvp"] = 100


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR: lista de exploraciones
# ═══════════════════════════════════════════════════════════════════════════


def _render_dot_for_exp(exp):
    color = _color_exploracion(exp)
    st.markdown(
        f"""
        <div style="
            width: 0.78rem;
            height: 0.78rem;
            border-radius: 50%;
            background: {color};
            margin: 0 auto;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.14);
        "></div>
        """,
        unsafe_allow_html=True,
    )


def _name_visible(exp, idx):
    nombre = exp.get("nombre")
    if not nombre or nombre == "Seleccionar":
        nombre = f"EXPLORACIÓN {idx+1}"

    region = _get_region_label(exp)
    return f"{region} · {nombre}".strip(" ·")


def _inject_sidebar_css():
    """CSS del sidebar: botones con texto completo (envuelto a varias líneas si
    hace falta), un único tamaño de fuente consistente para topogramas,
    exploraciones y botones de agregar. Sin truncado con elipsis."""
    st.markdown(
        """
        <style>
        /* Header "Exploraciones" que cabe bien aunque el sidebar sea angosto */
        section[data-testid="stVerticalBlock"] h3:first-of-type {
            font-size: 1.15rem !important;
            margin-bottom: 0.6rem !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.2 !important;
        }

        /* ── Botones de eliminar (tertiary: ✕) ── */
        button[kind="tertiary"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-height: 2.25rem !important;
            height: 2.25rem !important;
            width: 2.25rem !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 8px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1 !important;
            font-size: 1.05rem !important;
            color: #d8d8d8 !important;
        }
        button[kind="tertiary"]:hover {
            background: rgba(255,255,255,0.06) !important;
            color: white !important;
        }
        button[kind="tertiary"] p {
            margin: 0 !important;
            line-height: 1 !important;
        }

        /* ── Botones principales del sidebar (secondary y primary) ──
           Todos usan el mismo tamaño de fuente. Permitimos que el texto se
           envuelva a varias líneas para no truncarlo con "...". */
        div[data-testid="stButton"] > button[kind="secondary"],
        div[data-testid="stButton"] > button[kind="primary"] {
            min-height: 2.4rem !important;
            height: auto !important;
            padding-top: 0.45rem !important;
            padding-bottom: 0.45rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
            font-size: 0.85rem !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            text-align: center !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] p,
        div[data-testid="stButton"] > button[kind="secondary"] span,
        div[data-testid="stButton"] > button[kind="secondary"] div,
        div[data-testid="stButton"] > button[kind="primary"] p,
        div[data-testid="stButton"] > button[kind="primary"] span,
        div[data-testid="stButton"] > button[kind="primary"] div {
            font-size: 0.85rem !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            word-break: break-word !important;
            overflow-wrap: break-word !important;
            margin: 0 !important;
        }

        /* ── Botones de acción global (+ Exploración / + Topograma) ──
           Streamlit genera una clase `st-key-<key>` en el contenedor del
           widget según el key que le pasemos. Esto nos permite apuntarlos
           con precisión quirúrgica, sin depender de markers ni :has(). */
        .st-key-btn_add_exp_global button[kind="secondary"],
        .st-key-btn_add_set_sidebar button[kind="secondary"],
        div.stApp .st-key-btn_add_exp_global button[kind="secondary"],
        div.stApp .st-key-btn_add_set_sidebar button[kind="secondary"] {
            background-color: #6b6f7a !important;
            background: #6b6f7a !important;
            border: 1px solid #80848f !important;
            color: #ffffff !important;
            box-sizing: border-box !important;
            min-height: 2.75rem !important;
            height: 2.75rem !important;
            max-height: 2.75rem !important;
            font-size: 0.9rem !important;
            padding: 0 1rem !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        .st-key-btn_add_exp_global button[kind="secondary"]:hover,
        .st-key-btn_add_set_sidebar button[kind="secondary"]:hover,
        div.stApp .st-key-btn_add_exp_global button[kind="secondary"]:hover,
        div.stApp .st-key-btn_add_set_sidebar button[kind="secondary"]:hover {
            background-color: #7c808a !important;
            background: #7c808a !important;
            border-color: #90949e !important;
            color: #ffffff !important;
        }
        .st-key-btn_add_exp_global button[kind="secondary"] p,
        .st-key-btn_add_exp_global button[kind="secondary"] span,
        .st-key-btn_add_exp_global button[kind="secondary"] div,
        .st-key-btn_add_set_sidebar button[kind="secondary"] p,
        .st-key-btn_add_set_sidebar button[kind="secondary"] span,
        .st-key-btn_add_set_sidebar button[kind="secondary"] div {
            font-size: 0.9rem !important;
            line-height: 1 !important;
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Marker invisible (no ocupa espacio ni se ve) */
        div[data-testid="stElementContainer"]:has(.sb-add-buttons-zone) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar():

    _inject_sidebar_css()
    st.markdown("### 📋 Exploraciones")

    _init_topograma_sets()
    sets = st.session_state["topograma_sets"]
    set_activo = st.session_state.get("topograma_set_activo", 0)
    viendo_topo = st.session_state.get("exp_activa") == "topograma"
    exploraciones = st.session_state["exploraciones"]

    # ── Determinar a qué topograma se asociará la próxima exploración ──
    activa = st.session_state.get("exp_activa")
    if isinstance(activa, int) and 0 <= activa < len(exploraciones):
        target_idx = exploraciones[activa].get("topo_set_idx", set_activo)
    else:
        target_idx = set_activo
    if not (0 <= target_idx < len(sets)):
        target_idx = 0

    target_lbl = sets[target_idx].get("label") or f"Topograma {target_idx+1}"
    target_reg = sets[target_idx].get("examen") or sets[target_idx].get("region_anat") or "sin región"

    # Asegurar que toda exploración tenga `order` (defensivo / migración)
    for i_exp, exp in enumerate(exploraciones):
        if "order" not in exp:
            exp["order"] = _next_order()

    # Construir lista unificada ordenada cronológicamente
    items = []
    for i, s in enumerate(sets):
        items.append(("set", i, s.get("order", 0)))
    for i_exp, exp in enumerate(exploraciones):
        items.append(("exp", i_exp, exp.get("order", 0)))
    items.sort(key=lambda x: x[2])

    hay_varios_sets = len(sets) > 1
    hay_varias_exp = len(exploraciones) > 1

    # Renderizar ítems en orden de creación
    for item_type, item_idx, _ord in items:
        if item_type == "set":
            i = item_idx
            s = sets[i]
            lbl = s.get("label") or f"Topograma {i+1}"
            reg = s.get("examen") or s.get("region_anat") or "sin región"
            es_activo_topo = (viendo_topo and set_activo == i)
            tipo = "primary" if es_activo_topo else "secondary"

            if hay_varios_sets:
                c_dot, c_main, c_del = st.columns([0.45, 6.2, 0.55], gap="small", vertical_alignment="center")
                with c_dot:
                    st.markdown(
                        '<div style="width:0.78rem;height:0.78rem;border-radius:50%;margin:0 auto;opacity:0;"></div>',
                        unsafe_allow_html=True,
                    )
                with c_main:
                    if st.button(
                        f"📡 {lbl} · {reg}",
                        key=f"btn_topograma_sidebar_{i}",
                        type=tipo,
                        use_container_width=True,
                    ):
                        st.session_state["topograma_set_activo"] = i
                        st.session_state["exp_activa"] = "topograma"
                        st.rerun()
                with c_del:
                    st.markdown('<div style="height: 0.05rem;"></div>', unsafe_allow_html=True)
                    if st.button(
                        "✕",
                        key=f"del_set_sidebar_{i}",
                        type="tertiary",
                        use_container_width=True,
                        help=f"Eliminar {lbl} · {reg}",
                    ):
                        _eliminar_set_topograma(i)
                        st.rerun()
            else:
                c_dot, c_main = st.columns([0.45, 6.2], gap="small", vertical_alignment="center")
                with c_dot:
                    st.markdown(
                        '<div style="width:0.78rem;height:0.78rem;border-radius:50%;margin:0 auto;opacity:0;"></div>',
                        unsafe_allow_html=True,
                    )
                with c_main:
                    if st.button(
                        f"📡 {lbl} · {reg}",
                        key=f"btn_topograma_sidebar_{i}",
                        type=tipo,
                        use_container_width=True,
                    ):
                        st.session_state["topograma_set_activo"] = i
                        st.session_state["exp_activa"] = "topograma"
                        st.rerun()

        else:
            i_exp = item_idx
            exp = exploraciones[i_exp]
            es_exp_activa = (st.session_state.get("exp_activa") == i_exp)
            tipo_exp = "primary" if es_exp_activa else "secondary"

            topo_idx = exp.get("topo_set_idx", 0)
            s_exp = sets[topo_idx] if 0 <= topo_idx < len(sets) else None
            nombre_topo = None
            if s_exp is not None:
                nombre_topo = s_exp.get("examen") or s_exp.get("region_anat")

            region_exp = _get_region_label(exp)
            if region_exp:
                sufijo = ""
            elif nombre_topo:
                sufijo = f"  ·  {nombre_topo}"
            elif hay_varios_sets:
                sufijo = f"  ·  T{topo_idx + 1}"
            else:
                sufijo = ""

            nombre_exp = _name_visible(exp, i_exp)

            if hay_varias_exp:
                c_dot, c_main, c_del = st.columns([0.45, 6.2, 0.55], gap="small", vertical_alignment="center")
                with c_dot:
                    _render_dot_for_exp(exp)
                with c_main:
                    if st.button(
                        f"⚡ {nombre_exp}{sufijo}",
                        key=f"btn_sidebar_exp_{exp['id']}",
                        type=tipo_exp,
                        use_container_width=True,
                    ):
                        st.session_state["exp_activa"] = i_exp
                        st.rerun()
                with c_del:
                    st.markdown('<div style="height: 0.05rem;"></div>', unsafe_allow_html=True)
                    if st.button(
                        "✕",
                        key=f"del_exp_{exp['id']}",
                        type="tertiary",
                        use_container_width=True,
                        help=f"Eliminar {nombre_exp}",
                    ):
                        st.session_state["exploraciones"].pop(i_exp)
                        nueva_activa = min(i_exp, len(st.session_state["exploraciones"]) - 1)
                        st.session_state["exp_activa"] = nueva_activa
                        st.rerun()
            else:
                c_dot, c_main = st.columns([0.45, 6.2], gap="small", vertical_alignment="center")
                with c_dot:
                    _render_dot_for_exp(exp)
                with c_main:
                    if st.button(
                        f"⚡ {nombre_exp}{sufijo}",
                        key=f"btn_sidebar_exp_{exp['id']}",
                        type=tipo_exp,
                        use_container_width=True,
                    ):
                        st.session_state["exp_activa"] = i_exp
                        st.rerun()

    st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)

    # Marker para que el CSS identifique los botones de agregar
    st.markdown('<div class="sb-add-buttons-zone"></div>', unsafe_allow_html=True)

    # ➕ Exploración — con dot invisible a la izquierda, igual al layout
    # de las exploraciones, para que todo quede alineado
    c_dot_e, c_main_e = st.columns([0.45, 6.2], gap="small", vertical_alignment="center")
    with c_dot_e:
        st.markdown(
            '<div style="width:0.78rem;height:0.78rem;border-radius:50%;margin:0 auto;opacity:0;"></div>',
            unsafe_allow_html=True,
        )
    with c_main_e:
        if st.button(
            "+ Exploración",
            key="btn_add_exp_global",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["exploraciones"].append(
                _crear_exploracion_base(topo_set_idx=target_idx)
            )
            st.session_state["exp_activa"] = len(st.session_state["exploraciones"]) - 1
            st.rerun()

    st.markdown("<div style='height:0.18rem;'></div>", unsafe_allow_html=True)

    # ➕ Topograma — mismo patrón para alineación visual
    c_dot_t, c_main_t = st.columns([0.45, 6.2], gap="small", vertical_alignment="center")
    with c_dot_t:
        st.markdown(
            '<div style="width:0.78rem;height:0.78rem;border-radius:50%;margin:0 auto;opacity:0;"></div>',
            unsafe_allow_html=True,
        )
    with c_main_t:
        if st.button(
            "+ Topograma",
            key="btn_add_set_sidebar",
            use_container_width=True,
            type="secondary",
        ):
            _agregar_set_topograma()
            st.session_state["exp_activa"] = "topograma"
            st.rerun()


def obtener_imagen_posicion_corte(nombre_posicion):
    """Devuelve la ruta del PNG correspondiente a la posición de corte de bolus."""
    if not nombre_posicion:
        return None
    nombre = str(nombre_posicion).strip()
    if not nombre or nombre == "Seleccionar":
        return None

    candidatas = [
        DIR_POSICION_CORTE_BOLUS / f"{nombre}.png",
        DIR_POSICION_CORTE_BOLUS / f"{nombre}.jpg",
        DIR_POSICION_CORTE_BOLUS / f"{nombre}.jpeg",
    ]
    for ruta in candidatas:
        if ruta.exists():
            return ruta
    return None


# ═══════════════════════════════════════════════════════════════════════════
# TOPOGRAMAS CON DFOV (reemplaza al "Resumen de referencia" azul)
# ═══════════════════════════════════════════════════════════════════════════


def _guardar_snapshot_adquisicion(exp, group_keys):
    exp_id = exp.get("id")
    if not exp_id:
        st.error("No se encontró el ID de la exploración.")
        return False

    st.session_state.setdefault("canvas_group_keys_adq_por_exp", {})
    st.session_state["canvas_group_keys_adq_por_exp"][exp_id] = list(group_keys or [])

    items = []
    keys_usadas = [gk for gk in (group_keys or []) if gk]

    for idx, group_key in enumerate(keys_usadas):
        try:
            capturados = capture_canvas_group(
                group_key,
                js_key=f"cap_adq_{exp_id}_{idx}",
            )
            if capturados:
                items.extend(capturados)
        except Exception:
            pass

    if not items:
        st.warning(
            "No se pudo capturar el canvas visual de esta adquisición. "
            "Ajusta nuevamente los rangos, ROI o DFOV y vuelve a presionar el botón."
        )
        return False

    combinado = combine_png_bytes(items)
    if not combinado:
        st.warning(
            "Se encontraron canvases, pero no se pudo construir la imagen combinada para el PDF."
        )
        return False

    set_snapshot("canvas_snapshots_adq_por_exp", exp_id, combinado)

    topo_idx = exp.get("topo_set_idx")
    if topo_idx is not None:
        set_snapshot(
            "canvas_snapshots_topo_por_set",
            topo_idx,
            combinado,
            extra={"exp_id": exp_id},
        )

    st.success("Snapshot de adquisición guardado para el PDF.")
    return True


def _render_boton_snapshot_adquisicion(exp, group_keys):
    exp_id = exp.get("id")
    if not exp_id:
        return

    st.session_state.setdefault("canvas_group_keys_adq_por_exp", {})
    st.session_state["canvas_group_keys_adq_por_exp"][exp_id] = list(group_keys or [])

    c1, c2 = st.columns([1.35, 2.15], gap="small")

    with c1:
        if st.button(
            "📸 Guardar adquisición para PDF",
            key=f"btn_guardar_snapshot_adq_{exp_id}",
            use_container_width=True,
            type="secondary",
        ):
            ok = _guardar_snapshot_adquisicion(exp, group_keys)
            st.session_state["_ultimo_snapshot_adq"] = {
                "exp_id": exp_id,
                "ok": bool(ok),
            }

    with c2:
        ya_guardado = exp_id in (st.session_state.get("canvas_snapshots_adq_por_exp", {}) or {})
        if ya_guardado:
            st.caption("✅ Esta adquisición ya tiene snapshot guardado para el PDF.")
        else:
            st.caption("Guarda aquí los rangos, ROI, colores y recuadros visibles de esta adquisición.")

    ultimo = st.session_state.get("_ultimo_snapshot_adq")
    if isinstance(ultimo, dict) and ultimo.get("exp_id") == exp_id:
        if ultimo.get("ok"):
            st.success("Snapshot guardado. Ya puedes ir a Exportar.")
        else:
            st.error("No se pudo guardar el snapshot de esta adquisición.")

def _render_topogramas_adq(exp, es_bolus):
    """Muestra el/los topograma(s) con caja DFOV (rect) o línea de corte (bolus).
    Lee del set de topograma asociado a la exploración."""
    tstore = _get_set_exp(exp)
    hay_topo1 = bool(tstore.get("topograma_iniciado", False))
    hay_topo2 = bool(
        tstore.get("aplica_topo2") and tstore.get("topograma2_iniciado", False)
    )

    topos = []

    if hay_topo1:
        img1, _err1 = obtener_imagen_topograma_adquirido(
            tstore.get("examen") or st.session_state.get("examen", ""),
            tstore.get("posicion") or "",
            tstore.get("entrada") or "",
            tstore.get("t1pt") or "",
        )
        if img1 is not None:
            topos.append({
                "titulo": "✅ Topograma 1",
                "subtitulo": (
                    f"Tubo: {tstore.get('t1pt') or '—'} · "
                    f"{tstore.get('t1l') or '—'} mm · 100 kV · 40 mA"
                ),
                "img_b64": _pil_to_b64_jpeg(img1),
            })

    if hay_topo2:
        img2, _err2 = obtener_imagen_topograma_adquirido(
            tstore.get("t2_examen") or tstore.get("examen") or st.session_state.get("examen", ""),
            tstore.get("t2_posicion_paciente") or tstore.get("t2_posicion") or "",
            tstore.get("t2_entrada_paciente") or tstore.get("t2_entrada") or "",
            tstore.get("t2_posicion_tubo") or tstore.get("t2pt") or "",
        )
        if img2 is not None:
            topos.append({
                "titulo": "✅ Topograma 2",
                "subtitulo": (
                    f"Tubo: {tstore.get('t2pt') or '—'} · "
                    f"{tstore.get('t2l') or '—'} mm · 100 kV · 40 mA"
                ),
                "img_b64": _pil_to_b64_jpeg(img2),
            })

    if not topos:
        st.info("Inicia el/los topograma(s) en la pestaña Topograma para verlos aquí con la caja DFOV.")
        return

    # Enriquecer con inicio/fin para posicionar la caja
    grupo = _region_grupo(exp)
    refs_ini = REFS_INICIO.get(grupo, REFS_INICIO["CUERPO"])
    refs_fin = REFS_FIN.get(grupo, REFS_FIN["CUERPO"])
    ini_ref = exp.get("inicio_ref") or refs_ini[0]
    fin_ref = exp.get("fin_ref") or refs_fin[0]
    ini_mm = int(exp.get("ini_mm", 0) or 0)
    fin_mm = int(exp.get("fin_mm", 400) or 400)

    for t in topos:
        t["inicio_ref"] = ini_ref
        t["fin_ref"] = fin_ref
        t["inicio_mm"] = ini_mm
        t["fin_mm"] = fin_mm
        t["y_ini"] = get_y_position_with_offset(ini_ref, ini_mm)
        t["y_fin"] = get_y_position_with_offset(fin_ref, fin_mm)

    modo = "line" if es_bolus else "rect"
    color_exp = _color_exploracion(exp)

    if es_bolus:
        # En bolus se muestran los topogramas más compactos y, a la derecha,
        # la imagen de posición de corte más grande, como en el PlaniTC original.
        html_topo1 = None
        html_topo2 = None
        if len(topos) >= 1:
            html_topo1 = render_topogramas_independientes_interactivos(
                [topos[0]],
                modo=modo,
                storage_key=f"{exp['id']}_topo1",
                color=color_exp,
                show_labels=False,
                canvas_css_width=182,
                canvas_css_height=290,
            )
        if len(topos) >= 2:
            html_topo2 = render_topogramas_independientes_interactivos(
                [topos[1]],
                modo=modo,
                storage_key=f"{exp['id']}_topo2",
                color=color_exp,
                show_labels=False,
                canvas_css_width=182,
                canvas_css_height=290,
            )

        ruta_posicion = obtener_imagen_posicion_corte(exp.get("posicion_corte"))
        html_roi_corte = None
        if ruta_posicion is not None:
            try:
                img_pos = Image.open(ruta_posicion)
                html_roi_corte = render_topogramas_independientes_interactivos(
                    [{
                        "titulo": exp.get("posicion_corte", "Posición de corte"),
                        "subtitulo": "",
                        "img_b64": _pil_to_b64_jpeg(img_pos),
                    }],
                    modo="roi",
                    storage_key=f"{exp['id']}_roi_corte",
                    color=color_exp,
                    show_labels=False,
                    roi_label="ROI",
                    canvas_css_width=500,
                    canvas_css_height=300,
                    canvas_width=980,
                    canvas_height=600,
                )
            except Exception:
                html_roi_corte = None

        if len(topos) >= 2 and html_topo1 and html_topo2 and html_roi_corte:
            c1, c2, c3 = st.columns([0.86, 0.86, 2.08], gap="medium")
            with c1:
                st.components.v1.html(html_topo1, height=405)
            with c2:
                st.components.v1.html(html_topo2, height=405)
            with c3:
                st.components.v1.html(html_roi_corte, height=430)
            _render_boton_snapshot_adquisicion(exp, [f"{exp['id']}_topo1", f"{exp['id']}_topo2", f"{exp['id']}_roi_corte"])
        elif html_roi_corte:
            c1, c2 = st.columns([1.0, 2.0], gap="medium")
            with c1:
                html_topos = render_topogramas_independientes_interactivos(
                    topos,
                    modo=modo,
                    storage_key=exp["id"],
                    color=color_exp,
                    show_labels=False,
                    canvas_css_width=186 if len(topos) > 1 else 240,
                    canvas_css_height=290 if len(topos) > 1 else 340,
                )
                if html_topos:
                    st.components.v1.html(html_topos, height=430 if len(topos) > 1 else 470)
            with c2:
                st.components.v1.html(html_roi_corte, height=430 if len(topos) > 1 else 500)
            _render_boton_snapshot_adquisicion(exp, [exp['id'], f"{exp['id']}_roi_corte"])
        else:
            html = render_topogramas_independientes_interactivos(
                topos,
                modo=modo,
                storage_key=exp["id"],
                color=color_exp,
                show_labels=False,
                canvas_css_width=186 if len(topos) > 1 else None,
                canvas_css_height=290 if len(topos) > 1 else None,
            )
            if html:
                st.components.v1.html(html, height=430 if len(topos) > 1 else 470)
                _render_boton_snapshot_adquisicion(exp, [exp['id']])
        return

    html = render_topogramas_independientes_interactivos(
        topos,
        modo=modo,
        storage_key=exp["id"],
        color=color_exp,
        show_labels=False,
    )
    if html:
        alto = 430 if len(topos) > 1 else 470
        st.components.v1.html(html, height=alto)
        _render_boton_snapshot_adquisicion(exp, [exp['id']])


# ═══════════════════════════════════════════════════════════════════════════
# RENDERIZADO DE FILAS (lógica dinámica del PlaniTC original)
# ═══════════════════════════════════════════════════════════════════════════
def _render_normales(exp):
    """Filas 1-4 para exploraciones que no son BOLUS."""
    eid = exp["id"]
    grupo = _region_grupo(exp)
    refs_ini = REFS_INICIO.get(grupo, REFS_INICIO["CUERPO"])
    refs_fin = REFS_FIN.get(grupo, REFS_FIN["CUERPO"])

    # ── FILA 1: modulación / mAs / índice / kV (dinámica) ──
    r1_icon, r1_body = st.columns([0.12, 1], gap="small")
    with r1_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>☢️</div>", unsafe_allow_html=True)
    with r1_body:
        c1, c2, c3, c4 = st.columns(4, gap="small")

        def _render_mod():
            exp["mod_corriente"] = selectbox_con_placeholder(
                "Modulación corriente", MODULACION_CORRIENTE,
                value=exp.get("mod_corriente"),
                key=f"mod_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c1, "Modulación corriente", _render_mod)

        mod = exp.get("mod_corriente")
        if mod == "CARE DOSE 4D":
            def _render_mas():
                exp["mas_val"] = selectbox_con_placeholder(
                    "mAs REF", MAS_OPCIONES,
                    value=exp.get("mas_val"),
                    key=f"masref_{eid}", label_visibility="collapsed",
                )
            def _render_indice():
                exp["ind_cal"] = selectbox_con_placeholder(
                    "Índice de calidad", INDICE_CALIDAD,
                    value=exp.get("ind_cal"),
                    key=f"indcal_{eid}", label_visibility="collapsed",
                )
            mas_label = "mAs REF"
            indice_label = "Índice calidad"
            exp["ind_ruido"] = None
            exp["rango_ma"] = None
        elif mod == "AUTO mA":
            def _render_mas():
                exp["rango_ma"] = selectbox_con_placeholder(
                    "Rango mA", RANGO_MA,
                    value=exp.get("rango_ma"),
                    key=f"rangoma_{eid}", label_visibility="collapsed",
                )
                # Derivar mas_val del máximo del rango para cálculos de dosis
                try:
                    exp["mas_val"] = int(str(exp.get("rango_ma", "")).split("-")[1].strip())
                except Exception:
                    exp["mas_val"] = 200
            def _render_indice():
                exp["ind_ruido"] = selectbox_con_placeholder(
                    "Índice de ruido", INDICE_RUIDO,
                    value=exp.get("ind_ruido"),
                    key=f"indruido_{eid}", label_visibility="collapsed",
                )
            mas_label = "Rango mA"
            indice_label = "Índice ruido"
            exp["ind_cal"] = None
        else:  # MANUAL o sin seleccionar
            def _render_mas():
                exp["mas_val"] = selectbox_con_placeholder(
                    "mAs", MAS_OPCIONES,
                    value=exp.get("mas_val"),
                    key=f"mas_{eid}", label_visibility="collapsed",
                )
            def _render_indice():
                st.markdown("<div style='height: 2.45rem;'></div>", unsafe_allow_html=True)
            mas_label = "mAs"
            indice_label = ""
            exp["ind_ruido"] = None
            exp["ind_cal"] = None
            exp["rango_ma"] = None

        _adq_pair(c2, mas_label, _render_mas)
        _adq_pair(c3, indice_label, _render_indice)

        def _render_kv():
            exp["kvp"] = selectbox_con_placeholder(
                "kV", KVP_OPCIONES,
                value=exp.get("kvp"),
                key=f"kv_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c4, "kV", _render_kv)

    # ── FILA 2: tipo / doble muestreo / conf.detección / cobertura / grosor / SFOV ──
    r2_icon, r2_body = st.columns([0.12, 1], gap="small")
    with r2_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>⚙️</div>", unsafe_allow_html=True)
    with r2_body:
        c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")

        def _render_tipo():
            exp["tipo_exp"] = selectbox_con_placeholder(
                "Tipo exploración", TIPOS_EXPLORACION,
                value=exp.get("tipo_exp"),
                key=f"tipoexp_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c1, "Tipo exploración", _render_tipo)

        tipo_exp = exp.get("tipo_exp")
        if tipo_exp == "HELICOIDAL":
            def _render_dm():
                exp["doble_muestreo"] = selectbox_con_placeholder(
                    "Doble muestreo", ["NO", "SI"],
                    value=exp.get("doble_muestreo", "NO"),
                    key=f"dm_{eid}", label_visibility="collapsed",
                )
        else:
            exp["doble_muestreo"] = "NO"
            def _render_dm():
                _text_disabled("Doble muestreo", "No aplica", key=f"dm_na_{eid}")
        _adq_pair(c2, "Doble muestreo", _render_dm)

        opciones_conf = obtener_opciones_conf_det(tipo_exp, exp.get("doble_muestreo"))
        if exp.get("conf_det") not in opciones_conf:
            exp["conf_det"] = None

        def _render_confdet():
            exp["conf_det"] = selectbox_con_placeholder(
                "Conf. detección", opciones_conf,
                value=exp.get("conf_det"),
                key=f"confdet_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c3, "Conf. detección", _render_confdet)

        cobertura = obtener_cobertura_tabla(
            tipo_exp, exp.get("conf_det"), exp.get("doble_muestreo")
        )
        exp["cobertura_tabla"] = cobertura

        # NOTA: escribimos en session_state ANTES de renderizar porque
        # st.text_input con key= ignora el parámetro value= después del primer render.
        # Este es el patrón usado en el PlaniTC original.
        st.session_state[f"cobertura_{eid}"] = str(cobertura)

        def _render_cob():
            st.text_input(
                "Cobertura",
                key=f"cobertura_{eid}",
                disabled=True,
                label_visibility="collapsed",
            )
        _adq_pair(c4, "Cobertura", _render_cob)

        grosor_opciones = [str(g) for g in GROSOR_PROSP]
        def _render_grosor():
            exp["grosor_prosp"] = selectbox_con_placeholder(
                "Grosor prosp.", grosor_opciones,
                value=exp.get("grosor_prosp"),
                key=f"gpros_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c5, "Grosor prosp.", _render_grosor)

        def _render_sfov():
            exp["sfov"] = selectbox_con_placeholder(
                "SFOV", SFOV_OPCIONES,
                value=exp.get("sfov"),
                key=f"sfov_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c6, "SFOV", _render_sfov)

    # ── FILA 3: voz / retardo / pitch / rotación ──
    r3_icon, r3_body = st.columns([0.12, 1], gap="small")
    with r3_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>🕒</div>", unsafe_allow_html=True)
    with r3_body:
        c1, c2, c3, c4 = st.columns(4, gap="small")

        def _render_voz():
            exp["voz_adq"] = selectbox_con_placeholder(
                "Instrucción de voz", INSTRUCCIONES_VOZ,
                value=exp.get("voz_adq"),
                key=f"voz_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c1, "Instrucción de voz", _render_voz)

        def _render_delay():
            exp["retardo"] = selectbox_con_placeholder(
                "Retardo", RETARDOS,
                value=exp.get("retardo"),
                key=f"delay_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c2, "Retardo", _render_delay)

        if tipo_exp == "HELICOIDAL":
            def _render_pitch():
                exp["pitch"] = selectbox_con_placeholder(
                    "Pitch", PITCH_OPCIONES,
                    value=exp.get("pitch"),
                    key=f"pitch_{eid}", label_visibility="collapsed",
                )
        else:
            exp["pitch"] = 1.0
            def _render_pitch():
                _text_disabled("Pitch", "No aplica", key=f"pitch_na_{eid}")
        _adq_pair(c3, "Pitch", _render_pitch)

        def _render_rot():
            exp["rot_tubo"] = selectbox_con_placeholder(
                "TPO ROTACION TUBO", ROT_TUBO,
                value=exp.get("rot_tubo"),
                key=f"rot_{eid}", label_visibility="collapsed",
                format_func=lambda x: "Seleccionar" if x in (None, "Seleccionar") else f"{x} sg.",
            )
        _adq_pair(c4, "TPO ROTACION TUBO", _render_rot)

    # ── FILA 4: rango de exploración ──
    r4_icon, r4_body = st.columns([0.12, 1], gap="small")
    with r4_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>📏</div>", unsafe_allow_html=True)
    with r4_body:
        r1, r2, r3, r4 = st.columns(4, gap="small")

        def _render_iniref():
            exp["inicio_ref"] = selectbox_con_placeholder(
                "Inicio exploración", refs_ini,
                value=exp.get("inicio_ref"),
                key=f"iniref_{eid}", label_visibility="collapsed",
            )
        _adq_pair(r1, "Inicio exploración", _render_iniref)

        def _render_inimm():
            exp["ini_mm"] = _number("mm inicio", exp.get("ini_mm", 0), key=f"inimm_{eid}")
        _adq_pair(r2, "mm inicio", _render_inimm)

        def _render_finref():
            exp["fin_ref"] = selectbox_con_placeholder(
                "Fin exploración", refs_fin,
                value=exp.get("fin_ref"),
                key=f"finref_{eid}", label_visibility="collapsed",
            )
        _adq_pair(r3, "Fin exploración", _render_finref)

        def _render_finmm():
            exp["fin_mm"] = _number("mm fin", exp.get("fin_mm", 400), key=f"finmm_{eid}")
        _adq_pair(r4, "mm fin", _render_finmm)


def _render_bolus(exp):
    """Parámetros específicos para BOLUS TEST / BOLUS TRACKING.
    Según el PlaniTC original, estas exploraciones no usan el mismo bloque
    de parámetros que las demás adquisiciones.
    """
    eid = exp["id"]

    # Mantener configuración fija propia de bolus
    exp["tipo_exp"] = "SECUENCIAL CONTIGUO"
    exp["mod_corriente"] = "MANUAL"
    exp["mas_val"] = 20
    exp["kvp"] = 100
    exp["ind_ruido"] = None
    exp["ind_cal"] = None
    exp["rango_ma"] = None
    exp["doble_muestreo"] = "NO"
    exp["conf_det"] = None
    exp["cobertura_tabla"] = "—"
    exp["grosor_prosp"] = None
    exp["sfov"] = None
    exp["pitch"] = None
    exp["rot_tubo"] = None

    # FILA 1: parámetros propios del bolus
    r1_icon, r1_body = st.columns([0.12, 1], gap="small")
    with r1_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>🎯</div>", unsafe_allow_html=True)
    with r1_body:
        c1, c2, c3 = st.columns(3, gap="small")

        def _render_periodo():
            exp["periodo"] = selectbox_con_placeholder(
                "Periodo", PERIODO_TEST_BOLUS,
                value=exp.get("periodo"),
                key=f"periodo_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c1, "Periodo", _render_periodo)

        def _render_nimg():
            exp["n_imagenes"] = selectbox_con_placeholder(
                "N° imágenes", N_IMAGENES_TEST_BOLUS,
                value=exp.get("n_imagenes"),
                key=f"nimg_{eid}", label_visibility="collapsed",
            )
        _adq_pair(c2, "N° imágenes", _render_nimg)

        if exp.get("nombre") == "BOLUS TRACKING":
            def _render_umbral():
                exp["umbral_tracking"] = selectbox_con_placeholder(
                    "Umbral de disparo", UMBRAL_TRACKING,
                    value=exp.get("umbral_tracking"),
                    key=f"uth_{eid}", label_visibility="collapsed",
                )
            _adq_pair(c3, "Umbral disparo", _render_umbral)
        else:
            exp["umbral_tracking"] = None
            _adq_pair(
                c3,
                "Umbral disparo",
                lambda: _text_disabled("Umbral NA", "No aplica", key=f"uth_na_{eid}")
            )

    # FILA 2: configuración fija de bolus
    r2_icon, r2_body = st.columns([0.12, 1], gap="small")
    with r2_icon:
        st.markdown("<div style='font-size:2rem; text-align:center; margin-top:1.6rem;'>⚙️</div>", unsafe_allow_html=True)
    with r2_body:
        c1, c2 = st.columns(2, gap="small")

        _adq_pair(c1, "mAs", lambda: _text_disabled("mAs fijo", "20", key=f"mas_bolus_{eid}"))
        _adq_pair(c2, "kV", lambda: _text_disabled("kV fijo", "100", key=f"kv_bolus_{eid}"))


# ═══════════════════════════════════════════════════════════════════════════
# RESUMEN CALCULADO: CTDI, duración, ruido, cobertura
# ═══════════════════════════════════════════════════════════════════════════
def _render_resumen_calculado(exp):
    kvp = exp.get("kvp") or 120
    mas = exp.get("mas_val") or 200
    conf_det = exp.get("conf_det") or (CONF_DETECTORES[0] if CONF_DETECTORES else None)
    pitch = exp.get("pitch") or 1.0
    rot_tubo = exp.get("rot_tubo") or 0.5
    ini_mm = exp.get("ini_mm", 0)
    fin_mm = exp.get("fin_mm", 400)
    try:
        grosor_float = float(str(exp.get("grosor_prosp") or "1").replace(",", "."))
    except Exception:
        grosor_float = 1.0

    cob = calcular_cobertura_helical(conf_det, pitch)
    cob_str = f"{cob} mm/rot" if isinstance(cob, float) else "—"
    ctdi = estimar_dosis_ctdi(kvp, mas, conf_det)
    duracion = calcular_duracion(ini_mm, fin_mm, cob if isinstance(cob, float) else 1, rot_tubo)
    ruido = nivel_ruido_estimado(mas, kvp, grosor_float)

    exp["ctdi"] = ctdi
    exp["ruido_est"] = ruido
    exp["cobertura"] = cob
    exp["duracion"] = duracion

    st.markdown("---")
    st.markdown("**Resumen calculado automáticamente**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cobertura/rot.", cob_str)
    c2.metric("CTDIvol estimado", f"{ctdi} mGy" if ctdi != "—" else "—")
    c3.metric("Duración scan", f"{duracion} sg" if duracion != "—" else "—")
    c4.metric("Ruido relativo", f"{ruido}" if ruido != "—" else "—")

    if isinstance(ctdi, float) and ctdi > 30:
        st.warning("⚠️ Dosis estimada elevada. Considere reducir mAs o usar modulación automática.")
    elif isinstance(ctdi, float):
        st.info("✅ Dosis dentro de rangos aceptables para esta exploración.")


def _render_warnings(exp):
    msgs = []
    nombre = exp.get("nombre")
    es_bolus = nombre in ("BOLUS TEST", "BOLUS TRACKING")
    if not nombre:
        msgs.append("⚠️ Falta seleccionar el nombre de la exploración.")
    if not es_bolus:
        if not exp.get("conf_det"):
            msgs.append("⚠️ Falta seleccionar configuración de detectores.")
        if not exp.get("voz_adq"):
            msgs.append("⚠️ Falta definir la instrucción de voz.")
    else:
        if not exp.get("posicion_corte"):
            msgs.append("⚠️ Falta definir la posición de corte.")
    for m in msgs:
        st.warning(m)
    if not msgs and nombre:
        st.success("Configuración lista para continuar.")


# ═══════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════
def render_adquisicion():
    _init_state()

    col_sidebar, col_main = st.columns([1.05, 4.8], gap="large")
    with col_sidebar:
        _render_sidebar()

    with col_main:
        activa = st.session_state.get("exp_activa", "topograma")
        if activa == "topograma":
            render_topograma_panel()
            return

        idx = int(activa)
        if idx < 0 or idx >= len(st.session_state["exploraciones"]):
            st.warning("Selecciona una exploración en el panel lateral.")
            return

        exp = st.session_state["exploraciones"][idx]

        # ── Selector de topograma de referencia (solo si hay >1 set) ──
        sets = st.session_state.get("topograma_sets", [])
        if len(sets) > 1:
            opciones = list(range(len(sets)))

            def _fmt_set(i):
                s = sets[i]
                lbl = s.get("label") or f"Topograma {i+1}"
                reg = s.get("examen") or s.get("region_anat") or "sin región"
                return f"{lbl} — {reg}"

            cur = exp.get("topo_set_idx", 0)
            if cur not in opciones:
                cur = 0
            nuevo_set = st.selectbox(
                "Topograma de referencia",
                opciones,
                index=opciones.index(cur),
                format_func=_fmt_set,
                key=f"toposet_{exp['id']}",
            )
            if nuevo_set != exp.get("topo_set_idx"):
                exp["topo_set_idx"] = nuevo_set
                # Las refs anatómicas del otro set pueden ser distintas: reset
                exp["inicio_ref"] = None
                exp["fin_ref"] = None
                st.rerun()

        # Nombre de la exploración (arriba, ancho completo)
        nombre_prev = exp.get("nombre")
        exp["nombre"] = selectbox_con_placeholder(
            "Nombre de la exploración", NOMBRES_EXPLORACION,
            value=nombre_prev,
            key=f"nombre_{exp['id']}",
        )
        if exp["nombre"] != nombre_prev:
            _ajustar_por_nombre(exp)

        es_bolus = exp.get("nombre") in ("BOLUS TEST", "BOLUS TRACKING")

        # Para Bolus: posición de corte va justo debajo del nombre,
        # antes de los topogramas (afecta a la línea de corte del canvas).
        if es_bolus:
            exp["posicion_corte"] = selectbox_con_placeholder(
                "Posición de corte", POSICION_CORTE_BOLUS,
                value=exp.get("posicion_corte"),
                key=f"poscorte_{exp['id']}",
            )

        # Topogramas con DFOV (sustituye el "Resumen de referencia")
        _render_topogramas_adq(exp, es_bolus)

        # Filas de parámetros
        if es_bolus:
            _render_bolus(exp)
        else:
            _render_normales(exp)

        # Resumen calculado + warnings
        if not es_bolus:
            _render_resumen_calculado(exp)
        _render_warnings(exp)
