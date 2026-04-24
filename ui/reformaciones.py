import uuid
import io
import json
import base64
import hashlib
import time

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from ui.canvas_snapshot import (
    capture_canvas_group,
    capture_all_snapshots_raw,
    items_for_group,
    set_snapshot,
)

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


# Caché manual para _pil_to_b64_jpeg. Ver comentarios en adquisicion.py.
_B64_JPEG_CACHE: dict = {}
_B64_JPEG_CACHE_MAX = 128


def _render_b64_jpeg(img, max_width):
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


def _pil_to_b64_jpeg(img, max_width=1200):
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
        return _render_b64_jpeg(img, max_width)

    cached = _B64_JPEG_CACHE.get(fp)
    if cached is not None:
        return cached

    result = _render_b64_jpeg(img, max_width)
    if result is not None:
        _B64_JPEG_CACHE[fp] = result
        if len(_B64_JPEG_CACHE) > _B64_JPEG_CACHE_MAX:
            keys = list(_B64_JPEG_CACHE.keys())
            for k in keys[: len(keys) // 2]:
                _B64_JPEG_CACHE.pop(k, None)
    return result


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


def _get_region_label_for_exp_ref(exp: dict) -> str:
    """Obtiene el nombre del examen/región asociado a la exploración para
    mostrarlo junto al nombre de la reconstrucción en Reformaciones."""
    if not isinstance(exp, dict):
        return ""

    # 1) Intentar desde el set de topogramas asociado a la exploración
    sets = st.session_state.get("topograma_sets", []) or []
    topo_idx = exp.get("topo_set_idx", 0)
    try:
        if 0 <= int(topo_idx) < len(sets):
            topo = sets[int(topo_idx)] or {}
            region = topo.get("examen") or topo.get("region_anat") or topo.get("region") or ""
            if region:
                return str(region).strip()
    except Exception:
        pass

    # 2) Fallback directo desde la propia exploración
    region = exp.get("examen") or exp.get("region_anat") or exp.get("region") or ""
    if region:
        return str(region).strip()

    # 3) Último fallback: store legado
    topo_store = st.session_state.get("topograma_store", {}) or {}
    region = topo_store.get("examen") or topo_store.get("region_anat") or topo_store.get("region") or ""
    return str(region).strip() if region else ""


def _obtener_reconstrucciones_planas():
    recons_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    exploraciones = st.session_state.get("exploraciones", []) or []
    nombre_por_exp_id = {}
    for idx, exp in enumerate(exploraciones, start=1):
        if not isinstance(exp, dict):
            continue
        eid = exp.get("id") or f"exp_{idx}"
        nombre_base = exp.get("nombre") or f"Exploración {idx}"
        region = _get_region_label_for_exp_ref(exp)
        nombre_por_exp_id[eid] = f"{region} · {nombre_base}" if region else nombre_base

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
        "show_ranges": False,
        "range_count": 3,
        "angle_deg": 0,
        "show_refs": False,
        "refs": [
            {"enabled": False, "text": "", "ax": 0.28, "ay": 0.22, "tx": 0.18, "ty": 0.12},
            {"enabled": False, "text": "", "ax": 0.72, "ay": 0.26, "tx": 0.70, "ty": 0.12},
            {"enabled": False, "text": "", "ax": 0.50, "ay": 0.78, "tx": 0.40, "ty": 0.86},
        ],
    }


def _ensure_image_state(ref_id: str):
    store = st.session_state.setdefault("imagenes_ref_por_id", {})
    if ref_id not in store:
        store[ref_id] = {}
    for idx in (1, 2, 3):
        store[ref_id].setdefault(f"img{idx}", None)
        overlay = store[ref_id].setdefault(f"overlay{idx}", _default_overlay_settings(ref_id, idx))
        overlay.setdefault("show_ranges", False)
        overlay.setdefault("range_count", 3)
        overlay.setdefault("angle_deg", 0)
        overlay.setdefault("show_refs", False)
        refs = overlay.setdefault("refs", [])
        defaults = _default_overlay_settings(ref_id, idx)["refs"]
        # Normalizar a exactamente 3 referencias
        refs = list(refs[:3])
        while len(refs) < 3:
            refs.append(defaults[len(refs)].copy())
        for i in range(3):
            refs[i].setdefault("enabled", False)
            refs[i].setdefault("text", "")
            refs[i].setdefault("ax", defaults[i]["ax"])
            refs[i].setdefault("ay", defaults[i]["ay"])
            refs[i].setdefault("tx", defaults[i]["tx"])
            refs[i].setdefault("ty", defaults[i]["ty"])
        overlay["refs"] = refs
    return store[ref_id]


def _render_image_uploader(ref_id: str, img_idx: int, titulo: str):
    img_state = _ensure_image_state(ref_id)
    key_img = f"img{img_idx}"
    key_overlay = f"overlay{img_idx}"
    file_obj = st.file_uploader(titulo, type=["png", "jpg", "jpeg", "webp"], key=f"up_{ref_id}_{img_idx}")
    if file_obj is not None:
        data = file_obj.getvalue()
        file_sig = hashlib.md5(data).hexdigest()[:10]
        img_state[key_img] = {"name": file_obj.name, "bytes": data, "sig": file_sig}
        img_state[key_overlay] = _default_overlay_settings(ref_id, img_idx)
    if img_state.get(key_img) is not None:
        if st.button(f"🗑️ Borrar {titulo}", key=f"del_{ref_id}_{img_idx}", use_container_width=True):
            img_state[key_img] = None
            img_state[key_overlay] = _default_overlay_settings(ref_id, img_idx)
            st.rerun()
    return img_state.get(key_img)


