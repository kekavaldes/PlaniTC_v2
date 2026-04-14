import pandas as pd
import zipfile
from PIL import Image
import io
import os

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
EXCEL_PATH = os.path.join(BASE_PATH, "assets", "imagenes_topograma.xlsx")
ZIP_PATH = os.path.join(BASE_PATH, "assets", "IMAGENES TOPOGRAMA.zip")


def cargar_excel():
    try:
        df = pd.read_excel(EXCEL_PATH)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return None


def buscar_nombre_imagen(df, examen, posicion, entrada, pos_tubo):
    try:
        fila = df[
            (df["examen"] == examen)
            & (df["posicion"] == posicion)
            & (df["entrada"] == entrada)
            & (df["pos_tubo"] == pos_tubo)
        ]

        if fila.empty:
            return None

        return fila.iloc[0]["imagen"]
    except:
        return None


def obtener_imagen_desde_zip(nombre_imagen):
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            with z.open(nombre_imagen) as f:
                return Image.open(io.BytesIO(f.read()))
    except:
        return None


def obtener_imagen_topograma_adquirido(examen, posicion, entrada, pos_tubo):
    df = cargar_excel()

    if df is None:
        return None, "Error cargando Excel"

    nombre = buscar_nombre_imagen(df, examen, posicion, entrada, pos_tubo)

    if not nombre:
        return None, "No se encontró combinación en Excel"

    img = obtener_imagen_desde_zip(nombre)

    if img is None:
        return None, f"No se pudo abrir imagen: {nombre}"

    return img, None
