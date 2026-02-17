import base64
import io
import os
import uuid

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from streamlit.components.v1 import html as components_html

from utils.edge_detection import EdgeParams, compare_original_and_edges, detect_cartoon_edges, recommended_params
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
    st.warning("Please login first")
    if st.button("Go to Login", key="go_to_login_from_image_processing"):
        st.switch_page("pages/login.py")
    st.stop()

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


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #06b6d4;
    --secondary: #7c3aed;
    --text-primary: #f1f5f9;
    --text-secondary: #cbd5e1;
}

* { font-family: 'Poppins', sans-serif; }

body {
    background: linear-gradient(135deg, #0f172a 0%, #1a0f2e 50%, #0f172a 100%);
    color: var(--text-primary);
}

.panel {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 20px;
    padding: 30px;
    margin-bottom: 24px;
}

.title {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 6px;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.desc {
    color: var(--text-secondary);
    font-size: 0.95rem;
    line-height: 1.6;
}

.meta-card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(148, 163, 184, 0.25);
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

st.markdown(
    f"""
<div class="panel">
    <div class="title">Image Processing</div>
    <div class="desc">
        Upload a JPG, JPEG, PNG, or BMP image up to {MAX_UPLOAD_SIZE_MB} MB.
        Files are validated, previewed, and stored temporarily for subsequent processing.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

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
        st.image(original_image, caption="Uploaded image preview", use_container_width=True)

        confirm_col, replace_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, this is correct", key="confirm_uploaded_image", use_container_width=True):
                st.session_state["uploaded_image_confirmed"] = True
                st.rerun()
        with replace_col:
            if st.button("No, upload another image", key="reject_uploaded_image", use_container_width=True):
                remove_temp_file(st.session_state.get("uploaded_image_path"))
                st.session_state["uploaded_image_path"] = ""
                st.session_state["uploaded_image_metadata"] = {}
                st.session_state["uploaded_image_signature"] = ""
                st.session_state["uploaded_image_confirmed"] = False
                st.session_state["upload_widget_nonce"] += 1
                st.rerun()

        st.stop()

    preview_mode = st.selectbox(
        "Processed Preview Mode",
        ["Original", "Auto Contrast", "Contrast Boost", "Sharpen", "Grayscale", "Smooth"],
        index=0,
    )
    preview_intensity = st.slider("Effect Intensity", min_value=50, max_value=200, value=120, step=10)
    processed_image = _build_processed_preview(original_image, preview_mode, preview_intensity)

    zoom_percent = st.select_slider("Zoom", options=[25, 50, 75, 100, 125, 150, 200], value=100)
    fit_to_width = st.toggle("Fit preview to page width", value=True, key="fit_preview_to_width")

    base_width = int(metadata.get("width") or original_image.width or 800)
    preview_width = max(420, int(base_width * (zoom_percent / 100)))

    st.markdown("### Processed Preview")
    st.image(
        processed_image,
        caption=f"Processed ({preview_mode})",
        use_container_width=True,
    )
    with st.expander("Show Original Reference"):
        st.image(
            original_image,
            caption="Original",
            use_container_width=fit_to_width,
            width=None if fit_to_width else preview_width,
        )

    # ----------------------------------------------------
    st.markdown("### Before/After Slider")
    slider_id = f"compare_{uuid.uuid4().hex}"
    original_uri = _to_data_uri(original_image)
    compare_processed_image = processed_image
    if compare_processed_image.size != original_image.size:
        compare_processed_image = compare_processed_image.resize(original_image.size)
    processed_uri = _to_data_uri(compare_processed_image)
    compare_component_height = max(
        620,
        min(1400, int((original_image.height / max(original_image.width, 1)) * 1100) + 90),
    )

    components_html(
    f"""
<div style="
    position:relative;
    width:100%;
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

    original_filename = metadata.get("original_filename", "uploaded_image.png")
    with open(file_path, "rb") as original_file:
        original_bytes = original_file.read()

    output_format = "PNG" if preview_mode != "Original" else (metadata.get("format", "PNG") or "PNG")
    if output_format == "JPG":
        output_format = "JPEG"
    processed_bytes = _encoded_bytes_for_download(processed_image, output_format)
    processed_ext = ".png" if output_format == "PNG" else ".jpg" if output_format == "JPEG" else ".bmp"
    processed_name_root = os.path.splitext(original_filename)[0]
    processed_filename = f"{processed_name_root}_{preview_mode.lower().replace(' ', '_')}{processed_ext}"

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

    original_rgb = np.array(original_image)
    original_bgr = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR)
    edge_map = detect_cartoon_edges(original_bgr, edge_params)
    edge_map_rgb = cv2.cvtColor(edge_map, cv2.COLOR_GRAY2RGB)
    edge_preview = Image.fromarray(edge_map)

    edge_panel_bgr = compare_original_and_edges(original_bgr, edge_map, label_original="Original", label_edges="Cartoon Edges")
    edge_panel_rgb = cv2.cvtColor(edge_panel_bgr, cv2.COLOR_BGR2RGB)

    edge_preview_col_1, edge_preview_col_2 = st.columns(2)
    with edge_preview_col_1:
        st.image(edge_preview, caption="Detected Edge Map", use_container_width=True)
    with edge_preview_col_2:
        st.image(edge_panel_rgb, caption="Original vs Edge Comparison", use_container_width=True)

    edge_slider_id = f"edge_compare_{uuid.uuid4().hex}"
    edge_original_uri = _to_data_uri(original_image)
    edge_compare_image = Image.fromarray(edge_map_rgb)
    if edge_compare_image.size != original_image.size:
        edge_compare_image = edge_compare_image.resize(original_image.size)
    edge_map_uri = _to_data_uri(edge_compare_image)
    components_html(
        f"""
<style>
#{edge_slider_id}.compare-wrap {{
    position: relative;
    width: 100%;
    margin: 8px auto 18px auto;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.35);
}}
#{edge_slider_id} .base-img,
#{edge_slider_id} .overlay-img img {{
    display: block;
    width: 100%;
    height: auto;
}}
#{edge_slider_id} .overlay-img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 50%;
    overflow: hidden;
}}
#{edge_slider_id} .divider {{
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
#{edge_slider_id} .divider::after {{
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
<div id="{edge_slider_id}" class="compare-wrap">
  <img class="base-img" src="{edge_original_uri}" alt="Original">
  <div class="overlay-img" id="{edge_slider_id}_overlay">
    <img src="{edge_map_uri}" alt="Edges">
  </div>
  <div class="divider" id="{edge_slider_id}_divider"></div>
</div>
<script>
(() => {{
  const container = document.getElementById("{edge_slider_id}");
  const slider = document.getElementById("{edge_slider_id}_divider");
  const overlay = document.getElementById("{edge_slider_id}_overlay");
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

  // Start at exact 50/50
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
        height=compare_component_height,
        scrolling=False,
    )

    edge_bytes = _encoded_bytes_for_download(edge_preview.convert("RGB"), "PNG")
    edge_filename = f"{processed_name_root}_edges.png"
    comparison_panel_bytes = _encoded_bytes_for_download(Image.fromarray(edge_panel_rgb), "PNG")
    comparison_panel_filename = f"{processed_name_root}_edge_comparison.png"

    dl_col_1, dl_col_2, dl_col_3, dl_col_4 = st.columns(4)
    with dl_col_1:
        st.download_button(
            "Download Original",
            data=original_bytes,
            file_name=original_filename,
            mime=_get_mime_type(original_filename),
            use_container_width=True,
        )
    with dl_col_2:
        st.download_button(
            "Download Processed Preview",
            data=processed_bytes,
            file_name=processed_filename,
            mime=_get_mime_type(processed_filename),
            use_container_width=True,
        )
    with dl_col_3:
        st.download_button(
            "Download Edge Map",
            data=edge_bytes,
            file_name=edge_filename,
            mime="image/png",
            use_container_width=True,
        )
    with dl_col_4:
        st.download_button(
            "Download Edge Comparison",
            data=comparison_panel_bytes,
            file_name=comparison_panel_filename,
            mime="image/png",
            use_container_width=True,
        )

    if st.button("Upload New Image", key="replace_uploaded_image_btn"):
        remove_temp_file(st.session_state.get("uploaded_image_path"))
        st.session_state["uploaded_image_path"] = ""
        st.session_state["uploaded_image_metadata"] = {}
        st.session_state["uploaded_image_signature"] = ""
        st.session_state["uploaded_image_confirmed"] = False
        st.session_state["upload_widget_nonce"] += 1
        st.rerun()
