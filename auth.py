import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# ============================================
# 🔑 Load Environment Variables
# ============================================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # This should be your anon public key

# Debug: Show if credentials are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase credentials not found!")
    st.info("Create a `.env` file in your project root with:\n"
            "```\n"
            "SUPABASE_URL=your_supabase_url\n"
            "SUPABASE_KEY=your_anon_public_key\n"
            "```")
    st.stop()

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Failed to initialize Supabase: {str(e)}")
    st.stop()

# ============================================
# 🚀 AUTH FUNCTIONS
# ============================================

def signup_user(email: str, password: str):
    """Sign up a new user"""
    try:
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        # Correct Supabase SDK method
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            return True, f"✅ Account created! Check {email} for verification link."
        else:
            return False, "Signup failed. Try a different email."
            
    except Exception as e:
        error_msg = str(e)
        # Parse common Supabase errors
        if "already registered" in error_msg.lower():
            return False, "This email is already registered. Try logging in."
        elif "invalid email" in error_msg.lower():
            return False, "Invalid email format."
        else:
            return False, f"Signup error: {error_msg}"

def login_user(email: str, password: str):
    """Log in an existing user"""
    try:
        # Correct method for password-based login
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            # Store user info in session state
            st.session_state.user = response.user.email
            st.session_state.user_id = response.user.id
            st.session_state.access_token = response.session.access_token
            st.session_state.refresh_token = response.session.refresh_token
            
            return True, response.user
        else:
            return False, "Login failed. Check your credentials."
            
    except Exception as e:
        error_msg = str(e)
        if "invalid login credentials" in error_msg.lower():
            return False, "Invalid email or password."
        elif "user not found" in error_msg.lower():
            return False, "Email not found. Try signing up."
        else:
            return False, f"Login error: {error_msg}"

def reset_password(email: str):
    """Send password reset email"""
    try:
        response = supabase.auth.reset_password_for_email(email)
        return True, "📩 Password reset email sent! Check your inbox."
    except Exception as e:
        return False, f"Reset error: {str(e)}"

def logout_user():
    """Log out the current user"""
    try:
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.user_id = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        return True
    except Exception as e:
        return False

# ============================================
# 🎯 INITIALIZE SESSION STATE
# ============================================
if "user" not in st.session_state:
    st.session_state.user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

# ============================================
# 🎯 MAIN AUTH UI
# ============================================

def show_auth_page():
    """
    Display authentication page
    Returns user email if authenticated, else None
    """
    # If already logged in, don't show auth page
    if st.session_state.user:
        return st.session_state.user

    # Auth page
    st.set_page_config(page_title="Login - QA AI Agent", page_icon="🔐")
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🔐 QA AI Agent</h1>
        <p style="color: #999;">Secure Authentication</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.5); padding: 2rem; border-radius: 12px; border: 1px solid rgba(99, 102, 241, 0.2);">
        """, unsafe_allow_html=True)
        
        choice = st.radio(
            "Choose an option:",
            ["Login", "Sign Up", "Reset Password"],
            horizontal=False
        )

        email = st.text_input(
            "📧 Email",
            placeholder="your@email.com",
            key="auth_email"
        )
        
        if choice != "Reset Password":
            password = st.text_input(
                "🔑 Password",
                type="password",
                placeholder="Enter your password",
                key="auth_password"
            )
        else:
            password = None

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # LOGIN
        if choice == "Login":
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if not email or not password:
                    st.warning("⚠️ Please enter both email and password")
                else:
                    with st.spinner("Logging in..."):
                        success, result = login_user(email, password)
                        if success:
                            st.success(f"✅ Welcome back, {result.email}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {result}")

        # SIGNUP
        elif choice == "Sign Up":
            if st.button("✨ Create Account", use_container_width=True, type="primary"):
                if not email or not password:
                    st.warning("⚠️ Please enter both email and password")
                else:
                    with st.spinner("Creating account..."):
                        success, message = signup_user(email, password)
                        if success:
                            st.success(message)
                            st.info("💡 Please verify your email before logging in.")
                        else:
                            st.error(f"❌ {message}")

        # RESET PASSWORD
        elif choice == "Reset Password":
            if st.button("📧 Send Reset Email", use_container_width=True, type="primary"):
                if not email:
                    st.warning("⚠️ Please enter your email")
                else:
                    with st.spinner("Sending reset email..."):
                        success, message = reset_password(email)
                        if success:
                            st.success(message)
                        else:
                            st.error(f"❌ {message}")

        st.markdown("</div>", unsafe_allow_html=True)
    
    return None

# ============================================
# 🔐 PROTECTED ROUTE DECORATOR
# ============================================

def require_login(f):
    """Decorator to protect pages that require login"""
    def wrapper(*args, **kwargs):
        if not st.session_state.user:
            st.error("❌ Please log in to access this page")
            return
        return f(*args, **kwargs)
    return wrapper