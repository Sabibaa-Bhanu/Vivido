import streamlit as st
from backend.database import get_connection

token = st.query_params.get("token")

if token:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users SET is_verified = 1
        WHERE verification_token = ?
    """, (token,))

    conn.commit()
    st.success("✅ Email verified successfully!")
else:
    st.error("Invalid or expired link")


st.title("✅ Verify Account")
st.write("This page can be used for email/OTP verification.")
