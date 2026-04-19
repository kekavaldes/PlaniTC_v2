"""
ui/reformaciones.py
Módulo de Reformaciones para PlaniTC_v2 (TAB 5).

Flujo:
- El usuario navega las reconstrucciones creadas en la pestaña
  "Reconstrucción" (session_state["reconstrucciones_por_exp"]).
- Por cada reconstrucción puede crear una o varias reformaciones.
- Cada reformación tiene un tipo (MPR / MIP / MinIP / VR); MIP tiene
  subtipos Grueso/Fino. Los parámetros que se piden cambian según
  tipo + subtipo (data-driven desde TIPOS_REFORMACION).

Layout:
- Sidebar izquierdo (similar a Adquisición): lista cronológica con las
  reconstrucciones como "encabezados" y debajo las reformaciones que
  el usuario haya creado para cada una.
- Panel central: parámetros de la reformación activa.

Entrypoint: render_reformaciones()
"""

import uuid

import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════
# CATÁLOGO DE TIPOS Y PARÁMETROS (data-driven)
# ═══════════════════════════════════════════════════════════════════════════

TIPOS_REFORMACION = ["MPR", "MIP", "MinIP", "VR"]

# Subtipos disponibles por tipo. None = sin subtipo.
SUBTIPOS = {
    "MPR": None,
    "MIP": ["Grueso", "Fino"],
    "MinIP": None,
    "VR": None,
}

# Parámetros requeridos por combinación tipo / subtipo.
# Clave: (tipo, subtipo)  — si el tipo no tiene subtipo, subtipo=None.
PARAMS_POR_TIPO = {
    ("MPR", None):     ["plano", "grosor", "distancia"],
    ("MIP", "Grueso"): ["n_vistas", "angulo"],
    ("MIP", "Fino"):   ["plano", "grosor", "distancia"],
    ("MinIP", None):   ["grosor", "distancia"],
    ("VR", None):      ["n_vistas", "angulo"],
}

# Opciones para cada parámetro (valores estándar para TC).
PARAMS_OPCIONES = {
    "plano":     ["AXIAL", "CORONAL", "SAGITAL", "CURVO"],
    "grosor":    ["1 mm", "2 mm", "3 mm", "4 mm", "5 mm", "7 mm", "10 mm"],
    "distancia": ["0,5 mm", "1 mm", "2 mm", "3 mm", "5 mm"],
    "n_vistas":  [6, 8, 10, 12, 15, 18, 24, 30, 36, 60, 72],
    "angulo":    ["5°", "10°", "12°", "15°", "20°", "30°", "45°", "60°"],
}

