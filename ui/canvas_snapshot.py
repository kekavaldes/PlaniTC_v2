"""
ui/canvas_snapshot.py
Captura de snapshots (PNG) de los canvas HTML interactivos del simulador.

El JS de cada canvas persiste su imagen actual en localStorage con la clave
    planitc_snapshot_{storage_key}_{idx}
en cada evento de arrastre (endDrag). Este módulo expone funciones para leer
esos snapshots desde Python vía streamlit_js_eval.

API pública:
- capture_all_snapshots_raw(js_key): UNA llamada JS que trae TODOS los
  snapshots del localStorage como {full_key: bytes}. Es la vía preferida y
  la usada al generar el PDF (minimiza reruns).
- items_for_group(all_snaps, group_key): filtra/ordena los items
  correspondientes a un group_key específico desde el dict masivo.
- capture_canvas_group(group_key, js_key): API por-grupo (compatibilidad).
  Cada llamada monta un componente JS y dispara un rerun, por eso se
  recomienda usar capture_all_snapshots_raw en su lugar.
- combine_png_bytes(items, ...): combina varias PNG en una sola (horizontal).
- set_snapshot(store_name, obj_key, png_bytes, extra): guarda bytes en
  st.session_state[store_name][obj_key].
"""

import base64
import io
import json
import re
from typing import Any

import streamlit as st
from PIL import Image

try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None


