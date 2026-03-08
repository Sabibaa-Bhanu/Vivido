import streamlit as st
import base64
import io
import os
import mimetypes
from urllib.parse import quote, unquote
import numpy as np
import cv2
from PIL import Image

st.set_page_config(page_title="AI Styles - Vivido", page_icon="assets/logo/vivido_logo2.jpeg", layout="wide")

# Check authentication
if (
    not st.session_state.get("logged_in")
    and st.session_state.get("user_id")
    and st.session_state.get("current_user")
):
    st.session_state["logged_in"] = True

if not st.session_state.get("logged_in"):
    st.session_state["redirect_after_login"] = "pages/ai_styles.py"
    st.switch_page("pages/login.py")

# Initialize session state for selected style
if "ai_style_selected" not in st.session_state:
    st.session_state["ai_style_selected"] = None

# ============================================================
# STYLES DATA
# ============================================================

MEDIUM_STYLES = {
    "Stencil": {
        "description": "Bold, graphic style with layered cut-out designs",
        "color": "#e74c3c",
        "emoji": "🔴"
    },
    "Watercolor": {
        "description": "Soft, flowing pigments with transparent washes",
        "color": "#3498db",
        "emoji": "🔵"
    },
    "Marker Illustration": {
        "description": "Vibrant, bold lines with marker-based coloring",
        "color": "#9b59b6",
        "emoji": "🟣"
    },
    "Risograph": {
        "description": "Retro, grainy print effect with offset colors",
        "color": "#f39c12",
        "emoji": "🟠"
    },
    "Graffiti": {
        "description": "Street art style with spray paint effects",
        "color": "#1abc9c",
        "emoji": "🟢"
    },
    "Oil Painting": {
        "description": "Rich, textured brushstrokes with impasto effects",
        "color": "#e67e22",
        "emoji": "🟤"
    },
    "Mosaic": {
        "description": "Tile-based pattern with tessellated fragments",
        "color": "#2ecc71",
        "emoji": "🧩"
    }
}

PHOTOGRAPHY_STYLES = {
    "High Key/Low Key": {
        "description": "High key: bright, minimal shadows. Low key: dark, dramatic lighting",
        "color": "#ecf0f1",
        "emoji": "☀️"
    },
    "Low Angle/High Angle": {
        "description": "Low: dramatic perspective from below. High: bird's eye view from above",
        "color": "#bdc3c7",
        "emoji": "📐"
    },
    "Extreme Close-up": {
        "description": "Macro photography revealing intricate details",
        "color": "#95a5a6",
        "emoji": "🔍"
    },
    "Low Shutter Speed": {
        "description": "Motion blur effects with long exposure",
        "color": "#7f8c8d",
        "emoji": "🌊"
    },
    "Bokeh": {
        "description": "Beautiful background blur with circular light spots",
        "color": "#d5dbdb",
        "emoji": "✨"
    },
    "Bird's-Eye View": {
        "description": "Top-down overhead perspective shot",
        "color": "#aeb6bf",
        "emoji": "🕊️"
    },
    "Black and White": {
        "description": "Monochrome photography with grayscale tones",
        "color": "#2c3e50",
        "emoji": "⬛"
    }
}

LIGHTING_STYLES = {
    "Natural Lighting": {
        "description": "Soft daylight using sun as light source",
        "color": "#f1c40f",
        "emoji": "🌤️"
    },
    "Light and Shadow": {
        "description": "Chiaroscuro with strong contrast between light and dark",
        "color": "#34495e",
        "emoji": "🌑"
    },
    "Volumetric Lighting": {
        "description": "God rays and light beams through atmosphere",
        "color": "#d35400",
        "emoji": "🌅"
    },
    "Neon Lighting": {
        "description": "Vibrant neon tubes with colorful glow effects",
        "color": "#e91e63",
        "emoji": "🌈"
    },
    "Golden Hour": {
        "description": "Warm sunset/golden light during sunrise/sunset",
        "color": "#f39c12",
        "emoji": "🌇"
    },
    "Candlelight": {
        "description": "Warm, intimate flickering candle illumination",
        "color": "#e67e22",
        "emoji": "🕯️"
    },
    "Fairy Lights": {
        "description": "String lights with magical twinkling effect",
        "color": "#9b59b6",
        "emoji": "💫"
    },
    "Street Lighting": {
        "description": "Urban night lights with city ambiance",
        "color": "#3498db",
        "emoji": "🏙️"
    }
}

