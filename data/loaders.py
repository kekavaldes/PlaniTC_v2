import os
import io
import zipfile
import pandas as pd
from PIL import Image

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
EXCEL_PATH = os.path.join(BASE_PATH, "assets", "imagenes_topograma.xlsx")
ZIP_PATH = os.path.join(BASE_PATH, "assets", "IMAGENES TOPOGRAMA.zip")


def cargar_excel():
    try:
        df = pd.read_excel(EXCEL_PATH)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.dropna(how="all").copy()

        rename_map = {
            "entrada del paciente": "entrada",
            "posición paciente": "posicion",
            "posicion paciente": "posicion",
            "posición tubo": "pos_tubo",
            "posicion tubo": "pos_tubo",
            "nombre exacto de la imagen": "imagen",
        }
        df = df.rename(columns=rename_map)

        # Limpieza básica de texto
        for col in ["entrada", "posicion", "pos_tubo", "examen", "imagen"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        return df
    except Exception:
        return None


def buscar_nombre_imagen(df, examen, posicion, entrada, pos_tubo):
    try:
        if df is None:
            return None

        examen = str(examen).strip()
        posicion = str(posicion).strip()
        entrada = str(entrada).strip()
        pos_tubo = str(pos_tubo).strip()

        fila = df[
            (df["examen"] == examen)
            & (df["posicion"] == posicion)
            & (df["entrada"] == entrada)
            & (df["pos_tubo"] == pos_tubo)
        ]

        if fila.empty:
            return None

        nombre = str(fila.iloc[0]["imagen"]).strip()
        if not nombre:
            return None

        if not nombre.lower().endswith(".png"):
            nombre += ".png"

        return nombre
    except Exception:
        return None


def obtener_imagen_desde_zip(nombre_imagen):
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            candidatos = [
                nombre_imagen,
                f"IMAGENES TOPOGRAMA/{nombre_imagen}",
            ]

            # búsqueda flexible por si cambia mayúsculas/minúsculas
            mapa = {n.lower(): n for n in z.namelist()}

            for cand in candidatos:
                real_name = mapa.get(cand.lower())
                if real_name:
                    with z.open(real_name) as f:
                        img = Image.open(io.BytesIO(f.read()))
                        return img.copy()

        return None
    except Exception:
        return None


def obtener_imagen_topograma_adquirido(examen, posicion, entrada, pos_tubo):
    df = cargar_excel()

    if df is None:
        return None, "Error cargando Excel"

    nombre = buscar_nombre_imagen(df, examen, posicion, entrada, pos_tubo)

    if not nombre:
        return None, (
            f"No se encontró combinación en Excel para: "
            f"examen={examen}, posicion={posicion}, entrada={entrada}, pos_tubo={pos_tubo}"
        )

    img = obtener_imagen_desde_zip(nombre)

    if img is None:
        return None, f"No se pudo abrir imagen: {nombre}"

    return img, None
