import streamlit as st
import os
import datetime
import base64
from PIL import Image
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Payment - Vivido",
    page_icon="assets/logo/vivido_logo2.jpeg",
    layout="wide"
)

# Import backend modules (with fallback for demo mode)
try:
    from backend.razorpay_payment import (
        create_payment_order, 
        verify_payment_signature,
        get_payment_amount,
        check_razorpay_configuration
    )
    RAZORPAY_AVAILABLE = True
except ModuleNotFoundError:
    # Demo mode - razorpay not installed
    RAZORPAY_AVAILABLE = False
    
    def create_payment_order(user_id, amount=None, image_quality="standard", notes=None):
        return {"success": True, "order_id": f"demo_{user_id}", "key_id": "demo"}
    
    def get_payment_amount(quality="standard"):
        amounts = {"standard": 1000, "hd": 2000, "premium": 5000}
        return amounts.get(quality, 1000)
    
    def check_razorpay_configuration():
        return {"configured": False}

# ============================================================
# AUTHENTICATION CHECK
# ============================================================

if (
    not st.session_state.get("logged_in")
    and st.session_state.get("user_id")
    and st.session_state.get("current_user")
):
    st.session_state["logged_in"] = True

if not st.session_state.get("logged_in"):
    st.session_state["redirect_after_login"] = "pages/payment_checkout.py"
    st.switch_page("pages/login.py")

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
    --success: #10b981;
    --error: #ef4444;
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

.payment-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 16px;
    padding: 24px;
}

.payment-header {
    text-align: center;
    padding: 20px 0;
    border-bottom: 1px solid rgba(124, 58, 237, 0.2);
    margin-bottom: 24px;
}

.payment-title {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.image-preview {
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid rgba(124, 58, 237, 0.3);
}

.order-details {
    background: rgba(124, 58, 237, 0.1);
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid rgba(124, 58, 237, 0.1);
}

.detail-label {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

.detail-value {
    color: var(--text-primary);
    font-weight: 600;
    font-size: 0.95rem;
}

.price-section {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.2), rgba(6, 182, 212, 0.1));
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    margin: 20px 0;
}

.price-amount {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary-light);
}

.price-currency {
    font-size: 1.5rem;
    vertical-align: top;
}

.payment-btn {
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    border: none;
    border-radius: 12px;
    padding: 16px 32px;
    color: white;
    font-weight: 600;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.3s ease;
    width: 100%;
    margin-top: 20px;
}

.payment-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(124, 58, 237, 0.4);
}

.payment-btn:disabled {
    background: linear-gradient(135deg, #4b5563, #6b7280);
    cursor: not-allowed;
    transform: none;
}

.success-card {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.1));
    border: 2px solid var(--success);
    border-radius: 16px;
    padding: 40px;
    text-align: center;
}

.success-icon {
    font-size: 4rem;
    margin-bottom: 20px;
}

.success-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--success);
    margin-bottom: 12px;
}

.download-btn {
    background: linear-gradient(135deg, #10b981, #06b6d4);
    border: none;
    border-radius: 12px;
    padding: 18px 36px;
    color: white;
    font-weight: 600;
    font-size: 1.2rem;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 24px;
}

.download-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
}

.error-card {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
    border: 2px solid var(--error);
    border-radius: 16px;
    padding: 40px;
    text-align: center;
}

.error-icon {
    font-size: 4rem;
    margin-bottom: 20px;
}

.error-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--error);
    margin-bottom: 12px;
}

.retry-btn {
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    border: none;
    border-radius: 12px;
    padding: 14px 28px;
    color: white;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 20px;
}

.retry-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(124, 58, 237, 0.4);
}

.security-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-secondary);
    font-size: 0.85rem;
    margin-top: 20px;
}

