# Vivido

**Vivido** is a Streamlit-based web app for AI-powered image stylization and cartoonization.  
It includes a custom-designed welcome screen, authentication flows (register/login), and a dashboard-ready structure for future features.

## Features
- Glassmorphism welcome page with Register/Login actions
- Register & login pages with validation and friendly UX
- SQLite-backed user management (local `data/` DB)
- Modular structure (`backend/`, `pages/`, `utils/`, `assets/`)

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

## Notes
- The local database is created automatically on first run.
- For production, move secrets/DB config to environment variables.

## Screens
Add screenshots in `assets/` and update this section.
