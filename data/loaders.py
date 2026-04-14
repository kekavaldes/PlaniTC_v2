from __future__ import annotations

import io
import os
import re
import zipfile
import unicodedata
from difflib import get_close_matches
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from PIL import Image

BASE_PATH = Path(__file__).resolve().parent
DEFAULT_EXCEL_PATH = BASE_PATH / "excel" / "imagenes_topograma.xlsx"
DEFAULT_ZIP_PATH = BASE_PATH / "images" / "IMAGENES TOPOGRAMA.zip"

REQUIRED_COLUMNS = [
    "entrada del paciente",
    "Posición paciente",
    "Posición tubo",
    "examen",
    "nombre exacto de la imagen",
]


def _fix_mojibake(text: str) -> str:
    """Corrige algunos problemas frecuentes de codificación."""
    replacements = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "╠â": "ñ",   # caso detectado en tu ZIP: mun╠âeca -> muñeca
        "╠ü": "á",
        "╠®": "é",
        "╠¡": "í",
        "╠│": "ó",
        "╠║": "ú",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def normalize_text(value: object) -> str:
    """Normaliza textos para comparaciones robustas."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    text = str(value).strip().lower()
    text = _fix_mojibake(text)
    text = re.sub(r"\.(png|jpg|jpeg|webp)$", "", text, flags=re.IGNORECASE)

    # Mantener palabras, pero comparar sin tildes ni símbolos raros.
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = " ".join(text.split())
    return text


def load_excel_config(excel_path: Optional[str | Path] = None) -> pd.DataFrame:
    """Carga y limpia el Excel con la tabla de topogramas."""
    path = Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH
    df = pd.read_excel(path)

    # Eliminar filas completamente vacías
    df = df.dropna(how="all").copy()

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Faltan columnas requeridas en Excel: {missing_cols}")

    # Conservar solo filas útiles
    df = df[df["nombre exacto de la imagen"].notna()].copy()

    # Columnas normalizadas para búsqueda
    df["_entrada_norm"] = df["entrada del paciente"].map(normalize_text)
    df["_posicion_norm"] = df["Posición paciente"].map(normalize_text)
    df["_tubo_norm"] = df["Posición tubo"].map(normalize_text)
    df["_examen_norm"] = df["examen"].map(normalize_text)
    df["_imagen_norm"] = df["nombre exacto de la imagen"].map(normalize_text)

    return df.reset_index(drop=True)


def load_topogram_images(zip_path: Optional[str | Path] = None) -> Dict[str, Image.Image]:
    """
    Carga imágenes desde ZIP y las indexa por nombre normalizado.
    Ignora carpetas y archivos basura de macOS.
    """
    path = Path(zip_path) if zip_path else DEFAULT_ZIP_PATH
    images: Dict[str, Image.Image] = {}

    with zipfile.ZipFile(path, "r") as zip_ref:
        for member in zip_ref.namelist():
            if "__MACOSX" in member or member.endswith("/"):
                continue

            ext = os.path.splitext(member)[1].lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue

            base_name = os.path.basename(member)
            image_key = normalize_text(base_name)

            with zip_ref.open(member) as image_file:
                image = Image.open(io.BytesIO(image_file.read())).copy()

            images[image_key] = image

    return images


def build_image_aliases(images: Dict[str, Image.Image]) -> Dict[str, Image.Image]:
    """
    Genera aliases extra para cubrir pequeños problemas de nombres.
    """
    aliases: Dict[str, Image.Image] = dict(images)

    manual_aliases = {
        "muneca frontal": "muneca frontal",
        "muneca lateral": "muneca lateral",
    }

    for alias, target in manual_aliases.items():
        if target in images:
            aliases[alias] = images[target]

    return aliases


def find_topogram_row(
    df: pd.DataFrame,
    entrada_paciente: str,
    posicion_paciente: str,
    posicion_tubo: str,
    examen: str,
) -> Optional[pd.Series]:
    """Busca la fila que corresponde a la combinación seleccionada."""
    filtro = (
        (df["_entrada_norm"] == normalize_text(entrada_paciente))
        & (df["_posicion_norm"] == normalize_text(posicion_paciente))
        & (df["_tubo_norm"] == normalize_text(posicion_tubo))
        & (df["_examen_norm"] == normalize_text(examen))
    )

    matches = df.loc[filtro]
    if matches.empty:
        return None

    return matches.iloc[0]


def get_topogram_image_name(
    df: pd.DataFrame,
    entrada_paciente: str,
    posicion_paciente: str,
    posicion_tubo: str,
    examen: str,
) -> Optional[str]:
    """Obtiene el nombre lógico de imagen desde el Excel."""
    row = find_topogram_row(
        df=df,
        entrada_paciente=entrada_paciente,
        posicion_paciente=posicion_paciente,
        posicion_tubo=posicion_tubo,
        examen=examen,
    )
    if row is None:
        return None

    return normalize_text(row["nombre exacto de la imagen"])


def get_topogram_image(
    df: pd.DataFrame,
    images: Dict[str, Image.Image],
    entrada_paciente: str,
    posicion_paciente: str,
    posicion_tubo: str,
    examen: str,
) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Devuelve la imagen PIL y la clave encontrada.
    Incluye fallback por similitud si no hay match exacto.
    """
    image_name = get_topogram_image_name(
        df=df,
        entrada_paciente=entrada_paciente,
        posicion_paciente=posicion_paciente,
        posicion_tubo=posicion_tubo,
        examen=examen,
    )

    if not image_name:
        return None, None

    image_map = build_image_aliases(images)

    if image_name in image_map:
        return image_map[image_name], image_name

    close = get_close_matches(image_name, image_map.keys(), n=1, cutoff=0.85)
    if close:
        return image_map[close[0]], close[0]

    return None, image_name
