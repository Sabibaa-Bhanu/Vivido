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

## Notes
- The local database is created automatically on first run.
- For production, move secrets/DB config to environment variables.

## Screens
Add screenshots in `assets/` and update this section.
