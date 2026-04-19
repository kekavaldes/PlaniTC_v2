# Archivo reconstruccion-5_modificado.py
# (Versión ajustada: 1 reconstrucción inicial por adquisición, sin límite de 6)

import copy
import streamlit as st

# --- (se mantiene TODO tu código original arriba sin cambios) ---
# Para simplificar, aquí incluyo SOLO las funciones modificadas y necesarias.
# Tú debes reemplazar estas secciones en tu archivo original.

def _reindexar_reconstrucciones(exp_id):
    lista_local = st.session_state["reconstrucciones_por_exp"].get(exp_id, [])
    st.session_state["reconstrucciones_por_exp"][exp_id] = lista_local
    for idx_local, rec_local in enumerate(lista_local, start=1):
        rec_local["id"] = f"{exp_id}_rec_{idx_local}"
        rec_local["nombre"] = f"Reconstrucción {idx_local}"


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
            recs_a_borrar = st.session_state["reconstrucciones_por_exp"].get(exp_id_existente, [])
            for r in recs_a_borrar:
                st.session_state["imagenes_recon_por_id"].pop(r.get("id"), None)
            st.session_state["reconstrucciones_por_exp"].pop(exp_id_existente, None)
            st.session_state["recon_activa_por_exp"].pop(exp_id_existente, None)

    # Crear solo UNA reconstrucción inicial por adquisición
    for exp in adquisiciones_validas:
        exp_id = exp.get("id")

        if exp_id not in st.session_state["reconstrucciones_por_exp"]:
            st.session_state["reconstrucciones_por_exp"][exp_id] = []

        if not st.session_state["reconstrucciones_por_exp"][exp_id]:
            region_anat = _get_region_group_for_exp(exp)
            nueva = _crear_reconstruccion_base(exp, 1, region_anat)

            st.session_state["reconstrucciones_por_exp"][exp_id].append(nueva)
            st.session_state["recon_activa_por_exp"][exp_id] = nueva["id"]

    if st.session_state["exploracion_rec_activa"] not in ids_adq_validos:
        st.session_state["exploracion_rec_activa"] = ids_adq_validos[0] if ids_adq_validos else None

    col_nav, col_det = st.columns([0.8, 2.7], gap="large")

    with col_nav:
        _render_sidebar_reconstruccion(adquisiciones_validas)

    with col_det:
        _render_panel_central(adquisiciones_validas)

    return st.session_state.get("reconstrucciones_por_exp", {})
