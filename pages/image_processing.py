import base64
import io
import os
import uuid

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from streamlit.components.v1 import html as components_html

from utils.cartoonization import (
    CartoonParams,
    create_classic_cartoon,
    compare_original_and_cartoon,
    create_base_cartoon_effect,
    documented_style_settings,
    recommended_style_params,
)
from utils.edge_detection import EdgeParams, detect_cartoon_edges, recommended_params
from utils.image_upload import MAX_UPLOAD_SIZE_MB, process_and_save_upload, remove_temp_file


st.set_page_config(page_title="Image Processing - Vivido",page_icon="assets/logo/vivido_logo2.jpeg", layout="wide")

if (
    not st.session_state.get("logged_in")
    and st.session_state.get("user_id")
    and st.session_state.get("current_user")
):
    st.session_state["logged_in"] = True

if not st.session_state.get("logged_in"):
    st.session_state["redirect_after_login"] = "pages/image_processing.py"
    st.switch_page("pages/login.py")

if "uploaded_image_path" not in st.session_state:
    st.session_state["uploaded_image_path"] = ""
if "uploaded_image_metadata" not in st.session_state:
    st.session_state["uploaded_image_metadata"] = {}
if "uploaded_image_signature" not in st.session_state:
    st.session_state["uploaded_image_signature"] = ""
if "upload_widget_nonce" not in st.session_state:
    st.session_state["upload_widget_nonce"] = 0
if "uploaded_image_confirmed" not in st.session_state:
    st.session_state["uploaded_image_confirmed"] = False
if "style_lab_processed_png" not in st.session_state:
    st.session_state["style_lab_processed_png"] = b""
if "style_lab_preview_png" not in st.session_state:
    st.session_state["style_lab_preview_png"] = b""
if "style_lab_style_name" not in st.session_state:
    st.session_state["style_lab_style_name"] = ""

# --- Sidebar ---
username = st.session_state.get("current_username", "User")

with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 20px 0;">
        <div style="color: #7c3aed; font-size: 1.3rem; font-weight: 700; letter-spacing: 0.02em;">Vivido</div>
    </div>
    """, unsafe_allow_html=True)

    st.page_link("pages/image_processing.py", label="🎨 Image Processing", icon=None)
    st.page_link("pages/ai_styles.py", label="🤖 AI Styles", icon=None)
    st.page_link("pages/dashboard.py", label="📊 Dashboard", icon=None)

    st.markdown("---")

    st.markdown(f"""
    <div style="
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 12px;
    ">
        <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;">Total Processed</div>
        <div style="color: #f1f5f9; font-size: 1.4rem; font-weight: 700;">0</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔓 Logout", key="sidebar_logout_btn", width='stretch'):
        from backend.user_management import revoke_remember_token
        remember_token = st.session_state.get("remember_token", "")
        if remember_token:
            revoke_remember_token(remember_token)
        st.session_state.clear()
        st.session_state["just_logged_out"] = True
        st.switch_page("pages/login.py")


def _get_mime_type(file_name: str) -> str:
    extension = os.path.splitext((file_name or "").lower())[1]
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
    }
    return mime_map.get(extension, "application/octet-stream")


def _to_data_uri(pil_image: Image.Image) -> str:
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _build_processed_preview(source_image: Image.Image, mode: str, intensity: int) -> Image.Image:
    if mode == "Original":
        return source_image.copy()

    if mode == "Grayscale":
        return ImageOps.grayscale(source_image).convert("RGB")

    if mode == "Auto Contrast":
        return ImageOps.autocontrast(source_image)

    if mode == "Sharpen":
        factor = max(1.0, intensity / 100)
        return ImageEnhance.Sharpness(source_image).enhance(factor)

    if mode == "Contrast Boost":
        factor = max(1.0, intensity / 100)
        return ImageEnhance.Contrast(source_image).enhance(factor)

    if mode == "Smooth":
        radius = max(0.1, intensity / 60)
        return source_image.filter(ImageFilter.GaussianBlur(radius=radius))

    return source_image.copy()


def _encoded_bytes_for_download(pil_image: Image.Image, output_format: str) -> bytes:
    buffer = io.BytesIO()
    save_kwargs = {}
    fmt = output_format.upper()
    if fmt in {"JPEG", "JPG"}:
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True
    pil_image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def _apply_sketch_style(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    blur = cv2.GaussianBlur(inv, (21, 21), 0)
    sketch = cv2.divide(gray, 255 - blur, scale=256)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)


def _apply_pencil_color_style(image_bgr: np.ndarray) -> np.ndarray:
    _gray_sketch, color_sketch = cv2.pencilSketch(
        image_bgr,
        sigma_s=60,
        sigma_r=0.07,
        shade_factor=0.05,
    )
    return color_sketch


