import zipfile
from PIL import Image
import io
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent

def load_images_from_zip():
    zip_path = BASE_PATH / "images" / "IMAGENES TOPOGRAMA.zip"
    images_dict = {}

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file in zip_ref.namelist():

            # 🚫 ignorar basura de Mac
            if "__MACOSX" in file or file.endswith("/"):
                continue

            if file.endswith(".png") or file.endswith(".jpg"):

                # 👇 nombre limpio
                nombre_base = file.split("/")[-1]          # cabeza frontal.png
                nombre_sin_ext = nombre_base.replace(".png", "").replace(".jpg", "").strip().lower()

                with zip_ref.open(file) as image_file:
                    image = Image.open(io.BytesIO(image_file.read()))

                    images_dict[nombre_sin_ext] = image

    return images_dict