def _overlay_canvas_html(
    img_b64,
    storage_key,
    acq_color,
    rec_color,
    settings,
    title="Imagen",
    css_width=320,
    css_height=260,
    internal_w=900,
    internal_h=700,
    overlay_mode="parallel",
    ranges_label="Rangos paralelos",
    exp_nombre=None,
    rec_nombre=None,
    ref_nombre=None,
):
    refs_cfg = settings.get("refs", [])[:3]
    while len(refs_cfg) < 3:
        refs_cfg.append({"enabled": False, "text": ""})
    html = f"""
<div data-planitc-snapshot-group="{storage_key}" style="text-align:center; margin:0;">
  <div id="toolbar_{storage_key}" style="width:{css_width}px; margin:0 auto 10px auto; display:flex; gap:8px; justify-content:flex-start; align-items:center; flex-wrap:wrap;">
    <div style="color:#d7d7d7; font-size:13px; font-weight:700; margin-right:4px;">Referencia anatómica</div>
    <button id="btn_{storage_key}_r1" type="button" style="background:rgba(0,0,0,0.65); color:#fff; border:1px solid {rec_color}; border-radius:999px; padding:7px 14px; font-size:13px; font-weight:700; cursor:pointer;">R1</button>
    <button id="btn_{storage_key}_r2" type="button" style="background:rgba(0,0,0,0.65); color:#fff; border:1px solid {rec_color}; border-radius:999px; padding:7px 14px; font-size:13px; font-weight:700; cursor:pointer;">R2</button>
    <button id="btn_{storage_key}_r3" type="button" style="background:rgba(0,0,0,0.65); color:#fff; border:1px solid {rec_color}; border-radius:999px; padding:7px 14px; font-size:13px; font-weight:700; cursor:pointer;">R3</button>
    <div style="width:14px;"></div>
    <button id="btn_{storage_key}_cuts" type="button" style="background:rgba(0,0,0,0.65); color:#fff; border:1px solid {acq_color}; border-radius:999px; padding:7px 14px; font-size:13px; font-weight:700; cursor:pointer;">{ranges_label}</button>
  </div>
  <div style="position:relative; width:{css_width}px; height:{css_height}px; margin:0 auto;">
    <canvas id="canvas_{storage_key}" data-planitc-snapshot-item="0" width="{internal_w}" height="{internal_h}"
      style="width:{css_width}px;height:{css_height}px;cursor:crosshair;border:1px solid #444;border-radius:8px;background:#000;display:block;touch-action:none;"></canvas>

    <div id="label_wrap_{storage_key}_0" style="position:absolute; display:none; z-index:7; align-items:center; gap:6px;">
      <div id="label_drag_{storage_key}_0" style="width:24px; height:24px; border-radius:999px; background:{rec_color}; color:#fff; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center; cursor:grab; user-select:none;">1</div>
      <input id="label_input_{storage_key}_0" type="text" value="{json.dumps(refs_cfg[0].get('text',''))[1:-1]}"
        style="width:150px; background:rgba(0,0,0,0.72); color:#fff; border:2px solid {rec_color}; border-radius:12px; padding:6px 10px; outline:none;" />
    </div>
    <div id="label_wrap_{storage_key}_1" style="position:absolute; display:none; z-index:7; align-items:center; gap:6px;">
      <div id="label_drag_{storage_key}_1" style="width:24px; height:24px; border-radius:999px; background:{rec_color}; color:#fff; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center; cursor:grab; user-select:none;">2</div>
      <input id="label_input_{storage_key}_1" type="text" value="{json.dumps(refs_cfg[1].get('text',''))[1:-1]}"
        style="width:150px; background:rgba(0,0,0,0.72); color:#fff; border:2px solid {rec_color}; border-radius:12px; padding:6px 10px; outline:none;" />
    </div>
    <div id="label_wrap_{storage_key}_2" style="position:absolute; display:none; z-index:7; align-items:center; gap:6px;">
      <div id="label_drag_{storage_key}_2" style="width:24px; height:24px; border-radius:999px; background:{rec_color}; color:#fff; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center; cursor:grab; user-select:none;">3</div>
      <input id="label_input_{storage_key}_2" type="text" value="{json.dumps(refs_cfg[2].get('text',''))[1:-1]}"
        style="width:150px; background:rgba(0,0,0,0.72); color:#fff; border:2px solid {rec_color}; border-radius:12px; padding:6px 10px; outline:none;" />
    </div>
  </div>
  <button type="button" onclick='downloadRefCanvas_{storage_key}({json.dumps(exp_nombre)}, {json.dumps(rec_nombre)}, {json.dumps(ref_nombre)})'
    style="margin-top:8px; background:#1f2937; color:#fff; border:1px solid #4b5563; border-radius:10px; padding:8px 12px; font-size:12px; font-weight:700; cursor:pointer;">Descargar PNG</button>
</div>
<script>
(function() {{
  var canvas = document.getElementById({json.dumps('canvas_' + storage_key)});
  if (!canvas) return;
  var wrapper = canvas.parentElement;
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  var img = new Image();
  img.src = 'data:image/jpeg;base64,' + {json.dumps(img_b64)};
  var storageKey = {json.dumps('planitc_ref_' + storage_key)};
  var snapshotKey = {json.dumps('planitc_snapshot_' + storage_key)};
  var acqColor = {json.dumps(acq_color)};
  var recColor = {json.dumps(rec_color)};
  var showRanges = {json.dumps(bool(settings.get('show_ranges', False)))};
  var overlayMode = {json.dumps(overlay_mode)};
  var defaultRangeCount = {json.dumps(int(settings.get('range_count', 3)))};
  var defaultAngleDeg = {json.dumps(float(settings.get('angle_deg', 0)))};
  var refsCfg = {json.dumps(refs_cfg)};

  var SPACING = 32;
  var LINE_LEN = Math.max(W, H) * 0.30;
  var MIN_RANGES = 1;
  var MAX_RANGES = 50;
  var ROT_HIT = 20;
  var EXT_HIT = 18;
  var LEN_HIT = 18;
  var HANDLE_OFFSET = 24;
  var MIN_LINE_LEN = Math.max(W, H) * 0.08;
  var MAX_LINE_LEN = Math.max(W, H) * 0.55;
  var minDim = Math.min(W, H);
  var displayScaleX = parseFloat(canvas.style.width) / W;
  var displayScaleY = parseFloat(canvas.style.height) / H;

  var state = {{
    linesOffset: 0,
    rangeCount: defaultRangeCount,
    angleDeg: defaultAngleDeg,
    lineLen: LINE_LEN,
    refs: [
      refsCfg[0] ? {{enabled: !!refsCfg[0].enabled, text: refsCfg[0].text || '', ax: refsCfg[0].ax || 0.28, ay: refsCfg[0].ay || 0.22, tx: refsCfg[0].tx || 0.18, ty: refsCfg[0].ty || 0.12}} : {{enabled:false,text:'',ax:0.28,ay:0.22,tx:0.18,ty:0.12}},
      refsCfg[1] ? {{enabled: !!refsCfg[1].enabled, text: refsCfg[1].text || '', ax: refsCfg[1].ax || 0.72, ay: refsCfg[1].ay || 0.26, tx: refsCfg[1].tx || 0.70, ty: refsCfg[1].ty || 0.12}} : {{enabled:false,text:'',ax:0.72,ay:0.26,tx:0.70,ty:0.12}},
      refsCfg[2] ? {{enabled: !!refsCfg[2].enabled, text: refsCfg[2].text || '', ax: refsCfg[2].ax || 0.50, ay: refsCfg[2].ay || 0.78, tx: refsCfg[2].tx || 0.40, ty: refsCfg[2].ty || 0.86}} : {{enabled:false,text:'',ax:0.50,ay:0.78,tx:0.40,ty:0.86}},
    ],
    drag: null,
    _handles: null,
    imageRect: {{x:0,y:0,w:W,h:H}}
  }};

  function clamp(v, lo, hi) {{ return Math.max(lo, Math.min(hi, v)); }}

  try {{
    var saved = localStorage.getItem(storageKey);
    if (saved) {{
      var parsed = JSON.parse(saved);
      if (parsed && parsed.refs && parsed.refs.length) {{
        for (var i = 0; i < Math.min(3, parsed.refs.length); i++) {{
          state.refs[i] = Object.assign(state.refs[i], parsed.refs[i]);
        }}
      }}
      if (parsed && typeof parsed.linesOffset === 'number') state.linesOffset = parsed.linesOffset;
      if (parsed && typeof parsed.rangeCount === 'number') state.rangeCount = clamp(Math.round(parsed.rangeCount), MIN_RANGES, MAX_RANGES);
      if (parsed && typeof parsed.angleDeg === 'number') state.angleDeg = parsed.angleDeg;
      if (parsed && typeof parsed.lineLen === 'number') state.lineLen = clamp(parsed.lineLen, MIN_LINE_LEN, MAX_LINE_LEN);
    }}
  }} catch(e) {{}}

  var labelWraps = [
    document.getElementById({json.dumps('label_wrap_' + storage_key + '_0')}),
    document.getElementById({json.dumps('label_wrap_' + storage_key + '_1')}),
    document.getElementById({json.dumps('label_wrap_' + storage_key + '_2')}),
  ];
  var labelDrags = [
    document.getElementById({json.dumps('label_drag_' + storage_key + '_0')}),
    document.getElementById({json.dumps('label_drag_' + storage_key + '_1')}),
    document.getElementById({json.dumps('label_drag_' + storage_key + '_2')}),
  ];
  var labelInputs = [
    document.getElementById({json.dumps('label_input_' + storage_key + '_0')}),
    document.getElementById({json.dumps('label_input_' + storage_key + '_1')}),
    document.getElementById({json.dumps('label_input_' + storage_key + '_2')}),
  ];
  var refBtns = [
    document.getElementById({json.dumps('btn_' + storage_key + '_r1')}),
    document.getElementById({json.dumps('btn_' + storage_key + '_r2')}),
    document.getElementById({json.dumps('btn_' + storage_key + '_r3')}),
  ];
  var cutsBtn = document.getElementById({json.dumps('btn_' + storage_key + '_cuts')});

  function downloadRefCanvas_{storage_key}(expNombre, recNombre, refNombre) {{
    console.log('Descargando con nombres:', {{expNombre, recNombre, refNombre}});
    
    // Construir nombre de archivo
    var parts = [];
    if (expNombre && String(expNombre).trim()) {{
      parts.push(String(expNombre).replace(/[^a-zA-Z0-9_-]+/g, '_'));
    }}
    if (recNombre && String(recNombre).trim()) {{
      parts.push(String(recNombre).replace(/[^a-zA-Z0-9_-]+/g, '_'));
    }}
    if (refNombre && String(refNombre).trim()) {{
      parts.push(String(refNombre).replace(/[^a-zA-Z0-9_-]+/g, '_'));
    }}
    var filename = parts.length > 0 ? parts.join('_') : {json.dumps(storage_key)};
    console.log('Nombre de archivo:', filename);
    
    // Crear canvas temporal para incluir texto de referencias
    var tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    var tempCtx = tempCanvas.getContext('2d');
    
    // Copiar la imagen actual del canvas principal
    tempCtx.drawImage(canvas, 0, 0);
    
    // Dibujar el texto de las referencias activas
    tempCtx.font = 'bold 24px Arial';
    tempCtx.textBaseline = 'middle';
    
    for (var i = 0; i < 3; i++) {{
      var ref = state.refs[i];
      if (!ref.enabled) continue;
      
      var input = refInputs[i];
      var text = input ? input.value.trim() : '';
      if (!text) continue;
      
      // Posición del ancla en píxeles del canvas
      var ap = normToPx(ref.ax, ref.ay);
      
      // Dibujar fondo semi-transparente para el texto
      tempCtx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      var textWidth = tempCtx.measureText(text).width;
      var padding = 12;
      tempCtx.fillRect(
        ap.x - textWidth/2 - padding,
        ap.y + 30 - 18,
        textWidth + padding * 2,
        36
      );
      
      // Dibujar texto
      tempCtx.fillStyle = recColor;
      tempCtx.textAlign = 'center';
      tempCtx.fillText(text, ap.x, ap.y + 30);
    }}
    
    // Descargar
    var a = document.createElement('a');
    a.href = tempCanvas.toDataURL('image/png');
    a.download = filename + '.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    console.log('Descargado:', filename + '.png');
  }}
  window.downloadRefCanvas_{storage_key} = downloadRefCanvas_{storage_key};

  function saveState() {{
    try {{
      localStorage.setItem(storageKey, JSON.stringify({{
        refs: state.refs,
        linesOffset: state.linesOffset,
        rangeCount: state.rangeCount,
        angleDeg: state.angleDeg,
        lineLen: state.lineLen
      }}));
      localStorage.setItem(snapshotKey, canvas.toDataURL('image/png'));
    }} catch(e) {{}}
  }}

  function imageBounds() {{ return state.imageRect; }}

  function normToPx(nx, ny) {{
    var r = imageBounds();
    return {{x: r.x + clamp(nx,0,1) * r.w, y: r.y + clamp(ny,0,1) * r.h}};
  }}

  function pxToNorm(px, py) {{
    var r = imageBounds();
    return {{
      x: clamp((px - r.x) / r.w, 0, 1),
      y: clamp((py - r.y) / r.h, 0, 1)
    }};
  }}

  function getGeometry() {{
    var ang = state.angleDeg * Math.PI / 180;
    var dx = Math.cos(ang), dy = Math.sin(ang);
    var nx = -dy, ny = dx;
    var r = imageBounds();
    var cx = r.x + r.w/2 + nx * state.linesOffset * Math.min(r.w, r.h);
    var cy = r.y + r.h/2 + ny * state.linesOffset * Math.min(r.w, r.h);
    return {{ang:ang, dx:dx, dy:dy, nx:nx, ny:ny, cx:cx, cy:cy}};
  }}

  function clipSegmentToRect(x1, y1, x2, y2, rect) {{
    var dx = x2 - x1, dy = y2 - y1;
    var t0 = 0, t1 = 1;
    var p = [-dx, dx, -dy, dy];
    var q = [x1 - rect.x, rect.x + rect.w - x1, y1 - rect.y, rect.y + rect.h - y1];
    for (var i = 0; i < 4; i++) {{
      if (p[i] === 0) {{
        if (q[i] < 0) return null;
      }} else {{
        var rr = q[i] / p[i];
        if (p[i] < 0) {{
          if (rr > t1) return null;
          if (rr > t0) t0 = rr;
        }} else {{
          if (rr < t0) return null;
          if (rr < t1) t1 = rr;
        }}
      }}
    }}
    return {{ x1: x1 + t0 * dx, y1: y1 + t0 * dy, x2: x1 + t1 * dx, y2: y1 + t1 * dy }};
  }}

  function drawArrow(fromX, fromY, toX, toY, color) {{
    var head = 12;
    var dx = toX - fromX, dy = toY - fromY;
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

  function drawParallelHandles(g) {{
    var r = imageBounds();
    var halfSpan = ((state.rangeCount - 1) / 2) * SPACING;
    if (state.rangeCount === 1) halfSpan = SPACING;
    var rotA = {{x: clamp(g.cx - g.dx * state.lineLen - g.nx * HANDLE_OFFSET, r.x, r.x + r.w), y: clamp(g.cy - g.dy * state.lineLen - g.ny * HANDLE_OFFSET, r.y, r.y + r.h)}};
    var rotB = {{x: clamp(g.cx + g.dx * state.lineLen + g.nx * HANDLE_OFFSET, r.x, r.x + r.w), y: clamp(g.cy + g.dy * state.lineLen + g.ny * HANDLE_OFFSET, r.y, r.y + r.h)}};
    var extA = {{x: clamp(g.cx - g.nx * halfSpan, r.x, r.x + r.w), y: clamp(g.cy - g.ny * halfSpan, r.y, r.y + r.h)}};
    var extB = {{x: clamp(g.cx + g.nx * halfSpan, r.x, r.x + r.w), y: clamp(g.cy + g.ny * halfSpan, r.y, r.y + r.h)}};
    var lenA1 = {{x: clamp(g.cx - g.nx * halfSpan - g.dx * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy - g.ny * halfSpan - g.dy * state.lineLen, r.y, r.y + r.h)}};
    var lenA2 = {{x: clamp(g.cx + g.nx * halfSpan - g.dx * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy + g.ny * halfSpan - g.dy * state.lineLen, r.y, r.y + r.h)}};
    var lenB1 = {{x: clamp(g.cx - g.nx * halfSpan + g.dx * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy - g.ny * halfSpan + g.dy * state.lineLen, r.y, r.y + r.h)}};
    var lenB2 = {{x: clamp(g.cx + g.nx * halfSpan + g.dx * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy + g.ny * halfSpan + g.dy * state.lineLen, r.y, r.y + r.h)}};
    state._handles = {{mode:'parallel', rotA:rotA, rotB:rotB, extA:extA, extB:extB, lenA1:lenA1, lenA2:lenA2, lenB1:lenB1, lenB2:lenB2, halfSpan:halfSpan, center:{{x:g.cx,y:g.cy}}}};

    ctx.fillStyle = '#FFD700';
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 2;
    [rotA, rotB].forEach(function(p) {{ ctx.beginPath(); ctx.arc(p.x, p.y, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); }});
    ctx.fillStyle = '#FFFFFF';
    drawTriangle(extA.x, extA.y, -g.nx, -g.ny, 9);
    drawTriangle(extB.x, extB.y, g.nx, g.ny, 9);
    ctx.fillStyle = '#7FDBFF';
    [lenA1, lenA2, lenB1, lenB2].forEach(function(p) {{ ctx.beginPath(); ctx.rect(p.x - 5, p.y - 5, 10, 10); ctx.fill(); ctx.stroke(); }});
  }}

  function drawRadialHandles(g) {{
    var r = imageBounds();
    var rotP = {{x: clamp(g.cx + Math.cos(g.ang) * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy + Math.sin(g.ang) * state.lineLen, r.y, r.y + r.h)}};
    var lenP = {{x: clamp(g.cx + Math.cos(g.ang + Math.PI/2) * state.lineLen, r.x, r.x + r.w), y: clamp(g.cy + Math.sin(g.ang + Math.PI/2) * state.lineLen, r.y, r.y + r.h)}};
    var extP = {{x: clamp(g.cx, r.x, r.x + r.w), y: clamp(g.cy - 28, r.y, r.y + r.h)}};
    state._handles = {{mode:'radial', rotA:rotP, extA:extP, lenA1:lenP, center:{{x:g.cx,y:g.cy}}}};

    ctx.fillStyle = '#FFD700';
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(rotP.x, rotP.y, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#FFFFFF';
    drawTriangle(extP.x, extP.y, 0, -1, 9);
    ctx.fillStyle = '#7FDBFF';
    ctx.beginPath(); ctx.rect(lenP.x - 5, lenP.y - 5, 10, 10); ctx.fill(); ctx.stroke();
  }}

  function drawRanges() {{
    if (!showRanges) {{ state._handles = null; return; }}
    var g = getGeometry();
    var rect = imageBounds();

    if (overlayMode === 'radial') {{
      for (var i = 0; i < state.rangeCount; i++) {{
        var ang = g.ang + (Math.PI * 2 * i / Math.max(1, state.rangeCount));
        var x2 = g.cx + Math.cos(ang) * state.lineLen;
        var y2 = g.cy + Math.sin(ang) * state.lineLen;
        var clipped = clipSegmentToRect(g.cx, g.cy, x2, y2, rect);
        if (!clipped) continue;
        ctx.strokeStyle = (i % 2 === 0) ? acqColor : recColor;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(clipped.x1, clipped.y1);
        ctx.lineTo(clipped.x2, clipped.y2);
        ctx.stroke();
      }}
      drawRadialHandles(g);
    }} else {{
      for (var i = 0; i < state.rangeCount; i++) {{
        var off = (i - (state.rangeCount - 1) / 2) * SPACING;
        var ox = g.nx * off, oy = g.ny * off;
        var x1 = g.cx + ox - g.dx * state.lineLen, y1 = g.cy + oy - g.dy * state.lineLen;
        var x2 = g.cx + ox + g.dx * state.lineLen, y2 = g.cy + oy + g.dy * state.lineLen;
        var clipped = clipSegmentToRect(x1, y1, x2, y2, rect);
        if (!clipped) continue;
        ctx.strokeStyle = (i % 2 === 0) ? acqColor : recColor;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(clipped.x1, clipped.y1);
        ctx.lineTo(clipped.x2, clipped.y2);
        ctx.stroke();
      }}
      drawParallelHandles(g);
    }}
  }}

  function updateRefButtons() {{
    for (var i = 0; i < 3; i++) {{
      if (!refBtns[i]) continue;
      refBtns[i].style.background = state.refs[i].enabled ? recColor : 'rgba(0,0,0,0.65)';
      refBtns[i].style.color = '#fff';
      refBtns[i].style.borderColor = recColor;
    }}
    if (cutsBtn) {{
      cutsBtn.style.background = showRanges ? acqColor : 'rgba(0,0,0,0.65)';
      cutsBtn.style.color = '#fff';
      cutsBtn.style.borderColor = acqColor;
    }}
  }}

  function syncLabelOverlays() {{
    var rectCanvas = canvas.getBoundingClientRect();
    displayScaleX = rectCanvas.width / W;
    displayScaleY = rectCanvas.height / H;
    for (var i = 0; i < 3; i++) {{
      var wrap = labelWraps[i], input = labelInputs[i], drag = labelDrags[i];
      if (!wrap || !input || !drag) continue;
      var ref = state.refs[i];
      if (!ref.enabled) {{ wrap.style.display = 'none'; continue; }}
      input.value = ref.text || '';
      wrap.style.display = 'flex';
      var p = normToPx(ref.tx, ref.ty);
      wrap.style.left = (p.x * displayScaleX) + 'px';
      wrap.style.top = (p.y * displayScaleY) + 'px';
    }}
    updateRefButtons();
  }}

  function drawRefs() {{
    for (var i = 0; i < 3; i++) {{
      var ref = state.refs[i];
      if (!ref.enabled) continue;
      var ap = normToPx(ref.ax, ref.ay);
      var tp = normToPx(ref.tx, ref.ty);
      drawArrow(tp.x + 18, tp.y + 14, ap.x, ap.y, recColor);
      ctx.beginPath();
      ctx.fillStyle = acqColor;
      ctx.arc(ap.x, ap.y, 7, 0, Math.PI*2);
      ctx.fill();
      ctx.strokeStyle = '#0a0a0a';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}
  }}

  function drawImage() {{
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    if (img.width && img.height) {{
      var scale = Math.min(W / img.width, H / img.height);
      var dw = img.width * scale, dh = img.height * scale;
      var dx = (W - dw) / 2, dy = (H - dh) / 2;
      state.imageRect = {{x: dx, y: dy, w: dw, h: dh}};
      ctx.drawImage(img, dx, dy, dw, dh);
    }} else {{
      state.imageRect = {{x: 0, y: 0, w: W, h: H}};
    }}
    drawRanges();
    drawRefs();
    syncLabelOverlays();
    saveState();
  }}

  function getPos(evt) {{
    var rect = canvas.getBoundingClientRect();
    var cx = (evt.touches && evt.touches[0]) ? evt.touches[0].clientX : evt.clientX;
    var cy = (evt.touches && evt.touches[0]) ? evt.touches[0].clientY : evt.clientY;
    return {{x: (cx - rect.left) * (W / rect.width), y: (cy - rect.top) * (H / rect.height)}};
  }}

  function hitRefPoint(pos) {{
    for (var i = 0; i < 3; i++) {{
      if (!state.refs[i].enabled) continue;
      var ap = normToPx(state.refs[i].ax, state.refs[i].ay);
      if (Math.hypot(pos.x - ap.x, pos.y - ap.y) < 16) return i;
    }}
    return -1;
  }}

  function hitBeamHandle(pos) {{
    if (!showRanges || !state._handles) return null;
    var h = state._handles;
    function near(a,b,r) {{ return Math.hypot(pos.x-a, pos.y-b) < r; }}
    if (near(h.center.x, h.center.y, 16)) return {{type:'move'}};
    if (near(h.rotA.x, h.rotA.y, ROT_HIT)) return {{type:'rot', side:'a'}};
    if (h.extA && near(h.extA.x, h.extA.y, EXT_HIT)) return {{type:'ext', side:'a'}};
    if (h.extB && near(h.extB.x, h.extB.y, EXT_HIT)) return {{type:'ext', side:'b'}};
    if (h.lenA1 && near(h.lenA1.x, h.lenA1.y, LEN_HIT)) return {{type:'len', side:'a'}};
    if (h.lenA2 && near(h.lenA2.x, h.lenA2.y, LEN_HIT)) return {{type:'len', side:'a'}};
    if (h.lenB1 && near(h.lenB1.x, h.lenB1.y, LEN_HIT)) return {{type:'len', side:'b'}};
    if (h.lenB2 && near(h.lenB2.x, h.lenB2.y, LEN_HIT)) return {{type:'len', side:'b'}};
    return null;
  }}

  function hitInsideBeam(pos) {{
    if (!showRanges) return false;
    var g = getGeometry();
    if (overlayMode === 'radial') {{
      return Math.hypot(pos.x - g.cx, pos.y - g.cy) < state.lineLen + 10;
    }}
    var dxp = pos.x - g.cx, dyp = pos.y - g.cy;
    var along = dxp * g.dx + dyp * g.dy;
    var perp = dxp * g.nx + dyp * g.ny;
    var halfSpan = Math.max(SPACING * 0.5, ((state.rangeCount - 1) / 2) * SPACING);
    return Math.abs(perp) < halfSpan + 8 && Math.abs(along) < state.lineLen;
  }}

  function setCursorFor(pos) {{
    if (hitRefPoint(pos) >= 0) {{ canvas.style.cursor = 'grab'; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{ canvas.style.cursor = (bh.type === 'len') ? 'ew-resize' : 'grab'; return; }}
    if (hitInsideBeam(pos)) {{ canvas.style.cursor = 'move'; return; }}
    canvas.style.cursor = 'crosshair';
  }}

  canvas.addEventListener('mousedown', function(e) {{
    var pos = getPos(e);
    var refIdx = hitRefPoint(pos);
    if (refIdx >= 0) {{ state.drag = {{type:'refPoint', i: refIdx}}; canvas.style.cursor = 'grabbing'; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{ state.drag = {{type:'beam', sub: bh.type, side: bh.side}}; canvas.style.cursor = 'grabbing'; return; }}
    if (hitInsideBeam(pos)) {{ state.drag = {{type:'beam', sub:'move'}}; canvas.style.cursor = 'grabbing'; }}
  }});

  function applyDrag(pos) {{
    if (!state.drag) return;
    var r = imageBounds();
    if (state.drag.type === 'refPoint') {{
      var n = pxToNorm(pos.x, pos.y);
      state.refs[state.drag.i].ax = n.x;
      state.refs[state.drag.i].ay = n.y;
      drawImage();
      return;
    }}
    var g = getGeometry();
    if (state.drag.sub === 'rot') {{
      var dxp = pos.x - g.cx, dyp = pos.y - g.cy;
      var ang = Math.atan2(dyp, dxp) * 180 / Math.PI;
      while (ang > 180) ang -= 360;
      while (ang < -180) ang += 360;
      state.angleDeg = ang;
    }} else if (state.drag.sub === 'ext') {{
      var dxp2 = pos.x - g.cx, dyp2 = pos.y - g.cy;
      if (overlayMode === 'radial') {{
        var dist = Math.hypot(dxp2, dyp2);
        var nRanges = Math.round(dist / 12);
        state.rangeCount = clamp(nRanges, MIN_RANGES, MAX_RANGES);
      }} else {{
        var perp = Math.abs(dxp2 * g.nx + dyp2 * g.ny);
        var nPar = Math.round((2 * perp) / SPACING) + 1;
        state.rangeCount = clamp(nPar, MIN_RANGES, MAX_RANGES);
      }}
    }} else if (state.drag.sub === 'len') {{
      var dxpLen = pos.x - g.cx, dypLen = pos.y - g.cy;
      var alongLen = Math.hypot(dxpLen, dypLen);
      state.lineLen = clamp(alongLen, MIN_LINE_LEN, MAX_LINE_LEN);
    }} else if (state.drag.sub === 'move') {{
      var dxp3 = pos.x - (r.x + r.w / 2), dyp3 = pos.y - (r.y + r.h / 2);
      var newOff = (dxp3 * g.nx + dyp3 * g.ny) / Math.min(r.w, r.h);
      state.linesOffset = clamp(newOff, -0.5, 0.5);
    }}
    drawImage();
  }}

  canvas.addEventListener('mousemove', function(e) {{
    var pos = getPos(e);
    if (!state.drag) {{ setCursorFor(pos); return; }}
    applyDrag(pos);
  }});
  window.addEventListener('mousemove', function(e) {{ if (state.drag) applyDrag(getPos(e)); }});
  window.addEventListener('mouseup', function() {{
    if (state.drag) saveState();
    state.drag = null;
    canvas.style.cursor = 'crosshair';
  }});

  canvas.addEventListener('touchstart', function(e) {{
    if (!e.touches || !e.touches.length) return;
    e.preventDefault();
    var pos = getPos(e);
    var refIdx = hitRefPoint(pos);
    if (refIdx >= 0) {{ state.drag = {{type:'refPoint', i: refIdx}}; return; }}
    var bh = hitBeamHandle(pos);
    if (bh) {{ state.drag = {{type:'beam', sub: bh.type, side: bh.side}}; return; }}
    if (hitInsideBeam(pos)) state.drag = {{type:'beam', sub:'move'}};
  }}, {{passive:false}});
  canvas.addEventListener('touchmove', function(e) {{
    if (!state.drag || !e.touches || !e.touches.length) return;
    e.preventDefault();
    applyDrag(getPos(e));
  }}, {{passive:false}});
  canvas.addEventListener('touchend', function() {{
    if (state.drag) saveState();
    state.drag = null;
  }});

  if (cutsBtn) {{
    cutsBtn.addEventListener('click', function() {{
      showRanges = !showRanges;
      saveState();
      drawImage();
    }});
  }}

  for (let i = 0; i < 3; i++) {{
    if (refBtns[i]) {{
      refBtns[i].addEventListener('click', function() {{
        state.refs[i].enabled = !state.refs[i].enabled;
        saveState();
        drawImage();
      }});
    }}
    if (labelInputs[i]) {{
      labelInputs[i].addEventListener('input', function() {{
        state.refs[i].text = this.value;
        saveState();
      }});
      labelInputs[i].addEventListener('mousedown', function(e) {{ e.stopPropagation(); }});
      labelInputs[i].addEventListener('click', function(e) {{ e.stopPropagation(); }});
      labelInputs[i].addEventListener('touchstart', function(e) {{ e.stopPropagation(); }}, {{passive:true}});
    }}
    if (labelDrags[i]) {{
      labelDrags[i].addEventListener('mousedown', function(e) {{
        e.preventDefault();
        e.stopPropagation();
        state.drag = {{type:'label', i:i}};
        canvas.style.cursor = 'grabbing';
      }});
      labelDrags[i].addEventListener('touchstart', function(e) {{
        e.preventDefault();
        e.stopPropagation();
        state.drag = {{type:'label', i:i}};
      }}, {{passive:false}});
    }}
  }}

  function moveLabelFromEvent(evt) {{
    if (!state.drag || state.drag.type !== 'label') return;
    var rect = wrapper.getBoundingClientRect();
    var cx = (evt.touches && evt.touches[0]) ? evt.touches[0].clientX : evt.clientX;
    var cy = (evt.touches && evt.touches[0]) ? evt.touches[0].clientY : evt.clientY;
    var xDisp = cx - rect.left;
    var yDisp = cy - rect.top;
    var xCanvas = xDisp / displayScaleX;
    var yCanvas = yDisp / displayScaleY;
    var n = pxToNorm(xCanvas, yCanvas);
    state.refs[state.drag.i].tx = n.x;
    state.refs[state.drag.i].ty = n.y;
    drawImage();
  }}

  window.addEventListener('mousemove', function(e) {{ if (state.drag && state.drag.type === 'label') moveLabelFromEvent(e); }});
  window.addEventListener('touchmove', function(e) {{
    if (state.drag && state.drag.type === 'label') {{
      e.preventDefault();
      moveLabelFromEvent(e);
    }}
  }}, {{passive:false}});
  window.addEventListener('mouseup', function() {{
    if (state.drag && state.drag.type === 'label') saveState();
    if (state.drag && state.drag.type === 'label') state.drag = null;
  }});
  window.addEventListener('touchend', function() {{
    if (state.drag && state.drag.type === 'label') saveState();
    if (state.drag && state.drag.type === 'label') state.drag = null;
  }});

  img.onload = drawImage;
  if (img.complete) drawImage();
}})();
</script>
"""
    return html


