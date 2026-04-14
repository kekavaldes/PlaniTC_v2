# PlaniTC refactor base

Esta es una base de refactor para separar tu app monolítica en módulos.

## Qué incluye
- `app.py`: archivo principal mínimo para navegar por pestañas.
- `constants.py`: opciones y listas fijas.
- `core/state.py`: inicialización y manejo central de `session_state`.
- `core/helpers.py`: widgets reutilizables.
- `core/models.py`: dataclasses opcionales para estructurar datos.
- `ui/topograma.py`: base modular para Topograma 1 y 2.
- `ui/adquisicion.py`: base modular de Adquisición con navegación lateral.
- `ui/ingreso.py`, `ui/reconstruccion.py`, `ui/inyectora.py`: placeholders integrables.
- `data/loaders.py`, `data/image_map.py`: base para mover loaders y mapeos.

## Importante
Esta base **no reemplaza todavía toda la funcionalidad** de tu archivo original. Está diseñada para que migres por partes sin cambiar toda la app de una vez.

## Orden sugerido de migración
1. Copiar `selectbox_con_placeholder` y helpers a `core/helpers.py`.
2. Mover creación/saneamiento de exploraciones a `core/state.py`.
3. Mover la UI de topograma a `ui/topograma.py`.
4. Mover la UI de adquisición a `ui/adquisicion.py`.
5. Mover `render_inyectora_svg()` a `ui/inyectora.py`.
6. Reemplazar portada embebida en base64 por archivo real en `assets/`.

## Cómo probar
Desde la carpeta del proyecto:

```bash
streamlit run app.py
```
