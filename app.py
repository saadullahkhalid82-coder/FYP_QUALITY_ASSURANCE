import streamlit as st
import os
import sys
from pathlib import Path
from fpdf import FPDF
import shutil
import time
from supabase import create_client
from dotenv import load_dotenv
from project_analyzer import find_python_entry_files, extract_zip, generate_ast_tree
from code_analyzer import CodeAnalyzer
from context_enricher import gather_enriched_context, generate_tests_with_llm, save_generated_tests
from Test_executor_agent import TestExecutorAgent
from reporting_agent import ReportingAgent
from context_enricher import gather_all_project_context

# ---------------------------
# Page Configuration
# ---------------------------
st.set_page_config(
    page_title="🤖 AI Test Generator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# 🔑 Load Supabase credentials from .env
# ---------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------
# 🔐 AUTH FUNCTIONS
# ---------------------------
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# ---------------------------
# 🔐 AUTH FUNCTIONS (FIXED)
# ---------------------------

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def signup_user(email, password):

    try:
        # 1️⃣ Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if not response or not response.user:
            return False, "Signup failed"

        user_id = response.user.id

        # 2️⃣ Insert into users table (SAFE)
        try:
            supabase.table("users").insert({
                "id": user_id,
                "email": email
            }).execute()
        except Exception as db_error:
            return False, f"User created but DB insert failed: {db_error}"

        return True, "Account created successfully!"

    except Exception as e:
        return False, str(e)


def login_user(email, password):
    try:
        result = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # result is a dict
        if result.session and result.user:
            st.session_state.user = result.user.email
            st.session_state.user_id = result.user.id
            st.session_state.access_token = result.session.access_token
            return True, result.user
        else:
            return False, "Invalid credentials"

    except Exception as e:
        return False, str(e)

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email)
        return True, "Password reset email sent"
    except Exception as e:
        return False, str(e)


def logout():
    st.session_state.clear()
    st.rerun()

