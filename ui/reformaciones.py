import uuid
import io
import json
import base64

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

TIPOS_REFORMACION = ["MPR", "MIP", "MinIP", "VR"]
SUBTIPOS = {
    "MPR": None,
    "MIP": ["Grueso", "Fino"],
    "MinIP": None,
    "VR": None,
}
PARAMS_POR_TIPO = {
    ("MPR", None): ["plano", "grosor", "distancia"],
    ("MIP", "Grueso"): ["n_vistas", "angulo"],
    ("MIP", "Fino"): ["plano", "grosor", "distancia"],
    ("MinIP", None): ["grosor", "distancia"],
    ("VR", None): ["n_vistas", "angulo"],
}
PARAMS_OPCIONES = {
    "plano": ["AXIAL", "CORONAL", "SAGITAL", "CURVO"],
    "grosor": ["1 mm", "2 mm", "3 mm", "4 mm", "5 mm", "7 mm", "10 mm"],
    "distancia": ["0,5 mm", "1 mm", "2 mm", "3 mm", "5 mm"],
    "n_vistas": [6, 8, 10, 12, 15, 18, 24, 30, 36, 60, 72],
    "angulo": ["5°", "10°", "12°", "15°", "20°", "30°", "45°", "60°"],
}
PARAMS_LABELS = {
    "plano": "Plano",
    "grosor": "Grosor",
    "distancia": "Distancia entre imágenes",
    "n_vistas": "N° de vistas",
    "angulo": "Ángulo entre vistas",
}

EXPLORACION_COLORS = [
    "#00D2FF", "#FFB000", "#7CFF6B", "#FF5CA8",
    "#A78BFA", "#FF7A59", "#5EEAD4", "#FACC15",
]
RECON_COLOR_DEFAULT = "#FFFFFF"


def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    opciones = ["Seleccionar"] + [str(o) for o in options]
    val_str = str(value) if value is not None else None
    idx = opciones.index(val_str) if val_str in opciones else 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    if val == "Seleccionar":
        return None
    for o in options:
        if str(o) == val:
            return o
    return val


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