PARAMS_LABELS = {
    "plano":     "Plano",
    "grosor":    "Grosor",
    "distancia": "Distancia entre imágenes",
    "n_vistas":  "N° de vistas",
    "angulo":    "Ángulo entre vistas",
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE UI (consistentes con el resto del proyecto)
# ═══════════════════════════════════════════════════════════════════════════

def selectbox_con_placeholder(label, options, key, value=None, label_visibility="visible"):
    """Selectbox con 'Seleccionar' al inicio; devuelve None si no hay selección."""
    opciones = ["Seleccionar"] + [str(o) for o in options]
    val_str = str(value) if value is not None else None
    idx = opciones.index(val_str) if val_str in opciones else 0
    val = st.selectbox(label, opciones, key=key, index=idx, label_visibility=label_visibility)
    if val == "Seleccionar":
        return None
    # Recuperar tipo original (para n_vistas que son int)
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


# ═══════════════════════════════════════════════════════════════════════════
# CSS DEL SIDEBAR (mismo patrón que Adquisición)
# ═══════════════════════════════════════════════════════════════════════════

def _inject_sidebar_css():
    """Reutilizamos el mismo CSS del sidebar de Adquisición: botones de
    topograma/exploración, botones ✕ tertiary, y botones '+ ...' con
    fondo gris claro identificables por st-key-*."""
    st.markdown(
        """
        <style>
        /* Header "Reformaciones" ajustado al sidebar angosto */
        section[data-testid="stVerticalBlock"] h3:first-of-type {
            font-size: 1.15rem !important;
            margin-bottom: 0.6rem !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.2 !important;
        }

        /* Botones de eliminar (tertiary: ✕) */
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

        /* Botones principales (secondary/primary) del sidebar */
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

        /* Botones de acción global (+ Reformación) — identificados por key */
        .st-key-ref_btn_add_ref button[kind="secondary"],
        div.stApp .st-key-ref_btn_add_ref button[kind="secondary"] {
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
        .st-key-ref_btn_add_ref button[kind="secondary"]:hover,
        div.stApp .st-key-ref_btn_add_ref button[kind="secondary"]:hover {
            background-color: #7c808a !important;
            background: #7c808a !important;
            border-color: #90949e !important;
            color: #ffffff !important;
        }
        .st-key-ref_btn_add_ref button[kind="secondary"] p,
        .st-key-ref_btn_add_ref button[kind="secondary"] span,
        .st-key-ref_btn_add_ref button[kind="secondary"] div {
            font-size: 0.9rem !important;
            line-height: 1 !important;
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ESTADO: reformaciones por reconstrucción
# ═══════════════════════════════════════════════════════════════════════════

def _new_id() -> str:
    return f"ref_{uuid.uuid4().hex[:8]}"


def _next_order() -> int:
    """Contador monotónico para ordenar reconstrucciones + reformaciones
    cronológicamente en el sidebar."""
    st.session_state["_ref_next_order"] = int(st.session_state.get("_ref_next_order", 0)) + 1
    return st.session_state["_ref_next_order"]


def _init_state():
    # dict: rec_id -> list[reformacion]
    st.session_state.setdefault("reformaciones_por_rec", {})
    # orden de creación para cada reconstrucción vista por primera vez
    st.session_state.setdefault("_ref_rec_order", {})
    # reformación activa en el panel central. Puede ser:
    #   - un id de reformación, o
    #   - un dict {"kind": "rec", "rec_id": "..."} para "estar mirando la rec"
    st.session_state.setdefault("ref_activa", None)


def _crear_reformacion_base(rec_id: str) -> dict:
    return {
        "id": _new_id(),
        "rec_id": rec_id,
        "order": _next_order(),
        "tipo": None,
        "subtipo": None,
        # Parámetros (los que apliquen según tipo; el resto quedan en None)
        "plano": None,
        "grosor": None,
        "distancia": None,
        "n_vistas": None,
        "angulo": None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# LECTURA DE RECONSTRUCCIONES DESDE session_state
# ═══════════════════════════════════════════════════════════════════════════

def _reconstruccion_completada(rec) -> bool:
    """Réplica exacta del check de `reconstruccion.py`: una reconstrucción
    se considera 'lista' cuando tiene imagen cargada + los parámetros
    esenciales elegidos (no en 'Seleccionar' ni vacíos)."""
    img_ok = bool(
        st.session_state.get("imagenes_recon_por_id", {}).get(rec.get("id"))
    )
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


def _obtener_reconstrucciones_planas():
    """Devuelve la lista plana de reconstrucciones **completadas** (con
    imagen subida + parámetros guardados). Las que aún están en edición
    no aparecen en Reformaciones.

    Cada item: {
        "id": rec_id,
        "nombre": "Reconstrucción 1",
        "exp_id": exp_id,
        "exp_nombre": "SIN CONTRASTE",
        "rec": <dict original>,
    }
    """
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
            if not rid:
                continue

            # FILTRO: solo reconstrucciones completadas
            if not _reconstruccion_completada(rec):
                continue

            resultado.append({
                "id": rid,
                "nombre": rec.get("nombre") or "Reconstrucción",
                "exp_id": exp_id,
                "exp_nombre": nombre_por_exp_id.get(exp_id, exp_id),
                "rec": rec,
            })

            # Asegurar que la reconstrucción tiene un `order` asignado la
            # primera vez que la vemos aquí, para ordenar el sidebar.
            if rid not in st.session_state["_ref_rec_order"]:
                st.session_state["_ref_rec_order"][rid] = _next_order()

    return resultado


def _contar_reconstrucciones_totales() -> int:
    """Total de reconstrucciones existentes (completadas o no). Útil para
    mostrar un mensaje informativo cuando hay recs pero ninguna está lista."""
    recons_map = st.session_state.get("reconstrucciones_por_exp", {}) or {}
    total = 0
    for lista_recons in recons_map.values():
        if isinstance(lista_recons, list):
            total += sum(1 for r in lista_recons if isinstance(r, dict))
    return total


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

def _render_sidebar(recons_planas):
    _inject_sidebar_css()
    st.markdown("### 📐 Reformaciones")

    if not recons_planas:
        total_existentes = _contar_reconstrucciones_totales()
        if total_existentes == 0:
            st.info(
                "No hay reconstrucciones aún. Ve a la pestaña "
                "**Reconstrucción** para crear al menos una."
            )
        else:
            st.info(
                f"{total_existentes} reconstrucción(es) en edición. "
                "Cárgales imagen y completa sus parámetros para poder "
                "reformarlas aquí."
            )
        return

    # Normalizar estructura del mapa (defensivo)
    reformaciones_map = st.session_state["reformaciones_por_rec"]
    for r in recons_planas:
        reformaciones_map.setdefault(r["id"], [])

    rec_order = st.session_state["_ref_rec_order"]
    activa = st.session_state["ref_activa"]

    # Orden de las reconstrucciones: por su `order` de aparición
    recons_ordenadas = sorted(
        recons_planas,
        key=lambda r: rec_order.get(r["id"], 0),
    )

    # Renderizar AGRUPADO: cada reconstrucción y debajo sus reformaciones
    for r in recons_ordenadas:
        rec_id = r["id"]
        lbl = r["nombre"]
        reg = r["exp_nombre"]

        # Botón de la reconstrucción
        es_activo_rec = (
            isinstance(activa, dict)
            and activa.get("kind") == "rec"
            and activa.get("rec_id") == rec_id
        )
        tipo_btn = "primary" if es_activo_rec else "secondary"

        if st.button(
            f"🧩 {lbl} · {reg}",
            key=f"ref_btn_rec_{rec_id}",
            type=tipo_btn,
            use_container_width=True,
        ):
            st.session_state["ref_activa"] = {"kind": "rec", "rec_id": rec_id}
            st.rerun()

        # Reformaciones de esta reconstrucción (ordenadas por su propio order)
        refs_de_esta_rec = sorted(
            reformaciones_map.get(rec_id, []),
            key=lambda x: x.get("order", 0),
        )

        for ref in refs_de_esta_rec:
            es_activo_ref = (isinstance(activa, str) and activa == ref["id"])
            tipo_btn_ref = "primary" if es_activo_ref else "secondary"
            nombre_legible = _nombre_reformacion(ref)

            c_main, c_del = st.columns([6, 1], gap="small", vertical_alignment="center")
            with c_main:
                if st.button(
                    f"📐 {nombre_legible}",
                    key=f"ref_btn_ref_{ref['id']}",
                    type=tipo_btn_ref,
                    use_container_width=True,
                ):
                    st.session_state["ref_activa"] = ref["id"]
                    st.rerun()
            with c_del:
                if st.button(
                    "✕",
                    key=f"ref_btn_del_{ref['id']}",
                    type="tertiary",
                    use_container_width=True,
                    help=f"Eliminar {nombre_legible}",
                ):
                    _eliminar_reformacion(ref["id"], ref.get("rec_id"))
                    st.rerun()

        # Pequeño espacio vertical entre grupos de rec + sus reformaciones
        st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)

    # ── Botón "+ Reformación" ──
    # Determinar a qué reconstrucción se agregará: la de la reformación
    # activa, o la reconstrucción si es la vista activa, o la primera rec.
    target_rec_id = _rec_target_id(recons_planas)

    st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)

    if target_rec_id is not None:
        rec_target = next((r for r in recons_planas if r["id"] == target_rec_id), None)
        target_name = rec_target["nombre"] if rec_target else "reconstrucción"
    else:
        target_name = "reconstrucción"

    if st.button(
        "+ Reformación",
        key="ref_btn_add_ref",
        type="secondary",
        use_container_width=True,
    ):
        if target_rec_id is None:
            st.warning("Selecciona una reconstrucción primero.")
        else:
            nueva = _crear_reformacion_base(target_rec_id)
            st.session_state["reformaciones_por_rec"].setdefault(target_rec_id, []).append(nueva)
            st.session_state["ref_activa"] = nueva["id"]
            st.rerun()


def _rec_target_id(recons_planas):
    """Determina a qué reconstrucción se asocia una nueva reformación."""
    activa = st.session_state["ref_activa"]
    # Caso 1: hay una reformación seleccionada → su rec
    if isinstance(activa, str):
        for lista in st.session_state["reformaciones_por_rec"].values():
            for ref in lista:
                if ref["id"] == activa:
                    return ref.get("rec_id")
    # Caso 2: el usuario está mirando una reconstrucción
    if isinstance(activa, dict) and activa.get("kind") == "rec":
        return activa.get("rec_id")
    # Caso 3: primera disponible
    if recons_planas:
        return recons_planas[0]["id"]
    return None


def _nombre_reformacion(ref: dict) -> str:
    """Nombre legible para mostrar en el sidebar."""
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
        # Búsqueda defensiva
        for rid, lista in mapa.items():
            mapa[rid] = [r for r in lista if r.get("id") != ref_id]
    # Si era la activa, limpiar
    if st.session_state.get("ref_activa") == ref_id:
        st.session_state["ref_activa"] = None


# ═══════════════════════════════════════════════════════════════════════════
# PANEL CENTRAL
# ═══════════════════════════════════════════════════════════════════════════

def _render_panel_rec(rec_id: str, recons_planas):
    """Vista cuando el usuario está sobre un encabezado de reconstrucción."""
    rec = next((r for r in recons_planas if r["id"] == rec_id), None)
    if rec is None:
        st.warning("Reconstrucción no encontrada.")
        return

    _panel_header("🧩", f"{rec['nombre']} · {rec['exp_nombre']}")

    recd = rec["rec"]  # dict original de la reconstrucción
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

    # Reformaciones ya creadas para esta reconstrucción
    lista_refs = st.session_state["reformaciones_por_rec"].get(rec_id, [])
    if lista_refs:
        st.markdown(f"**Reformaciones creadas ({len(lista_refs)}):**")
        for ref in lista_refs:
            st.markdown(f"- 📐 {_nombre_reformacion(ref)}")
    else:
        st.info(
            "Aún no hay reformaciones para esta reconstrucción. "
            "Usa **+ Reformación** en la barra lateral para crear la primera."
        )


def _render_panel_reformacion(ref_id: str, recons_planas):
    """Vista para editar una reformación."""
    # Buscar la ref
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

    # 1) Tipo
    tipo_prev = ref.get("tipo")
    ref["tipo"] = selectbox_con_placeholder(
        "Tipo de reformación",
        TIPOS_REFORMACION,
        key=f"ref_tipo_{ref['id']}",
        value=tipo_prev,
    )
    # Si cambió el tipo, resetear subtipo y params
    if ref["tipo"] != tipo_prev:
        ref["subtipo"] = None
        _reset_params(ref)

    if ref["tipo"] is None:
        st.info("Selecciona el tipo de reformación para continuar.")
        return

    # 2) Subtipo (solo si aplica)
    subtipos = SUBTIPOS.get(ref["tipo"])
    if subtipos:
        subt_prev = ref.get("subtipo")
        ref["subtipo"] = selectbox_con_placeholder(
            f"{ref['tipo']} — variante",
            subtipos,
            key=f"ref_subtipo_{ref['id']}",
            value=subt_prev,
        )
        if ref["subtipo"] != subt_prev:
            _reset_params(ref)

        if ref["subtipo"] is None:
            st.info("Selecciona la variante para continuar.")
            return
    else:
        ref["subtipo"] = None

    # 3) Parámetros según (tipo, subtipo)
    params = PARAMS_POR_TIPO.get((ref["tipo"], ref["subtipo"]), [])
    if not params:
        st.warning("Combinación no soportada.")
        return

    st.markdown("---")
    _panel_header("🎛️", "Parámetros")

    # Renderizamos en columnas (2 por fila para que se vea ordenado)
    for i in range(0, len(params), 2):
        fila = params[i:i+2]
        cols = st.columns(len(fila), gap="medium")
        for col, p in zip(cols, fila):
            with col:
                opts = PARAMS_OPCIONES.get(p, [])
                label = PARAMS_LABELS.get(p, p.title())
                ref[p] = selectbox_con_placeholder(
                    label,
                    opts,
                    key=f"ref_{p}_{ref['id']}",
                    value=ref.get(p),
                )

    # Resumen inferior
    st.markdown("---")
    _panel_header("📝", "Resumen")
    _render_resumen(ref)


def _reset_params(ref: dict):
    """Limpia los parámetros cuando cambia tipo/subtipo."""
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


# ═══════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

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
                st.info(
                    "Para crear reformaciones, primero debes programar "
                    "al menos una reconstrucción en la pestaña "
                    "**🧩 Reconstrucción**."
                )
            else:
                st.warning(
                    f"Tienes {total_existentes} reconstrucción(es) en la "
                    "pestaña **🧩 Reconstrucción**, pero ninguna está lista "
                    "para reformar. Para que una reconstrucción aparezca "
                    "aquí, debe tener:\n\n"
                    "- Una **imagen de referencia** cargada.\n"
                    "- Todos sus **parámetros principales** definidos "
                    "(fase, tipo, kernel, grosor, incremento, ventana y DFOV)."
                )
            return

        activa = st.session_state["ref_activa"]

        # Auto-seleccionar la primera reconstrucción si no hay nada activo
        if activa is None:
            activa = {"kind": "rec", "rec_id": recons_planas[0]["id"]}
            st.session_state["ref_activa"] = activa

        if isinstance(activa, dict) and activa.get("kind") == "rec":
            _render_panel_rec(activa["rec_id"], recons_planas)
        elif isinstance(activa, str):
            _render_panel_reformacion(activa, recons_planas)
        else:
            st.info("Selecciona una reconstrucción o reformación en la barra lateral.")
