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

        /* Selectores fijos de reconstrucción (6) */
        div[data-testid="stButton"] > button[kind][id*="btn_rec_item_"] {
            min-height: 3.25rem !important;
            height: 3.25rem !important;
            width: 100% !important;
            padding: 0.45rem 0.9rem !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            border-radius: 16px !important;
            text-align: left !important;
            box-shadow: none !important;
        }

        div[data-testid="stButton"] > button[kind][id*="btn_rec_item_"] p {
            line-height: 1.05 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 0.45rem !important;
            height: 100% !important;
            width: 100% !important;
            font-size: 0.94rem !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
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


def render_reconstruccion():
    _inject_recon_css()
    adquisiciones_validas = _obtener_adquisiciones_validas()

    st.session_state.setdefault("reconstrucciones_por_exp", {})
    st.session_state.setdefault("recon_activa_por_exp", {})
    st.session_state.setdefault("exploracion_rec_activa", None)
    st.session_state.setdefault("imagenes_recon_por_id", {})

    ids_adq_validos = [e.get("id") for e in adquisiciones_validas]

    for exp in adquisiciones_validas:
        exp_id = exp.get("id")
        region_anat = _get_region_group_for_exp(exp)
        existentes = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
        if not existentes:
            st.session_state["reconstrucciones_por_exp"][exp_id] = [
                _crear_reconstruccion_base(exp, i, region_anat) for i in range(1, 7)
            ]
        elif len(existentes) < 6:
            for i in range(len(existentes) + 1, 7):
                existentes.append(_crear_reconstruccion_base(exp, i, region_anat))
            st.session_state["reconstrucciones_por_exp"][exp_id] = existentes[:6]

        _reindexar_reconstrucciones(exp_id)
        ids_rec = [r.get("id") for r in st.session_state["reconstrucciones_por_exp"][exp_id]]
        if st.session_state["recon_activa_por_exp"].get(exp_id) not in ids_rec:
            st.session_state["recon_activa_por_exp"][exp_id] = ids_rec[0]

    for exp_id_existente in list(st.session_state["reconstrucciones_por_exp"].keys()):
        if exp_id_existente not in ids_adq_validos:
            st.session_state["reconstrucciones_por_exp"].pop(exp_id_existente, None)
            st.session_state["recon_activa_por_exp"].pop(exp_id_existente, None)

    if st.session_state["exploracion_rec_activa"] not in ids_adq_validos:
        st.session_state["exploracion_rec_activa"] = ids_adq_validos[0] if ids_adq_validos else None

    col_nav, col_det = st.columns([0.63, 2.4], gap="large")

    with col_nav:
        _panel_header("🧩", "Adquisiciones")

        if not adquisiciones_validas:
            st.info("Primero agrega al menos una adquisición en la pestaña Adquisición.")
        else:
            for i, exp in enumerate(adquisiciones_validas):
                exp_id = exp.get("id")
                activa = st.session_state["exploracion_rec_activa"] == exp_id
                n_rec = len(st.session_state["reconstrucciones_por_exp"].get(exp_id, []))
                color = _color_exploracion(exp)
                nombre_base = exp.get("nombre") if exp.get("nombre") and exp.get("nombre") != "Seleccionar" else f"EXPLORACIÓN {exp.get('orden', i + 1)}"
                region = _get_region_label_for_exp(exp)
                nombre_visible = f"{nombre_base} {region}".strip()

                _mini_chip(
                    color,
                    nombre_visible,
                    f"{exp.get('tipo_exploracion', 'HELICOIDAL')} · {n_rec} reconstrucción(es)",
                )

                if st.button(
                    f"⚡ {nombre_visible}",
                    key=f"btn_rec_sel_{exp_id}",
                    use_container_width=True,
                    type="primary" if activa else "secondary",
                ):
                    st.session_state["exploracion_rec_activa"] = exp_id
                    st.rerun()

    with col_det:
        if not adquisiciones_validas or st.session_state.get("exploracion_rec_activa") is None:
            st.warning("No hay adquisiciones disponibles para reconstruir.")
            return st.session_state.get("reconstrucciones_por_exp", {})

        exp_activa = next((e for e in adquisiciones_validas if e.get("id") == st.session_state.get("exploracion_rec_activa")), None)

        if exp_activa is None:
            st.warning("No se pudo cargar la adquisición seleccionada.")
            return st.session_state.get("reconstrucciones_por_exp", {})

        exp_id = exp_activa.get("id")
        region_anat = _get_region_group_for_exp(exp_activa)
        recs_exp = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
        rec_activa_id = st.session_state["recon_activa_por_exp"].get(exp_id, recs_exp[0]["id"])
        rec_actual = next((r for r in recs_exp if r.get("id") == rec_activa_id), recs_exp[0])
        st.session_state["recon_activa_por_exp"][exp_id] = rec_actual.get("id")

        nombre_base_exp = exp_activa.get("nombre") if exp_activa.get("nombre") and exp_activa.get("nombre") != "Seleccionar" else f"EXPLORACIÓN {exp_activa.get('orden', 1)}"
        region_exp = _get_region_label_for_exp(exp_activa)
        nombre_exp = f"{nombre_base_exp} {region_exp}".strip().upper()

        _panel_header("🔄", f"Reconstrucciones de {nombre_exp}")
        st.caption("Selecciona una de las 6 reconstrucciones disponibles para trabajar en ella.")

        recs_visibles = recs_exp[:6]
        if recs_visibles:
            filas = [recs_visibles[:3], recs_visibles[3:6]]
            for fila in filas:
                cols_rec = st.columns(3, gap="medium")
                for col, rec_btn in zip(cols_rec, fila):
                    seleccionada = rec_btn.get("id") == rec_actual.get("id")
                    completa = _reconstruccion_completada(rec_btn, exp_id)
                    if seleccionada and completa:
                        icono = "🟢"
                    elif seleccionada:
                        icono = "🔘"
                    elif completa:
                        icono = "🟢"
                    else:
                        icono = "⚪"
                    nombre_btn = f"{icono}  {rec_btn.get('nombre', 'Reconstrucción')}"
                    with col:
                        if st.button(
                            nombre_btn,
                            key=f"btn_rec_item_{rec_btn['id']}",
                            use_container_width=True,
                            type="primary" if seleccionada else "secondary",
                        ):
                            st.session_state["recon_activa_por_exp"][exp_id] = rec_btn.get("id")
                            st.rerun()
                st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)
        st.caption("🟢 = reconstrucción con imagen y parámetros guardados · 🔘 = reconstrucción activa")
        st.markdown("---")

        if rec_actual is not None:
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

                region_anat_activa = _get_region_group_for_exp(exp_activa)
                refs_ini_r = REFS_INICIO.get(region_anat_activa, REFS_INICIO["CUERPO"])
                refs_fin_r = REFS_FIN.get(region_anat_activa, REFS_FIN["CUERPO"])

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

    return st.session_state.get("reconstrucciones_por_exp", {})
