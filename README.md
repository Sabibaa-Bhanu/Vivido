# Vivido

**Vivido** is a Streamlit-based web app for AI-powered image stylization and cartoonization.  
It includes a custom-designed welcome screen, authentication flows (register/login), and a dashboard-ready structure for future features.

## Features
- Glassmorphism welcome page with Register/Login actions
- Register & login pages with validation and friendly UX
- SQLite-backed user management (local `data/` DB)
- Modular structure (`backend/`, `pages/`, `utils/`, `assets/`)
- OpenCV edge detection module for cartoonization foundations:
  - Canny edge detection with adjustable thresholds
  - Adaptive threshold edge detection for variable lighting
  - Median blur denoising pre-processing
  - Edge thickness and sensitivity controls
  - Original vs edge comparison panel generation
- Cartoon base effect module:
  - Bilateral filtering for paint-like smoothing with edge preservation
  - K-means color quantization (8-16 colors typical) for stylized palettes
  - Adjustable intensity/performance parameters
  - Runtime profiling across parameter combinations

## Tech Stack
- Python 3.x
- Streamlit
- SQLite (local)

## Project Structure
```
Vivido/
  app.py
  pages/
    welcome.py
    register.py
    login.py
    dashboard.py
    verify.py
  backend/
    database.py
    user_management.py
  utils/
    welcome_ui.py
  assets/
  data/
```

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Edge Detection Module
`utils/edge_detection.py` provides:
- `detect_edges_canny(...)`
- `detect_edges_adaptive(...)`
- `apply_median_blur(...)`
- `adjust_edge_thickness(...)`
- `detect_cartoon_edges(...)` using `EdgeParams`
- `compare_original_and_edges(...)`
- `recommended_params(image_type)` presets for:
  - `portrait`
  - `landscape`
  - `object`

### Recommended Cartoon Edge Settings
These defaults are tuned for cartoon-like edge maps and validated with synthetic portrait/landscape/object test scenes.

1. Portraits
- Method: `adaptive`
- `adaptive_block_size=11`
- `adaptive_c=3`
- `median_blur_kernel=7`
- `sensitivity=1.1`
- `edge_thickness=1`

2. Landscapes
- Method: `canny`
- `canny_low=60`
- `canny_high=150`
- `median_blur_kernel=5`
- `sensitivity=1.0`
- `edge_thickness=2`

3. Objects / Product Shots
- Method: `canny`
- `canny_low=80`
- `canny_high=180`
- `median_blur_kernel=5`
- `sensitivity=0.95`
- `edge_thickness=2`

### Run Edge Detection Tests
```bash
pytest tests/test_edge_detection.py
```

## Cartoonization Module
`utils/cartoonization.py` provides:
- `apply_bilateral_filter(...)`
- `color_quantize_kmeans(...)`
- `create_base_cartoon_effect(...)`
- `create_classic_cartoon(...)`
- `create_classic_cartoon_from_path(...)`
- `compare_original_and_cartoon(...)`
- `profile_parameter_combinations(...)`
- `benchmark_classic_cartoon(...)`
- `recommended_style_params(style)`
- `documented_style_settings()`

### Example Usage
```python
import cv2
from utils.cartoonization import CartoonParams, create_base_cartoon_effect

image = cv2.imread("input.jpg")
params = CartoonParams(
    num_colors=12,
    bilateral_d=9,
    bilateral_sigma_color=85.0,
    bilateral_sigma_space=85.0,
    bilateral_passes=2,
)
cartoon = create_base_cartoon_effect(image, params)
cv2.imwrite("cartoon_base.png", cartoon)
```

### Recommended Parameter Combinations by Artistic Style
1. Soft Paint
- Colors: `16`
- Bilateral: `d=9`, `sigma_color=60`, `sigma_space=60`, `passes=1`
- Notes: subtle stylization, retains more natural color variation.

2. Classic Cartoon
- Colors: `12`
- Bilateral: `d=9`, `sigma_color=85`, `sigma_space=85`, `passes=2`
- Notes: balanced cartoon look with clean regions and preserved boundaries.

3. Bold Poster
- Colors: `8`
- Bilateral: `d=7`, `sigma_color=95`, `sigma_space=95`, `passes=2`
- Notes: strong flattening and punchy graphic style.

4. Comic Ink
- Colors: `10`
- Bilateral: `d=11`, `sigma_color=110`, `sigma_space=100`, `passes=2`
- Notes: heavier smoothing, aggressive stylization for comic panels.

### Performance Guidance
- Use `downsample_scale` (for example `0.8-0.9`) to speed up high-resolution processing.
- Limit K-means training pixels via `sample_pixels` (for example `8000-14000`) for faster clustering.
- Use `profile_parameter_combinations(...)` to compare average processing times for style variants on your target hardware.

### Complete Classic Cartoon Pipeline
`create_classic_cartoon(...)` combines:
1. Preprocessing (resize + median denoise)
2. Bilateral smoothing
3. K-means color quantization
4. Edge detection (adaptive or Canny)
5. Black edge overlay on the color-reduced image

Intensity presets:
- `light`
- `medium`
- `strong`

Each preset balances quality vs speed. The medium preset is tuned for a strong visual result while keeping standard images within practical processing time.

### Run Cartoonization Tests
```bash
pytest tests/test_cartoonization.py
```

## Notes
- The local database is created automatically on first run.
- For production, move secrets/DB config to environment variables.

## Screens
Add screenshots in `assets/` and update this section.