def _inject_sidebar_css():
    st.markdown(
        """
        <style>
        section[data-testid="stVerticalBlock"] h3:first-of-type {
            font-size: 1.15rem !important;
            margin-bottom: 0.6rem !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.2 !important;
        }
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
        div[data-testid="stButton"] > button[kind="secondary"],
        div[data-testid="stButton"] > button[kind="primary"] {
            min-height: 2.4rem !important;
            padding-top: 0.45rem !important;
            padding-bottom: 0.45rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
            font-size: 0.85rem !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            text-align: center !important;
        }
        .st-key-ref_btn_add_ref button[kind="secondary"],
        div.stApp .st-key-ref_btn_add_ref button[kind="secondary"] {
            background-color: #6b6f7a !important;
            border: 1px solid #80848f !important;
            color: #ffffff !important;
            min-height: 2.75rem !important;
            height: 2.75rem !important;
            font-size: 0.9rem !important;
            padding: 0 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _pil_to_b64_jpeg(img, max_width=1200):
    if img is None:
        return None
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


def _new_id() -> str:
    return f"ref_{uuid.uuid4().hex[:8]}"


def _next_order() -> int:
    st.session_state["_ref_next_order"] = int(st.session_state.get("_ref_next_order", 0)) + 1
    return st.session_state["_ref_next_order"]


def _init_state():
    st.session_state.setdefault("reformaciones_por_rec", {})
    st.session_state.setdefault("_ref_rec_order", {})
    st.session_state.setdefault("ref_activa", None)
    st.session_state.setdefault("imagenes_ref_por_id", {})


def _crear_reformacion_base(rec_id: str) -> dict:
    return {
        "id": _new_id(),
        "rec_id": rec_id,
        "order": _next_order(),
        "tipo": None,
        "subtipo": None,
        "plano": None,
        "grosor": None,
        "distancia": None,
        "n_vistas": None,
        "angulo": None,
    }


def _reconstruccion_completada(rec) -> bool:
    img_ok = bool(st.session_state.get("imagenes_recon_por_id", {}).get(rec.get("id")))
    campos = [
        rec.get("fase_recons"), rec.get("tipo_recons"), rec.get("kernel_sel"),
        rec.get("grosor_recons"), rec.get("incremento"), rec.get("ventana_preset"), rec.get("dfov"),
    ]
    params_ok = all(v not in (None, "", "Seleccionar") for v in campos)
    return img_ok and params_ok


def _obtener_reconstrucciones_planas():
    recons_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    exploraciones = st.session_state.get("exploraciones", []) or []
    nombre_por_exp_id = {}
    for idx, exp in enumerate(exploraciones, start=1):
        if not isinstance(exp, dict):
            continue
        eid = exp.get("id") or f"exp_{idx}"
        nombre_por_exp_id[eid] = exp.get("nombre") or f"Exploración {idx}"

    resultado = []
    for exp_id, lista_recons in recons_map.items():
        if not isinstance(lista_recons, list):
            continue
        for rec in lista_recons:
            if not isinstance(rec, dict):
                continue
            rid = rec.get("id")
            if not rid or not _reconstruccion_completada(rec):
                continue
            resultado.append({
                "id": rid,
                "nombre": rec.get("nombre") or "Reconstrucción",
                "exp_id": exp_id,
                "exp_nombre": nombre_por_exp_id.get(exp_id, exp_id),
                "rec": rec,
            })
            if rid not in st.session_state["_ref_rec_order"]:
                st.session_state["_ref_rec_order"][rid] = _next_order()
    return resultado


def _contar_reconstrucciones_totales() -> int:
    recons_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    total = 0
    for lista_recons in recons_map.values():
        if isinstance(lista_recons, list):
            total += sum(1 for r in lista_recons if isinstance(r, dict))
    return total


def _rec_target_id(recons_planas):
    activa = st.session_state["ref_activa"]
    if isinstance(activa, str):
        for lista in st.session_state["reformaciones_por_rec"].values():
            for ref in lista:
                if ref["id"] == activa:
                    return ref.get("rec_id")
    if isinstance(activa, dict) and activa.get("kind") == "rec":
        return activa.get("rec_id")
    if recons_planas:
        return recons_planas[0]["id"]
    return None


def _nombre_reformacion(ref: dict) -> str:
    tipo = ref.get("tipo")
    subt = ref.get("subtipo")
    if tipo and subt:
        return f"{tipo} {subt}"
    if tipo:
        return tipo
    return "Reformación"


def _eliminar_reformacion(ref_id: str, rec_id):
    mapa = st.session_state["reformaciones_por_rec"]
    if rec_id and rec_id in mapa:
        mapa[rec_id] = [r for r in mapa[rec_id] if r.get("id") != ref_id]
    else:
        for rid, lista in mapa.items():
            mapa[rid] = [r for r in lista if r.get("id") != ref_id]
    st.session_state.get("imagenes_ref_por_id", {}).pop(ref_id, None)
    if st.session_state.get("ref_activa") == ref_id:
        st.session_state["ref_activa"] = None


def _render_sidebar(recons_planas):
    _inject_sidebar_css()
    st.markdown("### 📐 Reformaciones")

    if not recons_planas:
        total_existentes = _contar_reconstrucciones_totales()
        if total_existentes == 0:
            st.info("No hay reconstrucciones aún. Ve a la pestaña **Reconstrucción** para crear al menos una.")
        else:
            st.info(f"{total_existentes} reconstrucción(es) en edición. Cárgales imagen y completa sus parámetros para poder reformarlas aquí.")
        return

    reformaciones_map = st.session_state["reformaciones_por_rec"]
    for r in recons_planas:
        reformaciones_map.setdefault(r["id"], [])

    rec_order = st.session_state["_ref_rec_order"]
    activa = st.session_state["ref_activa"]

    rec_id_expandida = None
    if isinstance(activa, dict) and activa.get("kind") == "rec":
        rec_id_expandida = activa.get("rec_id")
    elif isinstance(activa, str):
        for rid, lista in reformaciones_map.items():
            for ref in lista:
                if ref.get("id") == activa:
                    rec_id_expandida = rid
                    break
            if rec_id_expandida:
                break

    recons_ordenadas = sorted(recons_planas, key=lambda r: rec_order.get(r["id"], 0))

    for r in recons_ordenadas:
        rec_id = r["id"]
        refs_de_esta_rec = sorted(reformaciones_map.get(rec_id, []), key=lambda x: x.get("order", 0))
        n_refs = len(refs_de_esta_rec)
        esta_expandida = (rec_id == rec_id_expandida)
        es_activo_rec = isinstance(activa, dict) and activa.get("kind") == "rec" and activa.get("rec_id") == rec_id
        contador = f"  ({n_refs})" if (n_refs > 0 and not esta_expandida) else ""

        if st.button(f"🧩 {r['nombre']} · {r['exp_nombre']}{contador}", key=f"ref_btn_rec_{rec_id}", type="primary" if es_activo_rec else "secondary", use_container_width=True):
            st.session_state["ref_activa"] = {"kind": "rec", "rec_id": rec_id}
            st.rerun()

        if esta_expandida:
            for ref in refs_de_esta_rec:
                es_activo_ref = isinstance(activa, str) and activa == ref["id"]
                c_main, c_del = st.columns([6, 1], gap="small", vertical_alignment="center")
                with c_main:
                    if st.button(f"📐 {_nombre_reformacion(ref)}", key=f"ref_btn_ref_{ref['id']}", type="primary" if es_activo_ref else "secondary", use_container_width=True):
                        st.session_state["ref_activa"] = ref["id"]
                        st.rerun()
                with c_del:
                    if st.button("✕", key=f"ref_btn_del_{ref['id']}", type="tertiary", use_container_width=True):
                        _eliminar_reformacion(ref["id"], ref.get("rec_id"))
                        st.rerun()
        st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)

    target_rec_id = _rec_target_id(recons_planas)
    st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)
    if st.button("+ Reformación", key="ref_btn_add_ref", type="secondary", use_container_width=True):
        if target_rec_id is None:
            st.warning("Selecciona una reconstrucción primero.")
        else:
            nueva = _crear_reformacion_base(target_rec_id)
            st.session_state["reformaciones_por_rec"].setdefault(target_rec_id, []).append(nueva)
            st.session_state["ref_activa"] = nueva["id"]
            st.rerun()


def _color_exploracion_por_exp_id(exp_id: str) -> str:
    exploraciones = st.session_state.get("exploraciones", [])
    try:
        idx = next(i for i, e in enumerate(exploraciones) if isinstance(e, dict) and e.get("id") == exp_id)
    except Exception:
        idx = 0
    return EXPLORACION_COLORS[idx % len(EXPLORACION_COLORS)]


def _color_reconstruccion(rec: dict) -> str:
    return _color_exploracion_por_exp_id(rec.get("exp_id")) if rec else RECON_COLOR_DEFAULT


def _default_overlay_settings(ref_id: str, img_idx: int):
    return {
        "show_ranges": True,
        "range_count": 3,
        "angle_deg": 0,
        "refs": [
            {"enabled": False, "text": ""},
            {"enabled": False, "text": ""},
            {"enabled": False, "text": ""},
        ],
    }


def _ensure_image_state(ref_id: str):
    store = st.session_state.setdefault("imagenes_ref_por_id", {})
    if ref_id not in store:
        store[ref_id] = {}
    for idx in (1, 2, 3):
        store[ref_id].setdefault(f"img{idx}", None)
        store[ref_id].setdefault(f"overlay{idx}", _default_overlay_settings(ref_id, idx))
    return store[ref_id]


def _render_image_uploader(ref_id: str, img_idx: int, titulo: str):
    img_state = _ensure_image_state(ref_id)
    key_img = f"img{img_idx}"
    current = img_state.get(key_img)

    # Solo mostrar el uploader mientras no exista imagen cargada.
    if current is None:
        file_obj = st.file_uploader(
            "",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_{ref_id}_{img_idx}",
            label_visibility="collapsed",
        )
        if file_obj is not None:
            current = {"name": file_obj.name, "bytes": file_obj.getvalue()}
            img_state[key_img] = current
            st.rerun()

    return img_state.get(key_img)


def _overlay_canvas_html(img_b64, storage_key, acq_color, rec_color, settings, title="Imagen", css_width=320, css_height=260, internal_w=900, internal_h=700):
    refs_cfg = settings.get("refs", [])
    html = f"""
<div style="text-align:center; margin:0;">
  <div id="wrap_{storage_key}" style="position:relative; width:{css_width}px; height:{css_height}px; margin:0 auto;">
    <canvas id="canvas_{storage_key}" width="{internal_w}" height="{internal_h}" style="position:absolute; inset:0; width:{css_width}px;height:{css_height}px;cursor:crosshair;border:1px solid #444;border-radius:8px;background:#000;display:block;touch-action:none;"></canvas>
    <div id="labels_{storage_key}" style="position:absolute; inset:0; pointer-events:none;"></div>
  </div>
</div>
<script>
(function() {{
  var wrap = document.getElementById({json.dumps('wrap_' + storage_key)});
  var labelsLayer = document.getElementById({json.dumps('labels_' + storage_key)});
  var canvas = document.getElementById({json.dumps('canvas_' + storage_key)});
  if (!canvas || !wrap || !labelsLayer) return;
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  var img = new Image();
  img.src = 'data:image/jpeg;base64,' + {json.dumps(img_b64)};
  var storageKey = {json.dumps('planitc_ref_' + storage_key)};
  var acqColor = {json.dumps(acq_color)};
  var recColor = {json.dumps(rec_color)};
  var showRanges = {json.dumps(bool(settings.get('show_ranges', True)))};
  var defaultRangeCount = {json.dumps(int(settings.get('range_count', 3)))};
  var defaultAngleDeg = {json.dumps(float(settings.get('angle_deg', 0)))};

  var SPACING = 38;
  var LINE_LEN = Math.max(W, H) * 0.42;
  var MIN_RANGES = 1;
  var MAX_RANGES = 50;
  var ROT_HIT = 22;
  var EXT_HIT = 18;
  var LEN_HIT = 18;
  var HANDLE_OFFSET = 26;
  var MIN_LINE_LEN = Math.max(W, H) * 0.08;
  var MAX_LINE_LEN = Math.max(W, H) * 0.62;
  var minDim = Math.min(W, H);
  var imgRect = {{x:0,y:0,w:W,h:H,x1:W,y1:H,cx:W/2,cy:H/2}};

  var state = {{
    linesOffset: 0,
    rangeCount: defaultRangeCount,
    angleDeg: defaultAngleDeg,
    lineLen: LINE_LEN,
    savedDefaultRange: defaultRangeCount,
    savedDefaultAngle: defaultAngleDeg,
    refs: [
      {{ax:0.22, ay:0.18, tx:0.08, ty:0.09, text:{json.dumps((refs_cfg[0].get('text','') if len(refs_cfg)>0 and isinstance(refs_cfg[0], dict) else ''))}}},
      {{ax:0.78, ay:0.20, tx:0.60, ty:0.09, text:{json.dumps((refs_cfg[1].get('text','') if len(refs_cfg)>1 and isinstance(refs_cfg[1], dict) else ''))}}},
      {{ax:0.48, ay:0.78, tx:0.28, ty:0.84, text:{json.dumps((refs_cfg[2].get('text','') if len(refs_cfg)>2 and isinstance(refs_cfg[2], dict) else ''))}}},
    ],
    drag: null,
    _handles: null
  }};

  try {{
    var saved = localStorage.getItem(storageKey);
    if (saved) {{
      var parsed = JSON.parse(saved);
      if (parsed && parsed.refs) state.refs = parsed.refs;
      if (parsed && typeof parsed.linesOffset === 'number') state.linesOffset = parsed.linesOffset;
      if (parsed && parsed.savedDefaultRange === defaultRangeCount && typeof parsed.rangeCount === 'number') {{
        state.rangeCount = Math.max(MIN_RANGES, Math.min(MAX_RANGES, Math.round(parsed.rangeCount)));
      }}
      if (parsed && parsed.savedDefaultAngle === defaultAngleDeg && typeof parsed.angleDeg === 'number') {{
        state.angleDeg = parsed.angleDeg;
      }}
      if (parsed && typeof parsed.lineLen === 'number') {{
        state.lineLen = Math.max(MIN_LINE_LEN, Math.min(MAX_LINE_LEN, parsed.lineLen));
      }}
    }}
  }} catch(e) {{}}

  function saveState() {{
    try {{
      localStorage.setItem(storageKey, JSON.stringify({{
        refs: state.refs,
        linesOffset: state.linesOffset,
        rangeCount: state.rangeCount,
        angleDeg: state.angleDeg,
        lineLen: state.lineLen,
        savedDefaultRange: state.savedDefaultRange,
        savedDefaultAngle: state.savedDefaultAngle
      }}));
    }} catch(e) {{}}
  }}

  function clamp(v,a,b) {{ return Math.max(a, Math.min(b, v)); }}

  function computeImageRect() {{
    if (!(img.width && img.height)) return imgRect;
    var scale = Math.min(W / img.width, H / img.height);
    var dw = img.width * scale, dh = img.height * scale;
    var dx = (W - dw) / 2, dy = (H - dh) / 2;
    imgRect = {{x:dx, y:dy, w:dw, h:dh, x1:dx+dw, y1:dy+dh, cx:dx+dw/2, cy:dy+dh/2}};
    return imgRect;
  }}

  function normToCanvasX(nx) {{ return nx * W; }}
  function normToCanvasY(ny) {{ return ny * H; }}
  function canvasToNormX(x) {{ return x / W; }}
  function canvasToNormY(y) {{ return y / H; }}

  function clampPointToImage(px, py, pad) {{
    var r = imgRect;
    return {{ x: clamp(px, r.x + pad, r.x1 - pad), y: clamp(py, r.y + pad, r.y1 - pad) }};
  }}

  function exitDistance(px, py, vx, vy, rect) {{
    var ts = [];
    if (vx > 1e-9) ts.push((rect.x1 - px) / vx);
    else if (vx < -1e-9) ts.push((rect.x - px) / vx);
    if (vy > 1e-9) ts.push((rect.y1 - py) / vy);
    else if (vy < -1e-9) ts.push((rect.y - py) / vy);
    ts = ts.filter(function(t) {{ return t >= 0; }});
    if (!ts.length) return 0;
    return Math.min.apply(null, ts);
  }}

  function getGeometry() {{
    var ang = state.angleDeg * Math.PI / 180;
    var dx = Math.cos(ang), dy = Math.sin(ang);
    var nx = -dy, ny = dx;
    var cx = imgRect.cx + nx * state.linesOffset * minDim;
    var cy = imgRect.cy + ny * state.linesOffset * minDim;
    return {{ang:ang, dx:dx, dy:dy, nx:nx, ny:ny, cx:cx, cy:cy}};
  }}

  function clampBeamState() {{
    computeImageRect();
    var g = getGeometry();
    var halfSpan = ((state.rangeCount - 1) / 2) * SPACING;

    var allowPos = Math.max(0, exitDistance(imgRect.cx, imgRect.cy, g.nx, g.ny, imgRect) - halfSpan);
    var allowNeg = Math.max(0, exitDistance(imgRect.cx, imgRect.cy, -g.nx, -g.ny, imgRect) - halfSpan);
    var offPx = state.linesOffset * minDim;
    offPx = clamp(offPx, -allowNeg, allowPos);
    state.linesOffset = offPx / minDim;

    g = getGeometry();
    var maxSpanCenter = Math.min(
      exitDistance(g.cx, g.cy, g.nx, g.ny, imgRect),
      exitDistance(g.cx, g.cy, -g.nx, -g.ny, imgRect)
    );
    var maxCount = Math.max(1, Math.min(MAX_RANGES, Math.floor((2 * maxSpanCenter) / SPACING) + 1));
    state.rangeCount = clamp(Math.round(state.rangeCount), MIN_RANGES, maxCount);

    var globalMaxLen = MAX_LINE_LEN;
    for (var i = 0; i < state.rangeCount; i++) {{
      var off = (i - (state.rangeCount - 1) / 2) * SPACING;
      var px = g.cx + g.nx * off;
      var py = g.cy + g.ny * off;
      var maxLenHere = Math.min(
        exitDistance(px, py, g.dx, g.dy, imgRect),
        exitDistance(px, py, -g.dx, -g.dy, imgRect)
      );
      globalMaxLen = Math.min(globalMaxLen, maxLenHere);
    }}
    state.lineLen = clamp(state.lineLen, Math.min(MIN_LINE_LEN, globalMaxLen), globalMaxLen);

    for (var r = 0; r < state.refs.length; r++) {{
      var ap = clampPointToImage(normToCanvasX(state.refs[r].ax), normToCanvasY(state.refs[r].ay), 8);
      var tp = clampPointToImage(normToCanvasX(state.refs[r].tx), normToCanvasY(state.refs[r].ty), 20);
      state.refs[r].ax = canvasToNormX(ap.x);
      state.refs[r].ay = canvasToNormY(ap.y);
      state.refs[r].tx = canvasToNormX(tp.x);
      state.refs[r].ty = canvasToNormY(tp.y);
    }}
  }}

  function drawArrow(fromX, fromY, toX, toY, color) {{
    var head = 14;
    var dx = toX-fromX, dy = toY-fromY;
    var ang = Math.atan2(dy, dx);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(fromX, fromY); ctx.lineTo(toX, toY); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - head*Math.cos(ang-Math.PI/6), toY - head*Math.sin(ang-Math.PI/6));
    ctx.lineTo(toX - head*Math.cos(ang+Math.PI/6), toY - head*Math.sin(ang+Math.PI/6));
    ctx.closePath(); ctx.fill();
  }}

  function drawTriangle(cx, cy, dirX, dirY, size) {{
    var px = -dirY, py = dirX;
    ctx.beginPath();
    ctx.moveTo(cx + dirX*size, cy + dirY*size);
    ctx.lineTo(cx + px*size*0.75, cy + py*size*0.75);
    ctx.lineTo(cx - px*size*0.75, cy - py*size*0.75);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
  }}

  function drawHandles(g) {{
    var liveLineLen = state.lineLen;
    var rotA = clampPointToImage(g.cx - g.dx * liveLineLen - g.nx * HANDLE_OFFSET, g.cy - g.dy * liveLineLen - g.ny * HANDLE_OFFSET, 12);
    var rotB = clampPointToImage(g.cx + g.dx * liveLineLen + g.nx * HANDLE_OFFSET, g.cy + g.dy * liveLineLen + g.ny * HANDLE_OFFSET, 12);

    var halfSpan = ((state.rangeCount - 1) / 2) * SPACING;
    if (state.rangeCount === 1) halfSpan = SPACING;
    var extA = clampPointToImage(g.cx - g.nx * halfSpan, g.cy - g.ny * halfSpan, 10);
    var extB = clampPointToImage(g.cx + g.nx * halfSpan, g.cy + g.ny * halfSpan, 10);

    var lenA1 = clampPointToImage(g.cx - g.nx * halfSpan - g.dx * liveLineLen, g.cy - g.ny * halfSpan - g.dy * liveLineLen, 8);
    var lenA2 = clampPointToImage(g.cx + g.nx * halfSpan - g.dx * liveLineLen, g.cy + g.ny * halfSpan - g.dy * liveLineLen, 8);
    var lenB1 = clampPointToImage(g.cx - g.nx * halfSpan + g.dx * liveLineLen, g.cy - g.ny * halfSpan + g.dy * liveLineLen, 8);
    var lenB2 = clampPointToImage(g.cx + g.nx * halfSpan + g.dx * liveLineLen, g.cy + g.ny * halfSpan + g.dy * liveLineLen, 8);

    state._handles = {{rotA:rotA, rotB:rotB, extA:extA, extB:extB, lenA1:lenA1, lenA2:lenA2, lenB1:lenB1, lenB2:lenB2, halfSpan:halfSpan}};

    ctx.fillStyle = '#FFD700';
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 2;
    [rotA, rotB].forEach(function(p) {{
      ctx.beginPath(); ctx.arc(p.x, p.y, 10, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }});

    ctx.fillStyle = '#FFFFFF';
    ctx.strokeStyle = '#1a1a1a';
    drawTriangle(extA.x, extA.y, -g.nx, -g.ny, 11);
    drawTriangle(extB.x, extB.y, g.nx, g.ny, 11);

    ctx.fillStyle = '#7FDBFF';
    [lenA1, lenA2, lenB1, lenB2].forEach(function(p) {{
      ctx.beginPath(); ctx.rect(p.x - 7, p.y - 7, 14, 14); ctx.fill(); ctx.stroke();
    }});
  }}

  function drawRanges() {{
    if (!showRanges) return;
    var g = getGeometry();
    ctx.save();
    ctx.beginPath();
    ctx.rect(imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    ctx.clip();
    for (var i=0; i<state.rangeCount; i++) {{
      var off = (i - (state.rangeCount-1)/2) * SPACING;
      var ox = g.nx*off, oy = g.ny*off;
      var x1 = g.cx + ox - g.dx*state.lineLen, y1 = g.cy + oy - g.dy*state.lineLen;
      var x2 = g.cx + ox + g.dx*state.lineLen, y2 = g.cy + oy + g.dy*state.lineLen;
      ctx.strokeStyle = (i % 2 === 0) ? acqColor : recColor;
      ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
    }}
    ctx.restore();
    drawHandles(g);
  }}

  function renderInputs() {{
    labelsLayer.innerHTML = '';

    var tools = document.createElement('div');
    tools.style.cssText = 'position:absolute; left:' + (imgRect.x + 8) + 'px; top:' + (imgRect.y + 8) + 'px; display:flex; gap:6px; pointer-events:auto; z-index:5;';
    for (var j = 0; j < 3; j++) {{
      (function(idx) {{
        var enabled = !!(refsCfg[idx] && refsCfg[idx].enabled);
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = 'R' + (idx + 1);
        btn.style.cssText = 'height:22px; min-width:30px; border-radius:999px; border:1px solid ' + recColor + '; background:' + (enabled ? recColor : 'rgba(0,0,0,0.68)') + '; color:#fff; font:700 11px Arial; cursor:pointer;';
        btn.addEventListener('click', function(e) {{
          e.preventDefault();
          e.stopPropagation();
          if (!refsCfg[idx]) refsCfg[idx] = {{enabled:false, text:''}};
          refsCfg[idx].enabled = !refsCfg[idx].enabled;
          saveState();
          drawImage();
        }});
        tools.appendChild(btn);
      }})(j);
    }}
    labelsLayer.appendChild(tools);

    for (var i = 0; i < state.refs.length; i++) {{
      (function(idx) {{
        if (!(refsCfg[idx] && refsCfg[idx].enabled)) return;
        var r = state.refs[idx];
        var left = clamp(normToCanvasX(r.tx), imgRect.x + 12, imgRect.x1 - 134);
        var top = clamp(normToCanvasY(r.ty) - 14, imgRect.y + 36, imgRect.y1 - 30);
        var box = document.createElement('div');
        box.style.cssText = 'position:absolute; left:' + left + 'px; top:' + top + 'px; width:122px; height:24px; display:flex; align-items:center; gap:4px; pointer-events:auto; z-index:6;';

        var handle = document.createElement('div');
        handle.textContent = String(idx + 1);
        handle.style.cssText = 'width:18px; height:18px; border-radius:50%; background:' + recColor + '; color:#fff; font:700 11px Arial; display:flex; align-items:center; justify-content:center; cursor:grab; flex:0 0 auto;';
        handle.addEventListener('mousedown', function(e) {{
          e.preventDefault();
          e.stopPropagation();
          state.drag = {{type:'ref_label', i:idx}};
        }});

        var input = document.createElement('input');
        input.type = 'text';
        input.value = r.text || '';
        input.placeholder = 'Anatomía';
        input.style.cssText = 'width:100px; height:24px; border:1px solid ' + recColor + '; border-radius:6px; background:rgba(0,0,0,0.72); color:#fff; padding:0 6px; font:12px Arial; outline:none;';
        input.addEventListener('mousedown', function(e) {{ e.stopPropagation(); }});
        input.addEventListener('click', function(e) {{ e.stopPropagation(); }});
        input.addEventListener('keydown', function(e) {{ e.stopPropagation(); }});
        input.addEventListener('input', function(e) {{
          e.stopPropagation();
          state.refs[idx].text = input.value;
          if (!refsCfg[idx]) refsCfg[idx] = {{enabled:true, text:''}};
          refsCfg[idx].text = input.value;
          saveState();
        }});
        input.addEventListener('change', function(e) {{
          e.stopPropagation();
          state.refs[idx].text = input.value;
          if (!refsCfg[idx]) refsCfg[idx] = {{enabled:true, text:''}};
          refsCfg[idx].text = input.value;
          saveState();
          drawImage();
        }});

        box.appendChild(handle);
        box.appendChild(input);
        labelsLayer.appendChild(box);
      }})(i);
    }}
  }}

  function drawRefs() {{
    ctx.font = 'bold 18px Arial';
    ctx.save();
    ctx.beginPath();
    ctx.rect(imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    ctx.clip();
    for (var i=0; i<state.refs.length; i++) {{
      if (!(refsCfg[i] && refsCfg[i].enabled)) continue;
      var r = state.refs[i];
      var ax = normToCanvasX(r.ax), ay = normToCanvasY(r.ay);
      var tx = normToCanvasX(r.tx), ty = normToCanvasY(r.ty);
      drawArrow(tx, ty, ax, ay, recColor);
      ctx.beginPath(); ctx.fillStyle = acqColor; ctx.arc(ax, ay, 7, 0, Math.PI*2); ctx.fill();
    }}
    ctx.restore();
    renderInputs();
  }}

  function drawImage() {{
    computeImageRect();
    clampBeamState();
    ctx.clearRect(0,0,W,H);
    ctx.fillStyle = '#000';
    ctx.fillRect(0,0,W,H);
    if (img.width && img.height) {{
      ctx.drawImage(img, imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    }}
    drawRanges();
    drawRefs();
  }}

  function getPos(evt) {{
    var rect = canvas.getBoundingClientRect();
    var cx = (evt.touches && evt.touches[0]) ? evt.touches[0].clientX : evt.clientX;
    var cy = (evt.touches && evt.touches[0]) ? evt.touches[0].clientY : evt.clientY;
    return {{x:(cx-rect.left)*(W/rect.width), y:(cy-rect.top)*(H/rect.height)}};
  }}

  function hitRef(pos) {{
    for (var i=0; i<state.refs.length; i++) {{
      if (!(refsCfg[i] && refsCfg[i].enabled)) continue;
      var r = state.refs[i];
      var ax = normToCanvasX(r.ax), ay = normToCanvasY(r.ay);
      if (Math.hypot(pos.x-ax, pos.y-ay) < 18) return {{i:i, p:'a'}};
    }}
    return null;
  }}

  function hitBeamHandle(pos) {{
    if (!showRanges || !state._handles) return null;
    var h = state._handles;
    if (Math.hypot(pos.x-h.rotA.x, pos.y-h.rotA.y) < ROT_HIT) return {{type:'rot', side:'a'}};
    if (Math.hypot(pos.x-h.rotB.x, pos.y-h.rotB.y) < ROT_HIT) return {{type:'rot', side:'b'}};
    if (Math.hypot(pos.x-h.extA.x, pos.y-h.extA.y) < EXT_HIT) return {{type:'ext', side:'a'}};
    if (Math.hypot(pos.x-h.extB.x, pos.y-h.extB.y) < EXT_HIT) return {{type:'ext', side:'b'}};
    if (Math.hypot(pos.x-h.lenA1.x, pos.y-h.lenA1.y) < LEN_HIT || Math.hypot(pos.x-h.lenA2.x, pos.y-h.lenA2.y) < LEN_HIT) return {{type:'len', side:'a'}};
    if (Math.hypot(pos.x-h.lenB1.x, pos.y-h.lenB1.y) < LEN_HIT || Math.hypot(pos.x-h.lenB2.x, pos.y-h.lenB2.y) < LEN_HIT) return {{type:'len', side:'b'}};
    return null;
  }}

  function hitInsideBeam(pos) {{
    if (!showRanges) return false;
    var g = getGeometry();
    var dxp = pos.x - g.cx, dyp = pos.y - g.cy;
    var along = dxp*g.dx + dyp*g.dy;
    var perp = dxp*g.nx + dyp*g.ny;
    var halfSpan = Math.max(SPACING*0.5, ((state.rangeCount-1)/2) * SPACING);
    return pos.x >= imgRect.x && pos.x <= imgRect.x1 && pos.y >= imgRect.y && pos.y <= imgRect.y1 && Math.abs(perp) < halfSpan + 8 && Math.abs(along) < state.lineLen;
  }}

  function setCursorFor(pos) {{
    if (hitRef(pos)) {{ canvas.style.cursor = 'grab'; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{
      if (bh.type === 'rot') canvas.style.cursor = 'grab';
      else if (bh.type === 'ext') canvas.style.cursor = (bh.side === 'a' ? 'nw-resize' : 'se-resize');
      else canvas.style.cursor = 'ew-resize';
      return;
    }}
    if (hitInsideBeam(pos)) {{ canvas.style.cursor = 'move'; return; }}
    canvas.style.cursor = 'crosshair';
  }}

  canvas.addEventListener('mousedown', function(e) {{
    var pos = getPos(e);
    var hr = hitRef(pos);
    if (hr) {{ state.drag = hr; canvas.style.cursor = 'grabbing'; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{ state.drag = {{type:'beam', sub:bh.type, side:bh.side}}; canvas.style.cursor = 'grabbing'; return; }}
    if (hitInsideBeam(pos)) state.drag = {{type:'beam', sub:'move'}};
  }});

  function applyDrag(pos) {{
    if (!state.drag) return;
    if (state.drag.p === 'a') {{
      var ap = clampPointToImage(pos.x, pos.y, 8);
      state.refs[state.drag.i].ax = canvasToNormX(ap.x);
      state.refs[state.drag.i].ay = canvasToNormY(ap.y);
    }} else if (state.drag.type === 'ref_label') {{
      var tp = clampPointToImage(pos.x, pos.y, 22);
      state.refs[state.drag.i].tx = canvasToNormX(tp.x);
      state.refs[state.drag.i].ty = canvasToNormY(tp.y);
    }} else if (state.drag.type === 'beam') {{
      var g = getGeometry();
      if (state.drag.sub === 'rot') {{
        var dxp = pos.x - g.cx, dyp = pos.y - g.cy;
        var ang = Math.atan2(dyp, dxp) * 180 / Math.PI;
        if (state.drag.side === 'a') ang += 180;
        while (ang > 180) ang -= 360;
        while (ang < -180) ang += 360;
        state.angleDeg = ang;
      }} else if (state.drag.sub === 'ext') {{
        var dxp2 = pos.x - g.cx, dyp2 = pos.y - g.cy;
        var perp = Math.abs(dxp2*g.nx + dyp2*g.ny);
        var n = Math.round((2 * perp) / SPACING) + 1;
        state.rangeCount = Math.max(MIN_RANGES, Math.min(MAX_RANGES, n));
      }} else if (state.drag.sub === 'len') {{
        var dxpLen = pos.x - g.cx, dypLen = pos.y - g.cy;
        var alongLen = Math.abs(dxpLen*g.dx + dypLen*g.dy);
        state.lineLen = Math.max(MIN_LINE_LEN, Math.min(MAX_LINE_LEN, alongLen));
      }} else if (state.drag.sub === 'move') {{
        var dxp3 = pos.x - imgRect.cx, dyp3 = pos.y - imgRect.cy;
        var newOff = (dxp3*g.nx + dyp3*g.ny) / minDim;
        state.linesOffset = clamp(newOff, -0.5, 0.5);
      }}
    }}
    drawImage();
  }}

  canvas.addEventListener('mousemove', function(e) {{ var pos = getPos(e); if (!state.drag) {{ setCursorFor(pos); return; }} applyDrag(pos); }});
  window.addEventListener('mousemove', function(e) {{ if (!state.drag) return; applyDrag(getPos(e)); }});
  window.addEventListener('mouseup', function() {{ if (state.drag) saveState(); state.drag = null; }});

  canvas.addEventListener('touchstart', function(e) {{
    if (!e.touches || !e.touches.length) return;
    e.preventDefault();
    var pos = getPos(e);
    var hr = hitRef(pos);
    if (hr) {{ state.drag = hr; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{ state.drag = {{type:'beam', sub:bh.type, side:bh.side}}; return; }}
    if (hitInsideBeam(pos)) state.drag = {{type:'beam', sub:'move'}};
  }}, {{passive:false}});
  canvas.addEventListener('touchmove', function(e) {{ if (!state.drag || !e.touches || !e.touches.length) return; e.preventDefault(); applyDrag(getPos(e)); }}, {{passive:false}});
  canvas.addEventListener('touchend', function() {{ if (state.drag) saveState(); state.drag = null; }});

  img.onload = drawImage;
  if (img.complete) drawImage();
}})();
</script>
"""
    return html


def _render_single_image_block(ref, rec, img_idx, title, css_width=320, css_height=250):
    img_state = _ensure_image_state(ref["id"])
    overlay = img_state.get(f"overlay{img_idx}")

    image_data = _render_image_uploader(ref["id"], img_idx, f"Subir {title.lower()}")

    if image_data is None:
        return

    try:
        pil = Image.open(io.BytesIO(image_data["bytes"]))
        img_b64 = _pil_to_b64_jpeg(pil)
        html = _overlay_canvas_html(
            img_b64=img_b64,
            storage_key=f"{ref['id']}_img{img_idx}",
            acq_color=_color_exploracion_por_exp_id(rec.get("exp_id")),
            rec_color=_color_reconstruccion(rec),
            settings=overlay,
            title="",
            css_width=css_width,
            css_height=css_height,
        )
        components.html(html, height=css_height + 8, scrolling=False)
    except Exception as e:
        st.error(f"No se pudo mostrar la imagen: {e}")

    _, col_btn = st.columns([1, 1], gap="small")
    with col_btn:
        if st.button("🗑️ Borrar imagen", key=f"del_{ref['id']}_{img_idx}", use_container_width=True):
            img_state[f"img{img_idx}"] = None
            st.rerun()


def _render_panel_rec(rec_id: str, recons_planas):
    rec = next((r for r in recons_planas if r["id"] == rec_id), None)
    if rec is None:
        st.warning("Reconstrucción no encontrada.")
        return
    _panel_header("🧩", f"{rec['nombre']} · {rec['exp_nombre']}")
    recd = rec["rec"]
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(f"**Fase:** {recd.get('fase_recons', '—')}")
        st.markdown(f"**Tipo:** {recd.get('tipo_recons', '—')}")
        st.markdown(f"**Kernel:** {recd.get('kernel_sel', '—')}")
        st.markdown(f"**Grosor:** {recd.get('grosor_recons', '—')}")
        st.markdown(f"**Incremento:** {recd.get('incremento', '—')}")
    with c2:
        st.markdown(f"**Ventana:** {recd.get('ventana_preset', '—')}")
        st.markdown(f"**WW / WL:** {recd.get('ww_val', '—')} / {recd.get('wl_val', '—')}")
        st.markdown(f"**DFOV:** {recd.get('dfov', '—')}")
        st.markdown(f"**Inicio:** {recd.get('inicio_recons', '—')}")
        st.markdown(f"**Fin:** {recd.get('fin_recons', '—')}")
    st.markdown("---")
    lista_refs = st.session_state["reformaciones_por_rec"].get(rec_id, [])
    if lista_refs:
        st.markdown(f"**Reformaciones creadas ({len(lista_refs)}):**")
        for ref in lista_refs:
            st.markdown(f"- 📐 {_nombre_reformacion(ref)}")
    else:
        st.info("Aún no hay reformaciones para esta reconstrucción. Usa **+ Reformación** en la barra lateral para crear la primera.")


def _reset_params(ref: dict):
    for p in ["plano", "grosor", "distancia", "n_vistas", "angulo"]:
        ref[p] = None


def _render_resumen(ref: dict):
    tipo = ref.get("tipo") or "—"
    subt = ref.get("subtipo")
    nombre = f"{tipo} {subt}" if subt else tipo
    params_activos = PARAMS_POR_TIPO.get((ref.get("tipo"), ref.get("subtipo")), [])
    lines = [f"**Tipo:** {nombre}"]
    for p in params_activos:
        val = ref.get(p)
        lines.append(f"**{PARAMS_LABELS.get(p, p)}:** {val if val is not None else '—'}")
    st.markdown("  \n".join(lines))


def _render_panel_reformacion(ref_id: str, recons_planas):
    ref = None
    for lista in st.session_state["reformaciones_por_rec"].values():
        for r in lista:
            if r["id"] == ref_id:
                ref = r
                break
        if ref:
            break
    if ref is None:
        st.warning("Reformación no encontrada.")
        return

    rec = next((r for r in recons_planas if r["id"] == ref.get("rec_id")), None)
    header_txt = _nombre_reformacion(ref)
    if rec:
        header_txt = f"{header_txt} · {rec['nombre']} ({rec['exp_nombre']})"
    _panel_header("📐", header_txt)

    tipo_prev = ref.get("tipo")
    ref["tipo"] = selectbox_con_placeholder("Tipo de reformación", TIPOS_REFORMACION, key=f"ref_tipo_{ref['id']}", value=tipo_prev)
    if ref["tipo"] != tipo_prev:
        ref["subtipo"] = None
        _reset_params(ref)

    if ref["tipo"] is None:
        st.info("Selecciona el tipo de reformación para continuar.")
        return

    subtipos = SUBTIPOS.get(ref["tipo"])
    if subtipos:
        subt_prev = ref.get("subtipo")
        ref["subtipo"] = selectbox_con_placeholder(f"{ref['tipo']} — variante", subtipos, key=f"ref_subtipo_{ref['id']}", value=subt_prev)
        if ref["subtipo"] != subt_prev:
            _reset_params(ref)
        if ref["subtipo"] is None:
            st.info("Selecciona la variante para continuar.")
            return
    else:
        ref["subtipo"] = None

    # Layout solicitado
    top_left, top_right = st.columns(2, gap="large")
    with top_left:
        _render_single_image_block(ref, rec, 1, "Imagen 1", css_width=340, css_height=250)
    with top_right:
        _render_single_image_block(ref, rec, 2, "Imagen 2", css_width=340, css_height=250)

    bottom_left, bottom_right = st.columns([1.15, 1.0], gap="large")
    with bottom_left:
        _render_single_image_block(ref, rec, 3, "Imagen 3", css_width=340, css_height=250)
    with bottom_right:
        st.markdown("<div style='height:0.2rem;'></div>", unsafe_allow_html=True)
        _panel_header("🎛️", "Parámetros de la reformación")
        params = PARAMS_POR_TIPO.get((ref["tipo"], ref["subtipo"]), [])
        if not params:
            st.warning("Combinación no soportada.")
            return
        for i in range(0, len(params), 2):
            fila = params[i:i+2]
            cols = st.columns(len(fila), gap="medium")
            for col, p in zip(cols, fila):
                with col:
                    ref[p] = selectbox_con_placeholder(
                        PARAMS_LABELS.get(p, p.title()),
                        PARAMS_OPCIONES.get(p, []),
                        key=f"ref_{p}_{ref['id']}",
                        value=ref.get(p),
                    )
        st.markdown("---")
        _panel_header("📝", "Resumen")
        _render_resumen(ref)


def render_reformaciones():
    _init_state()
    recons_planas = _obtener_reconstrucciones_planas()
    col_sidebar, col_main = st.columns([1.1, 4.5], gap="large")
    with col_sidebar:
        _render_sidebar(recons_planas)
    with col_main:
        if not recons_planas:
            st.subheader("Reformaciones")
            total_existentes = _contar_reconstrucciones_totales()
            if total_existentes == 0:
                st.info("Para crear reformaciones, primero debes programar al menos una reconstrucción en la pestaña **🧩 Reconstrucción**.")
            else:
                st.warning(
                    f"Tienes {total_existentes} reconstrucción(es) en la pestaña **🧩 Reconstrucción**, pero ninguna está lista para reformar. Para que una reconstrucción aparezca aquí, debe tener:\n\n"
                    "- Una **imagen de referencia** cargada.\n"
                    "- Todos sus **parámetros principales** definidos (fase, tipo, kernel, grosor, incremento, ventana y DFOV)."
                )
            return
        activa = st.session_state["ref_activa"]
        if activa is None:
            activa = {"kind": "rec", "rec_id": recons_planas[0]["id"]}
            st.session_state["ref_activa"] = activa
        if isinstance(activa, dict) and activa.get("kind") == "rec":
            _render_panel_rec(activa["rec_id"], recons_planas)
        elif isinstance(activa, str):
            _render_panel_reformacion(activa, recons_planas)
        else:
            st.info("Selecciona una reconstrucción o reformación en la barra lateral.")