def _render_single_image_block(ref, rec, img_idx, title, css_width=320, css_height=250, overlay_mode="parallel", ranges_label="Rangos paralelos"):
    img_state = _ensure_image_state(ref["id"])
    image_data = img_state.get(f"img{img_idx}")
    overlay = img_state.get(f"overlay{img_idx}")

    if image_data is None:
        _panel_header("🖼️", title)
        uploaded = _render_image_uploader(ref["id"], img_idx, f"Subir {title.lower()}")
        image_data = uploaded if uploaded is not None else img_state.get(f"img{img_idx}")
        if image_data is None:
            return
        st.rerun()

    try:
        pil = Image.open(io.BytesIO(image_data["bytes"]))
        img_b64 = _pil_to_b64_jpeg(pil)
        img_sig = image_data.get("sig") or hashlib.md5(image_data["bytes"]).hexdigest()[:10]
        
        # Calcular nombres limpios para archivo descargado
        exp_nombre_limpio = None
        rec_nombre_limpio = None
        ref_nombre_limpio = None
        
        if rec:
            exp_nombre_raw = rec.get("exp_nombre", "")
            if exp_nombre_raw:
                exp_nombre_limpio = exp_nombre_raw.replace(" ", "_").replace("·", "_").replace("(", "").replace(")", "").replace("__", "_").strip("_")
            
            rec_nombre_raw = rec.get("nombre", "")
            if rec_nombre_raw:
                rec_nombre_limpio = rec_nombre_raw.replace(" ", "_")
        
        if ref:
            ref_nombre_raw = _nombre_reformacion(ref)
            if ref_nombre_raw:
                ref_nombre_limpio = ref_nombre_raw.replace(" ", "_")
        
        html = _overlay_canvas_html(
            img_b64=img_b64,
            storage_key=f"{ref['id']}_img{img_idx}_{img_sig}",
            acq_color=_color_exploracion_por_exp_id(rec.get("exp_id")),
            rec_color=_color_reconstruccion(rec),
            settings=overlay,
            title="",
            css_width=css_width,
            css_height=css_height,
            overlay_mode=overlay_mode,
            ranges_label=ranges_label,
            exp_nombre=exp_nombre_limpio,
            rec_nombre=rec_nombre_limpio,
            ref_nombre=ref_nombre_limpio,
        )
        components.html(html, height=css_height + 90, scrolling=False)
    except Exception as e:
        st.error(f"No se pudo mostrar la imagen: {e}")
        return

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