.loader {
    border: 4px solid rgba(124, 58, 237, 0.2);
    border-top: 4px solid var(--primary);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 20px auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_image_preview(image_path):
    """Get base64 encoded image for preview."""
    if not os.path.exists(image_path):
        return None
    
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize for preview (max 400px)
            max_size = 400
            ratio = min(max_size/img.width, max_size/img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to buffer
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None


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
# MAIN CONTENT
# ============================================================

# Check payment status from session state
payment_status = st.session_state.get("payment_status", "pending")
order_id = st.session_state.get("razorpay_order_id", "")
payment_id = st.session_state.get("razorpay_payment_id", "")

# Payment Success Page
if payment_status == "success":
    st.markdown("""
    <div class="success-card">
        <div class="success-icon">✅</div>
        <div class="success-title">Payment Successful!</div>
        <p style="color: var(--text-secondary);">Your payment has been processed successfully.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Transaction details
    st.markdown(f"""
    <div class="order-details" style="margin-top: 30px;">
        <div class="detail-row">
            <span class="detail-label">Transaction ID</span>
            <span class="detail-value">{payment_id or 'N/A'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Order ID</span>
            <span class="detail-value">{order_id or 'N/A'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Amount Paid</span>
            <span class="detail-value">₹{st.session_state.get('payment_amount', 0)/100:.2f}</span>
        </div>
        <div class="detail-row" style="border-bottom: none;">
            <span class="detail-label">Date</span>
            <span class="detail-value">{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Download button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⬇️ Download Your Image", key="download_btn", use_container_width=True):
            # Mark as paid in session
            st.session_state["payment_verified"] = True
            st.switch_page("pages/image_processing.py")
    
    # Back to home
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to Home", key="back_home_btn"):
        st.switch_page("pages/dashboard.py")

# Payment Failure Page
elif payment_status == "failed":
    st.markdown("""
    <div class="error-card">
        <div class="error-icon">❌</div>
        <div class="error-title">Payment Failed</div>
        <p style="color: var(--text-secondary);">We couldn't process your payment. Please try again.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Error details
    error_msg = st.session_state.get("payment_error", "Unknown error")
    st.markdown(f"""
    <div class="order-details" style="margin-top: 30px;">
        <div class="detail-row" style="border-bottom: none;">
            <span class="detail-label">Error</span>
            <span class="detail-value" style="color: var(--error);">{error_msg}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Retry button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Try Again", key="retry_btn", use_container_width=True):
            # Clear payment state and go back to checkout
            st.session_state["payment_status"] = "pending"
            st.session_state["razorpay_order_id"] = ""
            st.session_state["razorpay_payment_id"] = ""
            st.session_state["payment_error"] = ""
            st.rerun()
    
    # Contact support
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: var(--text-secondary);">
        <p>Need help? Contact our support team:</p>
        <p style="font-weight: 600;">📧 support@vivido.com | 📞 +91 98765 43210</p>
    </div>
    """, unsafe_allow_html=True)

# Payment Checkout Page (Default)
else:
    # Get payment details from session state
    # Try multiple possible keys for processed image
    style_name = st.session_state.get("selected_style", st.session_state.get("style_lab_style_name", "Custom"))
    original_filename = st.session_state.get("uploaded_filename", st.session_state.get("uploaded_image_name", "image.jpg"))
    processed_image_path = st.session_state.get("processed_image_path", st.session_state.get("style_lab_output_path", ""))
    image_quality = st.session_state.get("image_quality", "standard")
    
    # Debug info - show what's in session state (remove in production)
    with st.expander("Debug Info"):
        st.write("Session State Keys:", list(st.session_state.keys()))
        st.write("processed_image_path:", processed_image_path)
        st.write("style_lab_output_path:", st.session_state.get("style_lab_output_path", "NOT SET"))
    
    # Check if user came from processing page
    has_processed_image = processed_image_path and os.path.exists(processed_image_path)
    
    # Calculate price
    
    # Calculate price
    price_paise = get_payment_amount(image_quality)
    price_rupees = price_paise / 100
    
    # Header
    st.markdown("""
    <div class="payment-header">
        <div class="payment-title">💳 Secure Payment</div>
        <p style="color: var(--text-secondary);">Complete your purchase to download your image</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main layout - two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Image Preview
        st.markdown("### 🖼️ Your Image")
        
        if processed_image_path and os.path.exists(processed_image_path):
            try:
                with Image.open(processed_image_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize for preview
                    max_size = 350
                    ratio = min(max_size/img.width, max_size/img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    st.image(img, use_container_width=True, clamp=True)
            except Exception as e:
                st.error(f"Error loading image: {e}")
                st.info("Image preview not available")
        else:
            # Show placeholder for demo mode
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(124, 58, 237, 0.2), rgba(6, 182, 212, 0.1));
                border: 2px dashed rgba(124, 58, 237, 0.4);
                border-radius: 12px;
                padding: 60px;
                text-align: center;
            ">
                <div style="font-size: 3rem; margin-bottom: 12px;">🖼️</div>
                <div style="color: var(--text-secondary);">Demo Mode</div>
                <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">
                    Process an image first to see preview
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Order Summary
        st.markdown("### 📋 Order Summary")
        
        st.markdown(f"""
        <div class="order-details">
            <div class="detail-row">
                <span class="detail-label">Image</span>
                <span class="detail-value">{original_filename}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Style Applied</span>
                <span class="detail-value">{style_name}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Quality</span>
                <span class="detail-value">{image_quality.title()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Format</span>
                <span class="detail-value">PNG / JPG / PDF</span>
            </div>
            <div class="detail-row" style="border-bottom: none;">
                <span class="detail-label">File ID</span>
                <span class="detail-value" style="font-size: 0.8rem;">{st.session_state.get('user_id', 'N/A')}_{datetime.datetime.now().strftime('%Y%m%d')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Price section
        st.markdown(f"""
        <div class="price-section">
            <div style="color: var(--text-secondary); margin-bottom: 8px;">Total Amount</div>
            <div class="price-amount">
                <span class="price-currency">₹</span>{int(price_rupees)}
            </div>
            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">
                Includes all taxes
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Proceed to Payment button
        if st.button("💳 Proceed to Payment", key="proceed_payment_btn", use_container_width=True):
            # Check Razorpay configuration
            if not RAZORPAY_AVAILABLE:
                st.warning("⚠️ Demo Mode - Payment system not available")
                # Simulate successful order for demo
                st.session_state["razorpay_order_id"] = f"demo_{st.session_state.get('user_id', 1)}"
                st.session_state["razorpay_key_id"] = "demo"
                st.session_state["payment_amount"] = price_paise
                
                st.info("💳 **Demo Mode**\n\nUsing test card for demo:\n\n- **Card Number:** 4111 1111 1111 1111\n- **Expiry:** 12/25\n- **CVV:** 123\n- **OTP:** 123456")
                
                if st.button("✅ Simulate Successful Payment (Demo)", key="simulate_payment"):
                    st.session_state["payment_status"] = "success"
                    st.session_state["razorpay_payment_id"] = f"pay_demo_{st.session_state.get('user_id', 1)}"
                    st.session_state["payment_verified"] = True
                    st.rerun()
            else:
                config = check_razorpay_configuration()
                
                if not config["configured"]:
                    st.error("⚠️ Payment system not configured. Please contact support.")
                else:
                    # Create payment order
                    with st.spinner("Initializing payment..."):
                        order_result = create_payment_order(
                            user_id=st.session_state.get("user_id", 1),
                            amount=price_paise,
                            image_quality=image_quality,
                            notes={
                                "style": style_name,
                                "filename": original_filename,
                                "quality": image_quality
                            }
                        )
                    
                    if order_result.get("success"):
                        # Store order details
                        st.session_state["razorpay_order_id"] = order_result.get("order_id")
                        st.session_state["razorpay_key_id"] = order_result.get("key_id")
                        st.session_state["payment_amount"] = price_paise
                        
                        # Show payment form info
                        st.success(f"✅ Order created! Order ID: {order_result.get('order_id')}")
                        
                        # Display Razorpay checkout info
                        st.info("💳 **Razorpay Checkout**\n\nIn production, Razorpay's secure checkout form would open here. For testing, use:\n\n- **Card Number:** 4111 1111 1111 1111\n- **Expiry:** 12/25\n- **CVV:** 123\n- **OTP:** 123456")
                        
                        # Simulate payment (for demo)
                        st.warning("⚠️ Demo Mode: Click below to simulate successful payment")
                        
                        if st.button("✅ Simulate Successful Payment (Demo)", key="simulate_payment_real"):
                            st.session_state["payment_status"] = "success"
                            st.session_state["razorpay_payment_id"] = f"pay_{order_result.get('order_id')}_demo"
                            st.session_state["payment_verified"] = True
                            st.rerun()
                    else:
                        st.error(f"Failed to create payment order: {order_result.get('error')}")
        
        # Security badges
        st.markdown("""
        <div class="security-badge">
            <span>🔒</span>
            <span>Secure Payment powered by Razorpay</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Back button
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back", key="back_btn"):
            st.switch_page("pages/image_processing.py")

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); font-size: 0.8rem; padding: 20px;">
    <p>🔒 Your payment is secured with 256-bit SSL encryption</p>
    <p>© 2024 Vivido - AI Image Processing</p>
</div>
""", unsafe_allow_html=True)
