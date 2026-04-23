import base64
import io
import json
from typing import Any

import streamlit as st
from PIL import Image

try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None


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
    if not group_key or st_javascript is None:
        return []

    script = f"""(() => {{
      try {{
        const groupKey = {json.dumps(group_key)};
        const out = [];
        const frames = Array.from(window.parent.document.querySelectorAll('iframe'));
        frames.forEach((frame) => {{
          try {{
            const doc = frame.contentDocument || (frame.contentWindow && frame.contentWindow.document);
            if (!doc) return;
            const groups = Array.from(doc.querySelectorAll('[data-planitc-snapshot-group]'));
            groups.forEach((groupNode) => {{
              if (groupNode.getAttribute('data-planitc-snapshot-group') !== groupKey) return;
              const canvases = Array.from(groupNode.querySelectorAll('canvas[data-planitc-snapshot-item], canvas'));
              canvases.forEach((canvas, idx) => {{
                try {{
                  if (!canvas || !canvas.width || !canvas.height) return;
                  const item = canvas.getAttribute('data-planitc-snapshot-item') || String(idx);
                  out.push({{item, data_url: canvas.toDataURL('image/png')}});
                }} catch (e) {{}}
              }});
            }});
          }} catch (e) {{}}
        }});
        out.sort((a, b) => String(a.item).localeCompare(String(b.item), undefined, {{ numeric: true, sensitivity: 'base' }}));
        return out;
      }} catch (err) {{
        return [];
      }}
    }})()"""

    result = _normalize_js_result(st_javascript(script, key=js_key or f"js_{group_key}"))
    if not isinstance(result, list):
        return []

    items = []
    for entry in result:
        if not isinstance(entry, dict):
            continue
        data = _data_url_to_bytes(entry.get('data_url'))
        if data:
            items.append({'item': str(entry.get('item', len(items))), 'bytes': data})
    return items


def combine_png_bytes(items, gap=12, padding=10, bg=(14, 17, 23, 255)):
    valid = []
    for item in items or []:
        data = item.get('bytes') if isinstance(item, dict) else item
        if not data:
            continue
        try:
            im = Image.open(io.BytesIO(data)).convert('RGBA')
            valid.append(im)
        except Exception:
            continue
    if not valid:
        return None
    total_w = sum(im.width for im in valid) + gap * (len(valid) - 1) + padding * 2
    max_h = max(im.height for im in valid) + padding * 2
    canvas = Image.new('RGBA', (total_w, max_h), bg)
    x = padding
    for im in valid:
        y = padding + (max_h - padding * 2 - im.height) // 2
        canvas.alpha_composite(im, (x, y))
        x += im.width + gap
    out = io.BytesIO()
    canvas.save(out, format='PNG')
    return out.getvalue()


def set_snapshot(store_name: str, obj_key, png_bytes: bytes, extra: dict | None = None):
    if not png_bytes:
        return
    store = st.session_state.setdefault(store_name, {{}})
    payload = {{'bytes': png_bytes}}
    if extra:
        payload.update(extra)
    store[obj_key] = payload