# ────────────────────────────────────────────────────────────────────────
# Helpers internos
# ────────────────────────────────────────────────────────────────────────
def _normalize_js_result(value: Any):
    """Normaliza lo que devuelve streamlit_js_eval.

    Distingue:
    - None  → JS aún no retornó (estamos en el primer render post-click).
    - dict/list → resultado válido (posiblemente vacío).
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None
    return value


def _data_url_to_bytes(data_url: str):
    if not data_url or not isinstance(data_url, str) or "," not in data_url:
        return None
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────────────
# Captura MASIVA (preferida): una sola llamada JS para todos los snapshots
# ────────────────────────────────────────────────────────────────────────
def capture_all_snapshots_raw(js_key: str):
    """Lee en UNA sola ronda JS todos los keys de localStorage que comienzan
    con 'planitc_snapshot_' y los devuelve decodificados como:

        {full_key: png_bytes, ...}

    El parámetro js_key es usado por streamlit_js_eval para cachear el
    resultado; cambia el valor de js_key para forzar una lectura nueva
    (ej. `f"pdf_snaps_{nonce}"`).

    Retornos:
    - None  → el JS todavía no respondió (primer render). El caller debe
              mostrar un mensaje de "capturando…" y esperar al próximo rerun.
    - {}    → JS respondió pero no hay snapshots en localStorage.
    - dict  → {planitc_snapshot_xxx_N: bytes, ...}
    """
    if streamlit_js_eval is None:
        return {}

    script = """
    (function() {
      const out = {};

      function push(key, raw) {
        try {
          if (!key || !key.startsWith('planitc_snapshot_')) return;
          if (!raw || typeof raw !== 'string' || !raw.startsWith('data:image/')) return;
          // Si existe en varias capas, nos quedamos con la primera válida.
          if (!out[key]) out[key] = raw;
        } catch (e) {}
      }

      function readStorage(storage) {
        try {
          if (!storage) return;
          for (let i = 0; i < storage.length; i++) {
            const key = storage.key(i);
            if (!key || !key.startsWith('planitc_snapshot_')) continue;
            push(key, storage.getItem(key));
          }
        } catch (e) {}
      }


      try { readStorage(window.localStorage); } catch (e) {}
      try { readStorage(window.sessionStorage); } catch (e) {}
      // En Streamlit, streamlit_js_eval corre en la página principal.
      // Igual dejamos estos fallbacks por si cambia el contenedor.
      try { if (window.parent && window.parent !== window) readStorage(window.parent.localStorage); } catch (e) {}
      try { if (window.top && window.top !== window) readStorage(window.top.localStorage); } catch (e) {}

      return JSON.stringify(out);
    })()
    """

    result = _normalize_js_result(
        streamlit_js_eval(js_expressions=script, key=js_key)
    )
    if result is None:
        return None  # aún esperando al navegador
    if not isinstance(result, dict):
        return {}

    decoded = {}
    for key, data_url in result.items():
        data = _data_url_to_bytes(data_url)
        if data:
            decoded[key] = data
    return decoded


def items_for_group(all_snaps_bytes: dict, group_key: str):
    """Desde el dict devuelto por capture_all_snapshots_raw, extrae los
    items que pertenecen a `group_key`, ordenados por índice numérico
    (el sufijo después del group_key).

    Devuelve: [{"item": "0", "bytes": b"..."}, ...]
    """
    if not all_snaps_bytes or not group_key:
        return []
    prefix = "planitc_snapshot_" + group_key
    items = []
    for key, data_bytes in all_snaps_bytes.items():
        if key != prefix and not key.startswith(prefix + "_"):
            continue
        suffix = "0" if key == prefix else key[len(prefix) + 1:]
        m = re.search(r"(\d+)$", str(suffix))
        item_id = m.group(1) if m else (suffix or "0")
        items.append({"item": item_id, "bytes": data_bytes})
    items.sort(key=lambda x: (len(str(x["item"])), str(x["item"])))
    return items


# ────────────────────────────────────────────────────────────────────────
# API por-grupo (compatibilidad con el código que ya existía)
# ────────────────────────────────────────────────────────────────────────
def capture_canvas_group(group_key: str, js_key: str | None = None):
    """Captura por grupo. Hace una llamada JS por cada group_key.
    Preferir capture_all_snapshots_raw + items_for_group cuando se capture
    más de un grupo a la vez (ej. al generar el PDF)."""
    if not group_key or streamlit_js_eval is None:
        return []

    script = f"""
    (function() {{
      try {{
        const groupKey = {json.dumps(group_key)};
        const prefix = 'planitc_snapshot_' + groupKey;
        const out = [];

        function pushEntry(item, dataUrl) {{
          try {{
            if (!dataUrl || typeof dataUrl !== 'string' || !dataUrl.startsWith('data:image/')) return;
            out.push({{ item: String(item), data_url: dataUrl }});
          }} catch (e) {{}}
        }}

        function readStorage(storage) {{
          try {{
            if (!storage) return;
            for (let i = 0; i < storage.length; i++) {{
              const key = storage.key(i);
              if (!key || (key !== prefix && !key.startsWith(prefix + '_'))) continue;
              const raw = storage.getItem(key);
              if (!raw) continue;
              const suffix = key === prefix ? '0' : key.slice(prefix.length + 1);
              const match = String(suffix).match(/(\\d+)$/);
              const item = match ? match[1] : suffix || '0';
              pushEntry(item, raw);
            }}
          }} catch (e) {{}}
        }}


        readStorage(window.localStorage);
        readStorage(window.sessionStorage);
        try {{ if (window.parent && window.parent !== window) readStorage(window.parent.localStorage); }} catch (e) {{}}
        try {{ if (window.top && window.top !== window) readStorage(window.top.localStorage); }} catch (e) {{}}

        out.sort((a, b) => String(a.item).localeCompare(String(b.item), undefined, {{ numeric: true, sensitivity: 'base' }}));
        return JSON.stringify(out);
      }} catch (err) {{
        return JSON.stringify([]);
      }}
    }})()
    """

    result = _normalize_js_result(
        streamlit_js_eval(js_expressions=script, key=js_key or f"js_{group_key}")
    )
    if not isinstance(result, list):
        return []

    items = []
    for entry in result:
        if not isinstance(entry, dict):
            continue
        data = _data_url_to_bytes(entry.get("data_url"))
        if data:
            items.append({"item": str(entry.get("item", len(items))), "bytes": data})
    return items


# ────────────────────────────────────────────────────────────────────────
# Composición y guardado
# ────────────────────────────────────────────────────────────────────────
def combine_png_bytes(items, gap=12, padding=10, bg=(14, 17, 23, 255)):
    """Combina una lista de PNGs en un único PNG horizontal."""
    valid = []
    for item in items or []:
        data = item.get("bytes") if isinstance(item, dict) else item
        if not data:
            continue
        try:
            im = Image.open(io.BytesIO(data)).convert("RGBA")
            valid.append(im)
        except Exception:
            continue
    if not valid:
        return None
    total_w = sum(im.width for im in valid) + gap * (len(valid) - 1) + padding * 2
    max_h = max(im.height for im in valid) + padding * 2
    canvas = Image.new("RGBA", (total_w, max_h), bg)
    x = padding
    for im in valid:
        y = padding + (max_h - padding * 2 - im.height) // 2
        canvas.alpha_composite(im, (x, y))
        x += im.width + gap
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def set_snapshot(store_name: str, obj_key, png_bytes: bytes, extra: dict | None = None):
    """Guarda png_bytes en st.session_state[store_name][obj_key]."""
    if not png_bytes:
        return
    store = st.session_state.setdefault(store_name, {})
    payload = {"bytes": png_bytes}
    if extra:
        payload.update(extra)
    store[obj_key] = payload