COLOR_PALETTE_STYLES = {
    "Cool/Warm Tone": {
        "description": "Cool: blues/greens. Warm: oranges/reds. Contrasting temperature",
        "color": "#2980b9",
        "emoji": "🌡️"
    },
    "Pastels/Vibrant": {
        "description": "Pastels: soft, muted colors. Vibrant: bold, saturated hues",
        "color": "#ff69b4",
        "emoji": "🎀"
    },
    "Earth/Jewel Tones": {
        "description": "Earth: browns/greens. Jewel: rich宝石 colors",
        "color": "#27ae60",
        "emoji": "💎"
    },
    "Autumn Leaves": {
        "description": "Warm oranges, reds, yellows of fall foliage",
        "color": "#d35400",
        "emoji": "🍂"
    },
    "Metallics": {
        "description": "Gold, silver, bronze with reflective metallic sheen",
        "color": "#bdc3c7",
        "emoji": "🥈"
    }
}

STYLE_SAMPLE_IMAGES = {
    # Medium styles
    ("Medium", "Stencil"): "assets/style_samples/stencil.jpeg",
    ("Medium", "Watercolor"): "assets/style_samples/watercolor.jpeg",
    ("Medium", "Marker Illustration"): "assets/style_samples/Marker Illustration.jpeg",
    ("Medium", "Risograph"): "assets/style_samples/Risograph.jpeg",
    ("Medium", "Graffiti"): "assets/style_samples/Graffiti.jpeg",
    ("Medium", "Oil Painting"): "assets/style_samples/Oil Painting.jpeg",
    ("Medium", "Mosaic"): "assets/style_samples/Mosaic.jpeg",
    
    # Photography styles
    ("Photography", "High Key/Low Key"): "assets/style_samples/High Key Low Key.jpeg",
    ("Photography", "Low Angle/High Angle"): "assets/style_samples/Low Angle High Angle.jpeg",
    ("Photography", "Extreme Close-up"): "assets/style_samples/Extreme Close-up .jpeg",
    ("Photography", "Low Shutter Speed"): "assets/style_samples/Low Shutter Speed.jpeg",
    ("Photography", "Bokeh"): "assets/style_samples/Bokeh.jpeg",
    ("Photography", "Bird's-Eye View"): "assets/style_samples/Bokeh.jpeg",
    ("Photography", "Black and White"): "assets/style_samples/Black and white.jpeg",
    
    # Lighting styles
    ("Lighting", "Natural Lighting"): "assets/style_samples/Natural Lighting.jpeg",
    ("Lighting", "Light and Shadow"): "assets/style_samples/Light and Shadow.jpeg",
    ("Lighting", "Volumetric Lighting"): "assets/style_samples/Volumetric Lighting.jpeg",
    ("Lighting", "Neon Lighting"): "assets/style_samples/Neon Lighting.jpeg",
    ("Lighting", "Golden Hour"): "assets/style_samples/Golden Hour.jpeg",
    ("Lighting", "Candlelight"): "assets/style_samples/Candle light.jpeg",
    ("Lighting", "Fairy Lights"): "assets/style_samples/Fairy Lights.jpeg",
    ("Lighting", "Street Lighting"): "assets/style_samples/Street Lighting.jpeg",
    
    # Color & Palette styles
    ("Color & Palette", "Cool/Warm Tone"): "assets/style_samples/Cool Warm Tone.jpeg",
    ("Color & Palette", "Pastels/Vibrant"): "assets/style_samples/Pastels Vibrant.jpeg",
    ("Color & Palette", "Earth/Jewel Tones"): "assets/style_samples/Earth Jewel Tones.jpeg",
    ("Color & Palette", "Autumn Leaves"): "assets/style_samples/Autumn Leaves.jpeg",
    ("Color & Palette", "Metallics"): "assets/style_samples/Metallics.jpeg",
}


def _set_style_from_key(style_key):
    style_groups = {
        "medium_": ("Medium", MEDIUM_STYLES),
        "photo_": ("Photography", PHOTOGRAPHY_STYLES),
        "light_": ("Lighting", LIGHTING_STYLES),
        "color_": ("Color & Palette", COLOR_PALETTE_STYLES),
    }

    for prefix, (category, style_dict) in style_groups.items():
        if style_key.startswith(prefix):
            style_name = style_key[len(prefix):]
            style_info = style_dict.get(style_name)
            if style_info:
                st.session_state["ai_style_selected"] = style_key
                st.session_state["ai_style_info"] = {
                    "name": style_name,
                    "category": category,
                    "description": style_info["description"],
                    "color": style_info["color"],
                }
            return


picked_style = st.query_params.get("pick_style")
if picked_style:
    _set_style_from_key(unquote(str(picked_style)))
    st.query_params.clear()
    st.rerun()

# ============================================================
# CSS STYLES
# ============================================================

