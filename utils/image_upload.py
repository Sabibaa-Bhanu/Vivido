import io
import os
import uuid
from datetime import datetime

from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_SIZE_MB = 10

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_UPLOAD_DIR = os.path.join(BASE_DIR, "..", "data", "temp_uploads")


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def ensure_temp_upload_dir() -> str:
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    return TEMP_UPLOAD_DIR


def remove_temp_file(file_path: str | None) -> None:
    if not file_path:
        return
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        # Best-effort cleanup only.
        pass


def process_and_save_upload(uploaded_file, previous_path: str | None = None) -> dict:
    if uploaded_file is None:
        return {"success": False, "message": "No file uploaded."}

    file_name = (uploaded_file.name or "").strip()
    extension = os.path.splitext(file_name)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return {
            "success": False,
            "message": "Unsupported file format. Use JPG, JPEG, PNG, or BMP.",
        }

    file_bytes = uploaded_file.getvalue()
    file_size = len(file_bytes)
    if file_size == 0:
        return {"success": False, "message": "Uploaded file is empty."}
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        return {
            "success": False,
            "message": f"File exceeds {MAX_UPLOAD_SIZE_MB} MB limit.",
        }

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        return {
            "success": False,
            "message": "The uploaded file is corrupted or not a valid image.",
        }

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            width, height = image.size
            image_format = (image.format or extension.replace(".", "")).upper()
    except (UnidentifiedImageError, OSError):
        return {
            "success": False,
            "message": "Unable to read image metadata from the uploaded file.",
        }

    upload_dir = ensure_temp_upload_dir()
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}{extension}"
    save_path = os.path.join(upload_dir, unique_name)

    try:
        with open(save_path, "wb") as temp_file:
            temp_file.write(file_bytes)
    except OSError as exc:
        return {"success": False, "message": f"Failed to save uploaded image: {exc}"}

    remove_temp_file(previous_path)

    return {
        "success": True,
        "file_path": save_path,
        "metadata": {
            "filename": unique_name,
            "original_filename": file_name,
            "size_bytes": file_size,
            "size_human": format_file_size(file_size),
            "format": image_format,
            "width": width,
            "height": height,
        },
    }
