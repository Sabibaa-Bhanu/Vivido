import streamlit as st
from datetime import datetime
from backend.user_management import delete_user, revoke_remember_token

st.set_page_config(page_title="Dashboard - Vivido", page_icon="assets/logo/dashboard.jpeg", layout="wide")

# Initialize delete confirmation state
if "show_delete_confirmation" not in st.session_state:
    st.session_state["show_delete_confirmation"] = False

# Custom CSS matching reference design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #7c3aed;
    --primary-light: #a78bfa;
    --secondary: #06b6d4;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
    --dark-bg: #0b0e1a;
    --dark-surface: #12091f;
    --dark-surface-light: #1a1030;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --border: rgba(124, 58, 237, 0.25);
    --card-glow: rgba(124, 58, 237, 0.08);
}

* {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0b0e1a 0%, #12091f 50%, #0b0e1a 100%);
    color: var(--text-primary);
}

/* Hide default Streamlit header */
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* Top Navbar */
.top-navbar {
    background: linear-gradient(135deg, rgba(18, 9, 31, 0.95), rgba(26, 16, 48, 0.95));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 28px;
    margin-bottom: 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    backdrop-filter: blur(12px);
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
}

.navbar-brand .brand-icon {
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}

.navbar-brand .brand-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: 0.02em;
}

.navbar-right {
    display: flex;
    align-items: center;
    gap: 18px;
}

.navbar-right .user-greeting {
    color: var(--text-secondary);
    font-size: 0.88rem;
}

.navbar-right .user-greeting strong {
    color: var(--primary-light);
}

/* Dashboard Title */
.dashboard-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 24px;
    padding-left: 4px;
}

/* Action Cards */
.action-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 32px;
}

.action-card {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(124, 58, 237, 0.05));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px 20px;
    cursor: pointer;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}

.action-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 30%, rgba(124, 58, 237, 0.12), transparent 70%);
    pointer-events: none;
}

.action-card:hover {
    border-color: rgba(124, 58, 237, 0.45);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(124, 58, 237, 0.15);
}

.action-card .card-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    margin-bottom: 14px;
}

.action-card .card-icon.purple {
    background: rgba(124, 58, 237, 0.25);
    border: 1px solid rgba(124, 58, 237, 0.4);
}

.action-card .card-icon.cyan {
    background: rgba(6, 182, 212, 0.25);
    border: 1px solid rgba(6, 182, 212, 0.4);
}

.action-card .card-icon.pink {
    background: rgba(236, 72, 153, 0.25);
    border: 1px solid rgba(236, 72, 153, 0.4);
}

.action-card .card-title {
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 4px;
}

.action-card .card-desc {
    color: var(--text-secondary);
    font-size: 0.82rem;
    line-height: 1.5;
}

/* Recent Activity */
.recent-activity-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 14px;
    padding-left: 4px;
}

.recent-activity-box {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.06), rgba(124, 58, 237, 0.03));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 36px 20px;
    text-align: center;
    margin-bottom: 30px;
}

.recent-activity-box .empty-icon {
    font-size: 2rem;
    margin-bottom: 10px;
    opacity: 0.5;
}

.recent-activity-box .empty-text {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* Streamlit button overrides for cards */
.st-key-card_image_processing button,
.st-key-card_payment_history button,
.st-key-card_profile_settings button {
    min-height: 160px;
    width: 100%;
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(124, 58, 237, 0.05)) !important;
    border: 1px solid rgba(124, 58, 237, 0.25) !important;
    border-radius: 14px !important;
    color: var(--text-primary) !important;
    text-align: left;
    padding: 22px 20px;
    line-height: 1.5;
    white-space: normal;
    font-size: 0.92rem;
}

.st-key-card_image_processing button p,
.st-key-card_payment_history button p,
.st-key-card_profile_settings button p {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.88rem;
    font-weight: 400;
    line-height: 1.5;
}

.st-key-card_image_processing button p strong,
.st-key-card_payment_history button p strong,
.st-key-card_profile_settings button p strong {
    display: block;
    margin-bottom: 8px;
    color: #ffffff;
    font-weight: 700;
    font-size: 1.15rem;
    line-height: 1.2;
}

.st-key-card_image_processing button:hover,
.st-key-card_payment_history button:hover,
.st-key-card_profile_settings button:hover {
    transform: translateY(-2px);
    border-color: rgba(124, 58, 237, 0.45) !important;
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(124, 58, 237, 0.08)) !important;
    box-shadow: 0 8px 30px rgba(124, 58, 237, 0.15);
}

/* Danger zone */
.danger-zone {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(220, 38, 38, 0.05));
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 14px;
    padding: 24px;
    margin-top: 40px;
}