def show_auth_page():
    """Display authentication UI"""
    # Custom CSS for Auth Page
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    .auth-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: #0a0a0f;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
            radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.1) 0%, transparent 40%);
    }
    
    .auth-box {
        background: rgba(17, 24, 39, 0.8);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 3rem;
        width: 100%;
        max-width: 450px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    
    .auth-title {
        background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        font-family: 'Outfit', sans-serif;
    }
    
    .auth-subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .auth-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    
    .auth-input {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 0.75rem !important;
    }
    
    .auth-input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }
    
    .auth-button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 0.75rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2) !important;
    }
    
    .auth-button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 20px 25px -5px rgba(79, 70, 229, 0.4) !important;
    }
    
    .auth-toggle {
        text-align: center;
        margin-top: 2rem;
        color: #94a3b8;
        font-size: 0.9rem;
    }
    
    .auth-toggle a {
        color: #6366f1;
        text-decoration: none;
        font-weight: 600;
        cursor: pointer;
    }
    
    .auth-toggle a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if Supabase is configured
    if not supabase_client:
        st.error("❌ Authentication service not configured. Please add SUPABASE_URL and SUPABASE_KEY to your .env file.")
        st.stop()
    
    # Initialize session state for auth tab
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"
    
    # Main container
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("""
        <div class="auth-box">
            <div class="auth-title">🤖 QA AI</div>
            <div class="auth-subtitle">Intelligent Test Generation Platform</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tab selection
        tab1, tab2, tab3 = st.tabs(["🔓 Login", "📝 Sign Up", "🔐 Reset Password"])
        
        # LOGIN TAB
        with tab1:
            st.markdown('<div class="auth-box" style="margin-top: 2rem;">', unsafe_allow_html=True)
            st.markdown("### Welcome Back!")
            
            email_login = st.text_input(
                "📧 Email",
                key="login_email",
                placeholder="your@email.com"
            )
            password_login = st.text_input(
                "🔑 Password",
                type="password",
                key="login_password",
                placeholder="Enter your password"
            )
            
            col_login1, col_login2 = st.columns(2)
            
            with col_login1:
                if st.button("🔓 Login", use_container_width=True, type="primary"):
                    if not email_login or not password_login:
                        st.warning("⚠️ Please enter both email and password")
                    else:
                        with st.spinner("Authenticating..."):
                            success, result = login_user(email_login, password_login)
                            if success:
                                st.success(f"✅ Login successful! Welcome back, {result.email}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Login failed: {result}")
            
            with col_login2:
                if st.button("← Back", use_container_width=True):
                    pass
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # SIGNUP TAB
        with tab2:
            st.markdown('<div class="auth-box" style="margin-top: 2rem;">', unsafe_allow_html=True)
            st.markdown("### Create Your Account")
            
            email_signup = st.text_input(
                "📧 Email",
                key="signup_email",
                placeholder="your@email.com"
            )
            password_signup = st.text_input(
                "🔑 Password",
                type="password",
                key="signup_password",
                placeholder="Create a strong password"
            )
            password_confirm = st.text_input(
                "🔑 Confirm Password",
                type="password",
                key="confirm_password",
                placeholder="Confirm your password"
            )
            
            if st.button("📝 Create Account", use_container_width=True, type="primary"):
                if not email_signup or not password_signup:
                    st.warning("⚠️ Please fill in all fields")
                elif password_signup != password_confirm:
                    st.error("❌ Passwords do not match")
                elif len(password_signup) < 6:
                    st.warning("⚠️ Password must be at least 6 characters")
                else:
                    with st.spinner("Creating account..."):
                        success, message = signup_user(email_signup.strip(), password_signup)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("📧 Please check your email to verify your account before logging in.")
                        else:
                            st.error(f"❌ Signup failed: {message}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # RESET PASSWORD TAB
        with tab3:
            st.markdown('<div class="auth-box" style="margin-top: 2rem;">', unsafe_allow_html=True)
            st.markdown("### Reset Your Password")
            
            email_reset = st.text_input(
                "📧 Email",
                key="reset_email",
                placeholder="your@email.com"
            )
            
            if st.button("📧 Send Reset Email", use_container_width=True, type="primary"):
                if not email_reset:
                    st.warning("⚠️ Please enter your email")
                else:
                    with st.spinner("Sending reset email..."):
                        success, message = reset_password(email_reset)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("📩 Check your email for password reset instructions")
                        else:
                            st.error(f"❌ {message}")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Custom CSS Styling (Main App)
# ---------------------------
st.markdown("""
<style>
/* =====================
   GLOBAL THEME
===================== */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

.stApp {
    background: #0a0a0f;
    background-image: 
        radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(6, 182, 212, 0.1) 0%, transparent 40%);
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    letter-spacing: -0.02em;
}

/* =====================
   COMPONENTS
===================== */
.main-container {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 2.5rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

/* Brand Header */
.brand-header {
    text-align: center;
    padding: 3rem 0;
    position: relative;
}

.brand-title {
    background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 4rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 0 30px rgba(99, 102, 241, 0.3));
}

.brand-subtitle {
    font-size: 1.25rem;
    color: #94a3b8;
    font-weight: 300;
    max-width: 600px;
    margin: 0 auto;
}

/* Glass Cards */
.glass-card {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
    transform: translateY(-4px);
    background: rgba(30, 41, 59, 0.6);
    border-color: rgba(99, 102, 241, 0.2);
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    border: none;
    color: white;
    border-radius: 12px;
    padding: 0.75rem 2rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2), 
                0 10px 15px -3px rgba(79, 70, 229, 0.2);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 25px -5px rgba(79, 70, 229, 0.4);
}

.stButton > button:active {
    transform: translateY(0);
}

/* Status Badges */
.status-badge {
    padding: 0.5rem 1rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.status-success {
    background: rgba(16, 185, 129, 0.1);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-pending {
    background: rgba(245, 158, 11, 0.1);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.2);
}

.status-error {
    background: rgba(239, 68, 68, 0.1);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Inputs */
.stTextInput > div > div > input {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: white;
    border-radius: 10px;
}

.stTextInput > div > div > input:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

/* Code Blocks */
.stCodeBlock {
    background: #0f172a !important;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
}

/* Progress Stepper */
.step-container {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
    margin: 2rem 0;
}

.step-card {
    text-align: center;
    padding: 1rem;
    border-radius: 12px;
    transition: all 0.3s ease;
}

.step-card.active {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.step-number {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    margin: 0 auto 0.5rem;
    font-weight: 700;
}

.step-card.active .step-number {
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    box-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
}

.step-card.completed .step-number {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
}

.metric-box {
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.4) 100%);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
}

.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}

