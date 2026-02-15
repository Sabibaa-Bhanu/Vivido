import json
import streamlit as st
from streamlit.components.v1 import html as components_html
from backend.user_management import register_user


st.set_page_config(page_title="Register - Vivido", layout="centered")

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
        --warning: #f59e0b;
        --dark-bg: #0f172a;
        --dark-surface: #1e293b;
        --dark-surface-light: #334155;
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

      /* Animated background gradient */
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

      .continue-btn {
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
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

      .continue-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
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

      .stars {
        position: absolute;
        width: 4px;
        height: 4px;
        background: #10b981;
        border-radius: 50%;
        animation: starPulse 1.5s ease-in-out infinite;
      }

      @keyframes starPulse {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
      }

      .star1 { top: 60px; left: 40px; animation-delay: 0s; }
      .star2 { top: 80px; right: 50px; animation-delay: 0.3s; }
      .star3 { bottom: 80px; left: 50px; animation-delay: 0.6s; }
      .star4 { bottom: 60px; right: 40px; animation-delay: 0.9s; }

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

      .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin-bottom: 20px;
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

      .toggle-pwd {
        background: none;
        border: none;
        cursor: pointer;
        padding: 8px;
        margin-right: 4px;
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

      .strength-bar {
        height: 4px;
        width: 100%;
        background: rgba(148, 163, 184, 0.2);
        border-radius: 2px;
        margin-top: 8px;
        overflow: hidden;
      }

      .strength-fill {
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, var(--error), var(--warning), var(--success));
        transition: width 0.3s ease;
        border-radius: 2px;
      }

      .strength-text {
        font-size: 12px;
        margin-top: 6px;
        color: var(--text-secondary);
        font-weight: 500;
      }

      .checkbox-group {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 20px;
        padding: 12px;
        background: rgba(6, 182, 212, 0.05);
        border-radius: 10px;
        border-left: 3px solid var(--primary);
      }

      input[type="checkbox"] {
        margin-top: 3px;
        cursor: pointer;
        accent-color: var(--primary);
      }

      .checkbox-label {
        font-size: 13px;
        color: var(--text-secondary);
        cursor: pointer;
        line-height: 1.4;
      }

      .checkbox-label a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
      }

      .checkbox-label a:hover {
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

      .login-link {
        font-size: 13px;
        color: var(--text-secondary);
      }

      .login-link a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
      }

      .login-link a:hover {
        color: var(--primary-dark);
      }

      .error-message {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 20px;
        color: var(--error);
        font-size: 13px;
        animation: shake 0.5s ease-in-out;
      }

      @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
      }

      @keyframes successGlow {
        0%, 100% {
          box-shadow: 0 0 18px rgba(16, 185, 129, 0.18), inset 0 0 10px rgba(6, 182, 212, 0.15);
        }
        50% {
          box-shadow: 0 0 35px rgba(16, 185, 129, 0.4), inset 0 0 18px rgba(6, 182, 212, 0.3);
        }
      }

      @keyframes successShine {
        0% { transform: translateX(-140%); }
        100% { transform: translateX(140%); }
      }

      .success-message {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 20px;
        color: var(--success);
        font-size: 13px;
      }

      .success-message.fx {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(6, 182, 212, 0.18));
        border: 1px solid rgba(16, 185, 129, 0.45);
        box-shadow: 0 0 25px rgba(16, 185, 129, 0.25), inset 0 0 15px rgba(6, 182, 212, 0.2);
        animation: successGlow 1.8s ease-in-out infinite;
      }

      .success-message.fx::after {
        content: "";
        position: absolute;
        inset: 0;
        transform: translateX(-140%);
        background: linear-gradient(120deg, transparent, rgba(255, 255, 255, 0.35), transparent);
        animation: successShine 2.2s ease-in-out infinite;
        pointer-events: none;
      }

      @media (max-width: 600px) {
        .card {
          padding: 30px 20px;
        }

        .form-row {
          grid-template-columns: 1fr;
          gap: 20px;
        }

        .title {
          font-size: 20px;
        }

        label {
          font-size: 12px;
        }
      }

      .try-again-btn {
        background: linear-gradient(135deg, var(--error) 0%, #dc2626 100%);
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
        margin-top: 15px;
      }

      .try-again-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4);
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="card">
        <div class="header">
          <div class="logo">✨ VIVIDO</div>
          <div class="title">Join Us</div>
          <div class="subtitle">Create your account to get started</div>
        </div>

        <div id="errorContainer"></div>
        <div id="successContainer"></div>

        <form id="registerForm">
          <div class="form-row">
            <div class="form-group">
              <label for="username">Username</label>
              <input 
                type="text" 
                id="username" 
                placeholder="Enter username"
                required
              />
              <div class="validation-text" id="usernameValidation"></div>
            </div>

            <div class="form-group">
              <label for="email">Email</label>
              <input 
                type="email" 
                id="email" 
                placeholder="Enter email"
                required
              />
              <div class="validation-text" id="emailValidation"></div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="password">Password</label>
              <div class="input-wrapper">
                <input 
                  type="password" 
                  id="password" 
                  placeholder="Create password"
                  required
                />
                <span class="input-icon" id="togglePassword">👁️</span>
              </div>
              <div class="strength-bar">
                <div class="strength-fill" id="strengthFill"></div>
              </div>
              <div class="strength-text" id="strengthText"></div>
              <div class="validation-text" id="passwordValidation"></div>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm Password</label>
              <div class="input-wrapper">
                <input 
                  type="password" 
                  id="confirmPassword" 
                  placeholder="Confirm password"
                  required
                />
                <span class="input-icon" id="toggleConfirm">👁️</span>
              </div>
              <div class="validation-text" id="confirmValidation"></div>
            </div>
          </div>

          <div class="checkbox-group">
            <input 
              type="checkbox" 
              id="terms" 
              required
            />
            <label for="terms" class="checkbox-label">
              I agree to the <a href="#terms">Terms & Conditions</a> and <a href="#privacy">Privacy Policy</a>
            </label>
          </div>

          <button type="submit" id="submitBtn">Create Account</button>

          <div class="footer">
            <div class="login-link">
              Already have an account? <a href="#" onclick="navigate('goto_login'); return false;" rel="noopener">Sign In</a>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Success/Error Message Overlay -->
    <div class="message-overlay" id="messageOverlay">
      <div class="message-card" id="messageCard">
        <div class="stars star1"></div>
        <div class="stars star2"></div>
        <div class="stars star3"></div>
        <div class="stars star4"></div>
        <div class="message-icon" id="messageIcon"></div>
        <div class="message-title" id="messageTitle"></div>
        <div class="message-text" id="messageText"></div>
        <button class="continue-btn" id="continueBtn" style="display: none;">Continue</button>
        <div class="countdown" id="countdownContainer" style="display: none;">
          Redirecting in <span class="countdown-number" id="countdownNum">10</span> seconds...
        </div>
      </div>
    </div>

    <script>
      function navigate(action) {
        window.location.href = `?action=${action}`;
      }
      const form = document.getElementById('registerForm');
      const usernameInput = document.getElementById('username');
      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const confirmPasswordInput = document.getElementById('confirmPassword');
      const termsInput = document.getElementById('terms');
      const submitBtn = document.getElementById('submitBtn');

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const usernameRegex = /^[a-zA-Z0-9_]{3,30}$/;

      function checkPasswordStrength(password) {
        let strength = 0;
        const checks = {
          length: password.length >= 8,
          uppercase: /[A-Z]/.test(password),
          lowercase: /[a-z]/.test(password),
          number: /[0-9]/.test(password),
          special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
        };

        Object.values(checks).forEach(check => {
          if (check) strength++;
        });

        const strengthFill = document.getElementById('strengthFill');
        const strengthText = document.getElementById('strengthText');
        
        strengthFill.style.width = (strength * 20) + '%';

        const labels = {
          0: 'Very Weak',
          1: 'Weak',
          2: 'Fair',
          3: 'Good',
          4: 'Strong',
          5: 'Very Strong'
        };

        strengthText.textContent = labels[strength];
        const colors = ['#ef4444', '#f59e0b', '#f59e0b', '#3b82f6', '#10b981', '#10b981'];
        strengthFill.style.background = colors[strength];

        return strength >= 3;
      }

      function validateUsername() {
        const value = usernameInput.value.trim();
        const validation = document.getElementById('usernameValidation');

        if (!value) {
          validation.textContent = '';
          usernameInput.classList.remove('valid', 'invalid');
          return false;
        }

        const isValid = usernameRegex.test(value);
        if (isValid) {
          validation.innerHTML = '✓ Valid username';
          validation.classList.add('success');
          validation.classList.remove('error');
          usernameInput.classList.add('valid');
          usernameInput.classList.remove('invalid');
        } else {
          validation.innerHTML = '✗ 3-30 alphanumeric & underscore only';
          validation.classList.add('error');
          validation.classList.remove('success');
          usernameInput.classList.add('invalid');
          usernameInput.classList.remove('valid');
        }
        return isValid;
      }

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
          validation.innerHTML = '✓ Valid email';
          validation.classList.add('success');
          validation.classList.remove('error');
          emailInput.classList.add('valid');
          emailInput.classList.remove('invalid');
        } else {
          validation.innerHTML = '✗ Invalid email format';
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

        const isStrong = checkPasswordStrength(value);
        if (isStrong) {
          validation.innerHTML = '✓ Strong password';
          validation.classList.add('success');
          validation.classList.remove('error');
          passwordInput.classList.add('valid');
          passwordInput.classList.remove('invalid');
        } else {
          validation.innerHTML = '✗ Need 8+ chars, uppercase, lowercase, number & symbol';
          validation.classList.add('error');
          validation.classList.remove('success');
          passwordInput.classList.add('invalid');
          passwordInput.classList.remove('valid');
        }
        validateConfirmPassword();
        return isStrong;
      }

      function validateConfirmPassword() {
        const value = confirmPasswordInput.value;
        const validation = document.getElementById('confirmValidation');

        if (!value) {
          validation.textContent = '';
          confirmPasswordInput.classList.remove('valid', 'invalid');
          return false;
        }

        const matches = value === passwordInput.value;
        if (matches) {
          validation.innerHTML = '✓ Passwords match';
          validation.classList.add('success');
          validation.classList.remove('error');
          confirmPasswordInput.classList.add('valid');
          confirmPasswordInput.classList.remove('invalid');
        } else {
          validation.innerHTML = '✗ Passwords do not match';
          validation.classList.add('error');
          validation.classList.remove('success');
          confirmPasswordInput.classList.add('invalid');
          confirmPasswordInput.classList.remove('valid');
        }
        return matches;
      }

      function updateSubmitButton() {
        const isUsernameValid = usernameInput.classList.contains('valid');
        const isEmailValid = emailInput.classList.contains('valid');
        const isPasswordValid = passwordInput.classList.contains('valid');
        const isConfirmValid = confirmPasswordInput.classList.contains('valid');
        const isTermsChecked = termsInput.checked;

        submitBtn.disabled = !(isUsernameValid && isEmailValid && isPasswordValid && isConfirmValid && isTermsChecked);
      }

      usernameInput.addEventListener('input', () => {
        validateUsername();
        updateSubmitButton();
      });

      emailInput.addEventListener('input', () => {
        validateEmail();
        updateSubmitButton();
      });

      passwordInput.addEventListener('input', () => {
        validatePassword();
        updateSubmitButton();
      });

      confirmPasswordInput.addEventListener('input', () => {
        validateConfirmPassword();
        updateSubmitButton();
      });

      termsInput.addEventListener('change', updateSubmitButton);

      document.getElementById('togglePassword').addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
        document.getElementById('togglePassword').textContent = type === 'password' ? '👁️' : '🙈';
      });

      document.getElementById('toggleConfirm').addEventListener('click', () => {
        const type = confirmPasswordInput.type === 'password' ? 'text' : 'password';
        confirmPasswordInput.type = type;
        document.getElementById('toggleConfirm').textContent = type === 'password' ? '👁️' : '🙈';
      });

      form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!validateUsername() || !validateEmail() || !validatePassword() || !validateConfirmPassword()) {
          return;
        }

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating Account...';

        // Use URL parameters to pass data to Streamlit
        window.location.href = `?action=register&username=${encodeURIComponent(username)}&email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;
      });

      // Function to show success message
      window.showSuccessMessage = function(message) {
        const overlay = document.getElementById('messageOverlay');
        const card = document.getElementById('messageCard');
        const icon = document.getElementById('messageIcon');
        const title = document.getElementById('messageTitle');
        const text = document.getElementById('messageText');
        const countdownContainer = document.getElementById('countdownContainer');
        const countdownNum = document.getElementById('countdownNum');
        const successContainer = document.getElementById('successContainer');
        const continueBtn = document.getElementById('continueBtn');

        icon.textContent = '🎉';
        title.textContent = 'Registration Successful!';
        text.textContent = message || 'Welcome to Vivido! Your account has been created successfully. You will be redirected to the login page.';

        if (successContainer) {
          successContainer.innerHTML = '';
          const banner = document.createElement('div');
          banner.className = 'success-message fx';
          banner.textContent = message || 'Registration successful! Redirecting to the login page.';
          successContainer.appendChild(banner);
        }
        
        card.classList.remove('error');
        card.classList.add('success');
        overlay.classList.add('show');
        document.body.classList.add('message-open');

        // Show countdown
        countdownContainer.style.display = 'block';
        continueBtn.style.display = 'inline-flex';
        let seconds = 2;
        countdownNum.textContent = String(seconds);
        
        const countdownInterval = setInterval(() => {
          seconds--;
          countdownNum.textContent = String(Math.max(seconds, 0));
          if (seconds < 0) {
            clearInterval(countdownInterval);
            window.location.href = '?action=goto_login';
          }
        }, 1000);
      };

      // Function to show error message
      window.showErrorMessage = function(message) {
        const overlay = document.getElementById('messageOverlay');
        const card = document.getElementById('messageCard');
        const icon = document.getElementById('messageIcon');
        const title = document.getElementById('messageTitle');
        const text = document.getElementById('messageText');
        const countdownContainer = document.getElementById('countdownContainer');
        const countdownNum = document.getElementById('countdownNum');
        const successContainer = document.getElementById('successContainer');
        const continueBtn = document.getElementById('continueBtn');

        icon.textContent = '⚠️';
        title.textContent = 'Registration Failed';
        text.textContent = message || 'An error occurred during registration.';

        if (successContainer) {
          successContainer.innerHTML = '';
        }
        
        card.classList.remove('success');
        card.classList.add('error');
        overlay.classList.add('show');
        document.body.classList.add('message-open');

        // Show countdown
        countdownContainer.style.display = 'block';
        continueBtn.style.display = 'none';
        let seconds = 2.5;
        countdownNum.textContent = String(Math.ceil(seconds));
        
        const countdownInterval = setInterval(() => {
          seconds -= 0.1;
          countdownNum.textContent = String(Math.max(Math.ceil(seconds), 0));
          if (seconds < 0) {
            clearInterval(countdownInterval);
            window.location.href = '?action=goto_login';
          }
        }, 100);
      };

      document.getElementById('continueBtn').addEventListener('click', () => {
        window.location.href = '?action=goto_login';
      });

      document.getElementById('messageOverlay').addEventListener('click', (e) => {
        if (e.target.id === 'messageOverlay') {
          e.currentTarget.classList.remove('show');
          document.body.classList.remove('message-open');
        }
      });

      // Show message from Streamlit-rendered state (inside this same page)
      try {
        const initialMessageType = __INITIAL_MESSAGE_TYPE__;
        const initialMessageText = __INITIAL_MESSAGE_TEXT__;
        if (initialMessageType === 'success') {
          window.showSuccessMessage(initialMessageText);
        } else if (initialMessageType === 'error') {
          window.showErrorMessage(initialMessageText || 'An error occurred.');
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

if "action" in query_params and query_params["action"][0] == "register":
    username = query_params.get("username", [""])[0]
    email = query_params.get("email", [""])[0]
    password = query_params.get("password", [""])[0]

    if username and email and password:
        try:
            result = register_user(username, email, password)
            if result["success"]:
                success_msg = result.get("message", "Registration successful!")
                st.query_params.clear()
                st.query_params["message_type"] = "success"
                st.query_params["message"] = success_msg
                st.rerun()
            else:
                error_msg = result.get("message", "Registration failed.")
                st.query_params.clear()
                st.query_params["message_type"] = "error"
                st.query_params["message"] = error_msg
                st.rerun()
        except Exception as e:
            st.query_params.clear()
            st.query_params["message_type"] = "error"
            st.query_params["message"] = str(e)
            st.rerun()
elif "action" in query_params and query_params["action"][0] == "goto_login":
    _set_query_params()
    st.switch_page("pages/login.py")

message_type = query_params.get("message_type", [""])[0]
message_text = query_params.get("message", [""])[0]

rendered_form_html = (
    form_html
    .replace("__INITIAL_MESSAGE_TYPE__", json.dumps(message_type))
    .replace("__INITIAL_MESSAGE_TEXT__", json.dumps(message_text))
)

# Render the form
components_html(rendered_form_html, height=1000)

# Clear query params after rendering to prevent message from showing again
if message_type:
    _set_query_params()

if message_type == "success":
    st.balloons()

# Redirect after showing the message
if message_type == "success":
    import time
    time.sleep(2.5)
    # Navigate to login page using Streamlit
    st.switch_page("pages/login.py")

error_msg = query_params.get("message", [""])[0]
if message_type == "error" and ("already exists" in error_msg.lower()):
    import time
    time.sleep(2.5)
    # Navigate to login page using Streamlit
    st.switch_page("pages/login.py")
