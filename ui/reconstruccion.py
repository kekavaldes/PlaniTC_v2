import copy
import io
import json
import base64

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image


def _inject_recon_css():
    st.markdown(
        """
        <style>
        /* Botones de reconstrucción más bajos */
        div[data-testid="stButton"] > button[kind] {
            white-space: nowrap !important;
            padding-top: 0.30rem !important;
            padding-bottom: 0.30rem !important;
            min-height: 2.0rem !important;
            font-size: 0.82rem !important;
            line-height: 1.05 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        div[data-testid="stButton"] > button[kind] p {
            font-size: 0.82rem !important;
            line-height: 1.05 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            color: white !important;
        }

        /* Botones ✕ de eliminar (tertiary) */
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
            font-size: 1.05rem !important;
        }

        /* Botón + Reconstrucción — gris más claro (identificado por st-key) */
        .st-key-rec_btn_add_recon button[kind="secondary"],
        div.stApp .st-key-rec_btn_add_recon button[kind="secondary"] {
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
        .st-key-rec_btn_add_recon button[kind="secondary"]:hover,
        div.stApp .st-key-rec_btn_add_recon button[kind="secondary"]:hover {
            background-color: #7c808a !important;
            background: #7c808a !important;
            border-color: #90949e !important;
            color: #ffffff !important;
        }
        .st-key-rec_btn_add_recon button[kind="secondary"] p,
        .st-key-rec_btn_add_recon button[kind="secondary"] span,
        .st-key-rec_btn_add_recon button[kind="secondary"] div {
            font-size: 0.9rem !important;
            line-height: 1 !important;
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Selects y number inputs un poco más angostos visualmente */
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stNumberInput"] > div {
            max-width: 260px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


REFS_INICIO = {
    "CABEZA": ["VERTEX", "SOBRE SENO FRONTAL", "TECHO ORBITARIO", "CAE",
                "PISO ORBITARIO", "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR",
                "BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO"],
    "CUELLO": ["TECHO ORBITARIO", "CAE", "ARCO AÓRTICO"],
    "EESS": ["SOBRE ART. ACROMIOCLAV.", "BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO",
              "TERCIO PROXIMAL RADIO-CUBITO", "TERCIO PROXIMAL MTC", "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["CAE", "SOBRE BASE DE CRÁNEO", "C6-C7", "T1-T2", "T11-T12", "L1-L2", "L4-L5", "S1-S2"],
    "CUERPO": ["SOBRE ÁPICES PULMONARES", "SOBRE CÚPULAS DIAF.", "ARCO AÓRTICO",
               "BAJO ANGULOS COSTOFR.", "L5-S1"],
    "EEII": ["EIAS", "TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR",
             "TERCIO PROXIMAL TIBIA-PERONÉ", "TERCIO DISTAL TIBIA-PERONÉ",
             "BAJO CALCÁNEO", "HASTA COMPLETAR ORTEJOS"],
    "ANGIO": ["SOBRE ÁPICES PULMONARES", "ARCO AÓRTICO", "SOBRE CÚPULAS DIAF.",
              "BAJO ANGULOS COSTOFR.", "L5-S1", "COMPLETAR FALANGE DISTAL"],
}

REFS_FIN = {
    "CABEZA": ["BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO", "PISO ORBITARIO",
                "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR"],
    "CUELLO": ["CAE", "ARCO AÓRTICO", "MENTON"],
    "EESS": ["BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO", "TERCIO PROXIMAL MTC",
              "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["SOBRE BASE DE CRÁNEO", "T1-T2", "T11-T12", "L4-L5", "S1-S2",
                "1 CM BAJO COXIS", "L5-S1"],
    "CUERPO": ["SOBRE CÚPULAS DIAF.", "BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA"],
    "EEII": ["TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR",
             "TERCIO PROXIMAL TIBIA-PERONÉ", "BAJO CALCÁNEO",
             "HASTA COMPLETAR ORTEJOS", "COMPLETAR ORTEJOS"],
    "ANGIO": ["BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA",
              "COMPLETAR FALANGE DISTAL", "COMPLETAR ORTEJOS"],
}

FASES_RECONS = [
    "SIN CONTRASTE", "ARTERIAL", "VENOSA", "TARDIA",
    "ANGIOGRÁFICA", "REPOSO", "VALSALVA", "INSPIRACIÓN", "ESPIRACIÓN",
]

TIPOS_RECONS = ["RETROP. FILTRADA", "RECONS. ITERATIVA"]
ALGORITMOS_ITERATIVOS = ["SAFIRE", "ADMIRE", "iDOSE", "ASIR-V", "AIDR-3D", "VEO"]

NIVEL_ITERATIVO = {
    "SAFIRE": [1, 2, 3, 4, 5],
    "ADMIRE": [1, 2, 3, 4, 5],
    "iDOSE": [1, 2, 3, 4, 5, 6, 7],
    "ASIR-V": ["0 (%)", "10 (%)", "20 (%)", "30 (%)", "40 (%)", "50 (%)", "60 (%)", "70 (%)", "80 (%)", "90 (%)"],
    "AIDR-3D": ["Mild", "Standard", "Strong"],
    "VEO": ["—"],
}

KERNELS = ["SUAVE 20f", "STANDARD 30f", "DEFINIDO 60f", "ULTRADEFINIDO 80f"]
GROSORES_RECONS = ["0,6 mm", "0,625 mm", "1 mm", "1,2 mm", "1,25 mm", "1,5 mm", "2 mm", "3 mm", "4 mm", "5 mm"]
INCREMENTOS_RECONS = ["0,3 mm", "0,5 mm", "0,6 mm", "0,75 mm", "1 mm", "1,5 mm", "2 mm", "2,5 mm"]

VENTANAS = {
    "PULMONAR": {"ww": 1500, "wl": -600},
    "PARTES BLANDAS": {"ww": 400, "wl": 40},
    "CEREBRO": {"ww": 80, "wl": 35},
    "OSEO": {"ww": 2000, "wl": 400},
    "ANGIOGRÁFICA": {"ww": 600, "wl": 150},
}

DFOV_OPCIONES = ["Mayor al SFOV", "Igual a SFOV", "Menor a SFOV"]


def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    opciones = ["Seleccionar"] + list(options)
    idx = opciones.index(value) if value in options else 0
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


def _mini_chip(color: str, titulo: str = "", subtitulo: str = ""):
    st.markdown(
        f"""
        <div style="
            border:1px solid {color};
            border-radius:12px;
            height:0.22rem;
            background:{color};
            margin-bottom:0.45rem;
        "></div>
        """,
        unsafe_allow_html=True,
    )



def _pil_to_b64_jpeg(img, max_width=900):
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


def render_canvas_recon_cuadrado(
    img_b64,
    storage_key,
    color="#00D2FF",
    titulo="Imagen cargada",
    canvas_css_width=360,
    canvas_css_height=360,
    canvas_width=760,
    canvas_height=760,
):
    if not img_b64:
        return None

    html = f"""
<div style="text-align:center; margin:0;">
  <div style="display:inline-block; font-size:16px; font-weight:600; color:#ddd; margin-bottom:6px;">
    {titulo}
  </div>
  <canvas id="reconSquareCanvas" width="{canvas_width}" height="{canvas_height}"
    style="width:{canvas_css_width}px; height:{canvas_css_height}px; cursor:grab; border:1px solid #444; border-radius:8px; background:#000; display:block; margin:0 auto; touch-action:none;"></canvas>
</div>
<script>
(function() {{
  var imgB64 = {json.dumps(img_b64)};
  var storageKey = {json.dumps('planitc_' + storage_key)};
  var strokeColor = {json.dumps(color)};
  var canvas = document.getElementById('reconSquareCanvas');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  var img = new Image();
  img.src = 'data:image/jpeg;base64,' + imgB64;

  var square = {{ x: 0.23, y: 0.23, s: 0.34 }};
  // Handle activo: 'body' (mover), 'tl', 'tr', 'bl', 'br' (esquinas),
  // 't', 'b', 'l', 'r' (bordes), o null.
  var dragMode = null;
  var dragOffsetX = 0;
  var dragOffsetY = 0;
  // Tolerancia para detectar handles (en px del canvas interno)
  var cornerTol = 22;
  var edgeTol = 14;
  // Tamaño visual de los manijas dibujados sobre el cuadrado
  var handleVisual = 11;
  var minS = 0.10;
  var maxS = 0.96;

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

  try {{
    var saved = localStorage.getItem(storageKey);
    if (saved) {{
      var parsed = JSON.parse(saved);
      if (parsed && parsed.square) square = parsed.square;
    }}
  }} catch (e) {{}}

  function saveState() {{
    try {{
      localStorage.setItem(storageKey, JSON.stringify({{ square: square }}));
    }} catch (e) {{}}
  }}

  function clampSquare() {{
    square.s = Math.max(minS, Math.min(maxS, square.s));
    square.x = Math.max(0.02, Math.min(0.98 - square.s, square.x));
    square.y = Math.max(0.02, Math.min(0.98 - square.s, square.y));
  }}

  function getSquarePx() {{
    return {{ x: square.x * W, y: square.y * H, s: square.s * Math.min(W, H) }};
  }}

  function isInsideSquare(mx, my, sp) {{
    return mx >= sp.x && mx <= sp.x + sp.s && my >= sp.y && my <= sp.y + sp.s;
  }}

  // Detecta qué zona del cuadrado está bajo el puntero. Las esquinas
  // tienen prioridad sobre los bordes; los bordes sobre el interior.
  function detectHandle(mx, my, sp) {{
    var left = sp.x, right = sp.x + sp.s;
    var top = sp.y, bottom = sp.y + sp.s;

    var nearLeft = Math.abs(mx - left) <= cornerTol;
    var nearRight = Math.abs(mx - right) <= cornerTol;
    var nearTop = Math.abs(my - top) <= cornerTol;
    var nearBottom = Math.abs(my - bottom) <= cornerTol;

    if (nearLeft && nearTop) return 'tl';
    if (nearRight && nearTop) return 'tr';
    if (nearLeft && nearBottom) return 'bl';
    if (nearRight && nearBottom) return 'br';

    // Bordes: cerca del borde y dentro del rango perpendicular (con margen)
    if (Math.abs(my - top) <= edgeTol && mx >= left - edgeTol && mx <= right + edgeTol) return 't';
    if (Math.abs(my - bottom) <= edgeTol && mx >= left - edgeTol && mx <= right + edgeTol) return 'b';
    if (Math.abs(mx - left) <= edgeTol && my >= top - edgeTol && my <= bottom + edgeTol) return 'l';
    if (Math.abs(mx - right) <= edgeTol && my >= top - edgeTol && my <= bottom + edgeTol) return 'r';

    if (isInsideSquare(mx, my, sp)) return 'body';
    return null;
  }}

  // Aplica el resize según el handle. El cuadrado siempre se mantiene
  // cuadrado (s es único). Cada handle tiene su punto de anclaje:
  // - esquinas: la esquina opuesta queda fija.
  // - bordes: el borde opuesto queda fijo y la dimensión perpendicular
  //   se expande/contrae simétricamente (se mantiene el centro del eje
  //   perpendicular sobre el que NO se está arrastrando).
  function resizeFromHandle(handle, pos) {{
    var minDim = Math.min(W, H);
    var minPx = minS * minDim;
    var maxPx = maxS * minDim;

    var left = square.x * W;
    var top = square.y * H;
    var sz = square.s * minDim;
    var right = left + sz;
    var bottom = top + sz;
    var cx = left + sz / 2;
    var cy = top + sz / 2;

    var newS;
    switch (handle) {{
      case 'br': {{
        var w = pos.x - left;
        var h = pos.y - top;
        newS = Math.max(w, h);
        newS = Math.max(minPx, Math.min(maxPx, newS));
        square.s = newS / minDim;
        // x, y no cambian (anclado en top-left)
        break;
      }}
      case 'tl': {{
        var w = right - pos.x;
        var h = bottom - pos.y;
        newS = Math.max(w, h);
        newS = Math.max(minPx, Math.min(maxPx, newS));
        square.x = (right - newS) / W;
        square.y = (bottom - newS) / H;
        square.s = newS / minDim;
        break;
      }}
      case 'tr': {{
        var w = pos.x - left;
        var h = bottom - pos.y;
        newS = Math.max(w, h);
        newS = Math.max(minPx, Math.min(maxPx, newS));
        square.x = left / W; // queda como estaba
        square.y = (bottom - newS) / H;
        square.s = newS / minDim;
        break;
      }}
      case 'bl': {{
        var w = right - pos.x;
        var h = pos.y - top;
        newS = Math.max(w, h);
        newS = Math.max(minPx, Math.min(maxPx, newS));
        square.x = (right - newS) / W;
        square.y = top / H; // queda como estaba
        square.s = newS / minDim;
        break;
      }}
      case 't': {{
        // Fijo: borde inferior + centro horizontal
        var h = bottom - pos.y;
        newS = Math.max(minPx, Math.min(maxPx, h));
        square.x = (cx - newS / 2) / W;
        square.y = (bottom - newS) / H;
        square.s = newS / minDim;
        break;
      }}
      case 'b': {{
        // Fijo: borde superior + centro horizontal
        var h = pos.y - top;
        newS = Math.max(minPx, Math.min(maxPx, h));
        square.x = (cx - newS / 2) / W;
        square.y = top / H;
        square.s = newS / minDim;
        break;
      }}
      case 'l': {{
        // Fijo: borde derecho + centro vertical
        var w = right - pos.x;
        newS = Math.max(minPx, Math.min(maxPx, w));
        square.x = (right - newS) / W;
        square.y = (cy - newS / 2) / H;
        square.s = newS / minDim;
        break;
      }}
      case 'r': {{
        // Fijo: borde izquierdo + centro vertical
        var w = pos.x - left;
        newS = Math.max(minPx, Math.min(maxPx, w));
        square.x = left / W;
        square.y = (cy - newS / 2) / H;
        square.s = newS / minDim;
        break;
      }}
    }}
    clampSquare();
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

  function drawSquare() {{
    clampSquare();
    var sp = getSquarePx();
    // Relleno semitransparente
    ctx.fillStyle = rgbaFromHex(strokeColor, 0.14);
    ctx.fillRect(sp.x, sp.y, sp.s, sp.s);
    // Borde punteado
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 3;
    ctx.setLineDash([10, 6]);
    ctx.strokeRect(sp.x, sp.y, sp.s, sp.s);
    ctx.setLineDash([]);

    // Manijas: 4 esquinas + 4 puntos medios de borde
    var hs = handleVisual;
    var cx = sp.x + sp.s / 2;
    var cy = sp.y + sp.s / 2;
    var points = [
      [sp.x, sp.y],                 // tl
      [sp.x + sp.s, sp.y],          // tr
      [sp.x, sp.y + sp.s],          // bl
      [sp.x + sp.s, sp.y + sp.s],   // br
      [cx, sp.y],                   // t
      [cx, sp.y + sp.s],            // b
      [sp.x, cy],                   // l
      [sp.x + sp.s, cy],            // r
    ];
    ctx.fillStyle = strokeColor;
    ctx.strokeStyle = '#0a0a0a';
    ctx.lineWidth = 1.5;
    for (var i = 0; i < points.length; i++) {{
      var px = points[i][0], py = points[i][1];
      ctx.fillRect(px - hs / 2, py - hs / 2, hs, hs);
      ctx.strokeRect(px - hs / 2, py - hs / 2, hs, hs);
    }}
  }}

  function draw() {{
    drawBaseImage();
    drawSquare();
    saveState();
  }}

  function getMousePos(e) {{
    var rect = canvas.getBoundingClientRect();
    var scaleX = W / rect.width;
    var scaleY = H / rect.height;
    return {{ x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY }};
  }}

  function cursorForHandle(h) {{
    if (h === 'tl' || h === 'br') return 'nwse-resize';
    if (h === 'tr' || h === 'bl') return 'nesw-resize';
    if (h === 't' || h === 'b') return 'ns-resize';
    if (h === 'l' || h === 'r') return 'ew-resize';
    if (h === 'body') return 'grab';
    return 'default';
  }}

  function updateCursor(mx, my) {{
    var sp = getSquarePx();
    var h = detectHandle(mx, my, sp);
    canvas.style.cursor = cursorForHandle(h);
  }}

  function startDrag(pos) {{
    var sp = getSquarePx();
    var h = detectHandle(pos.x, pos.y, sp);
    if (!h) return;
    if (h === 'body') {{
      dragMode = 'body';
      dragOffsetX = pos.x - sp.x;
      dragOffsetY = pos.y - sp.y;
      canvas.style.cursor = 'grabbing';
    }} else {{
      dragMode = h;
      canvas.style.cursor = cursorForHandle(h);
    }}
  }}

  function applyDrag(pos) {{
    if (!dragMode) return;
    if (dragMode === 'body') {{
      square.x = (pos.x - dragOffsetX) / W;
      square.y = (pos.y - dragOffsetY) / H;
      clampSquare();
    }} else {{
      resizeFromHandle(dragMode, pos);
    }}
    draw();
  }}

  canvas.addEventListener('mousedown', function(e) {{
    startDrag(getMousePos(e));
  }});

  canvas.addEventListener('mousemove', function(e) {{
    var pos = getMousePos(e);
    if (!dragMode) updateCursor(pos.x, pos.y);
    else applyDrag(pos);
  }});

  function endDrag() {{
    dragMode = null;
    saveState();
  }}

  canvas.addEventListener('mouseup', endDrag);
  canvas.addEventListener('mouseleave', endDrag);

  canvas.addEventListener('touchstart', function(e) {{
    e.preventDefault();
    var t = e.touches[0];
    startDrag(getMousePos(t));
  }}, {{passive:false}});

  canvas.addEventListener('touchmove', function(e) {{
    e.preventDefault();
    if (!dragMode) return;
    var t = e.touches[0];
    applyDrag(getMousePos(t));
  }}, {{passive:false}});

  canvas.addEventListener('touchend', endDrag);
  img.onload = function() {{ draw(); }};
  if (img.complete) draw();
}})();
</script>
"""
    return html


def render_canvas_topo_dfov_rect(
    img_b64,
    storage_key,
    color="#00D2FF",
    titulo="Topograma",
    default_y_ini=0.25,
    default_y_fin=0.75,
    default_x=0.15,
    default_w=0.70,
    canvas_css_width=300,
    canvas_css_height=420,
    canvas_width=600,
    canvas_height=840,
):
    """Topograma con caja DFOV rectangular (no cuadrada), movible y
    redimensionable desde las 4 esquinas o los 4 bordes. Misma UX que la
    caja axial pero con ancho y alto independientes.

    default_y_ini / default_y_fin: posiciones Y (0-1) del rect inicial.
    Se toman, por ejemplo, de get_y_position_with_offset(inicio_recons) y
    get_y_position_with_offset(fin_recons). Una vez que el usuario
    interactúa, el estado queda en localStorage y los defaults se
    ignoran."""
    if not img_b64:
        return None

    # Sanear defaults
    try:
        y_ini = max(0.02, min(0.95, float(default_y_ini)))
        y_fin = max(0.05, min(0.98, float(default_y_fin)))
    except Exception:
        y_ini, y_fin = 0.25, 0.75
    if y_fin < y_ini:
        y_ini, y_fin = y_fin, y_ini
    d_y = y_ini
    d_h = max(0.05, y_fin - y_ini)
    d_x = max(0.02, min(0.9, float(default_x)))
    d_w = max(0.08, min(0.95 - d_x, float(default_w)))

    canvas_id = "canvas_" + storage_key

    html = f"""
<div style="text-align:center; margin:0;">
  <div style="display:inline-block; font-size:14px; font-weight:600; color:#ddd; margin-bottom:4px;">
    {titulo}
  </div>
  <canvas id="{canvas_id}" width="{canvas_width}" height="{canvas_height}"
    style="width:{canvas_css_width}px; height:{canvas_css_height}px; cursor:grab; border:1px solid #444; border-radius:8px; background:#000; display:block; margin:0 auto; touch-action:none;"></canvas>
</div>
<script>
(function() {{
  var imgB64 = {json.dumps(img_b64)};
  var storageKey = {json.dumps('planitc_' + storage_key)};
  var strokeColor = {json.dumps(color)};
  var canvas = document.getElementById({json.dumps(canvas_id)});
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  var img = new Image();
  img.src = 'data:image/jpeg;base64,' + imgB64;

  // Rectángulo en coordenadas normalizadas 0-1. x,y = esquina sup-izq.
  var rect = {{ x: {d_x}, y: {d_y}, w: {d_w}, h: {d_h} }};

  var dragMode = null;
  var dragOffsetX = 0, dragOffsetY = 0;
  var cornerTol = 18;
  var edgeTol = 12;
  var handleVisual = 10;
  var minDim = 0.03;
  var maxDim = 0.97;

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

  try {{
    var saved = localStorage.getItem(storageKey);
    if (saved) {{
      var parsed = JSON.parse(saved);
      if (parsed && parsed.rect) rect = parsed.rect;
    }}
  }} catch (e) {{}}

  function saveState() {{
    try {{
      localStorage.setItem(storageKey, JSON.stringify({{ rect: rect }}));
    }} catch (e) {{}}
  }}

  function clampRect() {{
    rect.w = Math.max(minDim, Math.min(maxDim, rect.w));
    rect.h = Math.max(minDim, Math.min(maxDim, rect.h));
    rect.x = Math.max(0.01, Math.min(0.99 - rect.w, rect.x));
    rect.y = Math.max(0.01, Math.min(0.99 - rect.h, rect.y));
  }}

  function getRectPx() {{
    return {{ x: rect.x * W, y: rect.y * H, w: rect.w * W, h: rect.h * H }};
  }}

  function isInsideRect(mx, my, rp) {{
    return mx >= rp.x && mx <= rp.x + rp.w && my >= rp.y && my <= rp.y + rp.h;
  }}

  function detectHandle(mx, my, rp) {{
    var left = rp.x, right = rp.x + rp.w;
    var top = rp.y, bottom = rp.y + rp.h;

    var nearLeft = Math.abs(mx - left) <= cornerTol;
    var nearRight = Math.abs(mx - right) <= cornerTol;
    var nearTop = Math.abs(my - top) <= cornerTol;
    var nearBottom = Math.abs(my - bottom) <= cornerTol;

    if (nearLeft && nearTop) return 'tl';
    if (nearRight && nearTop) return 'tr';
    if (nearLeft && nearBottom) return 'bl';
    if (nearRight && nearBottom) return 'br';

    if (Math.abs(my - top) <= edgeTol && mx >= left - edgeTol && mx <= right + edgeTol) return 't';
    if (Math.abs(my - bottom) <= edgeTol && mx >= left - edgeTol && mx <= right + edgeTol) return 'b';
    if (Math.abs(mx - left) <= edgeTol && my >= top - edgeTol && my <= bottom + edgeTol) return 'l';
    if (Math.abs(mx - right) <= edgeTol && my >= top - edgeTol && my <= bottom + edgeTol) return 'r';

    if (isInsideRect(mx, my, rp)) return 'body';
    return null;
  }}

  // Cada handle ajusta ancho/alto de forma independiente. No se fuerza
  // aspecto (a diferencia de la caja axial cuadrada). La esquina/borde
  // opuesto queda fijo.
  function resizeFromHandle(handle, pos) {{
    var left = rect.x * W;
    var top = rect.y * H;
    var wpx = rect.w * W;
    var hpx = rect.h * H;
    var right = left + wpx;
    var bottom = top + hpx;
    var minPxW = minDim * W;
    var minPxH = minDim * H;

    switch (handle) {{
      case 'br': {{
        rect.w = Math.max(minPxW, pos.x - left) / W;
        rect.h = Math.max(minPxH, pos.y - top) / H;
        break;
      }}
      case 'tl': {{
        var nx = Math.min(right - minPxW, pos.x);
        var ny = Math.min(bottom - minPxH, pos.y);
        rect.x = nx / W;
        rect.y = ny / H;
        rect.w = (right - nx) / W;
        rect.h = (bottom - ny) / H;
        break;
      }}
      case 'tr': {{
        var ny = Math.min(bottom - minPxH, pos.y);
        rect.y = ny / H;
        rect.w = Math.max(minPxW, pos.x - left) / W;
        rect.h = (bottom - ny) / H;
        break;
      }}
      case 'bl': {{
        var nx = Math.min(right - minPxW, pos.x);
        rect.x = nx / W;
        rect.w = (right - nx) / W;
        rect.h = Math.max(minPxH, pos.y - top) / H;
        break;
      }}
      case 't': {{
        var ny = Math.min(bottom - minPxH, pos.y);
        rect.y = ny / H;
        rect.h = (bottom - ny) / H;
        break;
      }}
      case 'b': {{
        rect.h = Math.max(minPxH, pos.y - top) / H;
        break;
      }}
      case 'l': {{
        var nx = Math.min(right - minPxW, pos.x);
        rect.x = nx / W;
        rect.w = (right - nx) / W;
        break;
      }}
      case 'r': {{
        rect.w = Math.max(minPxW, pos.x - left) / W;
        break;
      }}
    }}
    clampRect();
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

    var hs = handleVisual;
    var cx = rp.x + rp.w / 2;
    var cy = rp.y + rp.h / 2;
    var points = [
      [rp.x, rp.y], [rp.x + rp.w, rp.y],
      [rp.x, rp.y + rp.h], [rp.x + rp.w, rp.y + rp.h],
      [cx, rp.y], [cx, rp.y + rp.h],
      [rp.x, cy], [rp.x + rp.w, cy],
    ];
    ctx.fillStyle = strokeColor;
    ctx.strokeStyle = '#0a0a0a';
    ctx.lineWidth = 1.5;
    for (var i = 0; i < points.length; i++) {{
      ctx.fillRect(points[i][0] - hs / 2, points[i][1] - hs / 2, hs, hs);
      ctx.strokeRect(points[i][0] - hs / 2, points[i][1] - hs / 2, hs, hs);
    }}
  }}

  function draw() {{
    drawBaseImage();
    drawRect();
    saveState();
  }}

  function getMousePos(e) {{
    var r = canvas.getBoundingClientRect();
    return {{ x: (e.clientX - r.left) * (W / r.width), y: (e.clientY - r.top) * (H / r.height) }};
  }}

  function cursorForHandle(h) {{
    if (h === 'tl' || h === 'br') return 'nwse-resize';
    if (h === 'tr' || h === 'bl') return 'nesw-resize';
    if (h === 't' || h === 'b') return 'ns-resize';
    if (h === 'l' || h === 'r') return 'ew-resize';
    if (h === 'body') return 'grab';
    return 'default';
  }}

  function updateCursor(mx, my) {{
    var rp = getRectPx();
    canvas.style.cursor = cursorForHandle(detectHandle(mx, my, rp));
  }}

  function startDrag(pos) {{
    var rp = getRectPx();
    var h = detectHandle(pos.x, pos.y, rp);
    if (!h) return;
    if (h === 'body') {{
      dragMode = 'body';
      dragOffsetX = pos.x - rp.x;
      dragOffsetY = pos.y - rp.y;
      canvas.style.cursor = 'grabbing';
    }} else {{
      dragMode = h;
      canvas.style.cursor = cursorForHandle(h);
    }}
  }}

  function applyDrag(pos) {{
    if (!dragMode) return;
    if (dragMode === 'body') {{
      rect.x = (pos.x - dragOffsetX) / W;
      rect.y = (pos.y - dragOffsetY) / H;
      clampRect();
    }} else {{
      resizeFromHandle(dragMode, pos);
    }}
    draw();
  }}

  canvas.addEventListener('mousedown', function(e) {{ startDrag(getMousePos(e)); }});
  canvas.addEventListener('mousemove', function(e) {{
    var pos = getMousePos(e);
    if (!dragMode) updateCursor(pos.x, pos.y);
    else applyDrag(pos);
  }});
  function endDrag() {{ dragMode = null; saveState(); }}
  canvas.addEventListener('mouseup', endDrag);
  canvas.addEventListener('mouseleave', endDrag);
  canvas.addEventListener('touchstart', function(e) {{
    e.preventDefault();
    startDrag(getMousePos(e.touches[0]));
  }}, {{passive:false}});
  canvas.addEventListener('touchmove', function(e) {{
    e.preventDefault();
    if (dragMode) applyDrag(getMousePos(e.touches[0]));
  }}, {{passive:false}});
  canvas.addEventListener('touchend', endDrag);
  img.onload = function() {{ draw(); }};
  if (img.complete) draw();
}})();
</script>
"""
    return html


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


def _color_exploracion(exp) -> str:
    """Usa la misma paleta y el mismo orden que Adquisición."""
    exploraciones = st.session_state.get("exploraciones", [])
    try:
        idx = next(i for i, e in enumerate(exploraciones) if e.get("id") == exp.get("id"))
    except Exception:
        try:
            idx = int(exp.get("orden", 1)) - 1
        except Exception:
            idx = 0
    return EXPLORACION_COLORS[idx % len(EXPLORACION_COLORS)]


def _fase_por_nombre_exploracion(nombre: str):
    mapa = {
        "SIN CONTRASTE": "SIN CONTRASTE",
        "ARTERIAL": "ARTERIAL",
        "VENOSA": "VENOSA",
        "TARDÍA": "TARDIA",
        "ANGIOGRÁFICA": "ANGIOGRÁFICA",
        "BOLUS TEST": "ARTERIAL",
        "BOLUS TRACKING": "ARTERIAL",
    }
    return mapa.get(nombre or "", FASES_RECONS[0])


def _crear_reconstruccion_base(exp, numero, region_anat):
    exp_id = exp.get("id")
    ventana_def = list(VENTANAS.keys())[0]
    ww_def = VENTANAS[ventana_def]["ww"]
    wl_def = VENTANAS[ventana_def]["wl"]
    refs_ini_local = REFS_INICIO.get(region_anat, REFS_INICIO["CUERPO"])
    refs_fin_local = REFS_FIN.get(region_anat, REFS_FIN["CUERPO"])
    algoritmo_def = ALGORITMOS_ITERATIVOS[0]
    niveles_def = NIVEL_ITERATIVO.get(algoritmo_def, [1])

    return {
        "id": f"{exp_id}_rec_{numero}",
        "nombre": f"Reconstrucción {numero}",
        "fase_recons": _fase_por_nombre_exploracion(exp.get("nombre")),
        "tipo_recons": TIPOS_RECONS[0],
        "algoritmo_iter": algoritmo_def,
        "nivel_iter": niveles_def[0],
        "kernel_sel": KERNELS[1] if len(KERNELS) > 1 else KERNELS[0],
        "grosor_recons": GROSORES_RECONS[6] if len(GROSORES_RECONS) > 6 else GROSORES_RECONS[0],
        "incremento": INCREMENTOS_RECONS[4] if len(INCREMENTOS_RECONS) > 4 else INCREMENTOS_RECONS[0],
        "ventana_preset": ventana_def,
        "ww_val": ww_def,
        "wl_val": wl_def,
        "dfov": DFOV_OPCIONES[2] if len(DFOV_OPCIONES) > 2 else DFOV_OPCIONES[0],
        "inicio_recons": refs_ini_local[0],
        "fin_recons": refs_fin_local[0],
    }


def _get_topograma_set_for_exp(exp):
    sets = st.session_state.get("topograma_sets", [])
    idx = exp.get("topo_set_idx", 0) if isinstance(exp, dict) else 0
    if isinstance(idx, int) and 0 <= idx < len(sets):
        return sets[idx] or {}
    return st.session_state.get("topograma_store", {}) or {}


def _get_region_label_for_exp(exp) -> str:
    store = _get_topograma_set_for_exp(exp)
    return (store.get("examen") or store.get("region_anat") or store.get("region") or "").strip()


def _get_region_group_for_exp(exp) -> str:
    region = _get_region_label_for_exp(exp).upper()
    if "ANGIO" in region or region.startswith("ATC"):
        return "ANGIO"
    for key in REFS_INICIO:
        if key in region:
            return key
    return "CUERPO"


def _reconstruccion_completada(rec, exp_id) -> bool:
    img_ok = bool(st.session_state.get("imagenes_recon_por_id", {}).get(rec.get("id")))
    campos = [
        rec.get("fase_recons"),
        rec.get("tipo_recons"),
        rec.get("kernel_sel"),
        rec.get("grosor_recons"),
        rec.get("incremento"),
        rec.get("ventana_preset"),
        rec.get("dfov"),
    ]
    params_ok = all(v not in (None, "", "Seleccionar") for v in campos)
    return img_ok and params_ok


def _reindexar_reconstrucciones(exp_id):
    lista_local = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])[:6]
    st.session_state["reconstrucciones_por_exp"][exp_id] = lista_local
    for idx_local, rec_local in enumerate(lista_local, start=1):
        rec_local["id"] = f"{exp_id}_rec_{idx_local}"
        rec_local["nombre"] = f"Reconstrucción {idx_local}"


def _obtener_adquisiciones_validas():
    exploraciones = st.session_state.get("exploraciones", [])
    if not exploraciones:
        exploraciones = st.session_state.get("exploraciones_adq", [])

    adquisiciones = []
    ids_vistos = set()
    for idx, exp in enumerate(exploraciones, start=1):
        if not isinstance(exp, dict):
            continue
        tipo = exp.get("tipo") or exp.get("tipo_item") or "adquisicion"
        if tipo != "adquisicion":
            continue

        nuevo = copy.deepcopy(exp)
        exp_id = nuevo.get("id") or f"exp_{idx}"
        if exp_id in ids_vistos:
            exp_id = f"{exp_id}_{idx}"
        ids_vistos.add(exp_id)
        nuevo["id"] = exp_id
        nuevo["orden"] = nuevo.get("orden") or nuevo.get("order") or idx
        nuevo["tipo_exploracion"] = nuevo.get("tipo_exploracion") or nuevo.get("tipo_exp") or "HELICOIDAL"
        adquisiciones.append(nuevo)

    return adquisiciones


def _eliminar_reconstruccion(exp_id, rec_id):
    """Elimina una reconstrucción específica de su exploración y limpia
    la imagen asociada si existe."""
    lista = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
    st.session_state["reconstrucciones_por_exp"][exp_id] = [
        r for r in lista if r.get("id") != rec_id
    ]
    # Limpiar imagen asociada
    st.session_state.get("imagenes_recon_por_id", {}).pop(rec_id, None)
    # Si era la reconstrucción activa, limpiar la referencia
    if st.session_state["recon_activa_por_exp"].get(exp_id) == rec_id:
        recs_restantes = st.session_state["reconstrucciones_por_exp"][exp_id]
        st.session_state["recon_activa_por_exp"][exp_id] = (
            recs_restantes[0]["id"] if recs_restantes else None
        )


def _siguiente_numero_recon(exp_id):
    """Devuelve el número más alto + 1 entre las reconstrucciones existentes
    de una exploración, para usarlo en la nueva."""
    lista = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
    if not lista:
        return 1
    nums = []
    for r in lista:
        # El id tiene formato "{exp_id}_rec_{n}". Tomamos el n.
        rid = r.get("id", "")
        try:
            nums.append(int(rid.rsplit("_", 1)[-1]))
        except (ValueError, IndexError):
            pass
    return (max(nums) + 1) if nums else (len(lista) + 1)


def render_reconstruccion():
    _inject_recon_css()
    adquisiciones_validas = _obtener_adquisiciones_validas()

    st.session_state.setdefault("reconstrucciones_por_exp", {})
    st.session_state.setdefault("recon_activa_por_exp", {})
    st.session_state.setdefault("exploracion_rec_activa", None)
    st.session_state.setdefault("imagenes_recon_por_id", {})

    ids_adq_validos = [e.get("id") for e in adquisiciones_validas]

    # Limpiar reconstrucciones de adquisiciones que ya no existen
    for exp_id_existente in list(st.session_state["reconstrucciones_por_exp"].keys()):
        if exp_id_existente not in ids_adq_validos:
            # También limpiar imágenes asociadas
            recs_a_borrar = st.session_state["reconstrucciones_por_exp"].get(exp_id_existente, [])
            for r in recs_a_borrar:
                st.session_state["imagenes_recon_por_id"].pop(r.get("id"), None)
            st.session_state["reconstrucciones_por_exp"].pop(exp_id_existente, None)
            st.session_state["recon_activa_por_exp"].pop(exp_id_existente, None)

    # Inicializar contenedores para adquisiciones nuevas (sin crear recons automáticas)
    for exp in adquisiciones_validas:
        exp_id = exp.get("id")
        st.session_state["reconstrucciones_por_exp"].setdefault(exp_id, [])

    # Auto-seleccionar la primera adquisición si no hay ninguna activa
    if st.session_state["exploracion_rec_activa"] not in ids_adq_validos:
        st.session_state["exploracion_rec_activa"] = ids_adq_validos[0] if ids_adq_validos else None

    # ── Layout: Sidebar (col_nav) + Panel central (col_det) ──
    col_nav, col_det = st.columns([0.8, 2.7], gap="large")

    with col_nav:
        _render_sidebar_reconstruccion(adquisiciones_validas)

    with col_det:
        _render_panel_central(adquisiciones_validas)

    return st.session_state.get("reconstrucciones_por_exp", {})


def _render_sidebar_reconstruccion(adquisiciones_validas):
    """Sidebar con lista de adquisiciones + sus reconstrucciones colapsables.
    Solo se expande la adquisición "activa" (la que el usuario está viendo o
    la que contiene la reconstrucción abierta)."""
    _panel_header("🧩", "Reconstrucciones")

    if not adquisiciones_validas:
        st.info("Primero agrega al menos una adquisición en la pestaña **Adquisición**.")
        return

    recons_map = st.session_state["reconstrucciones_por_exp"]
    exp_activa_id = st.session_state["exploracion_rec_activa"]
    recon_activa_ids = st.session_state["recon_activa_por_exp"]

    # Determinar qué adquisición está expandida:
    #   - Siempre la que está marcada como "exploracion_rec_activa"
    #     (que se actualiza tanto al clickear una adquisición como una rec)
    exp_expandida_id = exp_activa_id

    for i, exp in enumerate(adquisiciones_validas):
        exp_id = exp.get("id")
        recs_exp = recons_map.get(exp_id, [])
        n_recs = len(recs_exp)
        n_completas = sum(1 for r in recs_exp if _reconstruccion_completada(r, exp_id))
        esta_expandida = (exp_id == exp_expandida_id)

        color = _color_exploracion(exp)
        nombre_base = (
            exp.get("nombre")
            if exp.get("nombre") and exp.get("nombre") != "Seleccionar"
            else f"EXPLORACIÓN {exp.get('orden', i + 1)}"
        )
        region = _get_region_label_for_exp(exp)
        nombre_visible = f"{region} · {nombre_base}".strip(" ·")

        # Chip de color (igual al original)
        _mini_chip(color, nombre_visible, "")

        # Contador si está colapsada
        contador = ""
        if not esta_expandida and n_recs > 0:
            contador = f"  ({n_completas}/{n_recs})"

        # Botón principal de la adquisición
        es_activa_la_adq = (
            esta_expandida
            and recon_activa_ids.get(exp_id) is None
        )
        if st.button(
            f"⚡ {nombre_visible}{contador}",
            key=f"btn_rec_sel_{exp_id}",
            use_container_width=True,
            type="primary" if es_activa_la_adq else "secondary",
        ):
            st.session_state["exploracion_rec_activa"] = exp_id
            # Al seleccionar una adquisición, deseleccionar su reconstrucción
            # activa para que el panel central muestre el resumen de la adq.
            st.session_state["recon_activa_por_exp"][exp_id] = None
            st.rerun()

        # Reconstrucciones: solo visibles si la adquisición está expandida
        if esta_expandida and recs_exp:
            for rec in recs_exp:
                rec_id = rec.get("id")
                rec_activa = (recon_activa_ids.get(exp_id) == rec_id)
                completa = _reconstruccion_completada(rec, exp_id)

                # Icono de estado: 🟢 completa, ⚪ en edición
                icono = "🟢" if completa else "⚪"

                c_main, c_del = st.columns([6, 1], gap="small", vertical_alignment="center")
                with c_main:
                    if st.button(
                        f"{icono} {rec.get('nombre', 'Reconstrucción')}",
                        key=f"btn_rec_item_{rec_id}",
                        use_container_width=True,
                        type="primary" if rec_activa else "secondary",
                    ):
                        st.session_state["exploracion_rec_activa"] = exp_id
                        st.session_state["recon_activa_por_exp"][exp_id] = rec_id
                        st.rerun()
                with c_del:
                    if st.button(
                        "✕",
                        key=f"btn_rec_del_{rec_id}",
                        type="tertiary",
                        use_container_width=True,
                        help=f"Eliminar {rec.get('nombre', 'Reconstrucción')}",
                    ):
                        _eliminar_reconstruccion(exp_id, rec_id)
                        st.rerun()

        # Espacio vertical entre adquisiciones
        st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)

    # ── Botón "+ Reconstrucción" ──
    # Se agrega a la adquisición activa. Si no hay, no se puede agregar.
    st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)

    if st.button(
        "+ Reconstrucción",
        key="rec_btn_add_recon",
        type="secondary",
        use_container_width=True,
    ):
        if exp_activa_id is None:
            st.warning("Selecciona una adquisición primero.")
        else:
            exp_activa = next(
                (e for e in adquisiciones_validas if e.get("id") == exp_activa_id),
                None,
            )
            if exp_activa is not None:
                region_anat = _get_region_group_for_exp(exp_activa)
                nuevo_num = _siguiente_numero_recon(exp_activa_id)
                nueva = _crear_reconstruccion_base(exp_activa, nuevo_num, region_anat)
                st.session_state["reconstrucciones_por_exp"][exp_activa_id].append(nueva)
                # Dejar la nueva como activa
                st.session_state["recon_activa_por_exp"][exp_activa_id] = nueva["id"]
                st.rerun()


def _get_topogramas_de_adquisicion(exp, rec_actual):
    """Devuelve los topogramas de la adquisición listos para renderizar.

    Cada elemento incluye imagen, título, caption y la clave de storage
    para que luego puedan mostrarse en columnas una al lado de la otra.
    """
    tstore = _get_topograma_set_for_exp(exp)
    hay_topo1 = bool(tstore.get("topograma_iniciado", False))
    hay_topo2 = bool(
        tstore.get("aplica_topo2") and tstore.get("topograma2_iniciado", False)
    )

    if not hay_topo1 and not hay_topo2:
        return [], None

    try:
        from ui.topograma import obtener_imagen_topograma_adquirido
    except Exception as e:
        return [], f"No se pudo cargar el módulo de topograma: {e}"

    try:
        from ui.adquisicion import get_y_position_with_offset
        y_ini_default = get_y_position_with_offset(rec_actual.get("inicio_recons"), 0)
        y_fin_default = get_y_position_with_offset(rec_actual.get("fin_recons"), 0)
    except Exception:
        y_ini_default, y_fin_default = 0.25, 0.75

    def _caption_topo(tubo, largo, etiqueta):
        tubo_txt = tubo or "—"
        largo_txt = f"{largo} mm" if largo not in (None, "", "Seleccionar") else "— mm"
        return f"{etiqueta} · Tubo: {tubo_txt} · {largo_txt} · 100 kV · 40 mA"

    topogramas = []

    if hay_topo1:
        img1, err1 = obtener_imagen_topograma_adquirido(
            tstore.get("examen") or st.session_state.get("examen", ""),
            tstore.get("posicion") or "",
            tstore.get("entrada") or "",
            tstore.get("t1pt") or "",
        )
        if img1 is not None:
            topogramas.append({
                "img": img1,
                "storage_suffix": "topo1",
                "titulo": "Topograma 1",
                "caption": _caption_topo(tstore.get("t1pt"), tstore.get("t1l"), "Topo 1"),
                "default_y_ini": y_ini_default,
                "default_y_fin": y_fin_default,
            })
        elif err1:
            topogramas.append({"error": f"Topograma 1: {err1}"})

    if hay_topo2:
        img2, err2 = obtener_imagen_topograma_adquirido(
            tstore.get("t2_examen") or tstore.get("examen") or st.session_state.get("examen", ""),
            tstore.get("t2_posicion_paciente") or tstore.get("t2_posicion") or "",
            tstore.get("t2_entrada_paciente") or tstore.get("t2_entrada") or "",
            tstore.get("t2_posicion_tubo") or tstore.get("t2pt") or "",
        )
        if img2 is not None:
            topogramas.append({
                "img": img2,
                "storage_suffix": "topo2",
                "titulo": "Topograma 2",
                "caption": _caption_topo(tstore.get("t2pt"), tstore.get("t2l"), "Topo 2"),
                "default_y_ini": y_ini_default,
                "default_y_fin": y_fin_default,
            })
        elif err2:
            topogramas.append({"error": f"Topograma 2: {err2}"})

    return topogramas, None



def _render_topograma_en_columna(exp, rec_actual, topo_data):
    """Renderiza un topograma individual dentro de una columna."""
    if topo_data.get("error"):
        st.warning(topo_data["error"])
        return

    img_pil = topo_data.get("img")
    if img_pil is None:
        return

    color_rec = _color_exploracion(exp)

    img_b64 = _pil_to_b64_jpeg(img_pil, max_width=800)
    if not img_b64:
        st.image(img_pil, width=300)
        return

    html_topo = render_canvas_topo_dfov_rect(
        img_b64=img_b64,
        storage_key=f"recon_topo_rect_{rec_actual['id']}_{topo_data['storage_suffix']}",
        color=color_rec,
        titulo="Ajuste el DFOV",
        default_y_ini=topo_data.get("default_y_ini", 0.25),
        default_y_fin=topo_data.get("default_y_fin", 0.75),
        canvas_css_width=260,
        canvas_css_height=360,
        canvas_width=560,
        canvas_height=780,
    )
    if html_topo:
        components.html(html_topo, height=410, scrolling=False)
    else:
        st.image(img_pil, width=260)


def _render_panel_central(adquisiciones_validas):
    """Panel central: si hay reconstrucción seleccionada muestra sus parámetros;
    si no, muestra un resumen de la adquisición activa."""
    if not adquisiciones_validas or st.session_state.get("exploracion_rec_activa") is None:
        st.warning("No hay adquisiciones disponibles para reconstruir.")
        return

    exp_id = st.session_state["exploracion_rec_activa"]
    exp_activa = next((e for e in adquisiciones_validas if e.get("id") == exp_id), None)

    if exp_activa is None:
        st.warning("No se pudo cargar la adquisición seleccionada.")
        return

    recs_exp = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
    rec_activa_id = st.session_state["recon_activa_por_exp"].get(exp_id)
    rec_actual = None
    if rec_activa_id:
        rec_actual = next((r for r in recs_exp if r.get("id") == rec_activa_id), None)

    # Nombre legible de la adquisición
    nombre_base_exp = (
        exp_activa.get("nombre")
        if exp_activa.get("nombre") and exp_activa.get("nombre") != "Seleccionar"
        else f"EXPLORACIÓN {exp_activa.get('orden', 1)}"
    )
    region_exp = _get_region_label_for_exp(exp_activa)
    nombre_exp = f"{nombre_base_exp} · {region_exp}".strip(" ·").upper()

    # ── CASO A: no hay reconstrucción seleccionada → resumen de la adquisición ──
    if rec_actual is None:
        _panel_header("⚡", f"Adquisición: {nombre_exp}")
        st.caption(
            "Usa el botón **+ Reconstrucción** de la barra lateral para crear "
            "una nueva reconstrucción para esta adquisición."
        )
        st.markdown("---")

        if not recs_exp:
            st.info(
                f"Esta adquisición aún no tiene reconstrucciones. "
                f"Agrega la primera con **+ Reconstrucción**."
            )
        else:
            st.markdown(f"**Reconstrucciones creadas ({len(recs_exp)}):**")
            completas = sum(1 for r in recs_exp if _reconstruccion_completada(r, exp_id))
            st.markdown(f"🟢 Completadas: **{completas}** · ⚪ En edición: **{len(recs_exp) - completas}**")
            st.caption("Haz click en una reconstrucción de la barra lateral para editarla.")
        return

    # ── CASO B: hay reconstrucción seleccionada → parámetros editables ──
    region_anat = _get_region_group_for_exp(exp_activa)
    _panel_header("🔄", f"{rec_actual.get('nombre', 'Reconstrucción')} · {nombre_exp}")

    topogramas_data, topo_error = _get_topogramas_de_adquisicion(exp_activa, rec_actual)

    if topo_error:
        st.warning(topo_error)

    n_topos_visibles = len([t for t in topogramas_data if not t.get("error")])
    if n_topos_visibles >= 2:
        fila_cols = st.columns([1.2, 1, 1], gap="medium")
    elif n_topos_visibles == 1:
        fila_cols = st.columns([1.3, 1], gap="medium")
    else:
        fila_cols = st.columns([1], gap="medium")

    # Primer bloque: subir imagen y mostrar imagen de reconstrucción
    with fila_cols[0]:
        img_guardada = st.session_state["imagenes_recon_por_id"].get(rec_actual["id"])

        if img_guardada is None:
            imagen_recon = st.file_uploader(
                "Subir imagen de reconstrucción",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"img_recon_upload_{rec_actual['id']}",
            )
            if imagen_recon is not None:
                st.session_state["imagenes_recon_por_id"][rec_actual["id"]] = {
                    "name": imagen_recon.name,
                    "bytes": imagen_recon.getvalue(),
                }
                st.rerun()

        img_guardada = st.session_state["imagenes_recon_por_id"].get(rec_actual["id"])
        if img_guardada is not None:
            if st.button("🗑️ Borrar imagen", key=f"btn_borrar_img_recon_{rec_actual['id']}", use_container_width=True):
                st.session_state["imagenes_recon_por_id"].pop(rec_actual["id"], None)
                st.session_state.pop(f"img_recon_upload_{rec_actual['id']}", None)
                st.rerun()

            try:
                img_recon_pil = Image.open(io.BytesIO(img_guardada["bytes"]))
                img_b64 = _pil_to_b64_jpeg(img_recon_pil, max_width=900)
                color_rec = _color_exploracion(exp_activa)
                html_canvas = render_canvas_recon_cuadrado(
                    img_b64=img_b64,
                    storage_key=f"recon_square_{rec_actual['id']}",
                    color=color_rec,
                    titulo="Ajuste el Dfov",
                    canvas_css_width=360,
                    canvas_css_height=360,
                    canvas_width=760,
                    canvas_height=760,
                )
                if html_canvas:
                    components.html(html_canvas, height=430, scrolling=False)
                else:
                    st.image(img_guardada["bytes"], caption="Imagen cargada", width=360)
            except Exception as e:
                st.error(f"No se pudo cargar el cuadrado interactivo: {e}")
                st.image(img_guardada["bytes"], caption="Imagen cargada", width=360)

    # Topogramas a la derecha, uno al lado del otro si existen
    next_col_idx = 1
    for topo_data in topogramas_data:
        if next_col_idx >= len(fila_cols):
            break
        with fila_cols[next_col_idx]:
            _render_topograma_en_columna(exp_activa, rec_actual, topo_data)
        next_col_idx += 1

    if not topogramas_data:
        st.info(
            "Esta adquisición no tiene topograma iniciado. "
            "Inícialo en la pestaña **Topograma** para verlo aquí."
        )

    # Parámetros debajo de toda la fila de imágenes
    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    _panel_header("🔧", "Parámetros de Reconstrucción")

    col_pr1, col_pr2, col_pr3 = st.columns([1, 1, 1], gap="small")

    with col_pr1:
        rec_actual["fase_recons"] = selectbox_con_placeholder(
            "Fase a reconstruir",
            FASES_RECONS,
            key=f"fase_recons_{rec_actual['id']}_pr1",
            value=rec_actual.get("fase_recons"),
        )
        rec_actual["kernel_sel"] = selectbox_con_placeholder(
            "Algoritmo (Kernel)",
            KERNELS,
            key=f"kernel_sel_{rec_actual['id']}_pr1",
            value=rec_actual.get("kernel_sel"),
        )

    with col_pr2:
        rec_actual["tipo_recons"] = selectbox_con_placeholder(
            "Tipo de reconstrucción",
            TIPOS_RECONS,
            key=f"tipo_recons_{rec_actual['id']}_pr2",
            value=rec_actual.get("tipo_recons"),
        )
        rec_actual["grosor_recons"] = selectbox_con_placeholder(
            "Grosor reconstrucción",
            GROSORES_RECONS,
            key=f"grosor_recons_{rec_actual['id']}_pr2",
            value=rec_actual.get("grosor_recons"),
        )

    with col_pr3:
        if rec_actual["tipo_recons"] == "RECONS. ITERATIVA":
            rec_actual["algoritmo_iter"] = selectbox_con_placeholder(
                "Algoritmo iterativo",
                ALGORITMOS_ITERATIVOS,
                key=f"alg_iter_{rec_actual['id']}_pr3",
                value=rec_actual.get("algoritmo_iter"),
            )
            niveles_disp = NIVEL_ITERATIVO.get(rec_actual["algoritmo_iter"], [1])
            rec_actual["nivel_iter"] = selectbox_con_placeholder(
                "Nivel / Porcentaje / Modo",
                niveles_disp,
                key=f"nivel_iter_{rec_actual['id']}_pr3",
                value=rec_actual.get("nivel_iter"),
            )
        else:
            rec_actual["algoritmo_iter"] = "—"
            rec_actual["nivel_iter"] = "—"
            st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)
            st.caption("Algoritmo iterativo no aplica")
            st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)

        rec_actual["incremento"] = selectbox_con_placeholder(
            "Incremento",
            INCREMENTOS_RECONS,
            key=f"incremento_{rec_actual['id']}_pr3",
            value=rec_actual.get("incremento"),
        )

    _panel_header("🪟", "Ventana de Visualización")
    ventanas_disp = list(VENTANAS.keys())

    if rec_actual.get("ventana_preset") in VENTANAS:
        ww_default = VENTANAS[rec_actual["ventana_preset"]]["ww"]
        wl_default = VENTANAS[rec_actual["ventana_preset"]]["wl"]
    else:
        ww_default = 400
        wl_default = 40

    col_v1, col_v2, col_v3 = st.columns([1, 1, 1], gap="small")
    with col_v1:
        rec_actual["ventana_preset"] = selectbox_con_placeholder(
            "Preset de ventana",
            ventanas_disp,
            key=f"preset_ventana_{rec_actual['id']}_vv1",
            value=rec_actual.get("ventana_preset"),
        )

    with col_v2:
        rec_actual["ww_val"] = st.number_input(
            "WW",
            min_value=1,
            max_value=5000,
            value=int(rec_actual.get("ww_val", ww_default)),
            step=1,
            key=f"ww_{rec_actual['id']}_vv2",
        )

    with col_v3:
        rec_actual["wl_val"] = st.number_input(
            "WL",
            min_value=-1500,
            max_value=3000,
            value=int(rec_actual.get("wl_val", wl_default)),
            step=1,
            key=f"wl_{rec_actual['id']}_vv3",
        )
        rec_actual["dfov"] = selectbox_con_placeholder(
            "DFOV",
            DFOV_OPCIONES,
            key=f"dfov_{rec_actual['id']}_vv3",
            value=rec_actual.get("dfov"),
        )

    _panel_header("📍", "Rango de Reconstrucción")
    refs_ini_r = REFS_INICIO.get(region_anat, REFS_INICIO["CUERPO"])
    refs_fin_r = REFS_FIN.get(region_anat, REFS_FIN["CUERPO"])

    col_ini, col_fin = st.columns([1, 1], gap="small")
    with col_ini:
        rec_actual["inicio_recons"] = selectbox_con_placeholder("Inicio reconstrucción", refs_ini_r, key=f"ini_rec_{rec_actual['id']}", value=rec_actual.get("inicio_recons"))
    with col_fin:
        rec_actual["fin_recons"] = selectbox_con_placeholder("Fin reconstrucción", refs_fin_r, key=f"fin_rec_{rec_actual['id']}", value=rec_actual.get("fin_recons"))

    st.markdown("---")
    _panel_header("📝", "Resumen de reconstrucción activa")
    st.markdown(
        f"""
        **Adquisición:** {nombre_exp}  
        **Nombre:** {rec_actual.get('nombre', '—')}  
        **Fase:** {rec_actual.get('fase_recons', '—')}  
        **Tipo:** {rec_actual.get('tipo_recons', '—')}  
        **Algoritmo iterativo:** {rec_actual.get('algoritmo_iter', '—')}  
        **Nivel:** {rec_actual.get('nivel_iter', '—')}  
        **Kernel:** {rec_actual.get('kernel_sel', '—')}  
        **Grosor:** {rec_actual.get('grosor_recons', '—')}  
        **Incremento:** {rec_actual.get('incremento', '—')}  
        **Ventana:** {rec_actual.get('ventana_preset', '—')}  
        **WW / WL:** {rec_actual.get('ww_val', '—')} / {rec_actual.get('wl_val', '—')}  
        **DFOV:** {rec_actual.get('dfov', '—')}  
        **Inicio:** {rec_actual.get('inicio_recons', '—')}  
        **Fin:** {rec_actual.get('fin_recons', '—')}
        """
    )
