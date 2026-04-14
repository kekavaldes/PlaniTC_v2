import streamlit as st


def crear_exploracion_topograma() -> dict:
    return {
        "id": "topograma_panel",
        "orden": 0,
        "tipo": "topograma",
        "nombre": "Topograma",
    }


def crear_exploracion_adq(numero: int) -> dict:
    uid = f"exp_{st.session_state['exploracion_adq_counter']}"
    st.session_state["exploracion_adq_counter"] += 1
    return {
        "id": uid,
        "orden": numero,
        "tipo": "adquisicion",
        "nombre": "SIN CONTRASTE",
        "tipo_exp": None,
        "doble_muestreo": None,
        "voz_adq": None,
        "mod_corriente": None,
        "kvp": None,
        "mas_val": None,
        "ind_cal": None,
        "ind_ruido": None,
        "rango_ma": None,
        "conf_det": None,
        "sfov": None,
        "grosor_prosp": None,
        "pitch": None,
        "rot_tubo": None,
        "retardo": None,
        "inicio_ref": None,
        "ini_mm": 0,
        "fin_ref": None,
        "fin_mm": 400,
        "topo1_inicio_ref": None,
        "topo1_ini_mm": 0,
        "topo1_fin_ref": None,
        "topo1_fin_mm": 400,
        "topo2_inicio_ref": None,
        "topo2_ini_mm": 0,
        "topo2_fin_ref": None,
        "topo2_fin_mm": 400,
        "periodo_bolus": "1 sg",
        "n_imagenes_bolus": 15,
        "posicion_corte": "BOTON AORTICO",
        "umbral_disparo": "",
        "kvp_bolus": 100,
        "mas_bolus": 20,
        "store": {},
    }


def reindexar_exploraciones_adq() -> None:
    contador = 1
    for exp in st.session_state["exploraciones_adq"]:
        if exp.get("tipo") == "adquisicion":
            exp["orden"] = contador
            contador += 1


def sanear_exploraciones_adq() -> None:
    originales = st.session_state.get("exploraciones_adq", [])
    lista = []
    ids_vistos = set()
    tiene_topograma = False

    for exp in originales:
        tipo = exp.get("tipo")
        if tipo == "topograma":
            if not tiene_topograma:
                lista.append(crear_exploracion_topograma())
                ids_vistos.add("topograma_panel")
                tiene_topograma = True
            continue

        if tipo != "adquisicion":
            continue

        nuevo = dict(exp)
        exp_id = nuevo.get("id")
        if (not exp_id) or (exp_id in ids_vistos) or (exp_id == "topograma_panel"):
            exp_id = f"exp_{st.session_state['exploracion_adq_counter']}"
            st.session_state["exploracion_adq_counter"] += 1
        nuevo["id"] = exp_id
        nuevo["tipo"] = "adquisicion"
        ids_vistos.add(exp_id)
        lista.append(nuevo)

    if not tiene_topograma:
        lista.insert(0, crear_exploracion_topograma())

    st.session_state["exploraciones_adq"] = lista
    reindexar_exploraciones_adq()


def init_state() -> None:
    defaults = {
        "exploracion_adq_counter": 1,
        "exploraciones_adq": [crear_exploracion_topograma()],
        "exploracion_adq_activa": "topograma_panel",
        "topograma_store": {},
        "topograma_iniciado": False,
        "topograma2_iniciado": False,
        "_ultimo_exp_cargado": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    sanear_exploraciones_adq()


def get_exploracion_activa() -> dict | None:
    exp_id = st.session_state.get("exploracion_adq_activa")
    return next(
        (e for e in st.session_state["exploraciones_adq"] if e.get("id") == exp_id),
        None,
    )


def agregar_exploracion() -> None:
    existentes = [
        e for e in st.session_state["exploraciones_adq"] if e.get("tipo") == "adquisicion"
    ]
    numero = len(existentes) + 1
    nueva = crear_exploracion_adq(numero)
    st.session_state["exploraciones_adq"].append(nueva)
    st.session_state["exploracion_adq_activa"] = nueva["id"]


def eliminar_exploracion(exp_id: str) -> None:
    if exp_id == "topograma_panel":
        return
    st.session_state["exploraciones_adq"] = [
        e for e in st.session_state["exploraciones_adq"] if e.get("id") != exp_id
    ]
    reindexar_exploraciones_adq()
    st.session_state["exploracion_adq_activa"] = "topograma_panel"