.metric-label {
    color: #94a3b8;
    font-size: 0.9rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 🔐 Authentication Check
# ---------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    show_auth_page()
    st.stop()

# ---------------------------
# MAIN APP - Only shown when authenticated
# ---------------------------

# ---------------------------
# Header Section
# ---------------------------
st.markdown("""
<div class="brand-header">
    <div class="brand-title">QA AI AGENT</div>
    <div class="brand-subtitle">Automated Testing, Executed and Report Generator</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Constants
# ---------------------------
UPLOAD_DIR = "uploaded_projects"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------
# Session State Initialization
# ---------------------------
for key in ["folder", "context", "test_path", "target_file", "test_results", "report_path", "ast_generated", "tests_generated", "ast_content"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Initialize boolean states
if "ast_generated" not in st.session_state:
    st.session_state.ast_generated = False
if "tests_generated" not in st.session_state:
    st.session_state.tests_generated = False

# ---------------------------
# Progress Steps Indicator
# ---------------------------
def show_progress_steps(current_step):
    steps = ["Upload", "Analysis", "Generate", "Execute", "Report"]
    
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    cols = st.columns(len(steps))
    
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx < current_step:
                # Completed
                st.markdown(f"""
                <div class="step-card completed">
                    <div class="step-number">✓</div>
                    <div style="color: #34d399; font-weight: 600;">{step}</div>
                </div>
                """, unsafe_allow_html=True)
            elif idx == current_step:
                # Active
                st.markdown(f"""
                <div class="step-card active">
                    <div class="step-number">{idx+1}</div>
                    <div style="color: #6366f1; font-weight: 700;">{step}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Pending
                st.markdown(f"""
                <div class="step-card">
                    <div class="step-number" style="background: rgba(255,255,255,0.05); color: #64748b;">{idx+1}</div>
                    <div style="color: #64748b;">{step}</div>
                </div>
                """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)

# Determine current step
current_step = 0
if st.session_state.folder:
    current_step = 1
if st.session_state.target_file:
    current_step = 2
if st.session_state.test_path:
    current_step = 3
if st.session_state.test_results:
    current_step = 4

show_progress_steps(current_step)

st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)

# ---------------------------
# Sidebar - User Info & Stats
# ---------------------------
with st.sidebar:
    st.markdown("### 👤 User Profile")
    
    # Display user info
    st.markdown(f"""
    <div class="glass-card" style="padding: 1rem;">
        <strong style="color: #94a3b8;">📧 Email:</strong><br>
        <span style="color: #e2e8f0; font-weight: 600;">{st.session_state.user}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        logout()
    
    st.markdown("---")
    st.markdown("### Project Dashboard")
    
    if st.session_state.folder:
        st.markdown(f"""
        <div class="glass-card" style="padding: 1rem;">
            <strong style="color: #94a3b8;"> Project:</strong><br>
            <span style="color: #e2e8f0; font-weight: 600;">{os.path.basename(st.session_state.folder)}</span>
        </div>
        """, unsafe_allow_html=True)
    
    if st.session_state.target_file:
        st.markdown(f"""
        <div class="glass-card" style="padding: 1rem;">
            <strong style="color: #94a3b8;"> Target File:</strong><br>
            <span style="color: #e2e8f0; font-weight: 600;">{os.path.basename(st.session_state.target_file)}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Status indicators
    st.markdown("###  Status")
    
    statuses = [
        ("Project Uploaded", st.session_state.folder is not None),
        ("AST Generated", st.session_state.ast_generated),
        ("Tests Generated", st.session_state.tests_generated),
        ("Tests Executed", st.session_state.test_results is not None),
        ("Report Created", st.session_state.report_path is not None),
    ]
    
    for label, status in statuses:
        badge_class = "status-success" if status else "status-pending"
        icon = "✓" if status else "○"
        st.markdown(f'<span class="status-badge {badge_class}">{icon} {label}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #718096; font-size: 0.85rem;">
        <strong>Powered by AI</strong><br>
         Intelligent Test Generation<br>
         Automated Execution<br>
         Smart Reporting
    </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Main Content Area
# ---------------------------

# Step 1: Upload ZIP
st.markdown('<h2 class="section-header">📤 Step 1: Upload Project</h2>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    uploaded_zip = st.file_uploader(
        "Drop your Python project ZIP file here",
        type="zip",
        help="Upload a ZIP file containing your Python project"
    )
    
    if uploaded_zip:
        project_name = uploaded_zip.name.replace(".zip", "")
        project_path = os.path.join(UPLOAD_DIR, project_name)

        if not os.path.exists(project_path):
            with st.spinner(" Extracting project files..."):
                progress_bar = st.progress(0)
                
                zip_path = os.path.join(UPLOAD_DIR, uploaded_zip.name)
                with open(zip_path, "wb") as f:
                    f.write(uploaded_zip.getbuffer())
                progress_bar.progress(30)
                
                extract_zip(zip_path, extract_to=project_path)
                progress_bar.progress(70)
                
                os.remove(zip_path)
                progress_bar.progress(100)
                time.sleep(0.3)
                progress_bar.empty()

        st.session_state.folder = project_path
        st.success(f" Project successfully extracted to: {project_path}")

        # Ensure package structure
        for sub in ["", "src", "generated_tests"]:
            init_path = os.path.join(project_path, sub, "_init_.py")
            os.makedirs(os.path.dirname(init_path), exist_ok=True)
            if not os.path.exists(init_path):
                open(init_path, "w").close()

        # Detect entry files
        with st.spinner("🔍 Scanning for Python files..."):
            entry_files = find_python_entry_files(project_path)
        
        st.markdown("### Detected Python Files")
        
        cols = st.columns(3)
        for idx, file in enumerate(entry_files):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.4); padding: 0.75rem; border-radius: 8px; margin: 0.25rem 0; border-left: 3px solid #6366f1;">
                     {os.path.basename(file)}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("###  Select Target File")
        target_file = st.selectbox(
            "Choose the Python file to generate tests for:",
            entry_files,
            label_visibility="collapsed"
        )

        if target_file:
            st.session_state.target_file = target_file
            st.success(f"Target file selected: *{os.path.basename(target_file)}*")

            # AST Generation
            st.markdown("###  Abstract Syntax Tree (AST) Generation")
            
            if st.button(" Generate AST", use_container_width=True):
                with st.spinner("Parsing code structure..."):
                    try:
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        
                        ast_content = generate_ast_tree(target_file)
                        st.session_state.ast_content = ast_content
                        st.session_state.ast_generated = True
                        progress_bar.empty()
                        
                        st.success(" AST generated successfully!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f" Error generating AST: {str(e)}")

            # Display AST if already generated (persistent state)
            if st.session_state.ast_generated and st.session_state.ast_content:
                with st.expander("📜 View Abstract Syntax Tree (AST)", expanded=False):
                    st.code(st.session_state.ast_content, language="python")

            # Code Analysis
            if st.session_state.ast_generated:
                st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)
                st.markdown('<h2 class="section-header">🔍 Step 2: Code Analysis</h2>', unsafe_allow_html=True)
                
                with st.spinner(" Analyzing code complexity..."):
                    analyzer = CodeAnalyzer(target_file)
                    functions = analyzer.extract_functions()

                    for fn in functions:
                        fn["priority"] = analyzer.calculate_priority(fn)

                    ranked = sorted(functions, key=lambda x: x["priority"], reverse=True)
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{len(ranked)}</div>
                        <div class="metric-label">Functions Found</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    avg_complexity = sum(fn['complexity'] for fn in ranked) / len(ranked) if ranked else 0
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{avg_complexity:.1f}</div>
                        <div class="metric-label">Avg Complexity</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    high_priority = sum(1 for fn in ranked if fn['priority'] >= 7)
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{high_priority}</div>
                        <div class="metric-label">Critical Functions</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### Function Analysis Results")
                
                for fn in ranked:
                    priority_color = "#48bb78" if fn['priority'] >= 7 else "#ed8936" if fn['priority'] >= 4 else "#fc8181"
                    st.markdown(f"""
                    <div class="glass-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="font-size: 1.1rem; color: #e2e8f0;">🔹 {fn['name']}</strong><br>
                                <small style="color: #94a3b8;">Arguments: {', '.join(fn['args']) if fn['args'] else 'None'}</small>
                            </div>
                            <div style="text-align: right;">
                                <span style="background: {priority_color}20; color: {priority_color}; padding: 0.25rem 0.75rem; border-radius: 99px; font-weight: 600; border: 1px solid {priority_color}40;">
                                    Priority: {fn['priority']}
                                </span><br>
                                <small style="color: #64748b;">Complexity: {fn['complexity']}</small>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Context Enrichment
                st.session_state.context = gather_enriched_context(target_file, project_path)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Step 3: Generate Tests
# ---------------------------
if st.session_state.context:
    st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">🤖 Step 3: AI Test Generation</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card" style="border-left: 4px solid #6366f1; background: rgba(99, 102, 241, 0.1);">
        <strong>🧠 AI-Powered Testing</strong><br>
        Our intelligent system will analyze your code and generate comprehensive unit tests automatically.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(" Generate Tests with AI", use_container_width=True, type="primary"):
        with st.spinner("AI is analyzing your code and generating tests..."):
            progress_bar = st.progress(0)
            
            # Simulate progressive AI work
            for i in range(0, 30):
                time.sleep(0.02)
                progress_bar.progress(i)
            
            test_code = generate_tests_with_llm(st.session_state.context)
            
            for i in range(30, 100):
                time.sleep(0.01)
                progress_bar.progress(i)
            
            progress_bar.empty()
            
            st.markdown("### Generated Test Code")
            st.code(test_code, language="python", line_numbers=True)

            test_path = save_generated_tests(
                save_dir=os.path.join(st.session_state.folder, "generated_tests"),
                target_file=st.session_state.target_file,
                test_code=test_code,
            )
            st.session_state.test_path = test_path
            st.session_state.tests_generated = True
            
            st.success(f" Tests successfully saved at: {test_path}")
            st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Step 4: Execute Tests
# ---------------------------
if st.session_state.test_path:
    st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">⚡ Step 4: Test Execution</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    if st.button("⚡ Execute Generated Tests", use_container_width=True, type="primary"):
        st.markdown("### 🔄 Running Test Suite...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        project_path = os.path.abspath(st.session_state.folder)
        if project_path not in sys.path:
            sys.path.insert(0, project_path)

        # Animated progress
        for i in range(0, 50):
            time.sleep(0.02)
            progress_bar.progress(i)
            status_text.text(f" Initializing test environment... {i*2}%")
        
        executor = TestExecutorAgent(project_path=project_path)
        results = executor.execute_tests()
        st.session_state.test_results = results
        
        for i in range(50, 100):
            time.sleep(0.01)
            progress_bar.progress(i)
            status_text.text(f" Executing tests... {i}%")
        
        progress_bar.empty()
        status_text.empty()

        st.markdown("###  Test Execution Results")
        
        # Display results in a styled container
        st.markdown("""
        <div style="background: #1a202c; color: #48bb78; padding: 1.5rem; border-radius: 10px; font-family: monospace;">
        """, unsafe_allow_html=True)
        st.text(results)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.success(" Test execution completed!")

    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Step 5: Generate Report
# ---------------------------
if st.session_state.test_results:
    st.markdown('<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), transparent); margin: 2rem 0;"></div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header"> Step 5: Generate Report</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    if st.button(" Generate AI Test Report", use_container_width=True, type="primary"):
        log_path = st.session_state.test_results.get("log_report")
        if not log_path or not os.path.exists(log_path):
            st.error("Test log not found. Cannot generate report.")
        else:
            with st.spinner("Generating comprehensive AI report..."):
                progress_bar = st.progress(0)
                
                # Initialize ReportingAgent
                for i in range(0, 25):
                    time.sleep(0.02)
                    progress_bar.progress(i)
                
                reporter = ReportingAgent(log_path)
                reporter.parse_unittest_log()
                
                for i in range(25, 75):
                    time.sleep(0.02)
                    progress_bar.progress(i)

                # Generate PDF report
                pdf_output_path = os.path.join(
                    st.session_state.folder,
                    "ai_test_report.pdf"
                )
    
                
                reporter.generate_pdf_report(pdf_output_path)
                st.session_state.report_path = pdf_output_path
                
                for i in range(75, 100):
                    time.sleep(0.01)
                    progress_bar.progress(i)
                
                progress_bar.empty()

                st.success(f" AI Test Report Generated Successfully!")
                st.balloons()

                # Preview with download
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="glass-card" style="padding: 1rem;">
                        <strong style="color: #cbd5e1;"> Report Location:</strong><br>
                        <code style="background: rgba(0,0,0,0.3); color: #67e8f9;">{pdf_output_path}</code>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    with open(pdf_output_path, "rb") as f_pdf:
                        st.download_button(
                            label="Download PDF Report",
                            data=f_pdf,
                            file_name="ai_test_report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

import os
import streamlit as st
from dotenv import load_dotenv
from streamlit_lottie import st_lottie
import requests
from openai import OpenAI
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# ============================================
# 🔐 Load API Key
# ============================================
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("API Key not found in .env file")
    st.stop()

client = OpenAI(api_key=api_key)

# ============================================
# 🎨 Page Config
# ============================================
st.set_page_config(
    page_title="RAG QA Chatbot",
    page_icon="🤖",
    layout="wide"
)

# ============================================
# 🎨 Custom CSS
# ============================================
st.markdown("""
<style>
.chat-title { font-size: 36px; font-weight: bold; color: #4B4BFF; }
.sidebar-title { font-size: 20px; font-weight: bold; color: #FF5733; }

.user-msg { 
    background-color: #E1F5FE; 
    color: #000000;          
    padding: 10px; 
    border-radius: 10px; 
    margin-bottom: 5px; 
}

.assistant-msg { 
    background-color: #FFF9C4; 
    color: #000000;          
    padding: 10px; 
    border-radius: 10px; 
    margin-bottom: 5px; 
}

.typing { font-style: italic; color: gray; }
</style>
""", unsafe_allow_html=True)

# ============================================
# 🤖 Lottie Animation
# ============================================
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie_robot = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_kyu7xb1v.json")

# ============================================
# 🧠 Header
# ============================================
col1, col2 = st.columns([1, 3])
with col1: st_lottie(lottie_robot, height=200)
with col2:
    st.markdown('<p class="chat-title">RAG AI Assistant</p>', unsafe_allow_html=True)
    st.markdown("Ask questions based on your documents and get accurate answers!")

# ============================================
# 💬 Chat Memory
# ============================================
if "messages" not in st.session_state: 
    st.session_state.messages = []

for msg in st.session_state.messages:
    role_class = "user-msg" if msg["role"] == "user" else "assistant-msg"
    with st.chat_message(msg["role"]):
        st.markdown(f'<div class="{role_class}">{msg["content"]}</div>', unsafe_allow_html=True)

# ============================================
# 📚 Load or create vector store (RAG)
# ============================================
if "vectorstore" not in st.session_state:
    # Example: Load PDF documents
    pdf_loader = PyPDFLoader("rag.pdf")  # replace with your file
    documents = pdf_loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    st.session_state.vectorstore = vectorstore
else:
    vectorstore = st.session_state.vectorstore

# ============================================
# 💬 Chat Input
# ============================================
prompt = st.chat_input("Ask your question...")

if prompt:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f'<div class="user-msg">{prompt}</div>', unsafe_allow_html=True)

    # 1️⃣ Retrieve relevant documents
    docs = vectorstore.similarity_search(prompt, k=3)
    context = "\n\n".join([doc.page_content for doc in docs])

    # 2️⃣ Prepare RAG prompt for GPT
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Use the provided context to answer questions clearly."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
    ]

    # 3️⃣ Generate answer using GPT
    stream = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages,
        stream=True
    )

    # 4️⃣ Stream response in chat
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(f'<div class="assistant-msg">{full_response}▌</div>', unsafe_allow_html=True)
        message_placeholder.markdown(f'<div class="assistant-msg">{full_response}</div>', unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": full_response})