st.markdown("""
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
}

* { font-family: 'Poppins', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0b0e1a 0%, #12091f 50%, #0b0e1a 100%);
    color: var(--text-primary);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #0d0b1a 100%) !important;
    border-right: 1px solid rgba(124, 58, 237, 0.2) !important;
}

.header-section {
    background: linear-gradient(135deg, rgba(18, 24, 42, 0.95), rgba(15, 12, 30, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
}

.category-title {
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.category-desc {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 20px;
}

.style-box {
    background: linear-gradient(135deg, rgba(20, 26, 44, 0.95), rgba(15, 23, 42, 0.95));
    border: 2px solid var(--box-color);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    margin-bottom: 12px;
}

.style-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}

@media (max-width: 1200px) {
    .style-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 900px) {
    .style-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

.style-box:hover {
    transform: scale(1.05);
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

.style-box.selected {
    border-color: #7c3aed;
    box-shadow: 0 0 25px rgba(124, 58, 237, 0.5);
}

.style-box-emoji {
    font-size: 2rem;
    margin: auto;
    text-align: center;
}

.style-box-label {
    color: #f8fafc;
    font-size: 0.85rem;
    font-weight: 700;
    text-align: center;
    margin-top: 8px;
    word-wrap: break-word;
    white-space: normal;
    padding: 0 4px;
}

.style-name-below {
    color: #f8fafc;
    font-size: 0.75rem;
    font-weight: 700;
    text-align: center;
    margin-top: 8px;
    min-height: 44px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    line-height: 1.2;
    padding: 0 4px;
    word-wrap: break-word;
    white-space: normal;
}

.style-sample {
    width: 100%;
    height: 100%;
    overflow: hidden;
    border-radius: 10px;
    background: rgba(30, 41, 59, 0.45);
}

.style-sample img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.style-link {
    text-decoration: none;
    display: block;
}

.style-name-link {
    text-decoration: none;
    display: block;
}

.preview-panel {
    background: linear-gradient(135deg, rgba(18, 24, 42, 0.95), rgba(15, 12, 30, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 16px;
    padding: 24px;
    height: 100%;
}

.preview-title {
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 8px;
}

.preview-desc {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 20px;
}

.confirm-btn {
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    border: none;
    border-radius: 10px;
    padding: 14px 28px;
    color: white;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
    width: 100%;
    margin-top: 20px;
}

.confirm-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(124, 58, 237, 0.4);
}

.back-btn {
    background: rgba(148, 163, 184, 0.2);
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 10px;
    padding: 12px 24px;
    color: var(--text-secondary);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-right: 12px;
}

.back-btn:hover {
    background: rgba(148, 163, 184, 0.3);
    color: var(--text-primary);
}

.uploaded-image-section {
    background: linear-gradient(135deg, rgba(18, 24, 42, 0.95), rgba(15, 12, 30, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 24px;
}

.section-label {
    color: var(--text-secondary);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
}

.stButton > button {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: 8px;
    color: #f8fafc;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 8px 4px;
    height: auto;
    min-height: 40px;
    white-space: normal;
    word-wrap: break-word;
    line-height: 1.3;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.3), rgba(6, 182, 212, 0.2));
    border-color: rgba(124, 58, 237, 0.6);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _style_sample_data_uri(category, style_name):
    # Sample images are for UI preview/design only (not used for style processing).
    sample_path = STYLE_SAMPLE_IMAGES.get((category, style_name))
    if not sample_path:
        return ""
    if not os.path.exists(sample_path):
        return ""

    mime_type, _ = mimetypes.guess_type(sample_path)
    if not mime_type:
        mime_type = "image/jpeg"

    try:
        with open(sample_path, "rb") as sample_file:
            encoded = base64.b64encode(sample_file.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
    except OSError:
        return ""


def apply_style_preview(image_rgb, style_name, category):
    """Apply a preview effect to the image based on style with improved quality"""
    processed = image_rgb.copy()
    
    # First, upscale the image for better quality processing
    h, w = processed.shape[:2]
    if w < 1200 or h < 1200:
        # Upscale for better quality
        scale = max(1200/w, 1200/h, 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        processed = cv2.resize(processed, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    if category == "Medium":
        # Apply different medium effects with improved quality
        if style_name == "Stencil":
            # High quality stencil look with better edge detection
            gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
            # Use larger bilateral filter for smoother result
            smooth = cv2.bilateralFilter(gray, 13, 80, 80)
            # Use larger kernel for better edges
            grad_x = cv2.Sobel(smooth, cv2.CV_16S, 1, 0, ksize=5)
            grad_y = cv2.Sobel(smooth, cv2.CV_16S, 0, 1, ksize=5)
            edges = cv2.addWeighted(
                cv2.convertScaleAbs(grad_x), 0.5,
                cv2.convertScaleAbs(grad_y), 0.5, 0
            )
            # Adjust threshold for better edge detection
            _, edge_mask = cv2.threshold(edges, 30, 255, cv2.THRESH_BINARY)
            base_tones = cv2.equalizeHist(smooth)
            # Use larger bilateral filter for smoother tones
            base_tones = cv2.bilateralFilter(base_tones, 11, 60, 60)
            base_rgb = cv2.cvtColor(base_tones, cv2.COLOR_GRAY2RGB)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge_mask), cv2.COLOR_GRAY2RGB)
            # Better blending ratio for more detail
            processed = cv2.addWeighted(base_rgb, 0.85, edge_rgb, 0.15, 0)
            
        elif style_name == "Watercolor":
            # High quality watercolor with better smoothing
            base = cv2.bilateralFilter(processed, 15, 120, 120)
            base = cv2.bilateralFilter(base, 11, 90, 90)
            base = cv2.GaussianBlur(base, (7, 7), 0)
            # Less aggressive posterization for more detail
            poster = ((base.astype(np.uint16) // 32) * 32 + 16).clip(0, 255).astype(np.uint8)
            # Better blending
            blended = cv2.addWeighted(base, 0.65, poster, 0.35, 0)
            hsv = cv2.cvtColor(blended, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.75  # less saturation reduction
            hsv[:, :, 2] *= 1.08  # slight brightness lift
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            blended = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            blended = cv2.convertScaleAbs(blended, alpha=0.95, beta=5)
            # Subtle edge preservation
            edge = cv2.Canny(cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY), 50, 120)
            edge_soft = cv2.GaussianBlur(edge, (5, 5), 0)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge_soft), cv2.COLOR_GRAY2RGB)
            processed = cv2.addWeighted(blended, 0.94, edge_rgb, 0.06, 0)
            
        elif style_name == "Marker Illustration":
            # High quality marker look with better color blocks
            base = cv2.bilateralFilter(processed, 13, 100, 100)
            base = cv2.medianBlur(base, 5)
            # Less quantization for more detail
            quant = ((base.astype(np.uint16) // 24) * 24 + 12).clip(0, 255).astype(np.uint8)
            blended = cv2.addWeighted(base, 0.75, quant, 0.25, 0)
            hsv = cv2.cvtColor(blended, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 1.35  # higher saturation
            hsv[:, :, 2] *= 1.05  # slight brightness boost
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            blended = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            blended = cv2.convertScaleAbs(blended, alpha=1.15, beta=5)
            # Better edge detection
            edge = cv2.Canny(cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY), 50, 120)
            edge = cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1)
            edge_rgb = cv2.cvtColor(cv2.bitwise_not(edge), cv2.COLOR_GRAY2RGB)
            processed = cv2.addWeighted(blended, 0.92, edge_rgb, 0.08, 0)
            
        elif style_name == "Risograph":
            # Better risograph with improved color layers
            soft = cv2.GaussianBlur(processed, (5, 5), 0)
            # Less quantization for more detail
            quant = ((soft.astype(np.uint16) // 48) * 48 + 24).clip(0, 255).astype(np.uint8)
            # Build better pseudo-ink layers
            r = quant[:, :, 0].astype(np.float32)
            g = quant[:, :, 1].astype(np.float32)
            b = quant[:, :, 2].astype(np.float32)
            blue_layer = np.clip(0.6 * b + 0.3 * g, 0, 255)
            coral_layer = np.clip(0.65 * r + 0.2 * g, 0, 255)
            yellow_layer = np.clip(0.5 * r + 0.4 * g, 0, 255)
            # Slight misregistration
            blue_shift = np.roll(blue_layer, shift=2, axis=1)
            coral_shift = np.roll(coral_layer, shift=2, axis=0)
            y = yellow_layer.astype(np.uint8)
            c = coral_shift.astype(np.uint8)
            bl = blue_shift.astype(np.uint8)
            composed = np.dstack([c, y, bl])
            # Less noise for cleaner look
            noise = np.random.default_rng(42).normal(0, 5, composed.shape).astype(np.float32)
            composed = np.clip(composed.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            processed = cv2.convertScaleAbs(composed, alpha=1.12, beta=5)
            
        elif style_name == "Graffiti":
            # Better graffiti with more vibrant colors
            processed = cv2.convertScaleAbs(processed, alpha=1.35, beta=5)
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 1.4
            hsv[:, :, 2] *= 1.08
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            # Less speckle for cleaner look
            speckle = np.random.default_rng(24).normal(0, 4, processed.shape).astype(np.float32)
            processed = np.clip(processed.astype(np.float32) + speckle, 0, 255).astype(np.uint8)
            
        elif style_name == "Oil Painting":
            # High quality oil painting with better texture
            processed = cv2.edgePreservingFilter(processed, flags=1, sigma_s=80, sigma_r=0.5)
            processed = cv2.bilateralFilter(processed, 13, 100, 100)
            processed = cv2.convertScaleAbs(processed, alpha=1.25, beta=5)
            processed = cv2.medianBlur(processed, 5)
            
        elif style_name == "Mosaic":
            # Better mosaic with larger tiles for quality
            h, w = processed.shape[:2]
            # Larger tiles for better quality
            tile_size = 12
            new_w = (w // tile_size) * tile_size
            new_h = (h // tile_size) * tile_size
            processed = cv2.resize(processed, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            # Better median blur
            processed = cv2.medianBlur(processed, 7)
            # High quality resize back
            processed = cv2.resize(processed, (w, h), interpolation=cv2.INTER_LANCZOS4)
            # Subtle edge enhancement
            edges = cv2.Canny(processed, 40, 120)
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            processed = cv2.bitwise_and(processed, processed, mask=cv2.bitwise_not(edges))
            processed = cv2.add(processed, edges_colored // 4)
    
    elif category == "Photography":
        if style_name == "High Key/Low Key":
            # High key - brighten with better quality
            processed = cv2.convertScaleAbs(processed, alpha=1.2, beta=30)
            # Add subtle smoothing
            processed = cv2.bilateralFilter(processed, 9, 50, 50)
        elif style_name == "Low Angle/High Angle":
            # Perspective transformation - flip vertically for high angle effect
            processed = cv2.flip(processed, 0)
        elif style_name == "Extreme Close-up":
            # Crop center and resize back with high quality
            h, w = processed.shape[:2]
            processed = processed[h//4:3*h//4, w//4:3*w//4]
            processed = cv2.resize(processed, (w, h), interpolation=cv2.INTER_LANCZOS4)
        elif style_name == "Low Shutter Speed":
            # Motion blur with better quality kernel
            kernel_size = 25
            kernel = np.zeros((kernel_size, kernel_size))
            kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
            kernel = kernel / kernel_size
            processed = cv2.filter2D(processed, -1, kernel)
        elif style_name == "Bokeh":
            # Better bokeh effect with preserved highlights
            processed = cv2.bilateralFilter(processed, 11, 80, 80)
            processed = cv2.GaussianBlur(processed, (25, 25), 0)
        elif style_name == "Bird's-Eye View":
            # Top-down perspective - flip horizontally
            processed = cv2.flip(processed, 1)
        elif style_name == "Black and White":
            # High quality grayscale with contrast enhancement
            gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
            # Apply CLAHE for better contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    
    elif category == "Lighting":
        if style_name == "Natural Lighting":
            # Brighten and warm with better quality
            processed = cv2.convertScaleAbs(processed, alpha=1.12, beta=18)
            # Warm tint
            processed = processed.astype(np.float32)
            processed[:, :, 2] *= 1.12  # More red
            processed[:, :, 0] *= 0.92  # Less blue
            processed = np.clip(processed, 0, 255).astype(np.uint8)
            # Add subtle smoothing
            processed = cv2.bilateralFilter(processed, 7, 40, 40)
        elif style_name == "Light and Shadow":
            # High contrast with better quality
            processed = cv2.convertScaleAbs(processed, alpha=1.4, beta=5)
        elif style_name == "Volumetric Lighting":
            # Better light rays with improved glow
            processed = cv2.convertScaleAbs(processed, alpha=1.18, beta=25)
            blur = cv2.GaussianBlur(processed, (35, 35), 0)
            processed = cv2.addWeighted(processed, 0.72, blur, 0.28, 0)
        elif style_name == "Neon Lighting":
            # Better saturation with improved glow
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 1.7  # High saturation
            hsv[:, :, 2] *= 1.12  # Slight brightness
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            # Better glow effect
            blur = cv2.GaussianBlur(processed, (17, 17), 0)
            processed = cv2.addWeighted(processed, 0.82, blur, 0.18, 0)
        elif style_name == "Golden Hour":
            # Warm orange tint with better quality
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 0.72  # Reduce blue
            processed[:, :, 1] *= 0.92  # Slight green reduction
            processed[:, :, 2] *= 1.28  # Increase red
            processed = np.clip(processed, 0, 255).astype(np.uint8)
            processed = cv2.convertScaleAbs(processed, alpha=1.08, beta=12)
        elif style_name == "Candlelight":
            # Warm dim with better quality
            processed = cv2.convertScaleAbs(processed, alpha=0.88, beta=5)
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 0.82  # Less blue
            processed[:, :, 1] *= 0.92  # Slight green reduction
            processed[:, :, 2] *= 1.18  # More red
            processed = np.clip(processed, 0, 255).astype(np.uint8)
        elif style_name == "Fairy Lights":
            # Better glow effect with color enhancement
            processed = cv2.convertScaleAbs(processed, alpha=1.08, beta=15)
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 1.2
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            # Softer glow
            blur = cv2.GaussianBlur(processed, (23, 23), 0)
            processed = cv2.addWeighted(processed, 0.78, blur, 0.22, 0)
        elif style_name == "Street Lighting":
            # Better cool tint
            processed = cv2.convertScaleAbs(processed, alpha=0.92, beta=0)
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 1.18  # More blue
            processed[:, :, 1] *= 1.02
            processed[:, :, 2] *= 0.88   # Less red
            processed = np.clip(processed, 0, 255).astype(np.uint8)
    
    elif category == "Color & Palette":
        if style_name == "Cool/Warm Tone":
            # Better cool tone
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 0] = (hsv[:, :, 0] + 35) % 180  # Shift hue towards blue
            hsv[:, :, 1] *= 1.12  # Increase saturation
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        elif style_name == "Pastels/Vibrant":
            # Better pastels with improved softness
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.65  # Reduce saturation
            hsv[:, :, 2] *= 1.12  # Increase brightness
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            # Better bilateral filter for soft look
            processed = cv2.bilateralFilter(processed, 9, 60, 60)
        elif style_name == "Earth/Jewel Tones":
            # Better earth tones
            processed = processed.astype(np.float32)
            processed[:, :, 1] *= 1.28  # More green
            processed[:, :, 0] *= 0.88   # Less red
            processed[:, :, 2] *= 0.82  # Less blue
            processed = np.clip(processed, 0, 255).astype(np.uint8)
            processed = cv2.convertScaleAbs(processed, alpha=1.08, beta=8)
        elif style_name == "Autumn Leaves":
            # Better orange/red shift
            processed = processed.astype(np.float32)
            processed[:, :, 0] *= 1.38  # More red
            processed[:, :, 1] *= 0.88   # Less green
            processed[:, :, 2] *= 0.72  # Less blue
            processed = np.clip(processed, 0, 255).astype(np.uint8)
            processed = cv2.convertScaleAbs(processed, alpha=1.12, beta=12)
        elif style_name == "Metallics":
            # Better metallic with improved sheen
            lab = cv2.cvtColor(processed, cv2.COLOR_RGB2LAB)
            l, a, b = np.split(lab, 3, axis=2)
            l = l.squeeze()
            # Enhance L channel more
            l = cv2.convertScaleAbs(l, alpha=1.35, beta=12)
            lab = cv2.merge([l, a.squeeze(), b.squeeze()])
            processed = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
            # Better desaturation
            hsv = cv2.cvtColor(processed, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.8
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            processed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    
    # Final quality enhancement - sharpen the image slightly
    processed = cv2.convertScaleAbs(processed, alpha=1.02, beta=2)
    
    return processed


# ============================================================
# SIDEBAR
# ============================================================

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
    
    if st.button("🔓 Logout", key="sidebar_logout_btn", width='stretch'):
        from backend.user_management import revoke_remember_token
        remember_token = st.session_state.get("remember_token", "")
        if remember_token:
            revoke_remember_token(remember_token)
        st.session_state.clear()
        st.session_state["just_logged_out"] = True
        st.switch_page("pages/login.py")

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="header-section">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div class="category-title">🤖 AI Art Styles</div>
            <div class="category-desc">Select an art style to apply to your image</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SHOW UPLOADED IMAGE
# ============================================================

uploaded_image = None
uploaded_image_path = st.session_state.get("uploaded_image_path", "")

if uploaded_image_path and os.path.exists(uploaded_image_path):
    st.markdown(f"""
    <div class="uploaded-image-section">
        <div class="section-label">Your Uploaded Image</div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        with Image.open(uploaded_image_path) as uploaded_img:
            uploaded_image = uploaded_img.convert("RGB")
            st.image(uploaded_image, caption="Ready for style application", width=260)
    except Exception as e:
        st.error(f"Error loading image: {e}")
elif not uploaded_image_path:
    st.info("No image uploaded yet. Please upload an image in Image Processing first.")

# ============================================================
# TWO-COLUMN LAYOUT
# ============================================================

col1, col2 = st.columns([1.5, 1])

with col1:
    # ============================================================
    # MEDIUM (ART STYLES) SECTION
    # ============================================================
    st.markdown('''
    <div style="margin-top: 8px; margin-bottom: 20px;">
        <div class="category-title" style="font-size: 1.4rem;">🎨 Medium</div>
        <div class="category-desc" style="font-size: 0.9rem;">Art medium styles for your image</div>
    </div>
    ''', unsafe_allow_html=True)
    
    medium_cols = st.columns(4)
    medium_items = list(MEDIUM_STYLES.items())
    
    for idx, (style_name, style_info) in enumerate(medium_items):
        with medium_cols[idx % 4]:
            color = style_info["color"]
            emoji = style_info["emoji"]
            sample_uri = _style_sample_data_uri("Medium", style_name)
            style_key = f"medium_{style_name}"
            style_link = quote(style_key, safe="")
            sample_markup = (
                f'<div class="style-sample"><img src="{sample_uri}" alt="{style_name} sample"></div>'
                if sample_uri else
                f'<div class="style-box-emoji">{emoji}</div>'
            )
            
            # Custom styled button as a box
            is_selected = st.session_state.get("ai_style_selected") == f"medium_{style_name}"
            border_style = "border-color: #7c3aed;" if is_selected else f"border-color: {color};"
            box_shadow = "box-shadow: 0 0 25px rgba(124, 58, 237, 0.5);" if is_selected else ""
            
            st.markdown(f"""
            <a class="style-link" href="#" onclick="window.location.href = window.location.pathname + '?pick_style={style_link}'; return false;">
                <div class="style-box" style="{border_style} {box_shadow} --box-color: {color};">
                    {sample_markup}
                </div>
            </a>
            """, unsafe_allow_html=True)

            if st.button(style_name, key=f"style_name_medium_{idx}", use_container_width=True):
                _set_style_from_key(style_key)
                st.rerun()
    
    st.markdown("---")
    
    # ============================================================
    # PHOTOGRAPHY SECTION
    # ============================================================
    st.markdown('''
    <div style="margin-top: 24px; margin-bottom: 20px;">
        <div class="category-title" style="font-size: 1.4rem;">📷 Photography</div>
        <div class="category-desc" style="font-size: 0.9rem;">Photography techniques and styles</div>
    </div>
    ''', unsafe_allow_html=True)
    
    photo_cols = st.columns(4)
    photo_items = list(PHOTOGRAPHY_STYLES.items())
    
    for idx, (style_name, style_info) in enumerate(photo_items):
        with photo_cols[idx % 4]:
            color = style_info["color"]
            emoji = style_info["emoji"]
            sample_uri = _style_sample_data_uri("Photography", style_name)
            style_key = f"photo_{style_name}"
            style_link = quote(style_key, safe="")
            sample_markup = (
                f'<div class="style-sample"><img src="{sample_uri}" alt="{style_name} sample"></div>'
                if sample_uri else
                f'<div class="style-box-emoji">{emoji}</div>'
            )
            
            is_selected = st.session_state.get("ai_style_selected") == f"photo_{style_name}"
            border_style = "border-color: #7c3aed;" if is_selected else f"border-color: {color};"
            box_shadow = "box-shadow: 0 0 25px rgba(124, 58, 237, 0.5);" if is_selected else ""
            
            st.markdown(f"""
            <a class="style-link" href="#" onclick="window.location.href = window.location.pathname + '?pick_style={style_link}'; return false;">
                <div class="style-box" style="{border_style} {box_shadow} --box-color: {color};">
                    {sample_markup}
                </div>
            </a>
            """, unsafe_allow_html=True)

            if st.button(style_name, key=f"style_name_photo_{idx}", use_container_width=True):
                _set_style_from_key(style_key)
                st.rerun()
    
    st.markdown("---")
    
    # ============================================================
    # LIGHTING SECTION
    # ============================================================
    st.markdown('''
    <div style="margin-top: 24px; margin-bottom: 20px;">
        <div class="category-title" style="font-size: 1.4rem;">💡 Lighting</div>
        <div class="category-desc" style="font-size: 0.9rem;">Lighting effects and conditions</div>
    </div>
    ''', unsafe_allow_html=True)
    
    light_cols = st.columns(4)
    light_items = list(LIGHTING_STYLES.items())
    
    for idx, (style_name, style_info) in enumerate(light_items):
        with light_cols[idx % 4]:
            color = style_info["color"]
            emoji = style_info["emoji"]
            sample_uri = _style_sample_data_uri("Lighting", style_name)
            style_key = f"light_{style_name}"
            style_link = quote(style_key, safe="")
            sample_markup = (
                f'<div class="style-sample"><img src="{sample_uri}" alt="{style_name} sample"></div>'
                if sample_uri else
                f'<div class="style-box-emoji">{emoji}</div>'
            )
            
            is_selected = st.session_state.get("ai_style_selected") == f"light_{style_name}"
            border_style = "border-color: #7c3aed;" if is_selected else f"border-color: {color};"
            box_shadow = "box-shadow: 0 0 25px rgba(124, 58, 237, 0.5);" if is_selected else ""
            
            st.markdown(f"""
            <a class="style-link" href="#" onclick="window.location.href = window.location.pathname + '?pick_style={style_link}'; return false;">
                <div class="style-box" style="{border_style} {box_shadow} --box-color: {color};">
                    {sample_markup}
                </div>
            </a>
            """, unsafe_allow_html=True)

            if st.button(style_name, key=f"style_name_light_{idx}", use_container_width=True):
                _set_style_from_key(style_key)
                st.rerun()
    
    st.markdown("---")
    
    # ============================================================
    # COLOR AND PALETTE SECTION
    # ============================================================
    st.markdown('''
    <div style="margin-top: 24px; margin-bottom: 20px;">
        <div class="category-title" style="font-size: 1.4rem;">🎭 Color & Palette</div>
        <div class="category-desc" style="font-size: 0.9rem;">Color schemes and tonal preferences</div>
    </div>
    ''', unsafe_allow_html=True)
    
    color_cols = st.columns(4)
    color_items = list(COLOR_PALETTE_STYLES.items())
    
    for idx, (style_name, style_info) in enumerate(color_items):
        with color_cols[idx % 4]:
            color = style_info["color"]
            emoji = style_info["emoji"]
            sample_uri = _style_sample_data_uri("Color & Palette", style_name)
            style_key = f"color_{style_name}"
            style_link = quote(style_key, safe="")
            sample_markup = (
                f'<div class="style-sample"><img src="{sample_uri}" alt="{style_name} sample"></div>'
                if sample_uri else
                f'<div class="style-box-emoji">{emoji}</div>'
            )
            
            is_selected = st.session_state.get("ai_style_selected") == f"color_{style_name}"
            border_style = "border-color: #7c3aed;" if is_selected else f"border-color: {color};"
            box_shadow = "box-shadow: 0 0 25px rgba(124, 58, 237, 0.5);" if is_selected else ""
            
            st.markdown(f"""
            <a class="style-link" href="#" onclick="window.location.href = window.location.pathname + '?pick_style={style_link}'; return false;">
                <div class="style-box" style="{border_style} {box_shadow} --box-color: {color};">
                    {sample_markup}
                </div>
            </a>
            """, unsafe_allow_html=True)

            if st.button(style_name, key=f"style_name_color_{idx}", use_container_width=True):
                _set_style_from_key(style_key)
                st.rerun()

with col2:
    # ============================================================
    # PREVIEW PANEL
    # ============================================================
    st.markdown('<div class="preview-panel">', unsafe_allow_html=True)
    
    if st.session_state.get("ai_style_info"):
        style_info = st.session_state["ai_style_info"]
        
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
        ">
            <div style="color: #f8fafc; font-size: 1.4rem; font-weight: 700; margin-bottom: 8px;">{style_info["name"]}</div>
            <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 12px;">{style_info["description"]}</div>
            <div style="color: {style_info["color"]}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;">
                Category: {style_info["category"]}
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Show preview with uploaded image if available
        if uploaded_image is not None:
            original_rgb = np.array(uploaded_image)
            
            # Apply style preview
            styled_image = apply_style_preview(original_rgb, style_info["name"], style_info["category"])
            
            # Show only styled image
            st.image(styled_image, caption=f"{style_info['name']} Style Applied", use_container_width=True)
        else:
            # Show placeholder preview
            color = style_info.get("color", "#7c3aed")
            st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, {color}40, {color}80);
                border: 2px dashed {color};
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                margin-bottom: 20px;
            ">
                <div style="font-size: 4rem; margin-bottom: 16px;">🖼️</div>
                <div style="color: var(--text-secondary); font-size: 0.9rem;">
                    Style Preview<br>
                    <span style="font-size: 0.8rem;">{style_info["name"]}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            st.info("Upload an image in Image Processing to see preview")
        
        # Confirm button
        if st.button("✓ Confirm Style", key="confirm_ai_style_btn", use_container_width=True):
            st.session_state["confirmed_ai_style"] = st.session_state["ai_style_info"]
            st.success(f"Style '{style_info['name']}' confirmed! Redirecting to Image Processing...")
            
            # Small delay then redirect
            import time
            time.sleep(1)
            st.switch_page("pages/image_processing.py")
        
        # Clear selection button
        if st.button("✗ Clear Selection", key="clear_ai_style_btn", use_container_width=True):
            st.session_state["ai_style_selected"] = None
            st.session_state["ai_style_info"] = None
            st.rerun()
    
    else:
        st.markdown('''
        <div style="
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(6, 182, 212, 0.05));
            border: 1px dashed rgba(124, 58, 237, 0.3);
            border-radius: 16px;
            padding: 60px 20px;
            text-align: center;
        ">
            <div style="font-size: 3rem; margin-bottom: 16px;">🎨</div>
            <div style="color: #94a3b8; font-size: 0.95rem;">
                Select a style from the left panel<br>
                <span style="font-size: 0.8rem; color: #64748b;">Click on any style to preview</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# BACK BUTTON
# ============================================================

st.markdown("<br><br>", unsafe_allow_html=True)
back_col1, back_col2 = st.columns([1, 4])
with back_col1:
    if st.button("← Back to Image Processing", key="back_to_processing_btn", use_container_width=True):
        st.switch_page("pages/image_processing.py")
