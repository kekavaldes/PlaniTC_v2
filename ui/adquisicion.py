
import uuid
import streamlit as st

from ui.topograma import render_topograma_panel

# ───────────────────────────────────────────────────────────────
# Catálogos
# ───────────────────────────────────────────────────────────────
NOMBRES_EXPLORACION = [
    "Seleccionar",
    "SIN CONTRASTE",
    "ARTERIAL",
    "ANGIOGRÁFICA",
    "BOLUS TEST",
    "BOLUS TRACKING",
    "VENOSA",
    "TARDÍA",
]

TIPOS_EXPLORACION = ["Seleccionar", "HELICOIDAL", "SECUENCIAL", "VOLUMETRICA"]

MODULACION_CORRIENTE = ["Seleccionar", "NO", "CARE DOSE", "AUTOMATICA"]
MAS_OPCIONES = ["Seleccionar", "20", "40", "50", "80", "100", "120", "150", "180", "200", "220", "250", "300"]
INDICE_RUIDO_OPCIONES = ["Seleccionar", "6", "8", "10", "12", "14", "16", "18", "20"]
KV_OPCIONES = ["Seleccionar", "80", "100", "110", "120", "130", "140"]
DOBLE_MUESTREO_OPCIONES = ["Seleccionar", "NO", "SI"]
CONFIG_DETECTORES = ["Seleccionar", "16 x 0,6", "16 x 1,2", "32 x 0,6", "32 x 1,2", "64 x 0,6", "64 x 1,2", "80 x 0,6", "80 x 1,2", "128 x 0,6"]
GROSOR_PROSPECTIVO_OPCIONES = ["Seleccionar", "0,6", "0,75", "1", "1,2", "1,5", "2", "3", "5"]
SFOV_OPCIONES = ["Seleccionar", "CABEZA", "CUELLO", "PEQUEÑO", "MEDIANO", "GRANDE", "MAXIMO"]
INSTRUCCION_VOZ_OPCIONES = ["Seleccionar", "NINGUNA", "INSPIRACIÓN", "ESPIRACIÓN", "NO TRAGAR", "VALSALVA", "NO RESPIRE"]
RETARDO_OPCIONES = ["Seleccionar", "0 sg", "2 sg", "3 sg", "4 sg", "5 sg", "6 sg", "8 sg", "10 sg", "12 sg", "15 sg", "20 sg", "25 sg", "30 sg"]
PITCH_OPCIONES = ["Seleccionar", "0,5", "0,6", "0,8", "1", "1,2", "1,5", "1,8"]
ROTACION_TUBO_OPCIONES = ["Seleccionar", "0,25 sg.", "0,28 sg.", "0,33 sg.", "0,35 sg.", "0,5 sg.", "0,75 sg.", "1 sg."]
PERIODO_TEST_BOLUS = ["Seleccionar", "0,9 sg", "1 sg", "1,5 sg", "2 sg"]
N_IMAGENES_TEST_BOLUS = ["Seleccionar", "10", "15", "20", "25", "30"]
POSICION_CORTE_TEST_BOLUS = ["Seleccionar", "BOTON AORTICO", "BAJO CARINA"]
UMBRAL_TRACKING = ["Seleccionar", "80 UH", "100 UH", "120 UH", "150 UH", "180 UH"]

