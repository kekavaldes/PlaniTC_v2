import io
import zipfile
import unicodedata
from pathlib import Path

import pandas as pd
from PIL import Image
import streamlit as st


# =========================================================
# Configuración base
# =========================================================
st.set_page_config(page_title="PlaniTC_v2 - prueba topograma", layout="wide")

ROOT = Path(__file__).resolve().parent
EXCEL_PATH = ROOT / "data" / "excel" / "imagenes_topograma.xlsx"
ZIP_PATH = ROOT / "data" / "images" / "IMAGENES TOPOGRAMA.zip"


# =========================================================
# Utilidades
# =========================================================
def normalize_text(value) -> str:
    """Normaliza texto para comparar nombres y evitar problemas de tildes/espacios."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = " ".join(text.split())
    return text


@st.cache_data
def load_excel() -> pd.DataFrame:
    """Carga y limpia el Excel con las combinaciones de topograma."""
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"No se encontró el Excel en: {EXCEL_PATH}")

    df = pd.read_excel(EXCEL_PATH)
    df.columns = [str(col).strip() for col in df.columns]
    df = df.dropna(how="all").copy()

    required_cols = [
        "entrada del paciente",
        "Posición paciente",
        "Posición tubo",
        "examen",
        "nombre exacto de la imagen",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {missing}")

    # Columnas limpias para comparar
    df["entrada_norm"] = df["entrada del paciente"].apply(normalize_text)
    df["posicion_norm"] = df["Posición paciente"].apply(normalize_text)
    df["tubo_norm"] = df["Posición tubo"].apply(normalize_text)
    df["examen_norm"] = df["examen"].apply(normalize_text)
    df["imagen_norm"] = df["nombre exacto de la imagen"].apply(normalize_text)

    return df


@st.cache_resource
def load_images() -> dict[str, Image.Image]:
    """Carga imágenes desde ZIP e ignora basura de macOS."""
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"No se encontró el ZIP en: {ZIP_PATH}")

    images = {}

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        for member in zf.namelist():
            member_norm = member.replace("\\", "/")

            if "__MACOSX" in member_norm or member_norm.endswith("/"):
                continue

            lower = member_norm.lower()
            if not (lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")):
                continue

            file_name = member_norm.split("/")[-1]
            stem = Path(file_name).stem
            key = normalize_text(stem)

            with zf.open(member) as image_file:
                image = Image.open(io.BytesIO(image_file.read())).convert("RGB")
                images[key] = image

    return images


def get_sorted_options(df: pd.DataFrame, column: str) -> list[str]:
    values = (
        df[column]
        .dropna()
        .astype(str)
        .map(str.strip)
        .loc[lambda s: s != ""]
        .unique()
        .tolist()
    )
    return sorted(values)


def find_image_name(
    df: pd.DataFrame,
    entrada_paciente: str,
    posicion_paciente: str,
    posicion_tubo: str,
    examen: str,
) -> str | None:
    """Busca el nombre de imagen correspondiente a la combinación elegida."""
    filtro = (
        (df["entrada_norm"] == normalize_text(entrada_paciente))
        & (df["posicion_norm"] == normalize_text(posicion_paciente))
        & (df["tubo_norm"] == normalize_text(posicion_tubo))
        & (df["examen_norm"] == normalize_text(examen))
    )

    match = df.loc[filtro]
    if match.empty:
        return None

    return str(match.iloc[0]["imagen_norm"])


def get_image_by_name(images: dict[str, Image.Image], image_name: str | None) -> Image.Image | None:
    """Devuelve imagen exacta o una coincidencia cercana por normalización."""
    if not image_name:
        return None

    key = normalize_text(image_name)

    if key in images:
        return images[key]

    # Fallback suave: por si algún nombre tiene pequeñas diferencias
    for img_key, img in images.items():
        if img_key == key or img_key.startswith(key) or key.startswith(img_key):
            return img

    return None


# =========================================================
# Interfaz
# =========================================================
st.title("PlaniTC_v2")
st.subheader("Prueba mínima funcional: Excel + ZIP + topograma")

st.caption(
    "Esta versión está pensada para comprobar que la conexión entre tu Excel "
    "y el ZIP funciona correctamente antes de volver a montar el resto del simulador."
)

try:
    df = load_excel()
    images = load_images()
except Exception as exc:
    st.error(f"Error al cargar archivos: {exc}")
    st.stop()

with st.expander("Verificación de carga", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("Ruta Excel:", str(EXCEL_PATH))
        st.write("Ruta ZIP:", str(ZIP_PATH))
        st.write("Filas del Excel:", len(df))
        st.write("Imágenes cargadas:", len(images))
    with col_b:
        st.write("Columnas del Excel:", list(df.columns[:5]))
        st.write("Primeras claves de imágenes:", list(images.keys())[:10])

# Selectores basados en valores reales del Excel
c1, c2 = st.columns(2)

with c1:
    entrada_paciente = st.selectbox(
        "Entrada del paciente",
        ["Seleccionar"] + get_sorted_options(df, "entrada del paciente"),
        index=0,
    )

    posicion_paciente = st.selectbox(
        "Posición paciente",
        ["Seleccionar"] + get_sorted_options(df, "Posición paciente"),
        index=0,
    )

with c2:
    posicion_tubo = st.selectbox(
        "Posición del tubo",
        ["Seleccionar"] + get_sorted_options(df, "Posición tubo"),
        index=0,
    )

    examen = st.selectbox(
        "Examen",
        ["Seleccionar"] + get_sorted_options(df, "examen"),
        index=0,
    )

st.divider()

mostrar = all(
    value != "Seleccionar"
    for value in [entrada_paciente, posicion_paciente, posicion_tubo, examen]
)

if mostrar:
    image_name = find_image_name(
        df=df,
        entrada_paciente=entrada_paciente,
        posicion_paciente=posicion_paciente,
        posicion_tubo=posicion_tubo,
        examen=examen,
    )

    image = get_image_by_name(images, image_name)

    left, right = st.columns([1, 2])

    with left:
        st.markdown("### Selección actual")
        st.write(f"**Entrada:** {entrada_paciente}")
        st.write(f"**Posición paciente:** {posicion_paciente}")
        st.write(f"**Posición tubo:** {posicion_tubo}")
        st.write(f"**Examen:** {examen}")
        st.write(f"**Imagen esperada:** {image_name if image_name else 'No encontrada en Excel'}")

    with right:
        if image is not None:
            st.image(image, use_container_width=True)
        else:
            st.warning("No se encontró imagen para esta combinación.")

            with st.expander("Ayuda para depuración", expanded=True):
                st.write("Nombre de imagen obtenido desde Excel:", image_name)
                st.write("Primeras imágenes disponibles en ZIP:", list(images.keys())[:20])
else:
    st.info("Selecciona los cuatro parámetros para mostrar la imagen del topograma.")

st.divider()

with st.expander("Vista previa de la tabla", expanded=False):
    st.dataframe(df[[
        "entrada del paciente",
        "Posición paciente",
        "Posición tubo",
        "examen",
        "nombre exacto de la imagen",
    ]], use_container_width=True)
