import streamlit as st


def render_welcome_page() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
  --primary: #06b6d4;
  --secondary: #7c3aed;
  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
  --card-bg: rgba(15, 23, 42, 0.55);
  --card-border: rgba(148, 163, 184, 0.28);
  --glow-strong: rgba(6, 182, 212, 0.45);
  --glow-soft: rgba(124, 58, 237, 0.35);
}

* { font-family: 'Poppins', sans-serif; }

.stApp {
  background: linear-gradient(135deg, #0b1224 0%, #140e2a 50%, #0b1224 100%);
  color: var(--text-primary);
}

.stApp > div:first-child::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 12% 18%, rgba(6, 182, 212, 0.2), transparent 45%),
    radial-gradient(circle at 88% 12%, rgba(124, 58, 237, 0.18), transparent 40%),
    radial-gradient(circle at 50% 80%, rgba(6, 182, 212, 0.12), transparent 45%);
  animation: glowShift 12s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes glowShift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, -10px); }
}

.main, section.main, .block-container, div[data-testid="stAppViewContainer"] > .main {
  position: relative;
  z-index: 1;
}

.welcome-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 26px;
  padding: 2.4rem 2.2rem 2.1rem;
  box-shadow:
    0 28px 60px rgba(2, 6, 23, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  text-align: center;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}

.welcome-card::before {
  content: "";
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.25), rgba(6, 182, 212, 0.18), rgba(124, 58, 237, 0.2));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.welcome-card::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 20%, rgba(255, 255, 255, 0.08), transparent 55%),
    radial-gradient(circle at 82% 25%, rgba(6, 182, 212, 0.1), transparent 55%);
  animation: cardGlow 12s ease-in-out infinite;
  pointer-events: none;
}

@keyframes cardGlow {
  0%, 100% { opacity: 0.65; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-6px); }
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--primary);
  font-size: 0.85rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 6px 18px rgba(6, 182, 212, 0.2);
}

.title {
  font-size: clamp(2.2rem, 5vw, 3.3rem);
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: var(--text-primary);
  text-shadow: 0 8px 24px rgba(6, 182, 212, 0.1);
}

.subtitle {
  font-size: 1.05rem;
  color: var(--text-secondary);
  margin-bottom: 0.8rem;
}

.cta-row {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
  margin-bottom: 0.4rem;
}

.cta-row a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 190px;
  padding: 0.85rem 2.4rem;
  border-radius: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-decoration: none;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  color: var(--text-primary);
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(14px) saturate(150%);
  -webkit-backdrop-filter: blur(14px) saturate(150%);
  position: relative;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.cta-row a:hover {
  transform: translateY(-2px);
  box-shadow: 0 22px 48px rgba(2, 6, 23, 0.45);
  border-color: rgba(255, 255, 255, 0.35);
}

.cta-row .cta-primary {
  border-color: rgba(6, 182, 212, 0.55);
  color: #e6fbff;
  box-shadow: 0 18px 40px rgba(6, 182, 212, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

.cta-row .cta-primary::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(6, 182, 212, 0.18), rgba(124, 58, 237, 0.18));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.cta-row .cta-primary:hover::after {
  opacity: 1;
}

.cta-row .cta-ghost a::after,
.cta-row .cta-ghost [data-testid="stPageLink"] a::after,
.cta-row .cta-ghost a[data-testid="stPageLink"]::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(124, 58, 237, 0.15));
  opacity: 0;
  transition: opacity 0.25s ease;
}

.cta-row .cta-ghost a:hover::after,
.cta-row .cta-ghost [data-testid="stPageLink"] a:hover::after,
.cta-row .cta-ghost a[data-testid="stPageLink"]:hover::after {
  opacity: 0.35;
}
.micro {
  margin-top: 1.4rem;
  color: var(--text-primary);
  font-size: 0.95rem;
  letter-spacing: 0.02em;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  padding: 0.45rem 1.1rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.35);
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="welcome-card">
  <div class="badge">Vivido Studio</div>
  <div class="title">Style your moments</div>
  <div class="subtitle">A minimal, powerful canvas for AI image stylization.</div>
  <div class="micro">No clutter. Just create, stylize, and share.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="cta-row">
  <a class="cta-primary" href="/register" target="_self">Register</a>
  <a class="cta-ghost" href="/login" target="_self">Login</a>
</div>
""",
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navigation")
    st.sidebar.write("Use the links below to navigate:")
    st.sidebar.page_link("pages/welcome.py", label="Welcome")
    st.sidebar.page_link("pages/login.py", label="Login")
    st.sidebar.page_link("pages/register.py", label="Register")
    st.sidebar.page_link("pages/dashboard.py", label="Dashboard")
    st.sidebar.page_link("pages/verify.py", label="Verify")