.danger-title {
    color: var(--error);
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.danger-desc {
    color: var(--text-secondary);
    font-size: 0.88rem;
    margin-bottom: 16px;
    line-height: 1.6;
}

.modal-content {
    background: linear-gradient(135deg, rgba(18, 9, 31, 0.98), rgba(15, 12, 30, 0.98));
    border: 2px solid rgba(239, 68, 68, 0.4);
    border-radius: 16px;
    padding: 32px;
    max-width: 500px;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

.modal-icon {
    font-size: 2.5rem;
    margin-bottom: 16px;
    display: inline-block;
}

.modal-title {
    color: var(--error);
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 12px;
}

.modal-text {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 24px;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

# Check if user is logged in
if (
    not st.session_state.get("logged_in")
    and st.session_state.get("user_id")
    and st.session_state.get("current_user")
):
    st.session_state["logged_in"] = True

if not st.session_state.get("logged_in"):
    st.session_state["redirect_after_login"] = "pages/dashboard.py"
    st.switch_page("pages/login.py")

query_params = st.query_params
action = query_params.get("action", "")
if action == "open_image_processing":
    st.query_params.clear()
    st.switch_page("pages/image_processing.py")
if action == "open_payment_history":
    st.info("Payment History page is coming soon.")
    st.query_params.clear()
if action == "open_profile_settings":
    st.info("Profile Settings page is coming soon.")
    st.query_params.clear()

username = st.session_state.get("current_username", "User")
email = st.session_state.get("current_user", "N/A")
user_id = st.session_state.get("user_id", "N/A")

last_login_value = st.session_state.get("last_login")
last_login_display = "N/A"
if last_login_value:
    try:
        parsed = datetime.fromisoformat(last_login_value)
        last_login_display = parsed.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        last_login_display = str(last_login_value)

# Top Navbar (full width HTML with logout button integrated)
nav_col1, nav_col2 = st.columns([5, 1])
with nav_col1:
    st.markdown(f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <div class="brand-icon">✨</div>
            <div class="brand-name">Vivido</div>
        </div>
        <div class="navbar-right">
            <span class="user-greeting">Hello, <strong>{username}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with nav_col2:
    if st.button("Logout", key="logout_btn", help="Click to logout", width='stretch'):
        remember_token = st.session_state.get("remember_token", "")
        if remember_token:
            revoke_remember_token(remember_token)
        st.session_state.clear()
        st.session_state["just_logged_out"] = True
        st.switch_page("pages/login.py")

# Dashboard Title
st.markdown('<div class="dashboard-title">Dashboard</div>', unsafe_allow_html=True)

# Three Action Cards
card_col_1, card_col_2, card_col_3 = st.columns(3)
with card_col_1:
    if st.button(
        "**🎬 Vivido Studio**\nStyle your moments.",
        key="card_image_processing",
        width='stretch',
    ):
        st.switch_page("pages/image_processing.py")

with card_col_2:
    if st.button(
        "**🔍 Art Gallery**\nView your past creations.",
        key="card_payment_history",
        width='stretch',
    ):
        st.info("Art Gallery page is coming soon.")

with card_col_3:
    if st.button(
        "**⚙️ Profile Settings**\nUpdate your account information.",
        key="card_profile_settings",
        width='stretch',
    ):
        st.info("Profile Settings page is coming soon.")

# Last Login Info
st.markdown(f"""
<div style="
    color: var(--text-secondary);
    font-size: 0.82rem;
    margin-bottom: 20px;
    padding-left: 4px;
">
    🕒 Last Login: <strong style="color: var(--text-primary);">{last_login_display}</strong>
</div>
""", unsafe_allow_html=True)

# Recent Activity Section
st.markdown('<div class="recent-activity-title">Recent Activity</div>', unsafe_allow_html=True)
st.markdown("""
<div class="recent-activity-box">
    <div class="empty-icon">🖼️</div>
    <div class="empty-text">No recent activity found.</div>
</div>
""", unsafe_allow_html=True)

# Advanced toggle
show_advanced_dashboard = st.toggle(
    "Show Advanced Options",
    value=False,
    help="Enable account management actions.",
    key="dashboard_show_advanced_toggle",
)

if show_advanced_dashboard:
    # Delete Account Button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🗑️ Delete Account", key="delete_account_btn", help="Permanently delete your account", width='stretch'):
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
                if st.button("❌ Cancel", key="cancel_delete", width='stretch'):
                    st.session_state["show_delete_confirmation"] = False
                    st.rerun()

            with col2:
                if st.button("✓ Delete Permanently", key="confirm_delete", width='stretch'):
                    user_id = st.session_state.get("user_id")
                    if user_id:
                        result = delete_user(user_id)
                        if result.get("success"):
                            remember_token = st.session_state.get("remember_token", "")
                            if remember_token:
                                revoke_remember_token(remember_token)
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
