import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# ============================================
# 🔑 Load Supabase credentials from .env
# ============================================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase credentials not found. Add SUPABASE_URL and SUPABASE_KEY in .env")
    st.stop()

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# 🚀 AUTH FUNCTIONS
# ============================================

def signup_user(email, password):
    try:
        data = supabase.auth.sign_up(email=email, password=password)
        if data.user:
            return True, "Account created successfully! Please verify your email."
        else:
            return False, data.message
    except Exception as e:
        return False, str(e)

def login_user(email, password):
    try:
        data = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if data.user:
            # Save session in Streamlit
            st.session_state.user = data.user.email
            st.session_state.access_token = data.session.access_token
            return True, data.user
        else:
            return False, data.message
    except Exception as e:
        return False, str(e)

def reset_password(email):
    try:
        data = supabase.auth.reset_password_for_email(email)
        if data:
            return True, "Password reset email sent"
        else:
            return False, "Failed to send reset email"
    except Exception as e:
        return False, str(e)

# ============================================
# 🎯 MAIN AUTH UI
# ============================================

def show_auth():
    """
    Returns logged-in user email if authenticated, else None
    """
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        return st.session_state.user

    st.title("🔐 Login / Signup")
    choice = st.radio("Select Option", ["Login", "Signup", "Reset Password"])

    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")

    if choice == "Login" and st.button("Login"):
        if not email or not password:
            st.warning("Please enter email and password")
            return None

        success, result = login_user(email, password)
        if success:
            st.success(f"✅ Login successful: {result.email}")
            st.rerun()
        else:
            st.error(f"❌ {result}")

    elif choice == "Signup" and st.button("Create Account"):
        if not email or not password:
            st.warning("Please enter email and password")
            return None

        success, message = signup_user(email, password)
        if success:
            st.success(message)
        else:
            st.error(f"❌ {message}")

    elif choice == "Reset Password" and st.button("Send Reset Email"):
        if not email:
            st.warning("Enter your email")
            return None

        success, message = reset_password(email)
        if success:
            st.success("📩 " + message)
        else:
            st.error(f"❌ {message}")

    return None

# ============================================
# 🚪 LOGOUT FUNCTION
# ============================================

def logout():
    st.session_state.user = None
    st.session_state.access_token = None
    st.rerun()