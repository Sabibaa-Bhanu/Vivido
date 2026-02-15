import streamlit as st
from datetime import datetime
from backend.user_management import delete_user

st.set_page_config(page_title="Dashboard - Vivido", layout="wide")

# Initialize delete confirmation state
if "show_delete_confirmation" not in st.session_state:
    st.session_state["show_delete_confirmation"] = False

# Custom CSS to match login/register theme with enhanced design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #06b6d4;
    --primary-dark: #0891b2;
    --secondary: #7c3aed;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
    --dark-bg: #0f172a;
    --dark-surface: #1e293b;
    --dark-surface-light: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #cbd5e1;
    --border: #475569;
}

* {
    font-family: 'Poppins', sans-serif;
}

body {
    background: linear-gradient(135deg, #0f172a 0%, #1a0f2e 50%, #0f172a 100%);
    color: var(--text-primary);
}

body::before {
    content: "";
    position: fixed;
    top: -50%;
    right: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%),
                radial-gradient(circle at 80% 20%, rgba(124, 58, 237, 0.15) 0%, transparent 70%);
    animation: gradientShift 15s ease-in-out infinite;
    pointer-events: none;
    z-index: -1;
}

@keyframes gradientShift {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(-50px, -50px); }
}

.dashboard-header {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 20px;
    padding: 30px;
    margin-bottom: 30px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}

.header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.header-title {
    color: var(--primary);
    font-size: 2rem;
    font-weight: 700;
}

.user-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
}

.user-details {
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
    flex: 1;
}

.info-item {
    background: rgba(6, 182, 212, 0.1);
    border: 1px solid rgba(6, 182, 212, 0.3);
    border-radius: 12px;
    padding: 15px 20px;
    color: var(--text-primary);
    transition: all 0.3s ease;
}

.info-item:hover {
    background: rgba(6, 182, 212, 0.15);
    border-color: rgba(6, 182, 212, 0.5);
    transform: translateY(-2px);
}

.btn-container {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
}

.btn {
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.95rem;
}

.btn-logout {
    background: linear-gradient(135deg, var(--secondary), #a855f7);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
}

.btn-logout:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4);
}

.main-content {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 20px;
    padding: 40px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    margin-bottom: 30px;
}

.welcome-section {
    text-align: center;
    margin-bottom: 50px;
}

.welcome-title {
    color: var(--primary);
    font-size: 2.8rem;
    font-weight: 700;
    margin-bottom: 10px;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.welcome-subtitle {
    color: var(--text-secondary);
    font-size: 1.15rem;
    margin-bottom: 30px;
}

.account-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.account-card {
    background: rgba(6, 182, 212, 0.08);
    border: 1px solid rgba(6, 182, 212, 0.25);
    border-radius: 14px;
    padding: 18px 20px;
}

.account-label {
    color: var(--text-secondary);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}

.account-value {
    color: var(--text-primary);
    font-size: 1.05rem;
    font-weight: 600;
}

.nav-menu {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    margin-bottom: 35px;
}

.nav-link {
    display: inline-block;
    padding: 10px 18px;
    border-radius: 999px;
    border: 1px solid rgba(124, 58, 237, 0.4);
    color: var(--text-primary);
    text-decoration: none;
    background: rgba(124, 58, 237, 0.12);
    font-weight: 600;
    transition: all 0.25s ease;
}

.nav-link:hover {
    transform: translateY(-2px);
    background: rgba(124, 58, 237, 0.2);
    border-color: rgba(124, 58, 237, 0.6);
}

.section-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 22px;
}

.section-card {
    background: linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(124, 58, 237, 0.08));
    border: 1px solid rgba(6, 182, 212, 0.25);
    border-radius: 16px;
    padding: 24px;
}

.section-title {
    color: var(--text-primary);
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 10px;
}

.section-desc {
    color: var(--text-secondary);
    font-size: 0.95rem;
    line-height: 1.6;
}

.danger-zone {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.08));
    border: 2px solid rgba(239, 68, 68, 0.3);
    border-radius: 15px;
    padding: 30px;
    margin-top: 50px;
}

