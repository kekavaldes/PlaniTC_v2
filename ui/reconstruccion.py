import copy

import streamlit as st


def _inject_recon_css():
    st.markdown(
        """
        <style>
        /* Botones de reconstrucción en una sola línea */
        div[data-testid="stButton"] > button[kind] {
            white-space: nowrap !important;
        }

        /* Botones Agregar / Eliminar con 2 líneas y ancho según contenido */
        div[data-testid="stButton"] > button[kind][id*="add_rec"],
        div[data-testid="stButton"] > button[kind][id*="del_rec"] {
            white-space: pre-line !important;
            width: auto !important;
            min-width: fit-content !important;
            padding: 0.65rem 0.95rem !important;
            line-height: 1.2 !important;
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


def _color_exploracion(idx: int) -> str:
    palette = ["#00C2FF", "#8B5CF6", "#F59E0B", "#10B981", "#EF4444", "#EC4899", "#14B8A6", "#F97316"]
    return palette[idx % len(palette)]


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


def _reindexar_reconstrucciones(exp_id):
    lista_local = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
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
        nuevo["orden"] = nuevo.get("orden", idx)
        nuevo["tipo_exploracion"] = nuevo.get("tipo_exploracion") or nuevo.get("tipo_exp") or "HELICOIDAL"
        adquisiciones.append(nuevo)

    return adquisiciones


def render_reconstruccion():
    _inject_recon_css()
    topo_store = st.session_state.get("topograma_store", {})
    region_anat = topo_store.get("region_anat") or st.session_state.get("region_anat") or "CUERPO"
    adquisiciones_validas = _obtener_adquisiciones_validas()

    st.session_state.setdefault("reconstrucciones_por_exp", {})
    st.session_state.setdefault("recon_activa_por_exp", {})
    st.session_state.setdefault("exploracion_rec_activa", None)

    ids_adq_validos = [e.get("id") for e in adquisiciones_validas]

    for exp in adquisiciones_validas:
        exp_id = exp.get("id")
        if exp_id not in st.session_state["reconstrucciones_por_exp"] or not st.session_state["reconstrucciones_por_exp"][exp_id]:
            st.session_state["reconstrucciones_por_exp"][exp_id] = [_crear_reconstruccion_base(exp, 1, region_anat)]

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
                color = _color_exploracion(i)
                nombre_base = exp.get("nombre") if exp.get("nombre") and exp.get("nombre") != "Seleccionar" else f"EXPLORACIÓN {exp.get('orden', i + 1)}"
                region = (st.session_state.get("topograma_store", {}).get("examen") 
                          or st.session_state.get("topograma_store", {}).get("region_anat") 
                          or "")
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
        recs_exp = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
        rec_activa_id = st.session_state["recon_activa_por_exp"].get(exp_id, recs_exp[0]["id"])
        rec_actual = next((r for r in recs_exp if r.get("id") == rec_activa_id), recs_exp[0])
        st.session_state["recon_activa_por_exp"][exp_id] = rec_actual.get("id")

        nombre_base_exp = exp_activa.get("nombre") if exp_activa.get("nombre") and exp_activa.get("nombre") != "Seleccionar" else f"EXPLORACIÓN {exp_activa.get('orden', 1)}"
        region_exp = (st.session_state.get("topograma_store", {}).get("examen")
                      or st.session_state.get("topograma_store", {}).get("region_anat")
                      or "")
        nombre_exp = f"{nombre_base_exp} {region_exp}".strip().upper()

        _panel_header("🔄", f"Reconstrucciones de {nombre_exp}")
        st.caption("Puedes programar una o más reconstrucciones para esta adquisición.")

        for rec_btn in recs_exp[:6]:
            nombre_btn = f"🧱 {rec_btn.get('nombre', 'Reconstrucción')}"
            ancho_estimado = max(220, min(460, 110 + (len(nombre_btn) * 8)))

            st.markdown(
                f"""
                <style>
                div[data-testid="stButton"] button[kind][data-testid="stBaseButton-secondary"][id*="{rec_btn['id']}"],
                div[data-testid="stButton"] button[kind][data-testid="stBaseButton-primary"][id*="{rec_btn['id']}"] {{
                    width: {ancho_estimado}px !important;
                    min-width: {ancho_estimado}px !important;
                    max-width: {ancho_estimado}px !important;
                    white-space: nowrap !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                nombre_btn,
                key=f"btn_rec_item_{rec_btn['id']}",
                use_container_width=False,
                type="primary" if rec_btn.get("id") == rec_actual.get("id") else "secondary",
            ):
                st.session_state["recon_activa_por_exp"][exp_id] = rec_btn.get("id")
                st.rerun()

        c_add, c_del, c_spacer = st.columns([0.5, 0.5, 2.0], gap="small")

        with c_add:
            max_recons = len(recs_exp) >= 6
            if st.button(
                "➕ Agregar\nreconstrucción",
                key=f"add_rec_{exp_id}",
                use_container_width=False,
                disabled=max_recons,
            ):
                nuevo_num = len(recs_exp) + 1
                st.session_state["reconstrucciones_por_exp"][exp_id].append(
                    _crear_reconstruccion_base(exp_activa, nuevo_num, region_anat)
                )
                _reindexar_reconstrucciones(exp_id)
                st.session_state["recon_activa_por_exp"][exp_id] = f"{exp_id}_rec_{nuevo_num}"
                st.rerun()

        with c_del:
            deshabilitar = len(recs_exp) <= 1
            if st.button(
                "🗑 Eliminar\nreconstrucción",
                key=f"del_rec_{exp_id}",
                use_container_width=False,
                disabled=deshabilitar,
            ):
                st.session_state["reconstrucciones_por_exp"][exp_id] = [
                    r for r in st.session_state["reconstrucciones_por_exp"][exp_id]
                    if r.get("id") != rec_actual.get("id")
                ]
                _reindexar_reconstrucciones(exp_id)
                primer_id = st.session_state["reconstrucciones_por_exp"][exp_id][0]["id"]
                st.session_state["recon_activa_por_exp"][exp_id] = primer_id
                st.rerun()

        with c_spacer:
            st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

        st.markdown("---")
        col_r1, col_r2 = st.columns([1, 1], gap="large")

        with col_r1:
            _panel_header("🔧", "Parámetros de Reconstrucción")

            rec_actual["fase_recons"] = selectbox_con_placeholder("Fase a reconstruir", FASES_RECONS, key=f"fase_recons_{rec_actual['id']}", value=rec_actual.get("fase_recons"))
            rec_actual["tipo_recons"] = selectbox_con_placeholder("Tipo de reconstrucción", TIPOS_RECONS, key=f"tipo_recons_{rec_actual['id']}", value=rec_actual.get("tipo_recons"))

            if rec_actual["tipo_recons"] == "RECONS. ITERATIVA":
                rec_actual["algoritmo_iter"] = selectbox_con_placeholder("Algoritmo iterativo", ALGORITMOS_ITERATIVOS, key=f"alg_iter_{rec_actual['id']}", value=rec_actual.get("algoritmo_iter"))
                niveles_disp = NIVEL_ITERATIVO.get(rec_actual["algoritmo_iter"], [1])
                rec_actual["nivel_iter"] = selectbox_con_placeholder("Nivel / Porcentaje / Modo", niveles_disp, key=f"nivel_iter_{rec_actual['id']}", value=rec_actual.get("nivel_iter"))
            else:
                rec_actual["algoritmo_iter"] = "—"
                rec_actual["nivel_iter"] = "—"

            rec_actual["kernel_sel"] = selectbox_con_placeholder("Algoritmo (Kernel)", KERNELS, key=f"kernel_sel_{rec_actual['id']}", value=rec_actual.get("kernel_sel"))

            col_gr, col_inc = st.columns(2)
            with col_gr:
                rec_actual["grosor_recons"] = selectbox_con_placeholder("Grosor reconstrucción", GROSORES_RECONS, key=f"grosor_recons_{rec_actual['id']}", value=rec_actual.get("grosor_recons"))
            with col_inc:
                rec_actual["incremento"] = selectbox_con_placeholder("Incremento", INCREMENTOS_RECONS, key=f"incremento_{rec_actual['id']}", value=rec_actual.get("incremento"))

        with col_r2:
            _panel_header("🪟", "Ventana de Visualización")

            ventanas_disp = list(VENTANAS.keys())
            rec_actual["ventana_preset"] = selectbox_con_placeholder("Preset de ventana", ventanas_disp, key=f"preset_ventana_{rec_actual['id']}", value=rec_actual.get("ventana_preset"))

            if rec_actual["ventana_preset"] in VENTANAS:
                ww_default = VENTANAS[rec_actual["ventana_preset"]]["ww"]
                wl_default = VENTANAS[rec_actual["ventana_preset"]]["wl"]
            else:
                ww_default = 400
                wl_default = 40

            col_ww, col_wl = st.columns(2)
            with col_ww:
                rec_actual["ww_val"] = st.number_input("WW", min_value=1, max_value=5000, value=int(rec_actual.get("ww_val", ww_default)), step=1, key=f"ww_{rec_actual['id']}")
            with col_wl:
                rec_actual["wl_val"] = st.number_input("WL", min_value=-1500, max_value=3000, value=int(rec_actual.get("wl_val", wl_default)), step=1, key=f"wl_{rec_actual['id']}")

            rec_actual["dfov"] = selectbox_con_placeholder("DFOV", DFOV_OPCIONES, key=f"dfov_{rec_actual['id']}", value=rec_actual.get("dfov"))

            _panel_header("📍", "Rango de Reconstrucción")

            refs_ini_r = REFS_INICIO.get(region_anat, REFS_INICIO["CUERPO"])
            refs_fin_r = REFS_FIN.get(region_anat, REFS_FIN["CUERPO"])

            col_ini, col_fin = st.columns(2)
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
