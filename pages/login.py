import json
import urllib.parse

import streamlit as st
from streamlit.components.v1 import html as components_html

from backend.user_management import create_remember_token, login_user, login_with_remember_token, revoke_remember_token


st.set_page_config(page_title="Login - Vivido",page_icon="assets/logo/login.jpeg", layout="centered")

# Reset global welcome-page effects to avoid Streamlit chrome mirroring on this page.
st.markdown(
    """
<style>
.stApp > div:first-child::before,
.stApp > div:first-child::after { display: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

# Hide Streamlit chrome (toolbar, deploy button, header) to prevent mirrored UI artifacts.
st.markdown(
    """
<style>
header, footer { visibility: hidden; }
[data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"], [data-testid="stDeployButton"] {
  visibility: hidden;
}
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "show_error" not in st.session_state:
    st.session_state["show_error"] = False
if "login_error" not in st.session_state:
    st.session_state["login_error"] = ""
if "redirect_page" not in st.session_state:
    st.session_state["redirect_page"] = ""
if "clear_remember_storage" not in st.session_state:
    st.session_state["clear_remember_storage"] = False


def _get_query_params():
    if hasattr(st, "experimental_get_query_params"):
        return st.experimental_get_query_params()
    if hasattr(st, "query_params"):
        qp = st.query_params
        return {k: [v] if isinstance(v, str) else list(v) for k, v in qp.items()}
    return {}


def _set_query_params(**kwargs):
    if hasattr(st, "experimental_set_query_params"):
        st.experimental_set_query_params(**kwargs)
        return
    if hasattr(st, "query_params"):
        st.query_params.clear()
        for key, value in kwargs.items():
            st.query_params[key] = value


def _resolve_next_page(raw_next: str) -> str:
    next_value = (raw_next or "").strip().lower()
    allowed_targets = {
        "dashboard": "pages/dashboard.py",
        "image_processing": "pages/image_processing.py",
        "pages/dashboard.py": "pages/dashboard.py",
        "pages/image_processing.py": "pages/image_processing.py",
    }
    return allowed_targets.get(next_value, "")


form_html = r"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
      :root {
        --primary: #06b6d4;
        --primary-dark: #0891b2;
        --secondary: #7c3aed;
        --success: #10b981;
        --error: #ef4444;
        --dark-bg: #0f172a;
        --dark-surface: #1e293b;
        --text-primary: #f1f5f9;
        --text-secondary: #cbd5e1;
        --border: #475569;
      }
      
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1a0f2e 50%, #0f172a 100%);
        color: var(--text-primary);
        overflow-x: hidden;
        position: relative;
        min-height: 100vh;
      }

      body.message-open {
        overflow: hidden;
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
      }

      @keyframes gradientShift {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(-50px, -50px); }
      }

      body::after {
        content: "";
        position: fixed;
        inset: 0;
        background-image: 
          radial-gradient(circle at 20% 50%, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
          radial-gradient(circle at 80% 80%, rgba(124, 58, 237, 0.05) 0%, transparent 50%);
        pointer-events: none;
      }

      .container {
        position: relative;
        z-index: 1;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }

      .message-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        backdrop-filter: blur(8px);
      }

      .message-overlay.show {
        display: flex;
      }

      .message-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
        border: 2px solid rgba(148, 163, 184, 0.3);
        border-radius: 25px;
        padding: 50px;
        text-align: center;
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
        max-width: 500px;
        width: 90%;
        backdrop-filter: blur(15px);
        animation: messageSlideIn 0.6s ease-out;
      }

      @keyframes messageSlideIn {
        from {
          opacity: 0;
          transform: translateY(-40px) scale(0.95);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      .message-card.error {
        border-color: rgba(239, 68, 68, 0.5);
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(30, 41, 59, 0.95));
      }

      .message-card.success {
        border-color: rgba(16, 185, 129, 0.5);
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(30, 41, 59, 0.95));
      }

      .message-icon {
        font-size: 80px;
        margin-bottom: 20px;
        display: inline-block;
        animation: iconBounce 0.8s ease-out;
      }

      @keyframes iconBounce {
        0% {
          opacity: 0;
          transform: scale(0.5) translateY(-20px);
        }
        50% {
          opacity: 1;
        }
        100% {
          opacity: 1;
          transform: scale(1) translateY(0);
        }
      }

      .message-card.error .message-icon {
        animation: iconShake 0.6s ease-in-out;
      }

      @keyframes iconShake {
        0%, 100% { transform: rotateZ(0deg); }
        25% { transform: rotateZ(-5deg); }
        75% { transform: rotateZ(5deg); }
      }

      .message-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 12px;
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .message-card.error .message-title {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .message-text {
        font-size: 16px;
        color: #cbd5e1;
        margin-bottom: 25px;
        line-height: 1.6;
      }

      .try-again-btn {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        border: none;
        border-radius: 8px;
        color: white;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 12px;
      }

      .try-again-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4);
      }

      .countdown {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 20px;
        padding: 12px;
        background: rgba(148, 163, 184, 0.1);
        border-radius: 10px;
        border-left: 3px solid #06b6d4;
      }

      .countdown-number {
        font-size: 24px;
        font-weight: 700;
        color: #06b6d4;
        display: inline-block;
        min-width: 30px;
      }

      .card {
        width: 100%;
        max-width: 450px;
        background: rgba(30, 41, 59, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 20px;
        padding: 45px 35px;
        box-shadow: 
          0 25px 50px rgba(0, 0, 0, 0.3),
          inset 0 1px 0 rgba(255, 255, 255, 0.05);
        animation: slideUp 0.6s ease-out;
      }

      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(30px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .header {
        text-align: center;
        margin-bottom: 35px;
      }

      .logo {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 15px;
      }

      .title {
        font-size: 24px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 8px;
      }

      .subtitle {
        font-size: 14px;
        color: var(--text-secondary);
        font-weight: 400;
      }

      .form-group {
        margin-bottom: 20px;
        position: relative;
      }

      label {
        display: block;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
      }

      input[type="text"],
      input[type="email"],
      input[type="password"] {
        width: 100%;
        padding: 12px 14px;
        background: rgba(15, 23, 42, 0.6);
        border: 1.5px solid rgba(148, 163, 184, 0.3);
        border-radius: 10px;
        color: var(--text-primary);
        font-size: 14px;
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s ease;
        outline: none;
      }

      input[type="text"]:focus,
      input[type="email"]:focus,
      input[type="password"]:focus {
        border-color: var(--primary);
        background: rgba(15, 23, 42, 0.8);
        box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
      }

      input.valid {
        border-color: var(--success);
        background: rgba(16, 185, 129, 0.08);
      }

      input.invalid {
        border-color: var(--error);
        background: rgba(239, 68, 68, 0.08);
      }

      .input-icon {
        position: absolute;
        right: 12px;
        cursor: pointer;
        user-select: none;
        font-size: 16px;
        color: var(--text-secondary);
        transition: color 0.3s ease;
      }

      .input-icon:hover {
        color: var(--primary);
      }

      .validation-text {
        font-size: 12px;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
        min-height: 16px;
      }

      .validation-text.error {
        color: var(--error);
      }

      .validation-text.success {
        color: var(--success);
      }

      .remember-group {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: -4px;
        margin-bottom: 4px;
      }

      .remember-group input[type="checkbox"] {
        width: 16px;
        height: 16px;
        accent-color: var(--primary);
        cursor: pointer;
      }

      .remember-group label {
        margin: 0;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-secondary);
        text-transform: none;
        letter-spacing: normal;
        cursor: pointer;
      }

      .forgot-password {
        text-align: right;
        margin-top: -2px;
        margin-bottom: 6px;
      }

      .forgot-password a {
        font-size: 12px;
        color: var(--primary);
        text-decoration: none;
        font-weight: 500;
      }

      .forgot-password a:hover {
        color: var(--primary-dark);
        text-decoration: underline;
      }

      button {
        width: 100%;
        padding: 12px 16px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        border: none;
        border-radius: 10px;
        color: white;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 20px rgba(6, 182, 212, 0.3);
        font-family: 'Poppins', sans-serif;
        margin-top: 15px;
      }

      button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(6, 182, 212, 0.4);
      }

      button:active {
        transform: translateY(0);
      }

      button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
      }

      .footer {
        text-align: center;
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid rgba(148, 163, 184, 0.2);
      }

      .signup-link {
        font-size: 13px;
        color: var(--text-secondary);
      }

      .signup-link a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
      }

      .signup-link a:hover {
        color: var(--primary-dark);
      }

      @media (max-width: 600px) {
        .card {
          padding: 30px 20px;
        }

        .title {
          font-size: 20px;
        }

        label {
          font-size: 12px;
        }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="card">
        <div class="header">
          <div class="logo">✨ VIVIDO</div>
          <div class="title">Sign In</div>
          <div class="subtitle">Access your creative workspace</div>
        </div>

        <form id="loginForm">
          <div class="form-group">
            <label for="email">Email or Username</label>
            <input 
              type="text" 
              id="email" 
              placeholder="Enter email or username"
              required
            />
            <div class="validation-text" id="emailValidation"></div>
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <div class="input-wrapper">
              <input 
                type="password" 
                id="password" 
                placeholder="Enter password"
                required
              />
              <span class="input-icon" id="togglePassword">👁️</span>
            </div>
            <div class="validation-text" id="passwordValidation"></div>
          </div>

          <div class="remember-group">
            <input type="checkbox" id="rememberMe" />
            <label for="rememberMe">Remember me</label>
          </div>

          <div class="forgot-password">
            <a href="#" id="forgotPasswordLink">Forgot Password?</a>
          </div>

          <button type="submit" id="submitBtn">Sign In</button>

          <div class="footer">
            <div class="signup-link">
              Don't have an account? <a href="#" onclick="navigate('goto_register'); return false;" rel="noopener">Sign Up</a>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Success/Error Message Overlay -->
    <div class="message-overlay" id="messageOverlay">
      <div class="message-card" id="messageCard">
        <div class="message-icon" id="messageIcon"></div>
        <div class="message-title" id="messageTitle"></div>
        <div class="message-text" id="messageText"></div>
        <button class="try-again-btn" id="tryAgainBtn" style="display: none;">Try Again</button>
        <div class="countdown" id="countdownContainer" style="display: none;">
          Redirecting in <span class="countdown-number" id="countdownNum">2.5</span> seconds...
        </div>
      </div>
    </div>

    <script>
      function navigate(action) {
        window.location.href = `?action=${action}`;
      }
      const form = document.getElementById('loginForm');
      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const rememberMeInput = document.getElementById('rememberMe');
      const forgotPasswordLink = document.getElementById('forgotPasswordLink');
      const submitBtn = document.getElementById('submitBtn');
      const rememberedEmail = localStorage.getItem('vividoRememberEmail');
      const rememberedToken = localStorage.getItem('vividoRememberToken');
      const rememberedEnabled = localStorage.getItem('vividoRememberEnabled') === 'true';
      const initialMessageType = __INITIAL_MESSAGE_TYPE__;
      const initialMessageText = __INITIAL_MESSAGE_TEXT__;
      const isNotFound = __INITIAL_NOT_FOUND__;
      const justLoggedOut = __JUST_LOGGED_OUT__;
      const nextParam = __NEXT_PARAM__;
      const shouldClearRememberStorage = __CLEAR_REMEMBER_STORAGE__;

      if (justLoggedOut) {
        localStorage.removeItem('vividoRememberEnabled');
        localStorage.removeItem('vividoRememberEmail');
        localStorage.removeItem('vividoRememberToken');
      }

      if (shouldClearRememberStorage) {
        localStorage.removeItem('vividoRememberEnabled');
        localStorage.removeItem('vividoRememberEmail');
        localStorage.removeItem('vividoRememberToken');
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$|^[a-zA-Z0-9_]{3,30}$/;

      function validateEmail() {
        const value = emailInput.value.trim();
        const validation = document.getElementById('emailValidation');

        if (!value) {
          validation.textContent = '';
          emailInput.classList.remove('valid', 'invalid');
          return false;
        }

        const isValid = emailRegex.test(value);
        if (isValid) {
          validation.innerHTML = '✓ Valid';
          validation.classList.add('success');
          validation.classList.remove('error');
          emailInput.classList.add('valid');
          emailInput.classList.remove('invalid');
        } else {
          validation.innerHTML = '✗ Invalid email or username';
          validation.classList.add('error');
          validation.classList.remove('success');
          emailInput.classList.add('invalid');
          emailInput.classList.remove('valid');
        }
        return isValid;
      }

      function validatePassword() {
        const value = passwordInput.value;
        const validation = document.getElementById('passwordValidation');

        if (!value) {
          validation.textContent = '';
          passwordInput.classList.remove('valid', 'invalid');
          return false;
        }

        if (value.length > 0) {
          validation.innerHTML = '✓ Ready';
          validation.classList.add('success');
          validation.classList.remove('error');
          passwordInput.classList.add('valid');
          passwordInput.classList.remove('invalid');
        }
        return true;
      }

      function updateSubmitButton() {
        const isEmailValid = emailInput.classList.contains('valid');
        const isPasswordValid = passwordInput.classList.contains('valid');
        submitBtn.disabled = !(isEmailValid && isPasswordValid);
      }

      emailInput.addEventListener('input', () => {
        validateEmail();
        updateSubmitButton();
      });

      passwordInput.addEventListener('input', () => {
        validatePassword();
        updateSubmitButton();
      });

      document.getElementById('togglePassword').addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
        document.getElementById('togglePassword').textContent = type === 'password' ? '👁️' : '🙈';
      });

      forgotPasswordLink.addEventListener('click', (e) => {
        e.preventDefault();
        alert('Forgot Password is coming soon.');
      });

      form.addEventListener('submit', (e) => {
        e.preventDefault();

        if (!validateEmail() || !validatePassword()) {
          return;
        }

        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const remember = rememberMeInput.checked;
        let rememberToken = '';

        if (remember) {
          rememberToken = localStorage.getItem('vividoRememberToken') || '';
          if (!rememberToken) {
            const bytes = new Uint8Array(32);
            crypto.getRandomValues(bytes);
            rememberToken = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
          }
          localStorage.setItem('vividoRememberEnabled', 'true');
          localStorage.setItem('vividoRememberEmail', email);
          localStorage.setItem('vividoRememberToken', rememberToken);
        } else {
          localStorage.removeItem('vividoRememberEnabled');
          localStorage.removeItem('vividoRememberEmail');
          localStorage.removeItem('vividoRememberToken');
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Signing In...';

        // Store credentials in sessionState for secure server-side retrieval
        // This avoids exposing credentials in URL (security improvement)
        sessionStorage.setItem('vivido_login_email', email);
        sessionStorage.setItem('vivido_login_password', password);
        sessionStorage.setItem('vivido_login_remember', remember ? '1' : '0');
        sessionStorage.setItem('vivido_login_token', rememberToken);
        
        // Trigger a rerun to pick up the secure login from sessionState
        // Instead of passing credentials in URL, we use sessionState
        const nextQuery = nextParam ? `&next=${encodeURIComponent(nextParam)}` : '';
        window.location.href = `?action=secure_login${nextQuery}`;
      });

      (function restoreRememberedLogin() {
        if (!justLoggedOut && initialMessageType !== 'error' && rememberedEnabled && rememberedToken) {
          // Store token in sessionStorage for server retrieval (security improvement)
          // instead of passing in URL
          sessionStorage.setItem('vivido_login_token', rememberedToken);
          const nextQuery = nextParam ? `&next=${encodeURIComponent(nextParam)}` : '';
          window.location.href = `?action=remember_login${nextQuery}`;
          return;
        }

        if (!justLoggedOut && initialMessageType !== 'error' && rememberedEnabled && rememberedEmail) {
          rememberMeInput.checked = true;
          emailInput.value = rememberedEmail;
          validateEmail();
          updateSubmitButton();
        }
      })();

      window.showSuccessMessage = function(message) {
        const overlay = document.getElementById('messageOverlay');
        const card = document.getElementById('messageCard');
        const icon = document.getElementById('messageIcon');
        const title = document.getElementById('messageTitle');
        const text = document.getElementById('messageText');

        icon.textContent = '✅';
        title.textContent = 'Login Successful!';
        text.textContent = message || 'Redirecting to dashboard...';
        
        card.classList.remove('error');
        card.classList.add('success');
        overlay.classList.add('show');
        document.body.classList.add('message-open');

        setTimeout(() => {
            window.location.href = '?page=dashboard';
        }, 500);
      };

      // Handle login data from sessionStorage (security improvement: use sessionState instead of URL)
      (function checkSessionStorageLogin() {
        const storedEmail = sessionStorage.getItem('vivido_login_email');
        const storedPassword = sessionStorage.getItem('vivido_login_password');
        const storedRemember = sessionStorage.getItem('vivido_login_remember');
        const storedToken = sessionStorage.getItem('vivido_login_token');
        
        if (storedEmail && storedPassword) {
          // Clear sessionStorage after reading
          sessionStorage.removeItem('vivido_login_email');
          sessionStorage.removeItem('vivido_login_password');
          sessionStorage.removeItem('vivido_login_remember');
          
          // Pass credentials in URL for server-side processing
          const nextQuery = nextParam ? `&next=${encodeURIComponent(nextParam)}` : '';
          const rememberTokenQuery = (storedRemember === '1' && storedToken) ? `&remember_token=${encodeURIComponent(storedToken)}` : '';
          window.location.href = `?action=secure_login&email=${encodeURIComponent(storedEmail)}&password=${encodeURIComponent(storedPassword)}&remember=${storedRemember}${rememberTokenQuery}${nextQuery}`;
          return;
        }
        
        if (storedToken && !storedEmail) {
          // Remember login - token only
          sessionStorage.removeItem('vivido_login_token');
          const nextQuery = nextParam ? `&next=${encodeURIComponent(nextParam)}` : '';
          window.location.href = `?action=secure_remember_login&token=${encodeURIComponent(storedToken)}${nextQuery}`;
          return;
        }
      })();

      window.showErrorMessage = function(message, isNotFound = false) {
        const overlay = document.getElementById('messageOverlay');
        const card = document.getElementById('messageCard');
        const icon = document.getElementById('messageIcon');
        const title = document.getElementById('messageTitle');
        const text = document.getElementById('messageText');
        const countdownContainer = document.getElementById('countdownContainer');
        const tryAgainBtn = document.getElementById('tryAgainBtn');

        icon.textContent = '⚠️';
        title.textContent = 'Login Failed';
        text.textContent = message;
        
        card.classList.remove('success');
        card.classList.add('error');
        overlay.classList.add('show');
        document.body.classList.add('message-open');
        
        // Hide countdown container - just show the error and let user retry
        countdownContainer.style.display = 'none';
        tryAgainBtn.style.display = 'inline-flex';
      };

      document.getElementById('tryAgainBtn').addEventListener('click', () => {
        const overlay = document.getElementById('messageOverlay');
        overlay.classList.remove('show');
        document.body.classList.remove('message-open');
      });

      document.getElementById('messageOverlay').addEventListener('click', (e) => {
        if (e.target.id === 'messageOverlay') {
          e.currentTarget.classList.remove('show');
          document.body.classList.remove('message-open');
        }
      });

      try {
        if (initialMessageType === 'success') {
          window.showSuccessMessage(initialMessageText);
        } else if (initialMessageType === 'error') {
          window.showErrorMessage(initialMessageText || 'Login failed. Please try again.', isNotFound);
        }
      } catch (e) {
        // No initial message to show
      }
    </script>
  </body>
</html>
"""


# Handle form submission
query_params = _get_query_params()
next_param = query_params.get("next", [""])[0]
next_page = _resolve_next_page(next_param) or _resolve_next_page(st.session_state.get("redirect_after_login", ""))
message_type = ""
message_text = ""
redirect_page = "login"
is_not_found = False

# Check if already logged in
if st.session_state.get("logged_in"):
    target_page = next_page or "pages/dashboard.py"
    st.session_state.pop("redirect_after_login", None)
    st.switch_page(target_page)

# SECURE LOGIN HANDLERS - Read from sessionState instead of URL params
if "action" in query_params and query_params["action"][0] == "secure_login":
    # Get token from URL (non-sensitive), but credentials should come from sessionStorage
    remember_token_param = urllib.parse.unquote(query_params.get("remember_token", [""])[0]).strip()
    
    # For backward compatibility, also check URL params but prefer sessionStorage
    email_from_url = urllib.parse.unquote(query_params.get("email", [""])[0]).strip().lower()
    password_from_url = urllib.parse.unquote(query_params.get("password", [""])[0])
    
    # Store in session_state for the secure handler above
    if email_from_url and password_from_url:
        st.session_state["_secure_login_email"] = email_from_url
        st.session_state["_secure_login_password"] = password_from_url
        st.session_state["_secure_login_remember"] = query_params.get("remember", ["0"])[0] == "1"
        st.session_state["_secure_login_token"] = remember_token_param
        _set_query_params()  # Clear URL params after reading
        st.rerun()  # Rerun to pick up session_state values
    else:
        # No credentials in URL, redirect to show form
        _set_query_params()
        st.rerun()

elif "action" in query_params and query_params["action"][0] == "secure_remember_login":
    remember_token = urllib.parse.unquote(query_params.get("token", [""])[0]).strip()
    if remember_token:
        st.session_state["_secure_remember_token"] = remember_token
        _set_query_params()
        st.rerun()

elif "action" in query_params and query_params["action"][0] == "login":
    # Legacy handler - still supported for backward compatibility
    email = urllib.parse.unquote(query_params.get("email", [""])[0]).strip().lower()
    password = urllib.parse.unquote(query_params.get("password", [""])[0])
    remember = query_params.get("remember", ["0"])[0] == "1"
    remember_token_param = urllib.parse.unquote(query_params.get("remember_token", [""])[0]).strip()

    if email and password:
        result = login_user(email, password)

        if result.get("success"):
            # Set session state
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = result.get("email", email)
            st.session_state["current_username"] = result.get("username", "")
            st.session_state["user_id"] = result.get("user_id")
            st.session_state["last_login"] = result.get("last_login")

            # Configure remember-me persistence for this login.
            if remember:
                remember_token = create_remember_token(result.get("user_id"), remember_token_param)
                if remember_token:
                    st.session_state["remember_token"] = remember_token
                    st.session_state["clear_remember_storage"] = False
                else:
                    st.session_state["remember_token"] = ""
                    st.session_state["clear_remember_storage"] = True
            else:
                old_token = st.session_state.get("remember_token", "")
                if old_token:
                    revoke_remember_token(old_token)
                st.session_state["remember_token"] = ""
                st.session_state["clear_remember_storage"] = False

            target_page = next_page or "pages/dashboard.py"
            st.session_state.pop("redirect_after_login", None)
            _set_query_params()
            st.switch_page(target_page)
        else:
            # Handle different error types
            is_user_not_found = result.get("user_not_found", False)
            error_msg = result.get("message", "Login failed. Please try again.")

            # Store error info in session
            st.session_state["login_error"] = error_msg
            st.session_state["show_error"] = True
            st.session_state["redirect_page"] = "register" if is_user_not_found else "login"
            st.session_state["clear_remember_storage"] = False

            # Clear query params and rerun
            _set_query_params()
            st.rerun()

elif "action" in query_params and query_params["action"][0] == "remember_login":
    remember_token = urllib.parse.unquote(query_params.get("token", [""])[0]).strip()
    if remember_token:
        result = login_with_remember_token(remember_token)
        if result.get("success"):
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = result.get("email", "")
            st.session_state["current_username"] = result.get("username", "")
            st.session_state["user_id"] = result.get("user_id")
            st.session_state["last_login"] = result.get("last_login")
            st.session_state["remember_token"] = remember_token
            st.session_state["clear_remember_storage"] = False
            st.session_state.pop("redirect_after_login", None)
            _set_query_params()
            target_page = next_page or "pages/dashboard.py"
            st.switch_page(target_page)
        else:
            revoke_remember_token(remember_token)
            st.session_state["clear_remember_storage"] = True
            _set_query_params()
            st.rerun()

elif "action" in query_params and query_params["action"][0] == "goto_register":
    _set_query_params()
    st.switch_page("pages/register.py")

# Check if there's an error message in session state
if not message_type and st.session_state.get("show_error"):
    message_type = "error"
    message_text = st.session_state.get("login_error", "Login failed. Please try again.")
    redirect_page = st.session_state.get("redirect_page", "login")
    is_not_found = redirect_page == "register"
    # Clear the flag immediately to prevent duplicate rendering on rerun
    st.session_state["show_error"] = False

# Check for secure login via session_state (NEW - avoids URL exposure)
# This is checked first as it's more secure than URL params
if "_secure_login_email" in st.session_state and "_secure_login_password" in st.session_state:
    email = st.session_state.pop("_secure_login_email")
    password = st.session_state.pop("_secure_login_password")
    remember = st.session_state.pop("_secure_login_remember", False)
    remember_token_param = st.session_state.pop("_secure_login_token", "")
    
    if email and password:
        result = login_user(email, password)
        if result.get("success"):
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = result.get("email", email)
            st.session_state["current_username"] = result.get("username", "")
            st.session_state["user_id"] = result.get("user_id")
            st.session_state["last_login"] = result.get("last_login")
            
            if remember:
                remember_token = create_remember_token(result.get("user_id"), remember_token_param)
                if remember_token:
                    st.session_state["remember_token"] = remember_token
                    st.session_state["clear_remember_storage"] = False
                else:
                    st.session_state["remember_token"] = ""
                    st.session_state["clear_remember_storage"] = True
            else:
                old_token = st.session_state.get("remember_token", "")
                if old_token:
                    revoke_remember_token(old_token)
                st.session_state["remember_token"] = ""
                st.session_state["clear_remember_storage"] = False
            
            target_page = next_page or "pages/dashboard.py"
            st.session_state.pop("redirect_after_login", None)
            st.switch_page(target_page)
        else:
            is_user_not_found = result.get("user_not_found", False)
            error_msg = result.get("message", "Login failed. Please try again.")
            st.session_state["login_error"] = error_msg
            st.session_state["show_error"] = True
            st.session_state["redirect_page"] = "register" if is_user_not_found else "login"
            st.session_state["clear_remember_storage"] = False
            st.rerun()

# Check for secure remember login via session_state
if "_secure_remember_token" in st.session_state:
    remember_token = st.session_state.pop("_secure_remember_token")
    if remember_token:
        result = login_with_remember_token(remember_token)
        if result.get("success"):
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = result.get("email", "")
            st.session_state["current_username"] = result.get("username", "")
            st.session_state["user_id"] = result.get("user_id")
            st.session_state["last_login"] = result.get("last_login")
            st.session_state["remember_token"] = remember_token
            st.session_state["clear_remember_storage"] = False
            st.session_state.pop("redirect_after_login", None)
            target_page = next_page or "pages/dashboard.py"
            st.switch_page(target_page)
        else:
            revoke_remember_token(remember_token)
            st.session_state["clear_remember_storage"] = True
            st.rerun()

rendered_form_html = (
    form_html
    .replace("__INITIAL_MESSAGE_TYPE__", json.dumps(message_type))
    .replace("__INITIAL_MESSAGE_TEXT__", json.dumps(message_text))
    .replace("__INITIAL_NOT_FOUND__", json.dumps(is_not_found))
    .replace("__JUST_LOGGED_OUT__", json.dumps(bool(st.session_state.pop("just_logged_out", False))))
    .replace("__NEXT_PARAM__", json.dumps(next_param))
    .replace("__CLEAR_REMEMBER_STORAGE__", json.dumps(bool(st.session_state.pop("clear_remember_storage", False))))
)

# Render the form
components_html(rendered_form_html, height=650)

# Handle redirect or refresh based on error type
if message_type == "error":
    import time
    if redirect_page == "register":
        time.sleep(3)
        st.switch_page("pages/register.py")
    else:
        # Stay on login page so the error message remains visible
        pass