def _guardar_snapshots_reformacion_desde_bulk(ref_id: str, all_snaps) -> bool:
    """Extrae del bulk los snapshots de las 3 imágenes de esta reformación."""
    img_state = _ensure_image_state(ref_id)
    snaps = {}
    for img_idx in (1, 2, 3):
        image_data = img_state.get(f"img{img_idx}")
        if not image_data:
            continue
        img_sig = image_data.get("sig") or hashlib.md5(image_data["bytes"]).hexdigest()[:10]
        group_key = f"{ref_id}_img{img_idx}_{img_sig}"
        items = items_for_group(all_snaps, group_key)
        if items:
            snaps[f"img{img_idx}"] = {"bytes": items[0]["bytes"]}
    if not snaps:
        return False
    store = st.session_state.setdefault("canvas_snapshots_ref_por_id", {})
    store[ref_id] = snaps
    return True


def _render_boton_snapshot_reformacion(ref_id: str):
    """Botón manual para capturar los canvas de las imágenes de la reformación.

    Patrón robusto: streamlit_js_eval al tope (fuera de ramas condicionales)
    y botón Cancelar para que el usuario no quede bloqueado si el iframe
    interno no responde.
    """
    pending_key = f"_pending_snap_ref_{ref_id}"
    nonce = st.session_state.get(pending_key, 0)

    effective_key = (
        f"snap_ref_{ref_id}_{nonce}" if nonce else f"snap_ref_{ref_id}_idle"
    )
    all_snaps = capture_all_snapshots_raw(js_key=effective_key) if nonce else None

    if st.button(
        "💾 Guardar canvas para PDF",
        key=f"btn_snap_ref_{ref_id}",
        use_container_width=True,
        help="Guarda los canvas actuales de esta reformación en el reporte (opcional).",
    ):
        st.session_state[pending_key] = int(time.time() * 1000)
        st.rerun()

    if nonce:
        consumed_key = f"_consumed_snap_ref_{ref_id}_{nonce}"
        if st.session_state.get(consumed_key):
            pass
        elif all_snaps is None:
            col_wait, col_cancel = st.columns([3, 1], gap="small")
            with col_wait:
                st.info(
                    "📸 Capturando canvas… Si no avanza en 2-3 segundos, "
                    "vuelve a pulsar el botón."
                )
            with col_cancel:
                if st.button(
                    "Cancelar",
                    key=f"cancel_snap_ref_{ref_id}_{nonce}",
                    use_container_width=True,
                ):
                    st.session_state.pop(pending_key, None)
                    st.rerun()
        else:
            st.session_state[consumed_key] = True
            if _guardar_snapshots_reformacion_desde_bulk(ref_id, all_snaps):
                st.success("✓ Snapshots guardados para el PDF.")
            else:
                st.warning(
                    "No se pudieron capturar los canvas. Ajusta algo en las "
                    "imágenes y vuelve a intentarlo."
                )
            st.session_state.pop(pending_key, None)


