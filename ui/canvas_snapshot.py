import base64
import io
import json
from typing import Any

import streamlit as st
from PIL import Image

try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None


def _normalize_js_result(value: Any):
    if value in (None, "", [], {}):
        return []
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return []
        try:
            return json.loads(txt)
        except Exception:
            return []
    return value


def _data_url_to_bytes(data_url: str):
    if not data_url or not isinstance(data_url, str) or "," not in data_url:
        return None
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except Exception:
        return None


def capture_canvas_group(group_key: str, js_key: str | None = None):
    if not group_key:
        return []

    if streamlit_js_eval is None:
        st.error(
            "No se puede capturar el canvas porque falta la dependencia "
            "'streamlit-js-eval' en el despliegue."
        )
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

        for (let i = 0; i < window.localStorage.length; i++) {{
          const key = window.localStorage.key(i);
          if (!key || (key !== prefix && !key.startsWith(prefix + '_'))) continue;
          const raw = window.localStorage.getItem(key);
          if (!raw) continue;
          const suffix = key === prefix ? '0' : key.slice(prefix.length + 1);
          const match = String(suffix).match(/(\\d+)$/);
          const item = match ? match[1] : suffix || '0';
          pushEntry(item, raw);
        }}

        out.sort((a, b) => String(a.item).localeCompare(String(b.item), undefined, {{
          numeric: true,
          sensitivity: 'base'
        }}));

        return JSON.stringify(out);
      }} catch (err) {{
        return JSON.stringify([]);
      }}
    }})()
    """

    result = _normalize_js_result(
        streamlit_js_eval(
            js_expressions=script,
            key=js_key or f"js_{group_key}"
        )
    )

    if not isinstance(result, list):
        return []

    items = []
    for entry in result:
        if not isinstance(entry, dict):
            continue
        data = _data_url_to_bytes(entry.get("data_url"))
        if data:
            items.append({
                "item": str(entry.get("item", len(items))),
                "bytes": data
            })
    return items


def combine_png_bytes(items, gap=12, padding=10, bg=(14, 17, 23, 255)):
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
    if not png_bytes:
        return
    store = st.session_state.setdefault(store_name, {})
    payload = {"bytes": png_bytes}
    if extra:
        payload.update(extra)
    store[obj_key] = payload
