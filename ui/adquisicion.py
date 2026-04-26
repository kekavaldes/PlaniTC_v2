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
import time
import uuid
import base64
import hashlib
from pathlib import Path

import streamlit as st
from PIL import Image

from ui.canvas_snapshot import (
    capture_canvas_group,
    capture_all_snapshots_raw,
    items_for_group,
    combine_png_bytes,
    set_snapshot,
)

import ui.topograma as topograma_mod

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
# CONVERSIÓN DE IMAGEN PIL A BASE64 (para canvas HTML) — con caché manual
# ═══════════════════════════════════════════════════════════════════════════
# Evitamos @st.cache_data + hash_funcs porque PIL.Image es una familia de
# subclases (JpegImageFile, PngImageFile, …) y Streamlit las hashea por tipo
# exacto, no por isinstance → UnhashableParamError. Un dict de módulo con
# tope de tamaño funciona igual de bien para este caso.
_B64_JPEG_CACHE: dict = {}
_B64_JPEG_CACHE_MAX = 128


def _render_b64_jpeg(img, max_width):
    """Encodeo puro, sin caché."""
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


def _pil_to_b64_jpeg(img, max_width=900):
    """Convierte una imagen PIL a base64 JPEG para usarla en canvas HTML.
    Cacheado a nivel de módulo por (md5(tobytes), size, mode, max_width)."""
    if img is None:
        return None
    try:
        fp = (
            hashlib.md5(img.tobytes()).hexdigest(),
            img.size,
            img.mode,
            max_width,
        )
    except Exception:
        # Si no podemos calcular el fingerprint, encodeamos sin cachear.
        return _render_b64_jpeg(img, max_width)

    cached = _B64_JPEG_CACHE.get(fp)
    if cached is not None:
        return cached

    result = _render_b64_jpeg(img, max_width)
    if result is not None:
        _B64_JPEG_CACHE[fp] = result
        if len(_B64_JPEG_CACHE) > _B64_JPEG_CACHE_MAX:
            # Poda FIFO aproximada: borramos la mitad más vieja.
            keys = list(_B64_JPEG_CACHE.keys())
            for k in keys[: len(keys) // 2]:
                _B64_JPEG_CACHE.pop(k, None)
    return result


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
    exp_nombre=None,  # Nombre de la exploración para el archivo descargado
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
        # Ya no se usan campos manuales de inicio/fin del topograma.
        # Si no viene una posición guardada, se usa un DFOV inicial amplio y editable.
        y_ini = topo.get("y_ini", 0.25)
        y_fin = topo.get("y_fin", 0.75)

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
          <div style="margin-top:8px; font-size:12px; color:#ccc; text-align:center; min-height:32px;">{subtitulo}</div>
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
// Función global de descarga - VERSION SIMPLE PARA DEBUG
function downloadCanvasInd(idx, title, expNombre) {{
  console.log('downloadCanvasInd llamado con:', {{ idx: idx, title: title, expNombre: expNombre }});
  
  var canvas = document.getElementById('topoCanvasInd' + idx);
  if (!canvas) {{
    alert('Canvas no encontrado');
    return;
  }}
  
  // Construir nombre de archivo: EXPLORACION_TITULO.png
  var parts = [];
  
  // Limpiar y añadir nombre de exploración
  if (expNombre && expNombre !== 'null' && String(expNombre).trim()) {{
    var clean = String(expNombre).replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '');
    if (clean) parts.push(clean);
  }}
  
  // Limpiar y añadir título
  if (title && title !== 'null' && String(title).trim()) {{
    var clean = String(title).replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '');
    if (clean) parts.push(clean);
  }}
  
  // Fallback si no hay nada
  var filename = parts.length > 0 ? parts.join('_') : 'topograma_' + idx;
  
  console.log('Nombre de archivo generado:', filename);
  
  var a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = filename + '.png';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  
  console.log('Descargado:', filename + '.png');
}}