def _build_side_by_side_rgb(original_rgb: np.ndarray, processed_rgb: np.ndarray) -> np.ndarray:
    if processed_rgb.shape[:2] != original_rgb.shape[:2]:
        processed_rgb = cv2.resize(
            processed_rgb,
            (original_rgb.shape[1], original_rgb.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
    return np.hstack([original_rgb, processed_rgb])


def _slider_frame_size(image: Image.Image, max_width: int = 800) -> tuple[int, int]:
    image_width = max(int(getattr(image, "width", 0) or 1), 1)
    image_height = max(int(getattr(image, "height", 0) or 1), 1)
    display_width = min(image_width, max_width)
    display_height = max(220, int(display_width * (image_height / image_width)))
    return display_width, display_height


def _apply_ai_style_preview(image_rgb: np.ndarray, style_name: str, category: str) -> np.ndarray:
    processed = image_rgb.copy()

    if category == "Medium":
        if style_name == "Stencil":
            gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
            smooth = cv2.bilateralFilter(gray, 9, 60, 60)
            grad_x = cv2.Sobel(smooth, cv2.CV_16S, 1, 0, ksize=3)
            grad_y = cv2.Sobel(smooth, cv2.CV_16S, 0, 1, ksize=3)
            edges = cv2.addWeighted(
                cv2.convertScaleAbs(grad_x), 0.5,
                cv2.convertScaleAbs(grad_y), 0.5, 0,
            )
            _, edge_mask = cv2.threshold(edges, 35, 255, cv2.THRESH_BINARY)
            base_tones = cv2.equalizeHist(smooth)
            base_tones = cv2.bilateralFilter(base_tones, 7, 45, 45)
            base_rgb = cv2.cvtColor(base_tones, cv2.COLOR_GRAY2RGB)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge_mask), cv2.COLOR_GRAY2RGB)
            processed = cv2.addWeighted(base_rgb, 0.82, edge_rgb, 0.18, 0)
        elif style_name == "Watercolor":
            base = cv2.bilateralFilter(processed, 11, 90, 90)
            base = cv2.bilateralFilter(base, 9, 70, 70)
            base = cv2.GaussianBlur(base, (5, 5), 0)
            poster = ((base.astype(np.uint16) // 24) * 24 + 12).clip(0, 255).astype(np.uint8)
            blended = cv2.addWeighted(base, 0.6, poster, 0.4, 0)
            blended = np.array(ImageEnhance.Color(Image.fromarray(blended)).enhance(0.82))
            blended = np.array(ImageEnhance.Brightness(Image.fromarray(blended)).enhance(1.06))
            blended = np.array(ImageEnhance.Contrast(Image.fromarray(blended)).enhance(0.92))
            edge = cv2.Canny(cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY), 40, 110)
            edge_soft = cv2.GaussianBlur(edge, (3, 3), 0)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge_soft), cv2.COLOR_GRAY2RGB)
            processed = cv2.addWeighted(blended, 0.92, edge_rgb, 0.08, 0)
        elif style_name == "Marker Illustration":
            base = cv2.bilateralFilter(processed, 9, 80, 80)
            base = cv2.medianBlur(base, 3)
            quant = ((base.astype(np.uint16) // 16) * 16 + 8).clip(0, 255).astype(np.uint8)
            blended = cv2.addWeighted(base, 0.7, quant, 0.3, 0)
            blended = np.array(ImageEnhance.Color(Image.fromarray(blended)).enhance(1.45))
            blended = np.array(ImageEnhance.Contrast(Image.fromarray(blended)).enhance(1.18))
            blended = np.array(ImageEnhance.Brightness(Image.fromarray(blended)).enhance(1.03))
            edge = cv2.Canny(cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY), 60, 140)
            edge = cv2.dilate(edge, np.ones((2, 2), np.uint8), iterations=1)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge), cv2.COLOR_GRAY2RGB)
            processed = cv2.addWeighted(blended, 0.9, edge_rgb, 0.1, 0)
        elif style_name == "Risograph":
            soft = cv2.GaussianBlur(processed, (3, 3), 0)
            quant = ((soft.astype(np.uint16) // 32) * 32 + 16).clip(0, 255).astype(np.uint8)
            r = quant[:, :, 0].astype(np.float32)
            g = quant[:, :, 1].astype(np.float32)
            b = quant[:, :, 2].astype(np.float32)
            blue_layer = np.clip(0.55 * b + 0.25 * g, 0, 255)
            coral_layer = np.clip(0.60 * r + 0.15 * g, 0, 255)
            yellow_layer = np.clip(0.45 * r + 0.35 * g, 0, 255)
            blue_shift = np.roll(blue_layer, shift=1, axis=1)
            coral_shift = np.roll(coral_layer, shift=1, axis=0)
            y = yellow_layer.astype(np.uint8)
            c = coral_shift.astype(np.uint8)
            bl = blue_shift.astype(np.uint8)
            composed = np.dstack([c, y, bl])
            noise = np.random.default_rng(42).normal(0, 8, composed.shape).astype(np.float32)
            composed = np.clip(composed.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            processed = np.array(ImageEnhance.Contrast(Image.fromarray(composed)).enhance(1.08))
        elif style_name == "Graffiti":
            processed = np.array(ImageEnhance.Contrast(Image.fromarray(processed)).enhance(1.5))
            processed = np.array(ImageEnhance.Color(Image.fromarray(processed)).enhance(1.5))
        elif style_name == "Oil Painting":
            processed = np.array(ImageEnhance.Contrast(Image.fromarray(processed)).enhance(1.3))
        elif style_name == "Mosaic":
            h, w = processed.shape[:2]
            tile_size = 16
            new_w = (w // tile_size) * tile_size
            new_h = (h // tile_size) * tile_size
            processed = cv2.resize(processed, (new_w, new_h), interpolation=cv2.INTER_AREA)
            processed = cv2.medianBlur(processed, 5)
            processed = cv2.resize(processed, (w, h), interpolation=cv2.INTER_NEAREST)
            edges = cv2.Canny(processed, 50, 150)
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            processed = cv2.bitwise_and(processed, processed, mask=cv2.bitwise_not(edges))
            processed = cv2.add(processed, edges_colored // 3)

    elif category == "Photography":
        if style_name == "High Key/Low Key":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(1.4))
        elif style_name == "Extreme Close-up":
            h, w = processed.shape[:2]
            processed = processed[h // 4:3 * h // 4, w // 4:3 * w // 4]
            processed = cv2.resize(processed, (w, h))
        elif style_name == "Low Shutter Speed":
            processed = cv2.GaussianBlur(processed, (25, 25), 0)
        elif style_name == "Bokeh":
            processed = cv2.GaussianBlur(processed, (15, 15), 0)
        elif style_name == "Black and White":
            gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
            processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    elif category == "Lighting":
        if style_name == "Natural Lighting":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(1.2))
        elif style_name == "Light and Shadow":
            processed = np.array(ImageEnhance.Contrast(Image.fromarray(processed)).enhance(1.8))
        elif style_name == "Volumetric Lighting":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(1.3))
        elif style_name == "Neon Lighting":
            processed = np.array(ImageEnhance.Color(Image.fromarray(processed)).enhance(2.0))
        elif style_name == "Golden Hour":
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 0.8
            processed[:, :, 2] *= 1.2
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Candlelight":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(0.8))
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 0.9
            processed[:, :, 2] *= 1.1
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Fairy Lights":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(1.1))
            processed = np.array(ImageEnhance.Color(Image.fromarray(processed)).enhance(1.3))
        elif style_name == "Street Lighting":
            processed = np.array(ImageEnhance.Brightness(Image.fromarray(processed)).enhance(0.9))

    elif category == "Color & Palette":
        if style_name == "Cool/Warm Tone":
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 1.2
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Pastels/Vibrant":
            processed = np.array(ImageEnhance.Color(Image.fromarray(processed)).enhance(0.8))
        elif style_name == "Earth/Jewel Tones":
            processed = processed.astype(np.float32)
            processed[:, :, 1] *= 1.2
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Autumn Leaves":
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 1.3
            processed[:, :, 2] *= 0.8
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Metallics":
            processed = np.array(ImageEnhance.Contrast(Image.fromarray(processed)).enhance(1.4))
            processed = np.array(ImageEnhance.Color(Image.fromarray(processed)).enhance(0.9))

    return processed


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #7c3aed;
    --primary-light: #a78bfa;
    --secondary: #06b6d4;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --dark-bg: #0f172a;
    --dark-surface: #1e293b;
    --card-border: rgba(148, 163, 184, 0.2);
}

* { font-family: 'Poppins', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0b0e1a 0%, #12091f 50%, #0b0e1a 100%);
    color: var(--text-primary);
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #0d0b1a 100%) !important;
    border-right: 1px solid rgba(124, 58, 237, 0.2) !important;
}

section[data-testid="stSidebar"] .stPageLink a {
    color: var(--text-secondary) !important;
    font-weight: 500;
    border-radius: 8px;
    padding: 8px 12px;
    transition: all 0.2s ease;
}

section[data-testid="stSidebar"] .stPageLink a:hover,
section[data-testid="stSidebar"] .stPageLink a[aria-current="page"] {
    background: rgba(124, 58, 237, 0.2) !important;
    color: var(--text-primary) !important;
}

.workspace-header {
    background: linear-gradient(135deg, rgba(18, 24, 42, 0.95), rgba(15, 12, 30, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
}

.workspace-header .ws-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.workspace-header .ws-brand {
    color: var(--primary);
    font-weight: 700;
}

.workspace-header .ws-subtitle {
    color: var(--text-secondary);
    font-size: 0.88rem;
    font-style: italic;
}

.workspace-header .ws-welcome {
    float: right;
    text-align: right;
    color: var(--text-secondary);
    font-size: 0.85rem;
}

.workspace-header .ws-welcome strong {
    color: var(--text-primary);
    display: block;
    font-size: 0.9rem;
}

.workspace-header .ws-status {
    color: #10b981;
    font-size: 0.78rem;
}

.style-section {
    background: rgba(18, 24, 42, 0.8);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 20px;
}

.style-section .section-number {
    color: var(--text-secondary);
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin-bottom: 16px;
}

.style-card {
    background: rgba(124, 58, 237, 0.12);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: 10px;
    padding: 14px 16px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.style-card:hover {
    background: rgba(124, 58, 237, 0.2);
    border-color: rgba(124, 58, 237, 0.5);
}

.style-card.active {
    background: rgba(124, 58, 237, 0.25);
    border-color: rgba(124, 58, 237, 0.6);
    box-shadow: 0 0 20px rgba(124, 58, 237, 0.15);
}

.style-card .style-name {
    color: var(--text-primary);
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 2px;
}

.style-card .style-desc {
    color: var(--text-secondary);
    font-size: 0.8rem;
}

.panel {
    background: linear-gradient(135deg, rgba(18, 24, 42, 0.95), rgba(15, 12, 30, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
}

.title {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 6px;
    color: var(--text-primary);
}

.desc {
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.6;
}

.meta-card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 12px;
    padding: 14px 16px;
}

.meta-label {
    color: var(--text-secondary);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}

.meta-value {
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
}
</style>
""",
    unsafe_allow_html=True,
)

account_status = "Active"
st.markdown(
    f"""
<div class="workspace-header">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
        <div>
            <div class="ws-title"><span class="ws-brand">Vivido</span> Creative Workspace</div>
            <div class="ws-subtitle">"Art is the only way to run away without leaving home." — Twyla Tharp</div>
        </div>
        <div class="ws-welcome">
            <strong>Welcome back, {username}</strong>
            <span class="ws-status">Account Status: {account_status}</span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# STEP 1 — IMAGE UPLOAD
# ============================================================
uploaded_file = st.file_uploader(
    "Choose an image file",
    type=["jpg", "jpeg", "png", "bmp"],
    key=f"image_uploader_{st.session_state['upload_widget_nonce']}",
)

if uploaded_file is not None:
    file_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("uploaded_image_signature") != file_signature:
        result = process_and_save_upload(
            uploaded_file=uploaded_file,
            previous_path=st.session_state.get("uploaded_image_path"),
        )
        if result.get("success"):
            st.session_state["uploaded_image_path"] = result["file_path"]
            st.session_state["uploaded_image_metadata"] = result["metadata"]
            st.session_state["uploaded_image_signature"] = file_signature
            st.session_state["uploaded_image_confirmed"] = False
            st.success("Image uploaded successfully.")
        else:
            st.error(result.get("message", "Failed to upload image."))

if st.session_state.get("uploaded_image_path"):
    metadata = st.session_state.get("uploaded_image_metadata", {})
    file_path = st.session_state["uploaded_image_path"]

    try:
        with Image.open(file_path) as loaded_image:
            original_image = loaded_image.convert("RGB")
    except OSError:
        st.error("Could not load the uploaded image from temporary storage.")
        st.stop()

    if not st.session_state.get("uploaded_image_confirmed"):
        st.markdown("### Confirm Uploaded Image")
        st.info("Please confirm this is the correct image before processing.")
        st.image(original_image, caption="Uploaded image preview", width=260)

        confirm_col, replace_col, ai_styles_col = st.columns(3)
        with confirm_col:
            if st.button("Yes, this is correct", key="confirm_uploaded_image", width='stretch'):
                st.session_state["uploaded_image_confirmed"] = True
                # Redirect to AI Styles page
                st.switch_page("pages/ai_styles.py")
        with replace_col:
            if st.button("No, upload another image", key="reject_uploaded_image", width='stretch'):
                remove_temp_file(st.session_state.get("uploaded_image_path"))
                st.session_state["uploaded_image_path"] = ""
                st.session_state["uploaded_image_metadata"] = {}
                st.session_state["uploaded_image_signature"] = ""
                st.session_state["uploaded_image_confirmed"] = False
                st.session_state["upload_widget_nonce"] += 1
                st.rerun()
        with ai_styles_col:
            if st.button("🎨 Browse AI Styles", key="go_to_ai_styles", width='stretch'):
                st.session_state["uploaded_image_confirmed"] = True
                st.switch_page("pages/ai_styles.py")

        st.stop()

    # ============================================================
    # STEP 2 — AI STYLE SELECTION
    # ============================================================
    original_rgb = np.array(original_image)
    original_bgr = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR)
    original_filename = metadata.get("original_filename", "uploaded_image.png")
    processed_name_root = os.path.splitext(original_filename)[0]

    # Get confirmed AI style
    confirmed_ai_style = st.session_state.get("confirmed_ai_style")

    # Show selected style info
    if confirmed_ai_style:
        st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
">
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    ">
        <div>
            <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">
                ✨ Selected Style
            </div>
            <div style="color: #f8fafc; font-size: 1.4rem; font-weight: 700;">
                {confirmed_ai_style['name']}
                <span style="color: #7c3aed; margin: 0 8px;">•</span>
                <span style="color: #94a3b8; font-size: 1rem; font-weight: 500;">{confirmed_ai_style['category']}</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        
        # Add button to change AI style
        if st.button("🔄 Change AI Style", key="change_ai_style_btn"):
            st.session_state["confirmed_ai_style"] = None
            st.session_state["ai_style_selected"] = None
            st.session_state["ai_style_info"] = None
            st.switch_page("pages/ai_styles.py")
        
        st.markdown("---")
    else:
        st.info("Please select an AI Style from the AI Styles page")
        if st.button("Go to AI Styles", key="go_to_ai_styles_no_style"):
            st.switch_page("pages/ai_styles.py")

    # Process button
    process_col, try_col = st.columns([3, 2])
    with process_col:
        process_clicked = st.button("Process Image", key="process_style_lab_btn", width='stretch')
    with try_col:
        if st.button("Try Another Style", key="clear_style_lab_btn", width='stretch'):
            st.session_state["style_lab_processed_png"] = b""
            st.session_state["style_lab_preview_png"] = b""
            st.session_state["style_lab_style_name"] = ""

    if process_clicked and confirmed_ai_style:
        progress = st.progress(0)
        with st.spinner(f"Applying {confirmed_ai_style['name']} style..."):
            progress.progress(20)
            
            # Apply the AI style effect
            style_name = confirmed_ai_style['name']
            category = confirmed_ai_style['category']
            processed_rgb = _apply_ai_style_preview(original_rgb, style_name, category)

            progress.progress(70)
            preview_rgb = _build_side_by_side_rgb(original_rgb, processed_rgb)
            st.session_state["style_lab_processed_png"] = _encoded_bytes_for_download(Image.fromarray(processed_rgb), "PNG")
            st.session_state["style_lab_preview_png"] = _encoded_bytes_for_download(Image.fromarray(preview_rgb), "PNG")
            st.session_state["style_lab_style_name"] = confirmed_ai_style['name']
            progress.progress(100)
        st.success(f"{confirmed_ai_style['name']} preview generated.")

    # ============================================================
    # STEP 3 — PROCESSED IMAGE + BEFORE/AFTER SLIDER  (always visible)
    # ============================================================
    if st.session_state.get("style_lab_processed_png"):
        processed_preview_rgb = np.array(
            Image.open(io.BytesIO(st.session_state["style_lab_processed_png"])).convert("RGB")
        )
        processed_pil = Image.fromarray(processed_preview_rgb)

        # --- Side-by-side preview (Original vs Processed) ---
        st.markdown("### Original vs Processed")
        side_col_1, side_col_2 = st.columns(2)
        with side_col_1:
            st.image(
                original_rgb,
                caption="Original",
                use_container_width=True,
            )
        with side_col_2:
            st.image(
                processed_preview_rgb,
                caption=f"Processed ({st.session_state.get('style_lab_style_name', 'AI Style')})",
                use_container_width=True,
            )

        # --- Before / After Slider (optional, toggled) ---
        show_slider = st.toggle("🔀 Show Before/After Slider", value=False, key="show_before_after_slider")

        if show_slider:
            slider_id = f"compare_{uuid.uuid4().hex}"
            original_uri = _to_data_uri(original_image)
            compare_processed_image = processed_pil
            if compare_processed_image.size != original_image.size:
                compare_processed_image = compare_processed_image.resize(original_image.size)
            processed_uri = _to_data_uri(compare_processed_image)

            # Match the slider frame to the visual size of the processed preview column.
            slider_width, slider_height = _slider_frame_size(original_image, max_width=560)
            compare_component_height = slider_height + 8

            components_html(
                f"""
<div style="
    position:relative;
    width:100%;
    max-width:{slider_width}px;
    margin: 0 auto;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 25px 60px rgba(0,0,0,0.5);
">

    <img src="{original_uri}"
         style="width:100%;display:block;user-select:none;pointer-events:none;">

    <div id="{slider_id}_overlay"
         style="
            position:absolute;
            top:0;
            left:0;
            width:100%;
            height:50%;
            overflow:hidden;
         ">
        <img src="{processed_uri}"
             style="width:100%;display:block;user-select:none;pointer-events:none;">
    </div>

    <div id="{slider_id}_divider"
         style="
            position:absolute;
            top:50%;
            left:0;
            transform:translateY(-50%);
            width:100%;
            height:20px;
            cursor:ns-resize;
            display:flex;
            align-items:center;
            justify-content:center;
         ">

         <div style="
            width:100%;
            height:6px;
            background:linear-gradient(180deg,#06b6d4,#7c3aed);
            box-shadow:0 0 25px #06b6d4;
         "></div>

         <div style="
            position:absolute;
            width:46px;
            height:46px;
            border-radius:50%;
            background:linear-gradient(135deg,#06b6d4,#7c3aed);
            box-shadow:0 10px 30px rgba(0,0,0,0.6);
            display:flex;
            align-items:center;
            justify-content:center;
            color:white;
            font-weight:700;
            font-size:14px;
         ">
            ⇆
         </div>

    </div>
</div>

<script>
(function() {{
    const overlay = document.getElementById("{slider_id}_overlay");
    const divider = document.getElementById("{slider_id}_divider");
    const container = divider.parentElement;

    let dragging = false;

    function updatePosition(clientY) {{
        const rect = container.getBoundingClientRect();
        let offset = clientY - rect.top;

        if (offset < 0) offset = 0;
        if (offset > rect.height) offset = rect.height;

        overlay.style.height = offset + "px";
        divider.style.top = offset + "px";
    }}

    divider.addEventListener("mousedown", () => dragging = true);
    window.addEventListener("mouseup", () => dragging = false);

    window.addEventListener("mousemove", (e) => {{
        if (!dragging) return;
        updatePosition(e.clientY);
    }});

    divider.addEventListener("touchstart", (e) => {{
        dragging = true;
        updatePosition(e.touches[0].clientY);
        e.preventDefault();
    }}, {{ passive:false }});

    window.addEventListener("touchend", () => dragging = false);

    window.addEventListener("touchmove", (e) => {{
        if (!dragging) return;
        updatePosition(e.touches[0].clientY);
        e.preventDefault();
    }}, {{ passive:false }});
}})();
</script>
""",
                height=compare_component_height,
                scrolling=False,
            )

        # --- Download / Payment ---
        if st.session_state.get("payment_verified"):
            # Show download buttons if payment verified
            dl_col_1, dl_col_2 = st.columns(2)
            with dl_col_1:
                st.download_button(
                    "⬇ Download Processed Image",
                    data=st.session_state["style_lab_processed_png"],
                    file_name=f"{processed_name_root}_{st.session_state.get('style_lab_style_name', 'style').lower().replace(' ', '_')}.png",
                    mime="image/png",
                    key="style_lab_download_processed_btn",
                    use_container_width=True,
                )
            with dl_col_2:
                st.download_button(
                    "⬇ Download Side-by-Side Preview",
                    data=st.session_state["style_lab_preview_png"],
                    file_name=f"{processed_name_root}_{st.session_state.get('style_lab_style_name', 'style').lower().replace(' ', '_')}_preview.png",
                    mime="image/png",
                    key="style_lab_download_preview_btn",
                    use_container_width=True,
                )
            st.success("✅ Payment verified! You can download high quality images.")
        else:
            # Show payment button instead of download
            st.markdown("---")
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(6, 182, 212, 0.1));
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 12px;
                padding: 24px;
                text-align: center;
                margin: 20px 0;
            ">
                <h3 style="margin: 0 0 10px 0; color: #f1f5f9;">💳 Download Your Image</h3>
                <p style="margin: 0; color: #94a3b8; font-size: 0.95rem;">
                    Click below to proceed to secure payment and download
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Single payment button that redirects
            if st.button("💳 Proceed to Payment & Download", key="payment_btn", use_container_width=True):
                # Save processed image to a temp file for payment page
                import tempfile
                import datetime
                
                # Get the processed image
                img_to_save = st.session_state.get("style_lab_processed_pil")
                if img_to_save is None:
                    img_to_save = st.session_state.get("processed_image")
                
                if img_to_save:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, f"vivido_processed_{timestamp}.png")
                    img_to_save.save(temp_path)
                    st.session_state["processed_image_path"] = temp_path
                
                # Store payment details
                st.session_state["image_quality"] = "standard"
                st.session_state["selected_style"] = st.session_state.get("style_lab_style_name", "Custom")
                st.session_state["uploaded_filename"] = st.session_state.get("uploaded_image_name", "image.jpg")
                st.session_state["payment_status"] = "pending"
                st.switch_page("pages/payment_checkout.py")
        
    # ============================================================
    # ADVANCED SETTINGS  (hidden by default)
    # ============================================================
    st.markdown("---")
    show_advanced = st.toggle(
        "⚙ Show Advanced Settings",
        value=False,
        help="Access preview modes, zoom controls, image metadata, edge detection, cartoon tuning, and extra downloads.",
        key="show_advanced_studio",
    )

    if show_advanced:
        # --- Preview Mode & Intensity ---
        st.markdown("### Preview Mode")
        preview_mode = st.selectbox(
            "Processed Preview Mode",
            ["Original", "Auto Contrast", "Contrast Boost", "Sharpen", "Grayscale", "Smooth"],
            index=0,
        )
        preview_intensity = st.slider("Effect Intensity", min_value=50, max_value=200, value=120, step=10)
        processed_image = _build_processed_preview(original_image, preview_mode, preview_intensity)

        # --- Zoom & Fit ---
        zoom_percent = st.select_slider("Zoom", options=[25, 50, 75, 100, 125, 150, 200], value=100)
        fit_to_width = st.toggle("Fit preview to page width", value=True, key="fit_preview_to_width")

        base_width = int(metadata.get("width") or original_image.width or 800)
        preview_width = max(420, int(base_width * (zoom_percent / 100)))

        st.markdown("### Processed Preview")
        st.image(
            processed_image,
            caption=f"Processed ({preview_mode})",
            width='stretch',
        )
        with st.expander("Show Original Reference"):
            st.image(
                original_image,
                caption="Original",
                use_container_width=fit_to_width,
                width=None if fit_to_width else preview_width,
            )

        # --- Before/After Slider (preview mode) ---
        st.markdown("### Before/After Slider (Preview Mode)")
        adv_slider_id = f"adv_compare_{uuid.uuid4().hex}"
        adv_original_uri = _to_data_uri(original_image)
        adv_compare_processed_image = processed_image
        if adv_compare_processed_image.size != original_image.size:
            adv_compare_processed_image = adv_compare_processed_image.resize(original_image.size)
        adv_processed_uri = _to_data_uri(adv_compare_processed_image)
        adv_slider_width, adv_slider_height = _slider_frame_size(original_image, max_width=800)
        adv_compare_component_height = adv_slider_height + 8

        components_html(
            f"""
<div style="
    position:relative;
    width:100%;
    max-width:{adv_slider_width}px;
    margin:0 auto;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 25px 60px rgba(0,0,0,0.5);
">

    <img src="{adv_original_uri}"
         style="width:100%;display:block;user-select:none;pointer-events:none;">

    <div id="{adv_slider_id}_overlay"
         style="
            position:absolute;
            top:0;
            left:0;
            width:100%;
            height:50%;
            overflow:hidden;
         ">
        <img src="{adv_processed_uri}"
             style="width:100%;display:block;user-select:none;pointer-events:none;">
    </div>

    <div id="{adv_slider_id}_divider"
         style="
            position:absolute;
            top:50%;
            left:0;
            transform:translateY(-50%);
            width:100%;
            height:20px;
            cursor:ns-resize;
            display:flex;
            align-items:center;
            justify-content:center;
         ">

         <div style="
            width:100%;
            height:6px;
            background:linear-gradient(180deg,#06b6d4,#7c3aed);
            box-shadow:0 0 25px #06b6d4;
         "></div>

         <div style="
            position:absolute;
            width:46px;
            height:46px;
            border-radius:50%;
            background:linear-gradient(135deg,#06b6d4,#7c3aed);
            box-shadow:0 10px 30px rgba(0,0,0,0.6);
            display:flex;
            align-items:center;
            justify-content:center;
            color:white;
            font-weight:700;
            font-size:14px;
         ">
            ⇆
         </div>

    </div>
</div>

<script>
(function() {{
    const overlay = document.getElementById("{adv_slider_id}_overlay");
    const divider = document.getElementById("{adv_slider_id}_divider");
    const container = divider.parentElement;

    let dragging = false;

    function updatePosition(clientY) {{
        const rect = container.getBoundingClientRect();
        let offset = clientY - rect.top;

        if (offset < 0) offset = 0;
        if (offset > rect.height) offset = rect.height;

        overlay.style.height = offset + "px";
        divider.style.top = offset + "px";
    }}

    divider.addEventListener("mousedown", () => dragging = true);
    window.addEventListener("mouseup", () => dragging = false);

    window.addEventListener("mousemove", (e) => {{
        if (!dragging) return;
        updatePosition(e.clientY);
    }});

    divider.addEventListener("touchstart", (e) => {{
        dragging = true;
        updatePosition(e.touches[0].clientY);
        e.preventDefault();
    }}, {{ passive:false }});

    window.addEventListener("touchend", () => dragging = false);

    window.addEventListener("touchmove", (e) => {{
        if (!dragging) return;
        updatePosition(e.touches[0].clientY);
        e.preventDefault();
    }}, {{ passive:false }});
}})();
</script>
""",
            height=adv_compare_component_height,
            scrolling=False,
        )

        # --- Image Metadata ---
        st.markdown("### Image Metadata")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""
<div class="meta-card">
    <div class="meta-label">Dimensions</div>
    <div class="meta-value">{metadata.get('width', '-')} x {metadata.get('height', '-')}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
<div class="meta-card">
    <div class="meta-label">File Size</div>
    <div class="meta-value">{metadata.get('size_human', '-')}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""
<div class="meta-card">
    <div class="meta-label">Format</div>
    <div class="meta-value">{metadata.get('format', '-')}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.caption(f"Temporary file path (session): {file_path}")

        with open(file_path, "rb") as original_file:
            original_bytes = original_file.read()

        output_format = "PNG" if preview_mode != "Original" else (metadata.get("format", "PNG") or "PNG")
        if output_format == "JPG":
            output_format = "JPEG"
        processed_bytes = _encoded_bytes_for_download(processed_image, output_format)
        processed_ext = ".png" if output_format == "PNG" else ".jpg" if output_format == "JPEG" else ".bmp"
        processed_filename = f"{processed_name_root}_{preview_mode.lower().replace(' ', '_')}{processed_ext}"

        # --- Base Cartoon Effect ---
        st.divider()
        st.markdown("### Base Cartoon Effect (Bilateral + Color Quantization)")
        style_docs = documented_style_settings()
        style_labels = {
            "soft_paint": "Soft Paint",
            "classic_cartoon": "Classic Cartoon",
            "bold_poster": "Bold Poster",
            "comic_ink": "Comic Ink",
        }
        adv_selected_style = st.selectbox(
            "Artistic Style Preset",
            list(style_labels.keys()),
            index=1,
            format_func=lambda key: style_labels[key],
        )

        base_cartoon_params = recommended_style_params(adv_selected_style)
        st.caption(style_docs[adv_selected_style]["notes"])

        cartoon_col_1, cartoon_col_2, cartoon_col_3, cartoon_col_4 = st.columns(4)
        with cartoon_col_1:
            num_colors = st.slider("Color Count", min_value=4, max_value=24, value=base_cartoon_params.num_colors, step=1)
        with cartoon_col_2:
            bilateral_strength = st.slider(
                "Bilateral Sigma",
                min_value=20,
                max_value=150,
                value=int(base_cartoon_params.bilateral_sigma_color),
                step=5,
            )
        with cartoon_col_3:
            bilateral_passes = st.slider("Bilateral Passes", min_value=1, max_value=4, value=base_cartoon_params.bilateral_passes, step=1)
        with cartoon_col_4:
            downsample_scale = st.slider(
                "Performance Scale",
                min_value=0.6,
                max_value=1.0,
                value=float(base_cartoon_params.downsample_scale),
                step=0.05,
            )

        active_cartoon_params = CartoonParams(
            num_colors=num_colors,
            bilateral_d=base_cartoon_params.bilateral_d,
            bilateral_sigma_color=float(bilateral_strength),
            bilateral_sigma_space=float(bilateral_strength),
            bilateral_passes=bilateral_passes,
            kmeans_attempts=base_cartoon_params.kmeans_attempts,
            downsample_scale=downsample_scale,
            sample_pixels=base_cartoon_params.sample_pixels,
            random_seed=base_cartoon_params.random_seed,
        )

        cartoon_base_bgr = create_base_cartoon_effect(original_bgr, active_cartoon_params)
        cartoon_base_rgb = cv2.cvtColor(cartoon_base_bgr, cv2.COLOR_BGR2RGB)
        st.image(cartoon_base_rgb, caption=f"Cartoon Base ({style_labels[adv_selected_style]})", use_container_width=True)

        cartoon_panel_bgr = compare_original_and_cartoon(
            original_bgr,
            cartoon_base_bgr,
            label_original="Original",
            label_cartoon="Cartoon Base",
        )
        with st.expander("Show Original vs Cartoon Base"):
            st.image(cv2.cvtColor(cartoon_panel_bgr, cv2.COLOR_BGR2RGB), use_container_width=True)

        cartoon_output_bytes = _encoded_bytes_for_download(Image.fromarray(cartoon_base_rgb), "PNG")
        cartoon_output_filename = f"{processed_name_root}_{adv_selected_style}_cartoon_base.png"

        # --- Edge Detection ---
        st.divider()
        st.markdown("### Cartoon Edge Detection")
        preset_choice = st.selectbox(
            "Image Type Preset",
            ["Custom", "Portrait", "Landscape", "Object"],
            index=0,
            help="Choose a starting point tuned for image category, then fine-tune parameters.",
        )

        if preset_choice == "Portrait":
            base_params = recommended_params("portrait")
        elif preset_choice == "Landscape":
            base_params = recommended_params("landscape")
        elif preset_choice == "Object":
            base_params = recommended_params("object")
        else:
            base_params = EdgeParams()

        method_index = 0 if base_params.method == "canny" else 1
        edge_method_label = st.radio("Edge Method", ["Canny", "Adaptive"], index=method_index, horizontal=True)
        edge_method = "canny" if edge_method_label == "Canny" else "adaptive"

        edge_col_a, edge_col_b, edge_col_c, edge_col_d = st.columns(4)
        with edge_col_a:
            median_blur = st.slider("Median Blur Kernel", min_value=3, max_value=15, value=base_params.median_blur_kernel, step=2)
        with edge_col_b:
            sensitivity = st.slider("Sensitivity", min_value=0.5, max_value=2.0, value=float(base_params.sensitivity), step=0.05)
        with edge_col_c:
            edge_thickness = st.slider("Edge Thickness", min_value=1, max_value=5, value=base_params.edge_thickness, step=1)
        with edge_col_d:
            invert_edges = st.toggle("Invert Edges", value=base_params.invert)

        if edge_method == "canny":
            canny_low = st.slider("Canny Low Threshold", min_value=0, max_value=255, value=base_params.canny_low, step=1)
            canny_high_min = max(canny_low + 1, 1)
            canny_high_default = max(base_params.canny_high, canny_high_min)
            canny_high = st.slider(
                "Canny High Threshold",
                min_value=canny_high_min,
                max_value=255,
                value=min(canny_high_default, 255),
                step=1,
            )
            edge_params = EdgeParams(
                method="canny",
                canny_low=canny_low,
                canny_high=canny_high,
                median_blur_kernel=median_blur,
                sensitivity=sensitivity,
                edge_thickness=edge_thickness,
                invert=invert_edges,
            )
        else:
            adaptive_block_size = st.slider(
                "Adaptive Block Size",
                min_value=3,
                max_value=31,
                value=base_params.adaptive_block_size,
                step=2,
            )
            adaptive_c = st.slider("Adaptive C Value", min_value=-10, max_value=20, value=base_params.adaptive_c, step=1)
            edge_params = EdgeParams(
                method="adaptive",
                adaptive_block_size=adaptive_block_size,
                adaptive_c=adaptive_c,
                median_blur_kernel=median_blur,
                sensitivity=sensitivity,
                edge_thickness=edge_thickness,
                invert=invert_edges,
            )

        edge_map = detect_cartoon_edges(original_bgr, edge_params)
        edge_map_rgb = cv2.cvtColor(edge_map, cv2.COLOR_GRAY2RGB)
        edge_preview = Image.fromarray(edge_map)

        edge_preview_col_1, edge_preview_col_2 = st.columns(2)
        with edge_preview_col_1:
            st.image(edge_preview, caption="Detected Edge Map", width='stretch')
        with edge_preview_col_2:
            st.image(edge_map_rgb, caption="Edge Preview Overlay", width='stretch')

        # --- Classic Cartoon Tuning ---
        st.divider()
        st.markdown("### Complete Classic Cartoon")
        classic_col_1, classic_col_2 = st.columns(2)
        with classic_col_1:
            classic_intensity = st.selectbox(
                "Cartoon Intensity",
                ["light", "medium", "strong"],
                index=1,
                format_func=lambda x: x.title(),
            )
        with classic_col_2:
            classic_edge_method_label = st.radio(
                "Edge Method for Final Cartoon",
                ["Auto", "Adaptive", "Canny"],
                index=0,
                horizontal=True,
            )
        classic_edge_method = classic_edge_method_label.lower()

        classic_cartoon_bgr = create_classic_cartoon(
            original_bgr,
            intensity=classic_intensity,
            edge_method=classic_edge_method,
        )
        classic_cartoon_rgb = cv2.cvtColor(classic_cartoon_bgr, cv2.COLOR_BGR2RGB)
        classic_slider_id = f"classic_compare_{uuid.uuid4().hex}"
        classic_original_uri = _to_data_uri(original_image)
        classic_overlay_image = Image.fromarray(classic_cartoon_rgb)
        if classic_overlay_image.size != original_image.size:
            classic_overlay_image = classic_overlay_image.resize(original_image.size)
        classic_overlay_uri = _to_data_uri(classic_overlay_image)

        classic_slider_width, classic_slider_height = _slider_frame_size(original_image, max_width=800)
        adv_compare_component_height2 = classic_slider_height + 8

        components_html(
            f"""
<style>
#{classic_slider_id}.compare-wrap {{
    position: relative;
    width: 100%;
    max-width: {classic_slider_width}px;
    margin: 8px auto 18px auto;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.35);
}}
#{classic_slider_id} .base-img,
#{classic_slider_id} .overlay-img img {{
    display: block;
    width: 100%;
    height: auto;
}}
#{classic_slider_id} .overlay-img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 50%;
    overflow: hidden;
}}
#{classic_slider_id} .divider {{
    position: absolute;
    top: 50%;
    left: 0;
    transform: translateY(-50%);
    width: 100%;
    height: 12px;
    background: rgba(241, 245, 249, 0.96);
    box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.35), 0 8px 20px rgba(15, 23, 42, 0.25);
    pointer-events: auto;
    cursor: ns-resize;
}}
#{classic_slider_id} .divider::after {{
    content: "<>";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 34px;
    height: 34px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.8);
    border: 2px solid rgba(241, 245, 249, 0.95);
    color: rgba(241, 245, 249, 0.95);
    font-size: 11px;
    font-weight: 700;
    display: grid;
    place-items: center;
    letter-spacing: 0.04em;
}}
</style>
<div id="{classic_slider_id}" class="compare-wrap">
  <img class="base-img" src="{classic_original_uri}" alt="Original">
  <div class="overlay-img" id="{classic_slider_id}_overlay">
    <img src="{classic_overlay_uri}" alt="Classic Cartoon">
  </div>
  <div class="divider" id="{classic_slider_id}_divider"></div>
</div>
<script>
(() => {{
  const container = document.getElementById("{classic_slider_id}");
  const slider = document.getElementById("{classic_slider_id}_divider");
  const overlay = document.getElementById("{classic_slider_id}_overlay");
  if (!container || !slider || !overlay) return;

  let isDragging = false;
  const updateFromClientY = (clientY) => {{
    const rect = container.getBoundingClientRect();
    let offset = clientY - rect.top;
    if (offset < 0) offset = 0;
    if (offset > rect.height) offset = rect.height;
    slider.style.top = `${{offset}}px`;
    overlay.style.height = `${{offset}}px`;
  }};

  const initialRect = container.getBoundingClientRect();
  updateFromClientY(initialRect.top + (initialRect.height / 2));

  slider.addEventListener("mousedown", () => {{ isDragging = true; }});
  window.addEventListener("mouseup", () => {{ isDragging = false; }});
  window.addEventListener("mousemove", (e) => {{
    if (!isDragging) return;
    updateFromClientY(e.clientY);
  }});

  slider.addEventListener("touchstart", (e) => {{
    isDragging = true;
    if (e.touches && e.touches.length > 0) {{
      updateFromClientY(e.touches[0].clientY);
    }}
    e.preventDefault();
  }}, {{ passive: false }});
  window.addEventListener("touchend", () => {{ isDragging = false; }});
  window.addEventListener("touchmove", (e) => {{
    if (!isDragging || !e.touches || e.touches.length === 0) return;
    updateFromClientY(e.touches[0].clientY);
    e.preventDefault();
  }}, {{ passive: false }});
}})();
</script>
""",
            height=adv_compare_component_height2,
            scrolling=False,
        )

        # --- All Downloads ---
        edge_bytes = _encoded_bytes_for_download(edge_preview.convert("RGB"), "PNG")
        edge_filename = f"{processed_name_root}_edges.png"
        classic_cartoon_bytes = _encoded_bytes_for_download(Image.fromarray(classic_cartoon_rgb), "PNG")
        classic_cartoon_filename = f"{processed_name_root}_classic_cartoon_{classic_intensity}.png"

        st.divider()
        st.markdown("### Downloads")
        dl_col_1, dl_col_2, dl_col_3, dl_col_4 = st.columns(4)
        with dl_col_1:
            st.download_button(
                "Download Cartoon Base",
                data=cartoon_output_bytes,
                file_name=cartoon_output_filename,
                mime="image/png",
                width='stretch',
            )
        with dl_col_2:
            st.download_button(
                "Download Processed Preview",
                data=processed_bytes,
                file_name=processed_filename,
                mime=_get_mime_type(processed_filename),
                width='stretch',
            )
        with dl_col_3:
            st.download_button(
                "Download Edge Map",
                data=edge_bytes,
                file_name=edge_filename,
                mime="image/png",
                width='stretch',
            )
        with dl_col_4:
            st.download_button(
                "Download Classic Cartoon",
                data=classic_cartoon_bytes,
                file_name=classic_cartoon_filename,
                mime="image/png",
            )

    # --- Upload New Image button (always visible at bottom) ---
    st.markdown("---")
    if st.button("Upload New Image", key="replace_uploaded_image_btn", use_container_width=True):
        remove_temp_file(st.session_state.get("uploaded_image_path"))
        st.session_state["uploaded_image_path"] = ""
        st.session_state["uploaded_image_metadata"] = {}
        st.session_state["uploaded_image_signature"] = ""
        st.session_state["uploaded_image_confirmed"] = False
        st.session_state["upload_widget_nonce"] += 1
        st.rerun()