REFS_INICIO = {
    "CABEZA":  ["VERTEX", "SOBRE SENO FRONTAL", "TECHO ORBITARIO", "CAE", "PISO ORBITARIO", "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR", "BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO"],
    "CUELLO":  ["TECHO ORBITARIO", "CAE", "ARCO AÓRTICO"],
    "EESS":    ["SOBRE ART. ACROMIOCLAV.", "BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO", "TERCIO PROXIMAL RADIO-CUBITO", "TERCIO PROXIMAL MTC", "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["CAE", "SOBRE BASE DE CRÁNEO", "C6-C7", "T1-T2", "T11-T12", "L1-L2", "L4-L5", "S1-S2"],
    "CUERPO":  ["SOBRE ÁPICES PULMONARES", "SOBRE CÚPULAS DIAF.", "ARCO AÓRTICO", "BAJO ANGULOS COSTOFR.", "L5-S1"],
    "EEII":    ["EIAS", "TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR", "TERCIO PROXIMAL TIBIA-PERONÉ", "TERCIO DISTAL TIBIA-PERONÉ", "BAJO CALCÁNEO", "HASTA COMPLETAR ORTEJOS"],
    "ANGIO":   ["SOBRE ÁPICES PULMONARES", "ARCO AÓRTICO", "SOBRE CÚPULAS DIAF.", "BAJO ANGULOS COSTOFR.", "L5-S1", "COMPLETAR FALANGE DISTAL"],
}
REFS_FIN = {
    "CABEZA":  ["BAJO BASE DE CRÁNEO", "MENTON", "ARCO AÓRTICO", "PISO ORBITARIO", "SOBRE REGION PETROSA", "ARCADA DENTARIA SUPERIOR"],
    "CUELLO":  ["CAE", "ARCO AÓRTICO", "MENTON"],
    "EESS":    ["BAJO ESCÁPULA", "TERCIO DISTAL HÚMERO", "TERCIO PROXIMAL MTC", "COMPLETAR FALANGES DISTALES"],
    "COLUMNA": ["SOBRE BASE DE CRÁNEO", "T1-T2", "T11-T12", "L4-L5", "S1-S2", "1 CM BAJO COXIS", "L5-S1"],
    "CUERPO":  ["SOBRE CÚPULAS DIAF.", "BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA"],
    "EEII":    ["TERCIO PROXIMAL FEMUR", "TERCIO DISTAL FEMUR", "TERCIO PROXIMAL TIBIA-PERONÉ", "BAJO CALCÁNEO", "HASTA COMPLETAR ORTEJOS", "COMPLETAR ORTEJOS"],
    "ANGIO":   ["BAJO ANGULOS COSTOFR.", "L5-S1", "BAJO PELVIS OSEA", "COMPLETAR FALANGE DISTAL", "COMPLETAR ORTEJOS"],
}


def _new_id() -> str:
    return f"exp_{uuid.uuid4().hex[:8]}"


def _crear_exploracion_base():
    return {
        "id": _new_id(),
        "tipo": "adquisicion",
        "tipo_item": "adquisicion",
        "nombre": "Seleccionar",
        "tipo_exploracion": "Seleccionar",
        "tipo_exp": "Seleccionar",
        "modulacion_corriente": "Seleccionar",
        "mod_corriente": "Seleccionar",
        "mas": "Seleccionar",
        "mas_val": "Seleccionar",
        "indice_ruido": "Seleccionar",
        "ind_ruido": "Seleccionar",
        "kv": "Seleccionar",
        "kvp": "Seleccionar",
        "doble_muestreo": "Seleccionar",
        "config_detectores": "Seleccionar",
        "conf_det": "Seleccionar",
        "cobertura": "—",
        "grosor_prospectivo": "Seleccionar",
        "grosor_prosp": "Seleccionar",
        "sfov": "Seleccionar",
        "instruccion_voz": "Seleccionar",
        "retardo": "Seleccionar",
        "pitch": "Seleccionar",
        "rotacion_tubo": "Seleccionar",
        "rot_tubo": "Seleccionar",
        "periodo": "Seleccionar",
        "n_imagenes": "Seleccionar",
        "posicion_corte": "Seleccionar",
        "umbral_tracking": "Seleccionar",
        "inicio_ref": "Seleccionar",
        "ini_mm": 0,
        "fin_ref": "Seleccionar",
        "fin_mm": 400,
        "observaciones": "",
    }


def _init_state():
    st.session_state.setdefault("exploraciones", [])
    st.session_state.setdefault("exp_activa", "topograma")
    if not st.session_state["exploraciones"]:
        st.session_state["exploraciones"] = [_crear_exploracion_base()]
    _sync_adq()


def _sync_adq():
    exps = st.session_state.get("exploraciones", [])
    for i, exp in enumerate(exps, start=1):
        exp.setdefault("id", _new_id())
        exp["tipo"] = "adquisicion"
        exp["tipo_item"] = "adquisicion"
        exp["tipo_exp"] = exp.get("tipo_exploracion", "Seleccionar")
        exp["mod_corriente"] = exp.get("modulacion_corriente", "Seleccionar")
        exp["mas_val"] = exp.get("mas", "Seleccionar")
        exp["ind_ruido"] = exp.get("indice_ruido", "Seleccionar")
        exp["kvp"] = exp.get("kv", "Seleccionar")
        exp["conf_det"] = exp.get("config_detectores", "Seleccionar")
        exp["grosor_prosp"] = exp.get("grosor_prospectivo", "Seleccionar")
        exp["rot_tubo"] = exp.get("rotacion_tubo", "Seleccionar")
        if not exp.get("nombre") or exp.get("nombre") == "Seleccionar":
            exp["titulo_sidebar"] = f"EXPLORACIÓN {i}"
        else:
            exp["titulo_sidebar"] = exp["nombre"]
    st.session_state["exploraciones_adq"] = [dict(e) for e in exps]


def _calcular_cobertura(config_detectores, doble_muestreo):
    if not config_detectores or config_detectores == "Seleccionar":
        return "—"
    texto = config_detectores.replace(" ", "").replace(",", ".")
    if "x" not in texto:
        return "—"
    try:
        filas_txt, colim_txt = texto.split("x")
        cobertura = float(filas_txt) * float(colim_txt)
        if doble_muestreo == "SI":
            cobertura *= 2
        return f"{int(cobertura) if cobertura.is_integer() else round(cobertura, 1)}"
    except Exception:
        return "—"


def _select(label, options, value, key, label_visibility="visible", disabled=False):
    vals = list(options)
    if value not in vals:
        value = vals[0]
    idx = vals.index(value)
    return st.selectbox(label, vals, index=idx, key=key, label_visibility=label_visibility, disabled=disabled)


def _number(label, value, key, min_value=0, max_value=4000, step=1, disabled=False):
    try:
        value = int(value)
    except Exception:
        value = min_value
    return st.number_input(label, min_value=min_value, max_value=max_value, step=step, value=value, key=key, label_visibility="collapsed", disabled=disabled)


def _text_disabled(label, value, key):
    st.text_input(label, value=str(value), disabled=True, key=key, label_visibility="collapsed")


def _name_visible(exp, idx):
    return exp.get("titulo_sidebar") or f"EXPLORACIÓN {idx+1}"


def _ajustar_tipo_segun_nombre(exp):
    nombre = exp.get("nombre", "Seleccionar")
    if nombre == "BOLUS TEST":
        exp["tipo_exploracion"] = "SECUENCIAL"
        exp["tipo_exp"] = "SECUENCIAL"
        exp["mas"] = "20"
        exp["kv"] = "100"
    elif nombre == "BOLUS TRACKING":
        exp["tipo_exploracion"] = "SECUENCIAL"
        exp["tipo_exp"] = "SECUENCIAL"
        exp["mas"] = "20"
        exp["kv"] = "100"


def _region_grupo(store):
    region = (store.get("region_anatomica") or store.get("region") or "").upper()
    examen = (store.get("examen") or "").upper()
    if "ANGIO" in region or examen.startswith("ATC"):
        return "ANGIO"
    for key in REFS_INICIO:
        if key in region:
            return key
    return "CUERPO"


def _render_sidebar():
    st.markdown("### 📋 Exploraciones")
    if st.button("📡 Topograma", key="btn_topograma_sidebar", use_container_width=True):
        st.session_state["exp_activa"] = "topograma"
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    for idx, exp in enumerate(st.session_state["exploraciones"]):
        if st.button(f"⚡ {_name_visible(exp, idx)}", key=f"btn_sidebar_exp_{exp['id']}", use_container_width=True):
            st.session_state["exp_activa"] = idx
    st.markdown(" ")
    if st.button("➕ Agregar exploración", key="btn_agregar_exploracion", use_container_width=True):
        st.session_state["exploraciones"].append(_crear_exploracion_base())
        st.session_state["exp_activa"] = len(st.session_state["exploraciones"]) - 1
        _sync_adq()
        st.rerun()
    if isinstance(st.session_state.get("exp_activa"), int):
        idx = st.session_state["exp_activa"]
        if 0 <= idx < len(st.session_state["exploraciones"]):
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("📄 Duplicar", key="btn_duplicar_exp", use_container_width=True):
                    copia = dict(st.session_state["exploraciones"][idx])
                    copia["id"] = _new_id()
                    st.session_state["exploraciones"].insert(idx + 1, copia)
                    st.session_state["exp_activa"] = idx + 1
                    _sync_adq()
                    st.rerun()
            with c2:
                if st.button("🗑️ Eliminar", key="btn_eliminar_exp", use_container_width=True):
                    if len(st.session_state["exploraciones"]) > 1:
                        st.session_state["exploraciones"].pop(idx)
                        st.session_state["exp_activa"] = min(idx, len(st.session_state["exploraciones"]) - 1)
                        _sync_adq()
                        st.rerun()


def _render_resumen_topograma(store):
    st.markdown("## 📡 Resumen de referencia")
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.info(f"**Examen**\n\n{store.get('examen') or '—'}")
    c2.info(f"**Topograma 1**\n\n{store.get('t1_posicion_paciente') or '—'}")
    c3.info(f"**Entrada 1**\n\n{store.get('t1_entrada_paciente') or '—'}")
    c4.info(f"**Tubo 1**\n\n{store.get('t1_posicion_tubo') or '—'}")


def _adq_pair(col, title, render_fn):
    with col:
        st.markdown(f"**{title}**")
        render_fn()


def _render_normales(exp, store):
    eid = exp["id"]
    row_title = st.columns([2.2, 1], gap="medium")
    with row_title[0]:
        exp["nombre"] = _select("Nombre de la exploración", NOMBRES_EXPLORACION, exp.get("nombre", "Seleccionar"), key=f"nombre_exp_{eid}")
    _ajustar_tipo_segun_nombre(exp)
    with row_title[1]:
        disabled_tipo = exp.get("nombre") in {"BOLUS TEST", "BOLUS TRACKING"}
        exp["tipo_exploracion"] = _select("Tipo exploración", TIPOS_EXPLORACION, exp.get("tipo_exploracion", "Seleccionar"), key=f"tipo_exp_{eid}", disabled=disabled_tipo)

    row1 = st.columns([0.55, 1, 1, 1, 1], gap="medium")
    with row1[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>☢️</div>", unsafe_allow_html=True)
    _adq_pair(row1[1], "MODULACIÓN CORRIENTE", lambda: exp.__setitem__("modulacion_corriente", _select("Modulación corriente", MODULACION_CORRIENTE, exp.get("modulacion_corriente", "Seleccionar"), key=f"modcorr_{eid}", label_visibility="collapsed")))
    _adq_pair(row1[2], "MAS", lambda: exp.__setitem__("mas", _select("mAs", MAS_OPCIONES, exp.get("mas", "Seleccionar"), key=f"mas_{eid}", label_visibility="collapsed", disabled=exp.get("nombre") in {"BOLUS TEST","BOLUS TRACKING"})))
    _adq_pair(row1[3], "INDICE DE RUIDO", lambda: exp.__setitem__("indice_ruido", _select("Indice ruido", INDICE_RUIDO_OPCIONES, exp.get("indice_ruido", "Seleccionar"), key=f"indruido_{eid}", label_visibility="collapsed")))
    _adq_pair(row1[4], "KV", lambda: exp.__setitem__("kv", _select("kV", KV_OPCIONES, exp.get("kv", "Seleccionar"), key=f"kv_{eid}", label_visibility="collapsed", disabled=exp.get("nombre") in {"BOLUS TEST","BOLUS TRACKING"})))

    helicoidal = exp.get("tipo_exploracion") == "HELICOIDAL"
    exp["cobertura"] = _calcular_cobertura(exp.get("config_detectores"), exp.get("doble_muestreo") if helicoidal else "NO")

    row2 = st.columns([0.55, 1.2, 1, 1, 1, 1, 1], gap="medium")
    with row2[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>⚙️</div>", unsafe_allow_html=True)
    _adq_pair(row2[1], "TIPO EXPLORACIÓN", lambda: exp.__setitem__("tipo_exploracion", _select("Tipo exploración fila 2", TIPOS_EXPLORACION, exp.get("tipo_exploracion", "Seleccionar"), key=f"tipo_exploracion_row_{eid}", label_visibility="collapsed", disabled=exp.get("nombre") in {"BOLUS TEST","BOLUS TRACKING"})))
    if helicoidal:
        _adq_pair(row2[2], "DOBLE MUESTREO", lambda: exp.__setitem__("doble_muestreo", _select("Doble muestreo", DOBLE_MUESTREO_OPCIONES, exp.get("doble_muestreo", "Seleccionar"), key=f"doble_{eid}", label_visibility="collapsed")))
    else:
        with row2[2]:
            st.markdown("**DOBLE MUESTREO**")
            _text_disabled("Doble muestreo no aplica", "No aplica", key=f"doble_na_{eid}")
            exp["doble_muestreo"] = "NO"
    _adq_pair(row2[3], "CONF. DETECCIÓN", lambda: exp.__setitem__("config_detectores", _select("Config detectores", CONFIG_DETECTORES, exp.get("config_detectores", "Seleccionar"), key=f"confdet_{eid}", label_visibility="collapsed")))
    with row2[4]:
        st.markdown("**COBERTURA**")
        _text_disabled("Cobertura", exp.get("cobertura", "—"), key=f"cobertura_{eid}")
    _adq_pair(row2[5], "GROSOR PROSP.", lambda: exp.__setitem__("grosor_prospectivo", _select("Grosor prospectivo", GROSOR_PROSPECTIVO_OPCIONES, exp.get("grosor_prospectivo", "Seleccionar"), key=f"gpros_{eid}", label_visibility="collapsed")))
    _adq_pair(row2[6], "SFOV", lambda: exp.__setitem__("sfov", _select("SFOV", SFOV_OPCIONES, exp.get("sfov", "Seleccionar"), key=f"sfov_{eid}", label_visibility="collapsed")))

    row3 = st.columns([0.55, 1, 1, 1, 1], gap="medium")
    with row3[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>🕒</div>", unsafe_allow_html=True)
    _adq_pair(row3[1], "INSTRUCCIÓN DE VOZ", lambda: exp.__setitem__("instruccion_voz", _select("Instrucción de voz", INSTRUCCION_VOZ_OPCIONES, exp.get("instruccion_voz", "Seleccionar"), key=f"voz_{eid}", label_visibility="collapsed")))
    _adq_pair(row3[2], "RETARDO", lambda: exp.__setitem__("retardo", _select("Retardo", RETARDO_OPCIONES, exp.get("retardo", "Seleccionar"), key=f"delay_{eid}", label_visibility="collapsed")))
    if helicoidal:
        _adq_pair(row3[3], "PITCH", lambda: exp.__setitem__("pitch", _select("Pitch", PITCH_OPCIONES, exp.get("pitch", "Seleccionar"), key=f"pitch_{eid}", label_visibility="collapsed")))
    else:
        with row3[3]:
            st.markdown("**PITCH**")
            _text_disabled("Pitch no aplica", "No aplica", key=f"pitch_na_{eid}")
            exp["pitch"] = "NO APLICA"
    _adq_pair(row3[4], "TPO ROTACION TUBO", lambda: exp.__setitem__("rotacion_tubo", _select("Rotación tubo", ROTACION_TUBO_OPCIONES, exp.get("rotacion_tubo", "Seleccionar"), key=f"rot_{eid}", label_visibility="collapsed")))

    grupo = _region_grupo(store)
    ini_opts = ["Seleccionar"] + REFS_INICIO.get(grupo, REFS_INICIO["CUERPO"])
    fin_opts = ["Seleccionar"] + REFS_FIN.get(grupo, REFS_FIN["CUERPO"])
    row4 = st.columns([0.55, 1.2, 1, 1.2, 1], gap="medium")
    with row4[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>📏</div>", unsafe_allow_html=True)
    _adq_pair(row4[1], "INICIO EXPLORACIÓN", lambda: exp.__setitem__("inicio_ref", _select("Inicio exploración", ini_opts, exp.get("inicio_ref", "Seleccionar"), key=f"iniref_{eid}", label_visibility="collapsed")))
    with row4[2]:
        st.markdown("**MM INICIO**")
        exp["ini_mm"] = _number("mm inicio", exp.get("ini_mm", 0), key=f"inimm_{eid}")
    _adq_pair(row4[3], "FIN EXPLORACIÓN", lambda: exp.__setitem__("fin_ref", _select("Fin exploración", fin_opts, exp.get("fin_ref", "Seleccionar"), key=f"finref_{eid}", label_visibility="collapsed")))
    with row4[4]:
        st.markdown("**MM FIN**")
        exp["fin_mm"] = _number("mm fin", exp.get("fin_mm", 400), key=f"finmm_{eid}")

def _render_bolus(exp):
    eid = exp["id"]
    row_title = st.columns([2.2, 1], gap="medium")
    with row_title[0]:
        exp["nombre"] = _select("Nombre de la exploración", NOMBRES_EXPLORACION, exp.get("nombre", "Seleccionar"), key=f"nombre_exp_{eid}")
    _ajustar_tipo_segun_nombre(exp)
    with row_title[1]:
        exp["tipo_exploracion"] = _select("Tipo exploración", TIPOS_EXPLORACION, exp.get("tipo_exploracion", "SECUENCIAL"), key=f"tipo_exp_{eid}", disabled=True)

    row1 = st.columns([0.55, 1, 1, 1, 1], gap="medium")
    with row1[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>☢️</div>", unsafe_allow_html=True)
    _adq_pair(row1[1], "MODULACIÓN CORRIENTE", lambda: exp.__setitem__("modulacion_corriente", _select("Modulación corriente", MODULACION_CORRIENTE, exp.get("modulacion_corriente", "NO"), key=f"modcorr_{eid}", label_visibility="collapsed")))
    exp["mas"] = "20"
    exp["kv"] = "100"
    with row1[2]:
        st.markdown("**MAS**")
        _text_disabled("mas fijo", "20", key=f"mas_fijo_{eid}")
    _adq_pair(row1[3], "INDICE DE RUIDO", lambda: exp.__setitem__("indice_ruido", _select("Indice ruido", INDICE_RUIDO_OPCIONES, exp.get("indice_ruido", "Seleccionar"), key=f"indruido_{eid}", label_visibility="collapsed")))
    with row1[4]:
        st.markdown("**KV**")
        _text_disabled("kv fijo", "100", key=f"kv_fijo_{eid}")

    row2 = st.columns([0.55, 1, 1, 1, 1], gap="medium")
    with row2[0]:
        st.markdown("<div style='font-size:2rem; margin-top:1.6rem; text-align:center;'>🎯</div>", unsafe_allow_html=True)
    _adq_pair(row2[1], "PERIODO", lambda: exp.__setitem__("periodo", _select("Periodo", PERIODO_TEST_BOLUS, exp.get("periodo", "Seleccionar"), key=f"periodo_{eid}", label_visibility="collapsed")))
    _adq_pair(row2[2], "N° IMÁGENES", lambda: exp.__setitem__("n_imagenes", _select("N imágenes", N_IMAGENES_TEST_BOLUS, exp.get("n_imagenes", "Seleccionar"), key=f"nimg_{eid}", label_visibility="collapsed")))
    _adq_pair(row2[3], "POSICIÓN DE CORTE", lambda: exp.__setitem__("posicion_corte", _select("Posición corte", POSICION_CORTE_TEST_BOLUS, exp.get("posicion_corte", "Seleccionar"), key=f"poscorte_{eid}", label_visibility="collapsed")))
    if exp.get("nombre") == "BOLUS TRACKING":
        _adq_pair(row2[4], "UMBRAL DISPARO", lambda: exp.__setitem__("umbral_tracking", _select("Umbral tracking", UMBRAL_TRACKING, exp.get("umbral_tracking", "Seleccionar"), key=f"uth_{eid}", label_visibility="collapsed")))
    else:
        with row2[4]:
            st.markdown("**UMBRAL DISPARO**")
            _text_disabled("umbral na", "No aplica", key=f"uth_na_{eid}")

def _render_warnings(exp):
    msgs = []
    if exp.get("nombre") == "Seleccionar":
        msgs.append("⚠️ Falta seleccionar el nombre de la exploración.")
    if exp.get("config_detectores") == "Seleccionar" and exp.get("nombre") not in {"BOLUS TEST", "BOLUS TRACKING"}:
        msgs.append("⚠️ Falta seleccionar configuración de detectores.")
    if exp.get("nombre") not in {"BOLUS TEST", "BOLUS TRACKING"} and exp.get("instruccion_voz") == "Seleccionar":
        msgs.append("⚠️ Falta definir la instrucción de voz.")
    if exp.get("nombre") in {"BOLUS TEST", "BOLUS TRACKING"} and exp.get("posicion_corte") == "Seleccionar":
        msgs.append("⚠️ Falta definir la posición de corte.")
    for m in msgs:
        st.warning(m)
    if not msgs:
        st.success("Configuración lista para continuar.")

def render_adquisicion():
    _init_state()
    col_sidebar, col_main = st.columns([1.05, 4.8], gap="large")
    with col_sidebar:
        _render_sidebar()
    with col_main:
        activa = st.session_state.get("exp_activa", "topograma")
        if activa == "topograma":
            render_topograma_panel()
            return

        idx = int(activa)
        exp = st.session_state["exploraciones"][idx]
        store = st.session_state.get("topograma_store", {})

        _render_resumen_topograma(store)
        titulo = exp.get("nombre")
        if not titulo or titulo == "Seleccionar":
            titulo = f"EXPLORACIÓN {idx+1}"
        st.markdown(f"## ⚙️ {titulo}")

        if exp.get("nombre") in {"BOLUS TEST", "BOLUS TRACKING"}:
            _render_bolus(exp)
        else:
            _render_normales(exp, store)

        exp["observaciones"] = st.text_area("Observaciones", value=exp.get("observaciones", ""), key=f"obs_{exp['id']}", height=100)
        _sync_adq()
        _render_warnings(exp)