.danger-title {
    color: var(--error);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.danger-desc {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 20px;
    line-height: 1.6;
}

.btn-delete {
    background: linear-gradient(135deg, var(--error), #dc2626);
    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

.btn-delete:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
}

.btn-cancel {
    background: transparent;
    border: 2px solid var(--border);
    color: var(--text-secondary);
    box-shadow: none;
}

.btn-cancel:hover {
    background: rgba(71, 85, 105, 0.2);
    border-color: var(--text-primary);
    color: var(--text-primary);
}

.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
    backdrop-filter: blur(5px);
}

.modal-content {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
    border: 2px solid rgba(239, 68, 68, 0.5);
    border-radius: 20px;
    padding: 40px;
    max-width: 500px;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
}

.modal-icon {
    font-size: 3rem;
    margin-bottom: 20px;
    display: inline-block;
}

.modal-title {
    color: var(--error);
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 15px;
}

.modal-text {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 30px;
    line-height: 1.6;
}

.modal-buttons {
    display: flex;
    gap: 15px;
    justify-content: center;
}

.modal-buttons button {
    flex: 1;
}
</style>
""", unsafe_allow_html=True)

# Check if user is logged in
if not st.session_state.get("logged_in"):
    st.warning("Please login first")
    st.page_link("pages/login.py", label="Go to Login")
    st.stop()

last_login_value = st.session_state.get("last_login")
last_login_display = "N/A"
if last_login_value:
    try:
        parsed = datetime.fromisoformat(last_login_value)
        last_login_display = parsed.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        last_login_display = str(last_login_value)

# Dashboard header
st.markdown(f"""
<div class="dashboard-header">
    <div class="header-top">
        <div class="header-title">✨ Vivido Dashboard</div>
    </div>
    <div class="user-info">
        <div class="user-details">
            <div class="info-item">
                <strong>👤 User:</strong> {st.session_state.get('current_username', 'User')}
            </div>
            <div class="info-item">
                <strong>📧 Email:</strong> {st.session_state.get('current_user', 'N/A')}
            </div>
            <div class="info-item">
                <strong>🕒 Last Login:</strong> {last_login_display}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Logout button
col1, col2, col3 = st.columns([1, 1, 1])
with col3:
    if st.button("🔓 Logout", key="logout_btn", help="Click to logout and return to login page", use_container_width=True):
        st.session_state.clear()
        st.session_state["just_logged_out"] = True
        st.switch_page("pages/login.py")

username = st.session_state.get("current_username", "User")
email = st.session_state.get("current_user", "N/A")
user_id = st.session_state.get("user_id", "N/A")

st.markdown(f"""
<div class="main-content">
    <div class="welcome-section">
        <h1 class="welcome-title">Welcome back, {username}</h1>
        <p class="welcome-subtitle">Your personalized image styling platform.</p>
    </div>
    <div class="nav-menu">
        <a class="nav-link" href="#image-processing">Image Processing</a>
        <a class="nav-link" href="#payment-history">Payment History</a>
        <a class="nav-link" href="#profile-settings">Profile Settings</a>
    </div>
    <div class="section-grid">
        <div id="image-processing" class="section-card">
            <div class="section-title">Image Processing</div>
            <div class="section-desc">
                Start new stylization jobs, review recent outputs, and manage queued tasks.
            </div>
        </div>
        <div id="payment-history" class="section-card">
            <div class="section-title">Payment History</div>
            <div class="section-desc">
                Track invoices, subscriptions, and billing activity for your account.
            </div>
        </div>
        <div id="profile-settings" class="section-card">
            <div class="section-title">Profile Settings</div>
            <div class="section-desc">
                Update your profile, change credentials, and manage notification preferences.
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)




# Delete Account Button
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("🗑️ Delete Account", key="delete_account_btn", help="Permanently delete your account", use_container_width=True):
        st.session_state["show_delete_confirmation"] = True

# Show confirmation modal
if st.session_state.get("show_delete_confirmation"):
    col1, col2, col3 = st.columns([0.15, 0.7, 0.15])
    with col2:
        st.markdown("""
        <div class="modal-content">
            <div class="modal-icon">⚠️</div>
            <div class="modal-title">Delete Account?</div>
            <div class="modal-text">
                Are you absolutely sure? This action cannot be undone. Your account and all data will be permanently deleted, and you'll need to register again if you want to use Vivido in the future.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Cancel", key="cancel_delete", use_container_width=True):
                st.session_state["show_delete_confirmation"] = False
                st.rerun()
        
        with col2:
            if st.button("✓ Delete Permanently", key="confirm_delete", use_container_width=True):
                user_id = st.session_state.get("user_id")
                if user_id:
                    result = delete_user(user_id)
                    if result.get("success"):
                        st.session_state.clear()
                        st.markdown("""
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 2rem; margin-bottom: 20px;">✓</div>
                            <div style="color: #10b981; font-size: 1.2rem; font-weight: 600; margin-bottom: 20px;">
                                Account deleted successfully!
                            </div>
                            <div style="color: #cbd5e1; margin-bottom: 30px;">
                                Redirecting to register page...
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        import time
                        time.sleep(2)
                        st.switch_page("pages/register.py")
                    else:
                        st.error(f"Error: {result.get('message')}")

