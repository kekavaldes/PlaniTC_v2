import copy

import streamlit as st


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
    lista_local = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
    st.session_state["reconstrucciones_por_exp"][exp_id] = lista_local
    for idx_local, rec_local in enumerate(lista_local, start=1):
        rec_local["id"] = f"{exp_id}_rec_{idx_local}"
        rec_local["nombre"] = f"Reconstrucción {idx_local}"


for exp in adquisiciones_validas:
    exp_id = exp.get("id")

    if exp_id not in st.session_state["reconstrucciones_por_exp"]:
        st.session_state["reconstrucciones_por_exp"][exp_id] = []

    # 👇 SOLO UNA reconstrucción inicial
    if not st.session_state["reconstrucciones_por_exp"][exp_id]:
        region_anat = _get_region_group_for_exp(exp)
        nueva = _crear_reconstruccion_base(exp, 1, region_anat)

        st.session_state["reconstrucciones_por_exp"][exp_id].append(nueva)
        st.session_state["recon_activa_por_exp"][exp_id] = nueva["id"]

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
        nombre_visible = f"{nombre_base} · {region}".strip(" ·")

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

    col_img_param = st.columns([1.0, 1.15], gap="medium")

    with col_img_param[0]:
        c_img_left, c_img_center, c_img_right = st.columns([0.08, 1.0, 0.08], gap="small")
        with c_img_center:
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
            img_guardada = st.session_state["imagenes_recon_por_id"].get(rec_actual["id"])
            if img_guardada is not None:
                st.image(img_guardada["bytes"], caption="Imagen cargada", width=360)

    with col_img_param[1]:
        _panel_header("🔧", "Parámetros de Reconstrucción")

        col_pr1, col_pr2 = st.columns([1, 1], gap="small")
        with col_pr1:
            rec_actual["fase_recons"] = selectbox_con_placeholder("Fase a reconstruir", FASES_RECONS, key=f"fase_recons_{rec_actual['id']}", value=rec_actual.get("fase_recons"))
            if rec_actual["tipo_recons"] == "RECONS. ITERATIVA":
                rec_actual["algoritmo_iter"] = selectbox_con_placeholder("Algoritmo iterativo", ALGORITMOS_ITERATIVOS, key=f"alg_iter_{rec_actual['id']}", value=rec_actual.get("algoritmo_iter"))
            else:
                rec_actual["algoritmo_iter"] = "—"
            rec_actual["kernel_sel"] = selectbox_con_placeholder("Algoritmo (Kernel)", KERNELS, key=f"kernel_sel_{rec_actual['id']}", value=rec_actual.get("kernel_sel"))
            rec_actual["grosor_recons"] = selectbox_con_placeholder("Grosor reconstrucción", GROSORES_RECONS, key=f"grosor_recons_{rec_actual['id']}", value=rec_actual.get("grosor_recons"))

        with col_pr2:
            rec_actual["tipo_recons"] = selectbox_con_placeholder("Tipo de reconstrucción", TIPOS_RECONS, key=f"tipo_recons_{rec_actual['id']}", value=rec_actual.get("tipo_recons"))
            if rec_actual["tipo_recons"] == "RECONS. ITERATIVA":
                niveles_disp = NIVEL_ITERATIVO.get(rec_actual["algoritmo_iter"], [1])
                rec_actual["nivel_iter"] = selectbox_con_placeholder("Nivel / Porcentaje / Modo", niveles_disp, key=f"nivel_iter_{rec_actual['id']}", value=rec_actual.get("nivel_iter"))
            else:
                rec_actual["nivel_iter"] = "—"
            rec_actual["incremento"] = selectbox_con_placeholder("Incremento", INCREMENTOS_RECONS, key=f"incremento_{rec_actual['id']}", value=rec_actual.get("incremento"))

        _panel_header("🪟", "Ventana de Visualización")
        ventanas_disp = list(VENTANAS.keys())

        col_v1, col_v2 = st.columns([1, 1], gap="small")
        with col_v1:
            rec_actual["ventana_preset"] = selectbox_con_placeholder("Preset de ventana", ventanas_disp, key=f"preset_ventana_{rec_actual['id']}", value=rec_actual.get("ventana_preset"))
            if rec_actual["ventana_preset"] in VENTANAS:
                ww_default = VENTANAS[rec_actual["ventana_preset"]]["ww"]
                wl_default = VENTANAS[rec_actual["ventana_preset"]]["wl"]
            else:
                ww_default = 400
                wl_default = 40
            rec_actual["ww_val"] = st.number_input("WW", min_value=1, max_value=5000, value=int(rec_actual.get("ww_val", ww_default)), step=1, key=f"ww_{rec_actual['id']}")

        with col_v2:
            rec_actual["wl_val"] = st.number_input("WL", min_value=-1500, max_value=3000, value=int(rec_actual.get("wl_val", wl_default)), step=1, key=f"wl_{rec_actual['id']}")
            rec_actual["dfov"] = selectbox_con_placeholder("DFOV", DFOV_OPCIONES, key=f"dfov_{rec_actual['id']}", value=rec_actual.get("dfov"))

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
