import streamlit as st


def selectbox_con_placeholder(
    label,
    options,
    value=None,
    key=None,
    placeholder_text="Seleccionar",
    format_func=None,
    **kwargs,
):
    opciones = list(options)
    opciones_sin_placeholder = [
        opt
        for opt in opciones
        if not ((opt is None) or (isinstance(opt, str) and opt == placeholder_text))
    ]
    opciones_finales = [None] + opciones_sin_placeholder

    if value in opciones_finales and value is not None:
        indice = opciones_finales.index(value)
    else:
        indice = 0

    if format_func is None:
        format_func = (
            lambda x: placeholder_text
            if (x is None or x == placeholder_text)
            else str(x)
        )

    return st.selectbox(
        label,
        opciones_finales,
        index=indice,
        key=key,
        format_func=format_func,
        placeholder=placeholder_text,
        **kwargs,
    )


def is_bolus(nombre: str | None) -> bool:
    return str(nombre or "").upper() in ["BOLUS TEST", "BOLUS TRACKING"]