def _guardar_snapshots_reformacion(ref_id: str):
    """Compatibilidad: versión antigua por-grupo."""
    img_state = _ensure_image_state(ref_id)
    snaps = {}
    for img_idx in (1, 2, 3):
        image_data = img_state.get(f"img{img_idx}")
        if not image_data:
            continue
        img_sig = image_data.get("sig") or hashlib.md5(image_data["bytes"]).hexdigest()[:10]
        group_key = f"{ref_id}_img{img_idx}_{img_sig}"
        items = capture_canvas_group(group_key, js_key=f"cap_ref_{ref_id}_{img_idx}")
        if items:
            snaps[f"img{img_idx}"] = {"bytes": items[0]["bytes"]}
    if not snaps:
        st.warning("No se pudieron capturar los canvas de reformación.")
        return
    store = st.session_state.setdefault("canvas_snapshots_ref_por_id", {})
    store[ref_id] = snaps
    st.success("Snapshots de reformación guardados para el PDF.")

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

    st.caption("Descarga la captura visual directamente desde el botón **Descargar PNG** que aparece bajo cada canvas.")

    is_vr = ref["tipo"] == "VR"
    overlay_mode = "radial" if is_vr else "parallel"
    ranges_label = "Rangos radiales" if is_vr else "Rangos paralelos"

    top_left, top_right = st.columns(2, gap="large")
    with top_left:
        _render_single_image_block(ref, rec, 1, "Imagen 1", css_width=520, css_height=380, overlay_mode=overlay_mode, ranges_label=ranges_label)
    with top_right:
        _render_single_image_block(ref, rec, 2, "Imagen 2", css_width=520, css_height=380, overlay_mode=overlay_mode, ranges_label=ranges_label)

    bottom_left, bottom_right = st.columns([1.15, 1.0], gap="large")
    with bottom_left:
        if not is_vr:
            _render_single_image_block(ref, rec, 3, "Imagen 3", css_width=520, css_height=380, overlay_mode=overlay_mode, ranges_label=ranges_label)
        else:
            img_state = _ensure_image_state(ref["id"])
            if img_state.get("img3") is not None:
                img_state["img3"] = None
                img_state["overlay3"] = _default_overlay_settings(ref["id"], 3)
            st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)
            st.info("Para reformación **VR** solo se permiten **2 imágenes**.")
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
        if is_vr:
            st.caption("En **VR** se permiten solo 2 imágenes y los rangos se muestran como **radiales**.")
        else:
            st.caption("Los rangos paralelos pueden moverse sobre cada imagen. Las referencias anatómicas se activan por imagen y permiten escribir el nombre que se mostrará junto a una flecha.")


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