// Lógica de canvas
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

  topoData.forEach(function(data, idx) {{
    var canvas = document.getElementById('topoCanvasInd' + idx);
    if (!canvas) return;

    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var storageKey = baseStorageKey ? ('planitc_' + baseStorageKey + '_' + modo + '_' + idx) : '';
    var snapshotKey = baseStorageKey ? ('planitc_snapshot_' + baseStorageKey + '_' + idx) : '';

    // Persistencia robusta: en Safari/Streamlit a veces localStorage del iframe
    // se pierde o queda aislado. Por eso usamos varias capas:
    // 1) localStorage del iframe, 2) localStorage del padre/top si está permitido,
    // 3) sessionStorage, 4) window.name como memoria del iframe entre rerenders,
    // 5) window.name como memoria del iframe entre rerenders.
    // IMPORTANTE: no usamos cookies para imágenes/base64 porque inflan el header HTTP.
    function _wnRead() {{
      try {{
        if (!window.name || window.name.indexOf('PLANITC_STORE::') !== 0) return {{}};
        return JSON.parse(window.name.substring('PLANITC_STORE::'.length)) || {{}};
      }} catch(e) {{ return {{}}; }}
    }}

    function _wnWrite(obj) {{
      try {{ window.name = 'PLANITC_STORE::' + JSON.stringify(obj || {{}}); }} catch(e) {{}}
    }}


    function lsGet(key) {{
      var v = null;
      try {{ v = window.localStorage.getItem(key); if (v !== null && v !== undefined) return v; }} catch (e) {{}}
      try {{ v = window.sessionStorage.getItem(key); if (v !== null && v !== undefined) return v; }} catch (e) {{}}
      try {{
        if (window.parent && window.parent !== window && window.parent.localStorage) {{
          v = window.parent.localStorage.getItem(key);
          if (v !== null && v !== undefined) return v;
        }}
      }} catch (e) {{}}
      try {{
        if (window.top && window.top !== window && window.top.localStorage) {{
          v = window.top.localStorage.getItem(key);
          if (v !== null && v !== undefined) return v;
        }}
      }} catch (e) {{}}
      try {{ var store = _wnRead(); if (store && store[key]) return store[key]; }} catch(e) {{}}
      return null;
    }}

    function lsSet(key, value) {{
      try {{ window.localStorage.setItem(key, value); }} catch (e) {{}}
      try {{ window.sessionStorage.setItem(key, value); }} catch (e) {{}}
      try {{
        if (window.parent && window.parent !== window && window.parent.localStorage) {{
          window.parent.localStorage.setItem(key, value);
        }}
      }} catch (e) {{}}
      try {{
        if (window.top && window.top !== window && window.top.localStorage) {{
          window.top.localStorage.setItem(key, value);
        }}
      }} catch (e) {{}}
      try {{ var store = _wnRead(); store[key] = value; _wnWrite(store); }} catch(e) {{}}
    }}

    var saveTimer = null;
    function scheduleSave() {{
      if (saveTimer) return;
      saveTimer = window.setTimeout(function() {{
        saveTimer = null;
        saveState();
      }}, 80);
    }}

    var rectState = {{ x: data.rect_x, y: data.rect_y, w: data.rect_w, h: data.rect_h }};
    var lineState = {{ y: data.line_y }};
    var circleState = {{ x: data.circle_x, y: data.circle_y, r: data.circle_r }};

    try {{
      if (storageKey) {{
        var saved = lsGet(storageKey);
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
          lsSet(storageKey, JSON.stringify({{
            rectState: rectState,
            lineState: lineState,
            circleState: circleState
          }}));
        }}
        if (snapshotKey) {{
          lsSet(snapshotKey, canvas.toDataURL('image/png'));
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
      scheduleSave();
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
      scheduleSave();
    }}, {{passive:false}});

    canvas.addEventListener('touchend', endDrag);
    canvas.addEventListener('touchcancel', endDrag);
    window.addEventListener('pagehide', saveState);
    window.addEventListener('beforeunload', saveState);
    document.addEventListener('visibilitychange', function() {{ if (document.hidden) saveState(); }});
    img.onload = function() {{ draw(); saveState(); }};
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
# FIX ROBUSTO: imágenes para DECÚBITO LATERAL DERECHO / IZQUIERDO
# ═══════════════════════════════════════════════════════════════════════════
_ORIGINAL_OBTENER_IMAGEN_TOPOGRAMA_ADQUIRIDO = obtener_imagen_topograma_adquirido


def _strip_accents_planitc(texto):
    import unicodedata
    if texto is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")


def _posicion_paciente_variantes(posicion):
    if posicion is None:
        return [""]
    base = str(posicion).strip()
    if not base or base == "Seleccionar":
        return [""]
    up = _strip_accents_planitc(base).upper().strip()
    variantes = [base, up, up.title(), up.lower()]
    if "LATERAL" in up and ("DERECHO" in up or "DER" in up):
        variantes.extend([
            "DECÚBITO LATERAL DERECHO", "DECUBITO LATERAL DERECHO",
            "DECUBITO LATERAL DER", "DECÚBITO LATERAL DER",
            "LATERAL DERECHO", "LATERAL DER", "DERECHO", "DER",
            "decúbito lateral derecho", "decubito lateral derecho", "lateral derecho",
            "lateral_der", "lateral_derecho", "decubito_lateral_der",
            "decubito_lateral_derecho", "decúbito_lateral_derecho",
        ])
    elif "LATERAL" in up and ("IZQUIERDO" in up or "IZQ" in up):
        variantes.extend([
            "DECÚBITO LATERAL IZQUIERDO", "DECUBITO LATERAL IZQUIERDO",
            "DECUBITO LATERAL IZQ", "DECÚBITO LATERAL IZQ",
            "LATERAL IZQUIERDO", "LATERAL IZQ", "IZQUIERDO", "IZQ",
            "decúbito lateral izquierdo", "decubito lateral izquierdo", "lateral izquierdo",
            "lateral_izq", "lateral_izquierdo", "decubito_lateral_izq",
            "decubito_lateral_izquierdo", "decúbito_lateral_izquierdo",
        ])
    extras = []
    for v in variantes:
        s = str(v).strip()
        extras.extend([s, s.replace("_", " "), s.replace(" ", "_"),
                       s.replace("Ú", "U").replace("ú", "u"),
                       s.replace("DECUBITO", "DECÚBITO").replace("Decubito", "Decúbito"),
                       s.title(), s.lower(), s.upper()])
    salida, vistos = [], set()
    for v in extras:
        v = str(v).strip()
        k = _strip_accents_planitc(v).upper()
        if v and k not in vistos:
            vistos.add(k)
            salida.append(v)
    return salida or [base]


def _obtener_imagen_topograma_adquirido_flexible(examen, posicion, entrada, posicion_tubo):
    ultimo_error = None
    for pos in _posicion_paciente_variantes(posicion):
        img, err = _ORIGINAL_OBTENER_IMAGEN_TOPOGRAMA_ADQUIRIDO(examen, pos, entrada, posicion_tubo)
        if img is not None:
            return img, None
        ultimo_error = err
    return None, ultimo_error


obtener_imagen_topograma_adquirido = _obtener_imagen_topograma_adquirido_flexible


def _wrap_helper_lateral_flexible(func):
    if getattr(func, "_planitc_lateral_patch", False):
        return func

    def _wrapped(*args, **kwargs):
        res = None
        try:
            res = func(*args, **kwargs)
            if res is not None:
                if isinstance(res, tuple):
                    if len(res) and res[0] is not None:
                        return res
                else:
                    return res
        except Exception:
            pass

        for idx, val in enumerate(args):
            up = _strip_accents_planitc(val).upper() if isinstance(val, str) else ""
            if "LATERAL" not in up:
                continue
            for variante in _posicion_paciente_variantes(val):
                if variante == val:
                    continue
                new_args = list(args)
                new_args[idx] = variante
                try:
                    r = func(*new_args, **kwargs)
                    if r is None:
                        continue
                    if isinstance(r, tuple):
                        if len(r) and r[0] is not None:
                            return r
                    else:
                        return r
                except Exception:
                    pass

        for key, val in list(kwargs.items()):
            up = _strip_accents_planitc(val).upper() if isinstance(val, str) else ""
            if "LATERAL" not in up:
                continue
            for variante in _posicion_paciente_variantes(val):
                if variante == val:
                    continue
                new_kwargs = dict(kwargs)
                new_kwargs[key] = variante
                try:
                    r = func(*args, **new_kwargs)
                    if r is None:
                        continue
                    if isinstance(r, tuple):
                        if len(r) and r[0] is not None:
                            return r
                    else:
                        return r
                except Exception:
                    pass
        return res

    _wrapped._planitc_lateral_patch = True
    _wrapped.__name__ = getattr(func, "__name__", "wrapped_lateral_flexible")
    _wrapped.__doc__ = getattr(func, "__doc__", None)
    return _wrapped


def _patch_topograma_module_image_helpers():
    try:
        topograma_mod.obtener_imagen_topograma_adquirido = _obtener_imagen_topograma_adquirido_flexible
        for name in dir(topograma_mod):
            lname = name.lower()
            obj = getattr(topograma_mod, name, None)
            if not callable(obj):
                continue
            if name == "render_topograma_panel":
                continue
            if (("imagen" in lname or "image" in lname or "ruta" in lname or "path" in lname)
                and ("posicion" in lname or "paciente" in lname or "topograma" in lname)):
                setattr(topograma_mod, name, _wrap_helper_lateral_flexible(obj))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# FIX UI: ocultar inicio/fin y ordenar parámetros del topograma en 3 columnas
# ═══════════════════════════════════════════════════════════════════════════
def _norm_label_topo(label):
    return _strip_accents_planitc(label).upper() if isinstance(label, str) else ""


def _topo_field_id(label):
    """Clasifica los campos del panel de topograma que queremos reordenar."""
    texto = _norm_label_topo(label)
    if "INICIO TOPOGRAMA" in texto or "FIN TOPOGRAMA" in texto:
        return "ocultar_inicio_fin"
    if "CENTRAJE" in texto and "INICIO" in texto and "TOPOGRAMA" in texto:
        return "centraje"
    if "DIRECCION" in texto and "TOPOGRAMA" in texto:
        return "direccion"
    if "LONGITUD" in texto and "TOPOGRAMA" in texto:
        return "longitud"
    if "INSTRUCCION" in texto and "VOZ" in texto:
        return "voz"
    limpio = texto.strip().replace(" ", "")
    if limpio in ("KV", "KVP"):
        return "kv"
    if limpio in ("MA", "MAS", "MA."):
        return "ma"
    return None




def _es_label_kv_ma_markdown(body):
    """Detecta etiquetas sueltas kV/mA que ui.topograma.py a veces
    dibuja con st.markdown antes del number_input. Se usa solo dentro del
    parche del panel de topograma para que no queden duplicadas arriba.
    """
    if not isinstance(body, str):
        return False
    txt = body.strip()
    # Quitar markdown/html simple frecuente: **kV**, ### kV, <b>kV</b>
    for ch in "*#:_`":
        txt = txt.replace(ch, "")
    txt = txt.replace("<b>", "").replace("</b>", "")
    txt = txt.replace("<strong>", "").replace("</strong>", "")
    txt = txt.strip().lower()
    return txt in ("kv", "k v", "ma", "m a")


def _widget_default_value(args, kwargs):
    if "value" in kwargs:
        return kwargs.get("value")
    if len(args) >= 1:
        return args[0]
    return None


def _select_default_value(args, kwargs):
    options = None
    if args:
        options = args[0]
    else:
        options = kwargs.get("options")
    try:
        options = list(options or [])
    except Exception:
        options = []
    if not options:
        return "Seleccionar"
    idx = kwargs.get("index", 0)
    try:
        idx = int(idx)
    except Exception:
        idx = 0
    idx = max(0, min(idx, len(options) - 1))
    return options[idx]


def _guardar_spec_topograma(campo, widget_type, label, args, kwargs):
    """Guarda la definición real del widget de ui.topograma.py para poder
    volver a dibujarlo en el orden solicitado, usando la misma key y opciones.
    """
    specs = st.session_state.setdefault("_planitc_topograma_field_specs", {})
    key = kwargs.get("key")
    spec = {
        "widget_type": widget_type,
        "label": label,
        "args": list(args),
        "kwargs": dict(kwargs),
        "key": key,
    }
    specs[campo] = spec


def _valor_oculto_selectbox(args, kwargs):
    key = kwargs.get("key")
    if key and key in st.session_state:
        return st.session_state[key]
    return _select_default_value(args, kwargs)


def _valor_oculto_number(args, kwargs):
    key = kwargs.get("key")
    if key and key in st.session_state:
        return st.session_state[key]
    return _widget_default_value(args, kwargs)


def _render_widget_desde_spec(spec, original_selectbox, original_number_input, original_text_input, nuevo_label):
    """Dibuja un widget usando su configuración original, pero con etiqueta nueva.

    Importante: Streamlit recibe el label como primer argumento posicional.
    En la versión anterior se pasaba `label` como keyword y también quedaba
    un argumento posicional, provocando TypeError en Streamlit Cloud.
    """
    if not spec:
        return

    args = list(spec.get("args", []))
    kwargs = dict(spec.get("kwargs", {}))
    kwargs.pop("label", None)
    kwargs.pop("label_visibility", None)

    # Si por alguna razón el label original quedó dentro de args, se elimina.
    if args and isinstance(args[0], str):
        args = args[1:]

    if spec.get("widget_type") == "selectbox":
        original_selectbox(nuevo_label, *args, **kwargs)
    elif spec.get("widget_type") == "number_input":
        original_number_input(nuevo_label, *args, **kwargs)
    elif spec.get("widget_type") == "text_input":
        original_text_input(nuevo_label, *args, **kwargs)

def _render_topograma_campos_ordenados(original_selectbox, original_number_input, original_text_input):
    specs = st.session_state.get("_planitc_topograma_field_specs", {}) or {}
    campos_necesarios = ["centraje", "direccion", "longitud", "voz", "kv", "ma"]
    if not any(k in specs for k in campos_necesarios):
        return

    st.markdown(
        """
        <style>
        .planitc-topo-grid-wrap {
            width: 100%;
            max-width: 1280px;
            margin: 0 auto 1.1rem auto;
        }
        .planitc-topo-grid-wrap div[data-testid="stVerticalBlock"] {
            gap: 0.85rem !important;
        }
        .planitc-topo-grid-wrap label,
        .planitc-topo-grid-wrap [data-testid="stWidgetLabel"] {
            text-align: center !important;
            justify-content: center !important;
            font-weight: 700 !important;
        }
        .planitc-topo-grid-wrap div[data-baseweb="select"] > div,
        .planitc-topo-grid-wrap div[data-testid="stNumberInput"] input {
            text-align: center !important;
        }
        </style>
        <div class="planitc-topo-grid-wrap">
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        _render_widget_desde_spec(specs.get("centraje"), original_selectbox, original_number_input, original_text_input, "Centraje inicio de topograma")
        _render_widget_desde_spec(specs.get("direccion"), original_selectbox, original_number_input, original_text_input, "Dirección topograma")
    with col2:
        _render_widget_desde_spec(specs.get("longitud"), original_selectbox, original_number_input, original_text_input, "Longitud de topograma (mm)")
        _render_widget_desde_spec(specs.get("voz"), original_selectbox, original_number_input, original_text_input, "Instrucción de voz")
    with col3:
        _render_widget_desde_spec(specs.get("kv"), original_selectbox, original_number_input, original_text_input, "kV")
        _render_widget_desde_spec(specs.get("ma"), original_selectbox, original_number_input, original_text_input, "mA")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_topograma_panel_sin_inicio_fin():
    """Renderiza el panel de topograma con la grilla solicitada:

    Columna 1: Centraje inicio de topograma / Dirección topograma
    Columna 2: Longitud de topograma / Instrucción de voz
    Columna 3: kV / mA

    Además oculta los campos antiguos Inicio Topograma y Fin Topograma.

    IMPORTANTE:
    Los campos se insertan justo ANTES del checkbox "¿Aplica Topograma 2?".
    Así quedan en la misma zona visual del Topograma 1, debajo del título/imagen
    y no al comienzo de la página.
    """
    original_selectbox = st.selectbox
    original_number_input = st.number_input
    original_text_input = st.text_input
    original_checkbox = st.checkbox
    original_markdown = st.markdown
    st.session_state["_planitc_topograma_grid_rendered"] = False
    # Limpieza defensiva para que no queden specs antiguos de renders previos.
    st.session_state["_planitc_topograma_field_specs"] = {}

    def _selectbox_personalizado(label, *args, **kwargs):
        campo = _topo_field_id(label)
        if campo == "ocultar_inicio_fin":
            return _valor_oculto_selectbox(args, kwargs)
        if campo in ("centraje", "direccion", "longitud", "voz"):
            _guardar_spec_topograma(campo, "selectbox", label, args, kwargs)
            return _valor_oculto_selectbox(args, kwargs)
        return original_selectbox(label, *args, **kwargs)

    def _number_input_personalizado(label, *args, **kwargs):
        campo = _topo_field_id(label)

        # En algunas versiones de ui.topograma.py, kV y mA se dibujan con
        # una etiqueta aparte (st.markdown) y el number_input queda con
        # label oculto o genérico. Por eso, si no logramos reconocer el
        # campo por el label, capturamos los dos primeros number_input del
        # panel como kV y mA respectivamente. Este parche está activo SOLO
        # mientras se renderiza el panel de topograma, por lo que no afecta
        # los parámetros de adquisición.
        if campo is None:
            specs_actuales = st.session_state.get("_planitc_topograma_field_specs", {}) or {}
            if "kv" not in specs_actuales:
                campo = "kv"
            elif "ma" not in specs_actuales:
                campo = "ma"

        if campo in ("kv", "ma"):
            _guardar_spec_topograma(campo, "number_input", label, args, kwargs)
            return _valor_oculto_number(args, kwargs)
        return original_number_input(label, *args, **kwargs)

    def _text_input_personalizado(label, *args, **kwargs):
        campo = _topo_field_id(label)

        # IMPORTANTE:
        # No capturamos text_input sin etiqueta como kV/mA, porque en este panel
        # también existe el campo de nombre del topograma (ej.: "Topograma 1").
        # Ese fue el origen del box incorrecto que aparecía con valor "Topograma 1"
        # bajo la etiqueta kV.
        #
        # Solo capturamos text_input si el label identifica explícitamente kV o mA.
        # Si kV/mA vienen como number_input, se capturan en _number_input_personalizado.
        if campo in ("kv", "ma"):
            _guardar_spec_topograma(campo, "text_input", label, args, kwargs)
            return _widget_default_value(args, kwargs)
        return original_text_input(label, *args, **kwargs)

    def _markdown_personalizado(body, *args, **kwargs):
        # Oculta únicamente las etiquetas sueltas kV/mA del bloque original,
        # porque ahora esos campos se muestran en la tercera columna.
        if _es_label_kv_ma_markdown(body):
            return None
        return original_markdown(body, *args, **kwargs)

    def _checkbox_personalizado(label, *args, **kwargs):
        texto = _norm_label_topo(label)
        if ("APLICA" in texto and "TOPOGRAMA 2" in texto
                and not st.session_state.get("_planitc_topograma_grid_rendered", False)):
            _render_topograma_campos_ordenados(original_selectbox, original_number_input, original_text_input)
            st.session_state["_planitc_topograma_grid_rendered"] = True
        return original_checkbox(label, *args, **kwargs)

    try:
        # Renderizamos el panel original. Durante este render, los campos
        # que queremos mover se capturan y NO se muestran en su ubicación antigua.
        # Cuando aparece "¿Aplica Topograma 2?", insertamos la grilla justo antes.
        st.selectbox = _selectbox_personalizado
        st.number_input = _number_input_personalizado
        st.text_input = _text_input_personalizado
        st.markdown = _markdown_personalizado
        st.checkbox = _checkbox_personalizado
        topograma_mod.render_topograma_panel()

        # Fallback: si por algún cambio futuro no existe el checkbox de Topograma 2,
        # mostramos la grilla al final para que los campos no desaparezcan.
        if not st.session_state.get("_planitc_topograma_grid_rendered", False):
            _render_topograma_campos_ordenados(original_selectbox, original_number_input, original_text_input)
            st.session_state["_planitc_topograma_grid_rendered"] = True
    finally:
        st.selectbox = original_selectbox
        st.number_input = original_number_input
        st.text_input = original_text_input
        st.markdown = original_markdown
        st.checkbox = original_checkbox


# ═══════════════════════════════════════════════════════════════════════════
# TOPOGRAMAS CON DFOV (reemplaza al "Resumen de referencia" azul)
# ═══════════════════════════════════════════════════════════════════════════


def _guardar_snapshot_adquisicion_desde_bulk(exp, group_keys, all_snaps):
    """Toma el dict masivo de snapshots y guarda lo de esta exploración."""
    items = []
    for gk in group_keys:
        items.extend(items_for_group(all_snaps, gk))
    if not items:
        return False
    combinado = combine_png_bytes(items)
    if not combinado:
        return False
    set_snapshot("canvas_snapshots_adq_por_exp", exp["id"], combinado)
    topo_idx = exp.get("topo_set_idx")
    if topo_idx is not None:
        set_snapshot(
            "canvas_snapshots_topo_por_set",
            topo_idx,
            combinado,
            extra={"exp_id": exp.get("id")},
        )
    return True


def _render_boton_snapshot_adquisicion(exp, group_keys):
    """Muestra un botón manual para capturar el snapshot de esta adquisición
    y guardarlo en session_state para el PDF.

    NOTA sobre `streamlit_js_eval`: el componente tiene un bug conocido
    cuando se llama dentro de una rama condicional activada por un botón
    (GitHub issue #2 del repo). Por eso la llamada está al TOPE de la
    función, no dentro del `if nonce:`. Así el iframe permanece montado
    entre reruns y el valor vuelve de forma fiable.
    """
    pending_key = f"_pending_snap_adq_{exp['id']}"
    nonce = st.session_state.get(pending_key, 0)

    # 1) Llamada JS SIEMPRE, fuera de cualquier if. Key estable cuando
    #    no hay captura pendiente; key con nonce cuando sí la hay.
    effective_key = (
        f"snap_adq_{exp['id']}_{nonce}" if nonce else f"snap_adq_{exp['id']}_idle"
    )
    all_snaps = capture_all_snapshots_raw(js_key=effective_key) if nonce else None

    # 2) UI del botón
    col_info, col_btn = st.columns([2.6, 1], gap="small")
    with col_info:
        st.caption(
            "La captura visual se guarda automáticamente desde cada "
            "canvas. Al generar el PDF, el snapshot se incluye automáticamente."
        )
    with col_btn:
        if st.button(
            "💾 Guardar para PDF",
            key=f"btn_snap_adq_{exp['id']}",
            use_container_width=True,
            help="Guarda el canvas actual en el reporte (opcional).",
        ):
            st.session_state[pending_key] = int(time.time() * 1000)
            st.rerun()

    # 3) Procesamiento del resultado (sin st.rerun aquí para evitar loops)
    if nonce:
        consumed_key = f"_consumed_snap_adq_{exp['id']}_{nonce}"
        if st.session_state.get(consumed_key):
            pass  # ya procesado en este nonce
        elif all_snaps is None:
            col_wait, col_cancel = st.columns([3, 1], gap="small")
            with col_wait:
                st.info(
                    "📸 Capturando canvas… Si no avanza en 2-3 segundos, "
                    "vuelve a pulsar **Guardar para PDF**."
                )
            with col_cancel:
                if st.button(
                    "Cancelar",
                    key=f"cancel_snap_adq_{exp['id']}_{nonce}",
                    use_container_width=True,
                ):
                    st.session_state.pop(pending_key, None)
                    st.rerun()
        else:
            st.session_state[consumed_key] = True
            if _guardar_snapshot_adquisicion_desde_bulk(exp, group_keys, all_snaps):
                st.success("✓ Snapshot guardado para el PDF.")
            else:
                st.warning(
                    "No se pudo capturar el canvas. Ajusta algo en la imagen "
                    "y vuelve a intentarlo."
                )
            st.session_state.pop(pending_key, None)


def _guardar_snapshot_adquisicion(exp, group_keys):
    """Compatibilidad: captura por-grupo (versión antigua).
    Se mantiene por si algún código externo la invoca directamente."""
    items = []
    for idx, group_key in enumerate(group_keys):
        items.extend(capture_canvas_group(group_key, js_key=f"cap_adq_{exp['id']}_{idx}"))
    combinado = combine_png_bytes(items)
    if not combinado:
        st.warning("No se pudo capturar el canvas. Mueve un poco la imagen y vuelve a intentarlo.")
        return
    set_snapshot("canvas_snapshots_adq_por_exp", exp["id"], combinado)
    topo_idx = exp.get("topo_set_idx")
    if topo_idx is not None:
        set_snapshot("canvas_snapshots_topo_por_set", topo_idx, combinado, extra={"exp_id": exp.get("id")})
    st.success("Snapshot guardado para el PDF.")

# ═══════════════════════════════════════════════════════════════════════════
# CAPTURA AUTOMÁTICA DE SNAPSHOTS
# ═══════════════════════════════════════════════════════════════════════════
def _process_canvas_snapshot(snapshot_data, exp_id, topo_idx=None):
    """Procesa el snapshot retornado por components.html cuando el usuario
    Convierte el data URL a bytes y lo guarda
    en session_state para incluirlo en el PDF."""
    if not snapshot_data or snapshot_data.get('type') != 'snapshot':
        return False
    
    data_url = snapshot_data.get('data_url', '')
    if not data_url.startswith('data:image/png;base64,'):
        return False
    
    try:
        png_bytes = base64.b64decode(data_url.split(',')[1])
        set_snapshot("canvas_snapshots_adq_por_exp", exp_id, png_bytes)
        if topo_idx is not None:
            set_snapshot(
                "canvas_snapshots_topo_por_set",
                topo_idx,
                png_bytes,
                extra={"exp_id": exp_id},
            )
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# TOPOGRAMAS EN PESTAÑA ADQUISICIÓN
# ═══════════════════════════════════════════════════════════════════════════
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

    # DFOV inicial sin depender de campos manuales de inicio/fin del topograma.
    # El usuario ajusta el rango directamente sobre el canvas.
    for t in topos:
        t["y_ini"] = 0.25
        t["y_fin"] = 0.75

    modo = "line" if es_bolus else "rect"
    color_exp = _color_exploracion(exp)
    
    # Calcular nombre completo para archivos descargados (ej: "TORAX · SIN CONTRASTE")
    region = _get_region_label(exp)
    nombre = exp.get("nombre", "")
    if region and nombre:
        nombre_completo = f"{region}_{nombre}".replace(" ", "_").replace("·", "").replace("__", "_")
    elif region:
        nombre_completo = region.replace(" ", "_")
    elif nombre:
        nombre_completo = nombre.replace(" ", "_")
    else:
        nombre_completo = None

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
                exp_nombre=nombre_completo,
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
                exp_nombre=nombre_completo,
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
                    exp_nombre=nombre_completo,
                )
            except Exception:
                html_roi_corte = None

        if len(topos) >= 2 and html_topo1 and html_topo2 and html_roi_corte:
            c1, c2, c3 = st.columns([0.86, 0.86, 2.08], gap="medium")
            with c1:
                st.components.v1.html(html_topo1, height=470)
            with c2:
                st.components.v1.html(html_topo2, height=470)
            with c3:
                st.components.v1.html(html_roi_corte, height=430)
            # _render_boton_snapshot_adquisicion ya no es necesario (subida manual en pestaña Exportar)
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
                    exp_nombre=nombre_completo,
                )
                if html_topos:
                    st.components.v1.html(html_topos, height=500 if len(topos) > 1 else 560)
            with c2:
                st.components.v1.html(html_roi_corte, height=430 if len(topos) > 1 else 500)
            # _render_boton_snapshot_adquisicion ya no necesario
        else:
            html = render_topogramas_independientes_interactivos(
                topos,
                modo=modo,
                storage_key=exp["id"],
                color=color_exp,
                show_labels=False,
                canvas_css_width=186 if len(topos) > 1 else None,
                canvas_css_height=290 if len(topos) > 1 else None,
                exp_nombre=nombre_completo,
            )
            if html:
                st.components.v1.html(html, height=500 if len(topos) > 1 else 560)
                # _render_boton_snapshot_adquisicion ya no necesario
        return

    html = render_topogramas_independientes_interactivos(
        topos,
        modo=modo,
        storage_key=exp["id"],
        color=color_exp,
        show_labels=False,
        exp_nombre=nombre_completo,
    )
    if html:
        # Altura del componente sin botón manual de descarga
        alto = 455 if len(topos) > 1 else 510
        st.components.v1.html(html, height=alto)
        # _render_boton_snapshot_adquisicion ya no necesario


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
    # Sin campos manuales visibles de inicio/fin: se mantiene una longitud base
    # para el cálculo estimado hasta integrar lectura directa del canvas.
    ini_mm = 0
    fin_mm = 400
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
            _patch_topograma_module_image_helpers()
            _render_topograma_panel_sin_inicio_fin()
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
