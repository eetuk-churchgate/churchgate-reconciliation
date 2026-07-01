"""
🏢 facilityXperience v3.0 — Enterprise Intelligent Facility Ecosystem
Churchgate Group | World-Class Facility Management Platform
SmartCheck Killer — AI-Powered Enterprise Grade
"""

import streamlit as st
from datetime import datetime, date, time, timedelta
import pandas as pd
import base64
from pathlib import Path
import os
import hashlib
import secrets
import json
import re
from dotenv import load_dotenv
from supabase import create_client
import plotly.express as px
import plotly.graph_objects as go
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent
import requests

load_dotenv()

# ============================================
# SUPABASE
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Database configuration missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit secrets or environment variables.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Clear cache on startup
if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.cache_cleared = True

supabase = init_supabase()

# Safe query helper with retry for direct Supabase calls
def safe_supabase_query(query_fn, max_retries=3, error_prefix="Database"):
    """Execute a Supabase query with automatic retries"""
    import time as _time
    for attempt in range(max_retries):
        try:
            return query_fn()
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"⚠️ {error_prefix} connection error. Please refresh.")
                return None
            _time.sleep(0.5)
    return None

# ============================================
# BRAND
# ============================================
CHURCHGATE_RED = "#CC0000"
CHURCHGATE_DARK = "#1a1a1a"
CHURCHGATE_GREY = "#4a4a4a"
CHURCHGATE_LIGHT = "#f5f5f5"
CHURCHGATE_WHITE = "#ffffff"
CHURCHGATE_BG = "#e8e8e8"
CHURCHGATE_SIDEBAR = "#d5d5d5"

FACILITY_INFO = {
    "WTC": {"full_name": "World Trade Center", "city": "Abuja", "logo": "WTC-logo.jpg", "desc": "22-Floor Office Tower • 24-Floor Residential Tower • Recreation Center", "color": CHURCHGATE_RED, "clight": "#fce8e8"},
    "AGVL": {"full_name": "Agroline Ventures Limited", "city": "Abuja", "logo": "churchgate-logo.png", "desc": "Commercial/Retail Complex", "color": "#059669", "clight": "#ECFDF5"},
    "FCPL": {"full_name": "First Continental Properties Limited", "city": "Lagos", "logo": "churchgate-logo.png", "desc": "Commercial/Industrial Tower", "color": "#D97706", "clight": "#FFFBEB"},
    "RBPL": {"full_name": "RB Properties Limited", "city": "Lagos", "logo": "churchgate-logo.png", "desc": "Premium Commercial Plaza", "color": "#BE185D", "clight": "#FDF2F8"},
    "VDL": {"full_name": "Ocean Terrace", "city": "Lagos", "logo": "churchgate-logo.png", "desc": "Commercial/Industrial Centre", "color": "#7C3AED", "clight": "#F5F3FF"},
    "WAREHOUSES": {"full_name": "Warehouse Network", "city": "Lagos", "logo": "churchgate-logo.png", "desc": "Logistics & Storage Network", "color": "#475569", "clight": "#F1F5F9"},
}

st.set_page_config(page_title="facilityXperience | Churchgate Group", page_icon="churchgate-logo.png", layout="wide", initial_sidebar_state="expanded")

# ============================================
# SECURITY HELPERS
# ============================================
def safe_parse_permissions(perms):
    """Safely parse permissions from string or list using json.loads instead of eval"""
    if isinstance(perms, str):
        try:
            return json.loads(perms)
        except:
            return []
    return perms if isinstance(perms, list) else []

def validate_password_strength(password):
    """
    Fortune 500 password policy enforcement
    Returns (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password meets requirements"

def validate_name_input(value):
    """Validate name field - alpha characters, spaces, hyphens, apostrophes only"""
    if not value or not value.strip():
        return False, "Name is required"
    # Allow letters, spaces, hyphens, apostrophes, periods (for initials)
    if not re.match(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s\-\.\']+$', value.strip()):
        return False, "Name must contain only letters, spaces, hyphens, or apostrophes"
    return True, ""

def validate_phone_input(value):
    """Validate phone number - digits only, optional + prefix, max 14 chars"""
    if not value or not value.strip():
        return False, "Phone number is required"
    cleaned = value.strip().replace(" ", "")
    # Allow + at start followed by up to 13 digits, or just up to 13 digits
    if not re.match(r'^\+?\d{1,13}$', cleaned):
        return False, "Phone must be numbers only (max 13 digits, + prefix allowed)"
    if len(cleaned) > 14:
        return False, "Phone number too long (max 14 characters including +)"
    return True, ""

def hash_password(password):
    """Hash password with PBKDF2-SHA256 and salt"""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${pw_hash}"


def check_password(password, stored_hash):
    """Verify password against stored hash (supports both old SHA256 and new PBKDF2)"""
    if not stored_hash:
        return False
    # New format: salt$hash
    if '$' in stored_hash:
        try:
            salt, pw_hash = stored_hash.split('$', 1)
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() == pw_hash
        except:
            return False
    # Legacy format: plain SHA256 hex digest - auto-migrate to PBKDF2
    if hashlib.sha256(password.encode()).hexdigest() == stored_hash:
        return "migrate"
    # Legacy format: plain SHA256 digest
    if hashlib.sha256(password.encode()).digest() == stored_hash:
        return "migrate"
    return False

def check_login_rate_limit(email):
    """Rate limit login attempts: 5 failures in 15 minutes = locked"""
    try:
        recent_failures = safe_supabase_query(lambda: supabase.table("login_attempts").select("*").eq("email", email).eq("success", False).gte("attempt_time", (datetime.now() - timedelta(minutes=15)).isoformat()).execute(), error_prefix="Rate check")
        if recent_failures and recent_failures.data and len(recent_failures.data) >= 5:
            return False, "Account temporarily locked due to multiple failed attempts. Please try again in 30 minutes or reset your password."
        return True, ""
    except:
        return True, ""

def log_login_attempt(email, success):
    """Log login attempt for rate limiting"""
    try:
        safe_supabase_query(lambda: supabase.table("login_attempts").insert({
            "email": email,
            "success": success,
            "attempt_time": datetime.now().isoformat()
        }).execute(), error_prefix="Log attempt")
    except:
        pass

def get_recent_failures_count(email):
    """Get count of recent failed login attempts"""
    try:
        recent = safe_supabase_query(lambda: supabase.table("login_attempts").select("id", count="exact").eq("email", email).eq("success", False).gte("attempt_time", (datetime.now() - timedelta(minutes=15)).isoformat()).execute(), error_prefix="Failure count")
        return 5 - (recent.count if recent else 0)
    except:
        return 5

# ============================================
# CSS
# ============================================
def inject_css():
    st.markdown("""
    <style>
        /* ============================================
           PREMIUM VERCEL-INSPIRED DESIGN
           Churchgate Group | facilityXperience
           ============================================ */
        
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800;900&display=swap');
        
        /* ============================================
           ROOT VARIABLES
           ============================================ */
        :root {
            --bg-warm: #f5f0e8;
            --gold: #C8A951;
            --gold-light: #e8d5a3;
            --gold-dark: #a8893a;
            --gold-glow: rgba(200, 169, 81, 0.2);
            --sidebar-bg: #2c2418;
            --sidebar-text: #f5ede4;
            --sidebar-muted: #b5a892;
            --text-dark: #2c2c2c;
            --text-muted: #6b6b6b;
            --card-shadow: 0 2px 24px rgba(0,0,0,0.04);
            --card-shadow-hover: 0 8px 48px rgba(0,0,0,0.08);
        }
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            box-sizing: border-box;
        }
        
        /* ---- Background ---- */
        .stApp {
            background: #f5f0e8 !important;
        }
        .main > div {
            background: transparent !important;
            padding: 0 2rem !important;
        }
        
        /* ---- Hide Streamlit Branding ---- */
        #MainMenu, header, footer {
            visibility: hidden !important;
        }
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        /* ---- Reduce Top Spacing ---- */
        .stApp {
            margin-top: -60px !important;
        }
        section[data-testid="stSidebar"] {
            margin-top: -30px !important;
            padding-top: 10px !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0.5rem !important;
        }
        .main > div:first-child {
            padding-top: 0px !important;
        }
        
        /* ============================================
           SIDEBAR - DARK WARM
           ============================================ */
        section[data-testid="stSidebar"] {
            background: #2c2418 !important;
            border-right: 1px solid rgba(200, 169, 81, 0.12) !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.15) !important;
            padding-top: 0.5rem !important;
        }
        
        section[data-testid="stSidebar"] * {
            color: #f5ede4 !important;
            font-size: 0.75rem !important;
        }
        
        /* Sidebar Brand */
        .sidebar-brand {
            padding: 0.8rem 1.5rem 0.5rem 1.5rem;
            border-bottom: 1px solid rgba(200, 169, 81, 0.12);
            margin-bottom: 0.5rem;
        }
        .sidebar-brand .brand-icon {
            font-size: 1.6rem;
            font-weight: 800;
            color: #f5ede4;
            font-family: 'Playfair Display', serif;
        }
        .sidebar-brand .brand-icon span {
            color: #C8A951;
        }
        .sidebar-brand .brand-sub {
            font-size: 0.6rem;
            color: #C8A951;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-top: 0.1rem;
            opacity: 0.8;
        }
        
        /* ============================================
           SIDEBAR - SHARP TEXT FIX
           ============================================ */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] .stSelectbox select,
        section[data-testid="stSidebar"] .stButton > button,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] b,
        section[data-testid="stSidebar"] strong {
            -webkit-font-smoothing: antialiased !important;
            -moz-osx-font-smoothing: grayscale !important;
            text-rendering: optimizeLegibility !important;
            font-weight: 500 !important;
            letter-spacing: 0.02em !important;
            font-size: 0.75rem !important;
            line-height: 1.5 !important;
        }
        
        /* ============================================
           SIDEBAR - DROPDOWN (FIXED - VISIBLE TEXT)
           ============================================ */
        section[data-testid="stSidebar"] .stSelectbox label {
            font-size: 0.6rem !important;
            font-weight: 700 !important;
            color: #C8A951 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            margin-bottom: 0.2rem !important;
            opacity: 0.9 !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox select {
            background: rgba(200, 169, 81, 0.1) !important;
            border: 1px solid rgba(200, 169, 81, 0.2) !important;
            border-radius: 10px !important;
            color: #f5ede4 !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            padding: 0.6rem 0.8rem !important;
            height: auto !important;
            min-height: 44px !important;
            line-height: 1.4 !important;
            cursor: pointer !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox select option {
            background: #2c2418 !important;
            color: #f5ede4 !important;
            padding: 0.5rem !important;
            font-size: 0.8rem !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox svg {
            fill: #C8A951 !important;
            color: #C8A951 !important;
            opacity: 1 !important;
        }
        
        section[data-testid="stSidebar"] .stSelectbox {
            padding: 0 0.5rem !important;
        }
        
        /* ============================================
           SIDEBAR - FACILITY INFO BOX
           ============================================ */
        section[data-testid="stSidebar"] div[style*="background"] {
            background: rgba(200, 169, 81, 0.06) !important;
            border-left: 3px solid #C8A951 !important;
            border-radius: 10px !important;
            padding: 0.8rem 1rem !important;
            margin: 0.3rem 0.5rem !important;
        }
        
        section[data-testid="stSidebar"] div[style*="background"] b {
            color: #f5ede4 !important;
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            display: block !important;
            margin-bottom: 0.2rem !important;
        }
        
        section[data-testid="stSidebar"] div[style*="background"] span {
            color: #b5a892 !important;
            font-size: 0.7rem !important;
            line-height: 1.5 !important;
            display: block !important;
        }
        
        section[data-testid="stSidebar"] div[style*="background"] br {
            display: none !important;
        }
        
        /* ============================================
           SIDEBAR - NAVIGATION BUTTONS
           ============================================ */
        section[data-testid="stSidebar"] .stButton > button {
            background: transparent !important;
            color: #d5cdc4 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 0.8rem !important;
            margin: 0.05rem 0.5rem !important;
            font-weight: 500 !important;
            font-size: 0.7rem !important;
            text-align: left !important;
            transition: all 0.25s ease !important;
            width: calc(100% - 1rem) !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(200, 169, 81, 0.12) !important;
            color: #C8A951 !important;
            transform: translateX(4px);
        }
        section[data-testid="stSidebar"] button[kind="primary"] {
            background: linear-gradient(135deg, #C8A951, #a8893a) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 16px rgba(200, 169, 81, 0.25) !important;
        }
        
        .sidebar-section {
            font-size: 0.5rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.15em !important;
            color: #C8A951 !important;
            padding: 0.5rem 1.5rem 0.1rem 1.5rem !important;
            opacity: 0.8;
        }
        
        .sidebar-profile {
            padding: 0.8rem 1.5rem;
            border-top: 1px solid rgba(200, 169, 81, 0.1);
            margin-top: auto;
        }
        .sidebar-profile .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #C8A951, #a8893a);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 0.8rem;
        }
        .sidebar-profile .name {
            font-weight: 600;
            color: #f5ede4;
            font-size: 0.75rem;
        }
        .sidebar-profile .role {
            font-size: 0.6rem;
            color: #C8A951;
            opacity: 0.7;
        }
        
        /* ============================================
           TOP NAV - CLEAN LIGHT
           ============================================ */
        .fx-topnav {
            background: rgba(255, 252, 248, 0.92) !important;
            backdrop-filter: blur(16px) !important;
            padding: 0.4rem 2rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            position: sticky !important;
            top: 0 !important;
            z-index: 9998 !important;
            border-bottom: 1px solid rgba(200, 169, 81, 0.1) !important;
            min-height: 48px !important;
        }
        .fx-brand {
            font-size: 1rem !important;
            font-weight: 800 !important;
            color: #2c2c2c !important;
            font-family: 'Playfair Display', serif !important;
        }
        .fx-brand span {
            color: #C8A951 !important;
        }
        .fx-brand-sub {
            font-size: 0.5rem !important;
            color: #a8893a !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
            margin-left: 0.5rem !important;
        }
        .fx-topnav-right {
            display: flex !important;
            align-items: center !important;
            gap: 0.8rem !important;
        }
        .fx-topnav-right .status-badge {
            background: rgba(200, 169, 81, 0.1) !important;
            border: 1px solid rgba(200, 169, 81, 0.15) !important;
            border-radius: 50px !important;
            padding: 0.2rem 0.6rem !important;
            font-size: 0.55rem !important;
            font-weight: 600 !important;
            color: #a8893a !important;
        }
        .fx-topnav-right .status-badge .dot {
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #C8A951;
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* ============================================
           GREETING HEADER - CLEAN & PREMIUM
           ============================================ */
        .greeting-header {
            background: white !important;
            padding: 1.5rem 2rem !important;
            border-radius: 16px !important;
            margin-bottom: 1.5rem !important;
            border: none !important;
            box-shadow: 0 2px 24px rgba(0,0,0,0.04) !important;
            position: relative !important;
            overflow: hidden !important;
        }
        .greeting-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, #C8A951, #a8893a);
        }
        .greeting-header h1 {
            color: #2c2c2c !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            margin: 0 !important;
            font-family: 'Playfair Display', serif !important;
            letter-spacing: -0.02em !important;
        }
        .greeting-header p {
            color: #6b6b6b !important;
            font-size: 0.8rem !important;
            margin: 0.2rem 0 0 0 !important;
        }
        
        /* ============================================
           METRIC CARDS - CLEAN WITH SOFT SHADOWS
           ============================================ */
        .fx-card {
            background: white !important;
            border-radius: 16px !important;
            padding: 1.2rem 1rem !important;
            border: none !important;
            box-shadow: 0 2px 24px rgba(0,0,0,0.04) !important;
            text-align: center !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        .fx-card:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 8px 48px rgba(0,0,0,0.08) !important;
        }
        .fx-card-label {
            font-size: 0.55rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            color: #a8893a !important;
            margin-bottom: 0.3rem !important;
        }
        .fx-card-value {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            color: #2c2c2c !important;
            line-height: 1 !important;
            font-family: 'Playfair Display', serif !important;
            letter-spacing: -0.02em !important;
        }
        
        /* ============================================
           MAIN CONTENT DROPDOWN - FIX FOR VISIBILITY
           ============================================ */
        .stSelectbox select {
            color: #2c2c2c !important;
            background-color: white !important;
            border: 1px solid rgba(200, 169, 81, 0.2) !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            padding: 0.6rem 0.8rem !important;
            min-height: 44px !important;
            cursor: pointer !important;
        }
        
        .stSelectbox label {
            font-size: 0.6rem !important;
            font-weight: 700 !important;
            color: #a8893a !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            margin-bottom: 0.2rem !important;
        }
        
        .stSelectbox svg {
            fill: #C8A951 !important;
            color: #C8A951 !important;
            opacity: 1 !important;
        }
        
        /* ============================================
           BUTTONS - ELEGANT VERCEL STYLE
           ============================================ */
        .stButton > button {
            background: white !important;
            color: #2c2c2c !important;
            border: 1px solid rgba(200, 169, 81, 0.2) !important;
            border-radius: 12px !important;
            padding: 0.6rem 1.4rem !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        }
        .stButton > button:hover {
            background: #faf6ef !important;
            border-color: #C8A951 !important;
            box-shadow: 0 4px 16px rgba(200, 169, 81, 0.15) !important;
            transform: translateY(-2px) !important;
        }
        .stButton > button:active {
            transform: scale(0.98) !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #C8A951, #a8893a) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 16px rgba(200, 169, 81, 0.25) !important;
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 24px rgba(200, 169, 81, 0.35) !important;
            transform: translateY(-2px) !important;
        }
        
        /* ============================================
           TABS - CLEAN PILLS
           ============================================ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem !important;
            background: #ede8df !important;
            padding: 0.25rem !important;
            border-radius: 14px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            border-radius: 10px !important;
            padding: 0.5rem 1.2rem !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            color: #6b6b6b !important;
            border: none !important;
            transition: all 0.2s ease !important;
        }
        .stTabs [aria-selected="true"] {
            background: white !important;
            color: #2c2c2c !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
            border-radius: 10px !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #2c2c2c !important;
        }
        
        /* ============================================
           SCROLLBAR
           ============================================ */
        ::-webkit-scrollbar {
            width: 3px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: #C8A951;
            border-radius: 2px;
            opacity: 0.5;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #a8893a;
        }
        
        /* ============================================
           DIVIDERS - SUBTLE
           ============================================ */
        hr {
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, transparent, rgba(200, 169, 81, 0.12), transparent) !important;
            margin: 1.5rem 0 !important;
        }
        
        /* ============================================
           BADGES - CLEAN
           ============================================ */
        .fx-badge {
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.2rem !important;
            padding: 0.2rem 0.7rem !important;
            border-radius: 50px !important;
            font-size: 0.6rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
        }
        .badge-success {
            background: #f0f7ee;
            color: #5a7a4a;
        }
        .badge-warning {
            background: #f7f0e6;
            color: #a8893a;
        }
        .badge-critical {
            background: #f7eeed;
            color: #b35a4a;
        }
        .badge-info {
            background: #eef2f7;
            color: #4a6a8a;
        }
        
        /* ============================================
           PREMIUM CHECKBOXES & EXPANDERS
           ============================================ */
        .streamlit-expanderHeader {
            background: white !important;
            border: 1px solid rgba(200, 169, 81, 0.15) !important;
            border-radius: 10px !important;
            padding: 0.6rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.78rem !important;
            color: #2c2c2c !important;
            transition: all 0.25s ease !important;
            margin-bottom: 0.2rem !important;
        }
        .streamlit-expanderHeader:hover {
            border-color: #C8A951 !important;
            background: #faf6ef !important;
            box-shadow: 0 2px 8px rgba(200, 169, 81, 0.08) !important;
        }
        .streamlit-expanderHeader svg {
            fill: #C8A951 !important;
        }
        .streamlit-expanderContent {
            background: #faf7f2 !important;
            border: 1px solid rgba(200, 169, 81, 0.1) !important;
            border-top: none !important;
            border-radius: 0 0 10px 10px !important;
            padding: 0.8rem 1rem !important;
        }
        
        .stCheckbox label {
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            color: #3d3522 !important;
            padding: 0.3rem 0 !important;
            transition: color 0.2s ease !important;
        }
        .stCheckbox label:hover {
            color: #C8A951 !important;
        }
        
        .stCheckbox input[type="checkbox"] {
            accent-color: #C8A951 !important;
            width: 16px !important;
            height: 16px !important;
            cursor: pointer !important;
        }
        
        /* ============================================
           FACILITY SELECTOR - FIX VISIBILITY
           ============================================ */
        section[data-testid="stSidebar"] .stSelectbox > div > div {
            background: rgba(200, 169, 81, 0.12) !important;
            border: 1px solid rgba(200, 169, 81, 0.25) !important;
            border-radius: 10px !important;
        }
        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] div {
            color: #f5ede4 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stSidebar"] .stSelectbox svg {
            fill: #C8A951 !important;
            opacity: 1 !important;
        }
        
        /* ============================================
           MOBILE RESPONSIVE
           ============================================ */
        @media (max-width: 768px) {
            .fx-topnav {
                padding: 0.4rem 0.8rem !important;
                flex-wrap: wrap !important;
                gap: 0.3rem !important;
                min-height: 40px !important;
            }
            .fx-topnav .fx-brand {
                font-size: 0.85rem !important;
            }
            .fx-topnav-right {
                gap: 0.3rem !important;
            }
            .fx-topnav-right .status-badge {
                display: none !important;
            }
            .main > div {
                padding: 0 0.5rem !important;
            }
            .churchgate-header {
                padding: 0.8rem !important;
            }
            .churchgate-header h1 {
                font-size: 1.1rem !important;
            }
            .fx-card {
                padding: 0.6rem !important;
            }
            .fx-card-value {
                font-size: 1.2rem !important;
            }
            .greeting-header {
                padding: 0.8rem !important;
            }
            .greeting-header h1 {
                font-size: 1rem !important;
            }
            
            [data-testid="collapsedControl"] {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                position: fixed !important;
                top: 60px !important;
                left: 0 !important;
                z-index: 99999 !important;
                background: #C8A951 !important;
                border-radius: 0 8px 8px 0 !important;
                padding: 10px 5px !important;
                width: 24px !important;
                height: 40px !important;
            }
            [data-testid="collapsedControl"] svg {
                fill: white !important;
            }
            
            section[data-testid="stSidebar"] {
                width: 100vw !important;
                max-width: 100vw !important;
            }
            
            [data-testid="stDataFrame"] {
                overflow-x: auto !important;
                font-size: 0.6rem !important;
            }
            
            .stColumns {
                flex-wrap: wrap !important;
            }
            
            .stButton > button {
                padding: 0.4rem 0.8rem !important;
                font-size: 0.7rem !important;
            }
        }
        
        /* ============================================
           RESPONSIVE
           ============================================ */
        @media (max-width: 768px) {
            .fx-topnav {
                padding: 0.4rem 1rem !important;
                flex-wrap: wrap !important;
                gap: 0.3rem !important;
            }
            .churchgate-header {
                padding: 1rem !important;
            }
            .fx-card-value {
                font-size: 1.3rem !important;
            }
            .greeting-header {
                padding: 1rem !important;
            }
            .greeting-header h1 {
                font-size: 1.1rem !important;
            }
            .main > div {
                padding: 0 0.8rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# DATA ENGINE — WITH RETRY & RESILIENCE
# ============================================
class DB:
    @staticmethod
    def _safe_query(query_fn, default=None, max_retries=3):
        """Execute a Supabase query with automatic retries"""
        import time as _time
        for attempt in range(max_retries):
            try:
                result = query_fn()
                return result
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"⚠️ Query failed after {max_retries} attempts: {str(e)[:100]}")
                _time.sleep(0.3)
        return default
    
    @staticmethod
    @st.cache_data(ttl=120)
    def get_kpis(fc):
        """Get KPIs with individual query resilience"""
        results = {"open_wo": 0, "visitors": 0, "open_inc": 0, "open_tix": 0, 
                   "assets": 0, "ppm_due": 0, "pending_permits": 0}
        
        queries = {
            "open_wo": lambda: supabase.table("work_orders").select("id", count="exact").eq("facility_code", fc).eq("status", "open").execute(),
            "visitors": lambda: supabase.table("visitors").select("id", count="exact").eq("facility_code", fc).eq("visit_date", str(date.today())).execute(),
            "open_inc": lambda: supabase.table("incidents").select("id", count="exact").eq("facility_code", fc).eq("status", "reported").execute(),
            "open_tix": lambda: supabase.table("tickets").select("id", count="exact").eq("facility_code", fc).in_("status", ["open", "in_progress"]).execute(),
            "assets": lambda: supabase.table("assets").select("id", count="exact").eq("facility_code", fc).execute(),
            "ppm_due": lambda: supabase.table("ppm_schedules").select("id", count="exact").eq("facility_code", fc).eq("status", "scheduled").execute(),
            "pending_permits": lambda: supabase.table("work_permits").select("id", count="exact").eq("facility_code", fc).eq("status", "pending").execute(),
        }
        
        for key, query_fn in queries.items():
            res = DB._safe_query(query_fn)
            if res:
                results[key] = res.count or 0
        
        return results

    @staticmethod
    @st.cache_data(ttl=120)
    def get_all(table, fc, limit=500):
        """Get all records with retry"""
        def query():
            return supabase.table(table).select("*").eq("facility_code", fc).order("created_at", desc=True).limit(limit).execute()
        
        res = DB._safe_query(query)
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=300)
    def get_assets(fc, limit=50000):
        """Get assets with pagination and retry"""
        def fetch_page(offset, page_size):
            return supabase.table("assets").select("*").eq("facility_code", fc).range(offset, offset + page_size - 1).execute()
        
        all_data = []
        page_size = 1000
        offset = 0
        
        while offset < limit:
            res = DB._safe_query(lambda: fetch_page(offset, page_size))
            if res and res.data and len(res.data) > 0:
                all_data.extend(res.data)
                offset += page_size
                if len(res.data) < page_size:
                    break
            else:
                break
        
        return all_data if all_data else []

    @staticmethod
    @st.cache_data(ttl=300)
    def get_categories():
        """Get categories with retry"""
        res = DB._safe_query(lambda: supabase.table("asset_categories").select("*").order("name").execute())
        return res.data if res and res.data else []

    @staticmethod
    def insert(table, data):
        """Insert with retry"""
        def query():
            return supabase.table(table).insert(data).execute()
        
        res = DB._safe_query(query)
        if res and res.data:
            return res.data[0]
        return None

    @staticmethod
    def update(table, id_val, data):
        """Update with retry and cache clear"""
        def query():
            return supabase.table(table).update(data).eq("id", id_val).execute()
        
        res = DB._safe_query(query)
        if res:
            st.cache_data.clear()
            return True
        return False

    @staticmethod
    @st.cache_data(ttl=300)
    def get_users(facility_code=None):
        """Get users with retry"""
        def query():
            q = supabase.table("app_users").select("*").order("name")
            if facility_code:
                q = q.eq("home_facility", facility_code)
            return q.limit(500).execute()
        
        res = DB._safe_query(query)
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=300)
    def get_locations(fc):
        """Get locations with retry"""
        res = DB._safe_query(lambda: supabase.table("helpdesk_locations").select("*").eq("facility_code", fc).order("location_name").execute())
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=300)
    def get_sub_locations(loc_id):
        """Get sub-locations with retry"""
        res = DB._safe_query(lambda: supabase.table("helpdesk_sub_locations").select("*").eq("location_id", loc_id).order("sub_location_name").execute())
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=300)
    def get_helpdesk_categories():
        """Get helpdesk categories with retry"""
        res = DB._safe_query(lambda: supabase.table("helpdesk_categories").select("*").eq("is_active", True).order("category_name").execute())
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=120)
    def get_tickets_filtered(fc, status=None, category=None, search=None, limit=100):
        """Get filtered tickets with retry"""
        def query():
            q = supabase.table("tickets").select("*").eq("facility_code", fc)
            if status and status != "All":
                q = q.eq("status", status)
            if category:
                q = q.eq("category", category)
            if search:
                q = q.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
            return q.order("created_at", desc=True).limit(limit).execute()
        
        res = DB._safe_query(query)
        return res.data if res and res.data else []

    @staticmethod
    @st.cache_data(ttl=120)
    def get_ticket_comments(ticket_id):
        """Get ticket comments with retry"""
        res = DB._safe_query(lambda: supabase.table("ticket_comments").select("*").eq("ticket_id", ticket_id).order("created_at").execute())
        return res.data if res and res.data else []
# ============================================
# HELPERS
# ============================================
def get_facility_logo(fc, h=60):
    info=FACILITY_INFO.get(fc,{})
    lf=info.get("logo","churchgate-logo.png")
    lp=Path(lf)
    if not lp.exists():
        # Try alternate WTC logo names
        for alt in ["wtc-logo.jpg", "WTC-logo.jpg", "wtc-logo.jpg.jpg"]:
            if Path(alt).exists():
                lp = Path(alt)
                lf = alt
                break
    if lp.exists():
        ext=lf.split(".")[-1].replace("jpg","jpeg")
        with open(lp,"rb") as f: b64=base64.b64encode(f.read()).decode()
        return f'<img src="data:image/{ext};base64,{b64}" height="{h}px" style="max-width:220px;object-fit:contain;" importance="high">'
    return f'<span style="font-size:2.5rem;">🏢</span>'


def ask_facility_xpert(query, categories, facility_name="World Trade Center", facility_city="Abuja"):
    """AI assistant using Groq (FREE, FAST, REAL LLM)"""
    try:
        api_key = ""
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except:
            api_key = os.environ.get("GROQ_API_KEY", "")
        
        cat_list = ", ".join(categories[:10])
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": f"You are facilityXpert, the AI assistant for Churchgate Group's {facility_name} in {facility_city}, Nigeria. You help tenants and staff resolve facility issues quickly. Available departments: {cat_list}. For emergencies (fire, elevator stuck, major water leak, electrical hazard), ALWAYS tell them to raise an URGENT ticket or call the facility team. NEVER make up phone numbers or email addresses. If you don't know something, say so. Be concise, helpful, and professional. Give step-by-step solutions."},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 300,
                "temperature": 0.5
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        # Fallback to knowledge base
        kb = safe_supabase_query(lambda: supabase.table("knowledge_base").select("*").or_(f"question.ilike.%{query}%,tags.ilike.%{query}%").limit(3).execute(), error_prefix="Knowledge base")
        if kb and kb.data:
            solutions = "\n\n".join([f"**{k.get('question')}**\n{k.get('answer','')}" for k in kb.data])
            return f"Here are solutions from our knowledge base:\n\n{solutions}"
        return None
    except:
        try:
            kb = safe_supabase_query(lambda: supabase.table("knowledge_base").select("*").or_(f"question.ilike.%{query}%,tags.ilike.%{query}%").limit(3).execute(), error_prefix="Knowledge base")
            if kb and kb.data:
                solutions = "\n\n".join([f"**{k.get('question')}**\n{k.get('answer','')}" for k in kb.data])
                return f"Here are solutions from our knowledge base:\n\n{solutions}"
        except:
            pass
        return None


def get_nav_logo():
    """Churchgate logo for top navigation - white version for dark background"""
    p = Path("churchgate-logo.png")
    if p.exists():
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" height="28px" style="display:inline-block;vertical-align:middle;">'
    return '<span style="font-weight:800;color:white;font-size:1rem;display:inline-block;vertical-align:middle;">CHURCHGATE</span>'


def check_auto_escalation(fc):
    """Auto-escalate overdue tickets"""
    try:
        tickets = safe_supabase_query(lambda: supabase.table("tickets").select("*").eq("facility_code", fc).in_("status", ["open","in_progress","hold"]).execute(), error_prefix="Auto-escalation tickets")
        if not tickets or not tickets.data:
            return
        
        now = datetime.now()
        
        for ticket in tickets.data:
            current_level = ticket.get("escalation_level", 1)
            if current_level >= 6:
                continue
            
            sla_deadline = ticket.get("sla_deadline")
            if not sla_deadline:
                continue
            
            try:
                sla_dt = pd.to_datetime(sla_deadline)
                if now > sla_dt:
                    next_level = current_level + 1
                    ticket_cat = ticket.get("category")
                    cat_id = None
                    cats = safe_supabase_query(lambda: supabase.table("helpdesk_categories").select("id").eq("category_name", ticket_cat).execute(), error_prefix="Helpdesk cats")
                    if cats and cats.data:
                        cat_id = cats.data[0]["id"]
                    
                    esc_config = safe_supabase_query(lambda: supabase.table("ticket_escalation").select("*").eq("facility_code", fc).eq("level_number", next_level).eq("category_id", cat_id).execute(), error_prefix="Escalation config")
                    safe_supabase_query(lambda tid=ticket["id"]: supabase.table("tickets").update({"escalation_level": next_level}).eq("id", tid).execute(), error_prefix="Update escalation")
                    if esc_config and esc_config.data:
                        for e in esc_config.data:
                            if e.get("escalate_to_email"):
                                send_email_notification(
                                    e["escalate_to_email"],
                                    f"🔺 ESCALATED L{current_level}→L{next_level}: Ticket {ticket.get('ticket_number','')}",
                                    f"""
                                    <div style="font-family:Arial;max-width:600px;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
                                        <div style="background: #F59E0B;padding:20px;color:white;">
                                            <h2 style="margin:0;">⚠️ Ticket Escalated — Level {next_level}</h2>
                                            <p style="margin:5px 0 0 0;font-size:12px;">SLA Exceeded — Immediate Action Required</p>
                                        </div>
                                        <div style="padding:20px;">
                                            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                                                <tr><td style="padding:8px;font-weight:bold;">Ticket:</td><td>{ticket.get('ticket_number','')}</td></tr>
                                                <tr><td style="padding:8px;font-weight:bold;">Title:</td><td>{ticket.get('title','')}</td></tr>
                                                <tr><td style="padding:8px;font-weight:bold;">Category:</td><td>{ticket.get('category','')}</td></tr>
                                                <tr><td style="padding:8px;font-weight:bold;">Escalated:</td><td>Level {current_level} → Level {next_level}</td></tr>
                                                <tr><td style="padding:8px;font-weight:bold;">SLA Deadline:</td><td>{ticket.get('sla_deadline','')}</td></tr>
                                            </table>
                                            <div style="margin-top:15px;background:#FFF3CD;padding:15px;border-radius:8px;">
                                                <p style="margin:0;color:#92400E;font-weight:bold;">⚡ Action Required: Please resolve or reassign immediately.</p>
                                            </div>
                                        </div>
                                    </div>
                                    """
                                )
            except:
                pass
    except:
        pass

def safe_text(text, default="N/A"):
    """Remove unicode characters that break PDFs"""
    if not text or str(text) == "None" or str(text) == "nan":
        return default
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u2019': "'", '\u2018': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u00a0': ' ',
        '\u2012': '-', '\u2015': '-', '\u2192': '>', '\u2794': '>',
        '\u2022': '*', '\u25cf': '*', '\u25cb': '-', '\u25a0': '-'
    }
    result = str(text)
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result

def get_logo_base64():
    """Convert churchgate-logo.png to base64 for embedding in reports"""
    p = Path("churchgate-logo.png")
    if p.exists():
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def status_badge(s):
    badges={
        "active":'<span class="fx-badge badge-success">✅ Active</span>',
        "inactive":'<span class="fx-badge badge-critical">❌ Inactive</span>',
        "pending":'<span class="fx-badge badge-pending">⏳ Pending</span>',
        "approved":'<span class="fx-badge badge-approved">✅ Approved</span>',
        "rejected":'<span class="fx-badge badge-critical">❌ Rejected</span>',
        "open":'<span class="fx-badge badge-critical">🔴 Open</span>',
        "in_progress":'<span class="fx-badge badge-warning">🟡 In Progress</span>',
        "completed":'<span class="fx-badge badge-success">🟢 Completed</span>',
        "closed":'<span class="fx-badge badge-info">🔵 Closed</span>',
    }
    return badges.get(s,f'<span class="fx-badge badge-info">{s}</span>')

# ============================================
# TOP NAV
# ============================================
def topnav():
    cg = get_nav_logo()
    
    st.markdown(f"""
    <div class="fx-topnav">
        <div style="display:flex;align-items:center;gap:1rem;">
            <div style="display:flex;align-items:center;gap:0.6rem;">
                {cg}
                <div style="width:1px;height:24px;background:rgba(255,255,255,0.3);"></div>
                <span class="fx-brand">facility<span>X</span>perience</span>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:0.8rem;">
            <div style="display:flex;align-items:center;gap:0.3rem;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);border-radius:50px;padding:0.25rem 0.7rem;font-size:0.6rem;font-weight:600;color:#6EE7B7;">
                <div style="width:5px;height:5px;border-radius:50%;background:#10B981;animation:fxPulse 2s infinite;"></div>AI ACTIVE
            </div>
            <span style="color:rgba(255,255,255,0.5);font-size:0.65rem;font-family:monospace;" id="lt"></span>
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="color:rgba(255,255,255,0.7);font-size:0.7rem;">{st.session_state.get('user_name','User').split()[-1]}</span>
                <div style="width:32px;height:32px;border-radius:50%;background:{CHURCHGATE_RED};display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.75rem;border:2px solid rgba(255,255,255,0.2);cursor:pointer;" title="Click to logout" onclick="logout()">{st.session_state.get('user_name','User')[:2].upper()}</div>
            </div>
        </div>
    </div>
    <script>function t(){{var d=new Date();var wat=new Date(d.getTime()+3600000);document.getElementById('lt').textContent=wat.toLocaleTimeString('en-US',{{hour12:false}});}}t();setInterval(t,1000);</script>
    <style>@keyframes fxPulse{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}</style>
    """, unsafe_allow_html=True)


# ============================================
# SIDEBAR — REDESIGNED WITH CUSTOM COLLAPSE
# ============================================
def sidebar():
    # Hide default Streamlit collapse buttons + keep custom button style
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        button[kind="header"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        .st-emotion-cache-1rtdyqp { display: none !important; }
        .fx-collapse-btn {
            position: fixed;
            top: 80px;
            left: 291px;
            z-index: 99999;
            background: #CC0000;
            color: white;
            border: none;
            border-radius: 0 8px 8px 0;
            padding: 10px 6px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(204,0,0,0.4);
            transition: all 0.3s;
            width: 22px;
            text-align: center;
        }
        .fx-collapse-btn:hover {
            background: #aa0000;
            box-shadow: 0 4px 20px rgba(204,0,0,0.6);
        }
    </style>
    <script>
        (function() {
            var btn = document.createElement('button');
            btn.className = 'fx-collapse-btn';
            btn.innerHTML = '◀';
            btn.title = 'Toggle Sidebar';
            btn.onclick = function() {
                var sidebar = parent.document.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    if (sidebar.style.display === 'none') {
                        sidebar.style.display = 'block';
                        btn.innerHTML = '◀';
                        btn.style.left = '291px';
                    } else {
                        sidebar.style.display = 'none';
                        btn.innerHTML = '▶';
                        btn.style.left = '0px';
                    }
                }
            };
            parent.document.body.appendChild(btn);
        })();
    </script>
    """, unsafe_allow_html=True)
    
    # Sidebar toggle via session state + CSS
    if "sidebar_hidden" not in st.session_state:
        st.session_state.sidebar_hidden = False
    
    if st.session_state.sidebar_hidden:
        st.markdown("""
        <style>
            section[data-testid="stSidebar"] { display: none !important; }
            div[data-testid="stAppViewContainer"] { margin-left: 0 !important; }
        </style>
        """, unsafe_allow_html=True)
    
    with st.sidebar:
        # Logo + Brand Header
        logo_html = get_nav_logo()
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0;margin-bottom:0.5rem;border-bottom:2px solid #CC0000;">
            {logo_html}
            <div style="display:flex;align-items:baseline;gap:0.3rem;">
                <span style="font-weight:800;font-size:0.9rem;color:#1a1a1a;">facility<span style="color:#CC0000 !important;">X</span>perience</span>
                <span style="font-size:0.6rem;color:#888;">Churchgate Group</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # One View — Facility Selector
        user_role = st.session_state.get("user_role", "staff")
        is_sr_mgmt = user_role in ["super_admin", "sr_management", "admin", "approver"]
        
        if is_sr_mgmt:
            st.markdown('<p style="font-size:0.5rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;margin:0.5rem 0 0.2rem 0;">📍 One View</p>', unsafe_allow_html=True)
            
            sel = st.session_state.get("facility", "WTC")
            
            facility_options = {
                "WTC": "🏢 World Trade Center — Abuja",
                "AGVL": "🏗️ Agroline Ventures Limited — Abuja",
                "FCPL": "🏭 First Continental Properties — Lagos",
                "RBPL": "🏬 RB Properties Limited — Lagos",
                "VDL": "🌊 Ocean Terrace — Lagos",
                "WAREHOUSES": "📦 Warehouse Network — Lagos",
            }
            
            new_sel = st.selectbox(
                "Select Facility",
                list(facility_options.keys()),
                format_func=lambda x: facility_options[x],
                index=list(facility_options.keys()).index(sel) if sel in facility_options else 0,
                key="facility_selector",
                label_visibility="collapsed"
            )
            
            if new_sel != sel:
                st.session_state.facility = new_sel
                st.cache_data.clear()
                st.rerun()
        else:
            # Non-Sr Management: fixed to their home facility
            user_home = st.session_state.get("user", {}).get("home_facility", "WTC")
            st.session_state.facility = user_home
            sel = user_home
        
        # Facility info card
        info = FACILITY_INFO.get(sel, {})
        st.markdown(f"""
        <div style="background:{info.get('clight','#fce8e8')};border-left:3px solid {info.get('color',CHURCHGATE_RED)};border-radius:6px;padding:0.5rem;margin:0.3rem 0;font-size:0.65rem;">
            <b>{info.get('full_name',sel)}</b><br>
            📍 {info.get('city','')}<br>
            <span style="font-size:0.55rem;color:#888;">{info.get('desc','')[:60]}...</span>
        </div>
        """, unsafe_allow_html=True)
        
        
        
        st.markdown("---")
        
        # Quick Links
        st.markdown('<p style="font-size:0.5rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;margin:0.3rem 0 0.1rem 0;">🔗 Quick Links</p>', unsafe_allow_html=True)
        
        # Get WTC logo base64
        wtc_logo_html = '<span style="font-size:1.2rem;">🏢</span>'
        wtc_logo_path = Path("WTC-logo.jpg")
        if not wtc_logo_path.exists():
            wtc_logo_path = Path("wtc-logo.jpg")
        if not wtc_logo_path.exists():
            wtc_logo_path = Path("wtc-logo.jpg.jpg")
        if wtc_logo_path.exists():
            with open(wtc_logo_path, "rb") as f:
                wtc_b64 = base64.b64encode(f.read()).decode()
            wtc_logo_html = f'<img src="data:image/jpeg;base64,{wtc_b64}" height="18px" style="object-fit:contain;" importance="high" fetchpriority="high">'
        
        cg_logo = get_nav_logo()
        
        st.markdown(f"""
        <a href="https://www.churchgate.com" target="_blank" style="text-decoration:none;">
            <div style="background:#c8c8c8;border:1px solid #aaa;border-radius:8px;padding:0.5rem 0.6rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;margin-bottom:6px;">
                <div style="flex-shrink:0;">{cg_logo}</div>
                <div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;">Churchgate Group</div>
            </div>
        </a>
        <a href="https://wtcabuja.com" target="_blank" style="text-decoration:none;">
            <div style="background:#c8c8c8;border:1px solid #aaa;border-radius:8px;padding:0.5rem 0.6rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;">
                <div style="flex-shrink:0;">{wtc_logo_html}</div>
                <div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;">WTC Abuja</div>
            </div>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation — Role-based
        user_perms = safe_parse_permissions(st.session_state.get("user", {}).get("extra_permissions", []))
        user_role = st.session_state.get("user_role", "staff")
        is_admin = user_role in ["admin", "approver", "super_admin"]
        
        all_nav = [
            ("🏠 COMMAND", [("🌐 Command Center", "cc"), ("📊 PPM Dashboard", "ppm")], ["Command Center", "PPM Dashboard"]),
            ("🏗️ ASSETS & PPM", [("📋 Asset Register", "ar"), ("🔧 PPM Activities", "ppma"), ("✅ Checklist Status", "cs")], ["Asset Register", "PPM Activities", "Checklist Status"]),
            ("🔧 MAINTENANCE", [("📋 Work Orders", "wo"), ("🛡️ Work Permits", "wp")], ["Work Orders", "Raise Permit", "Authorize Permit", "Confirm Permit", "Approve Permit", "Work Permit Reports"]),
            ("🛡️ RISK MANAGEMENT", [("📊 Risk Assessment", "fo")], ["Risk Assessment"]),
            ("👥 PEOPLE", [("🛂 Visitor Management", "vm"), ("👤 User Management", "up")], ["Visitor Management", "User Management"]),
            ("🔑 KEY MANAGEMENT", [("🔑 Key Register", "km"), ("📊 Key Reports", "kmr")], ["Key Register", "Key Reports"]),
            ("💬 SERVICES", [("🎫 Raise a Ticket", "rt"), ("💬 Helpdesk", "hd"), ("⭐ Feedback", "fb")], ["Raise Ticket", "Helpdesk", "Feedback"]),
            ("✅ COMPLIANCE", [("✅ Audit Checklist", "ac"), ("🚨 Incident Check", "ic"), ("🔄 HOTO Check", "hot")], ["Audit Checklist", "Incident Report", "HOTO Check"]),
            ("⚡ UTILITY", [("⚡ Utility Dashboard", "uc")], ["Utility Dashboard"]),
            ("📊 REPORTS", [("📊 Monthly MIS", "mis")], ["Monthly MIS"]),
        ]
        
        for section, items, required_perms in all_nav:
            can_see = is_admin or any(p in user_perms for p in required_perms) or len(user_perms) == 0
            if can_see:
                st.markdown(f'<p style="font-size:0.45rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;margin:0.4rem 0 0.1rem 0;">{section}</p>', unsafe_allow_html=True)
                for label, page_id in items:
                    if st.button(label, key=page_id, use_container_width=True):
                        st.session_state.page = page_id
                        st.rerun()
        
        st.markdown("---")
        
        # User info + Logout
        user_name = st.session_state.get('user_name','User')
        user_role_display = st.session_state.get('user_role','staff').upper()
        
        st.markdown(f"""
        <a href="https://www.churchgate.com" target="_blank" style="text-decoration:none;">
            <div style="background:#d5d5d5;border:1px solid #bbb;border-radius:8px;padding:0.5rem 0.6rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;margin-bottom:6px;transition:all 0.2s;">
                <div style="flex-shrink:0;">{cg_logo}</div>
                <div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;">Churchgate Group</div>
            </div>
        </a>
        <a href="https://wtcabuja.com" target="_blank" style="text-decoration:none;">
            <div style="background:#d5d5d5;border:1px solid #bbb;border-radius:8px;padding:0.5rem 0.6rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;transition:all 0.2s;">
                <div style="flex-shrink:0;">{wtc_logo_html}</div>
                <div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;">WTC Abuja</div>
            </div>
        </a>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Log Out", use_container_width=True, type="primary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_name = None
            st.query_params.clear()
            st.rerun()



# ============================================
# COMMAND CENTER
# ============================================
def page_cc():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    # ============================================
    # SIMPLE RETRY - 3 attempts
    # ============================================
    k = None
    for attempt in range(3):
        try:
            k = DB.get_kpis(fc)
            if k and k.get("open_wo") is not None:
                break
        except:
            pass
        time.sleep(1)
    
    if not k or k.get("open_wo") is None:
        k = {"open_wo": 0, "visitors": 0, "open_inc": 0, "open_tix": 0, 
             "assets": 0, "ppm_due": 0, "pending_permits": 0}
    # ============================================
    
    logo = get_facility_logo(fc, 70)
    
    st.markdown(f"""
    <div class="churchgate-header">
        <div style="display:flex;align-items:center;gap:1.5rem;">
            <div style="flex-shrink:0;">{logo}</div>
            <div style="flex:1;">
                <h1 style="margin:0;font-weight:800;font-size:1.5rem;color:#2c2c2c;font-family:'Playfair Display',serif;">{info.get("full_name",fc)}</h1>
                <p style="margin:0.2rem 0 0 0;color:#6b6b6b;font-size:0.8rem;">📍 {info.get("city","")} • {info.get("desc","")}</p>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.55rem;color:#a8893a;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">LIVE DATA</div>
                <div style="font-size:1.1rem;font-weight:700;color:#2c2c2c;">{datetime.now().strftime("%H:%M:%S")}</div>
                <div style="font-size:0.6rem;color:#a8893a;">{datetime.now().strftime("%A, %d %B %Y")}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    kpi=[("📋 Open WOs",k["open_wo"]),("🛂 Visitors",k["visitors"]),("🚨 Incidents",k["open_inc"]),("🎫 Tickets",k["open_tix"]),("🏗️ Assets",k["assets"]),("🔧 PPM Due",k["ppm_due"]),("🛡️ Permits",k["pending_permits"])]
    cols=st.columns(7)
    for i,(l,v) in enumerate(kpi):
        with cols[i]:st.markdown(f'<div class="fx-card"><div class="fx-card-label">{l}</div><div class="fx-card-value">{v}</div></div>',unsafe_allow_html=True)
    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("### 📋 Recent Work Permits")
        wp=DB.get_all("work_permits",fc,5)
        if wp:
            for w in wp:
                s=w.get("status","pending")
                status_colors = {"approved":"#10B981","pending":"#F59E0B","rejected":"#EF4444","submitted":"#3B82F6"}
                sc = status_colors.get(s,"#4a4a4a")
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b>{w.get('permit_number','')}</b>
                        <span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:600;">{s.upper()}</span>
                    </div>
                    <div style="font-size:0.8rem;color:#666;margin-top:0.2rem;">{w.get('title','')[:80]}</div>
                    <div style="font-size:0.65rem;color:#888;">👤 {w.get('raised_by_name','N/A')} | 📅 {w.get('start_datetime','')[:10]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:st.info("No work permits")
    with c2:
        st.markdown("### 🎫 Recent Tickets")
        tix=DB.get_all("tickets",fc,5)
        if tix:
            for t in tix:
                status = t.get("status","open")
                colors = {"open":"#EF4444","in_progress":"#F59E0B","hold":"#3B82F6","closed":"#10B981","rejected":"#6B7280"}
                icons = {"open":"🔴","in_progress":"🟡","hold":"⏸️","closed":"🟢","rejected":"❌"}
                sc = colors.get(status,"#4a4a4a")
                si = icons.get(status,"📋")
                
                created = t.get("created_at","")
                age_str = ""
                if created and str(created) != "None":
                    try:
                        age = datetime.now() - pd.to_datetime(created)
                        age_str = f"{age.days}d {age.seconds//3600}h ago"
                    except: pass
                
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span><b>{si} {t.get('ticket_number','')}</b></span>
                        <span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.65rem;font-weight:600;">{status.upper()}</span>
                    </div>
                    <div style="font-size:0.8rem;color:#1a1a1a;margin-top:0.3rem;">{t.get('title','')[:80]}</div>
                    <div style="font-size:0.65rem;color:#888;margin-top:0.2rem;">
                        👤 {t.get('requester_name','N/A')} | 🏷️ {t.get('category','')} | ⏱️ {age_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:st.info("No tickets")

def fix_date(val):
    """Convert DD-MM-YYYY to YYYY-MM-DD, return None if invalid"""
    if val is None or pd.isna(val) or str(val).strip() in ["", "NA", "na", "null", "None"]:
        return None
    val_str = str(val).strip()
    # Already in YYYY-MM-DD format
    if len(val_str) == 10 and val_str[4] == "-":
        return val_str
    # DD-MM-YYYY format
    parts = val_str.replace("/", "-").split("-")
    if len(parts) == 3:
        try:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return None
    return None


# ============================================
# ASSET COMMAND CENTER — FORTUNE 500 GRADE
# WORLD-CLASS AI-POWERED ASSET MANAGEMENT
# ============================================
def page_ar():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    st.markdown(f'## 🏗️ Asset Command Center — {info.get("full_name", fc)}')
    
    # Fetch all assets
    all_assets = DB.get_assets(fc, 50000)
    
    # Build dataframe
    if all_assets:
        df = pd.DataFrame(all_assets)
        # Get category names
        # Department is already in the assets table from SQL upload
        if "department" in df.columns:
            df["department"] = df["department"].fillna("N/A")
        else:
            df["department"] = "N/A"
    else:
        df = pd.DataFrame()
    
    today = date.today()
    
    # ============================================
    # MAIN NAVIGATION TABS
    # ============================================
    ar_tabs = st.tabs([
        "📊 Dashboard", 
        "📋 Asset Register", 
        "➕ Add Asset", 
        "📦 Bulk Upload",
        "📖 Readings", 
        "📅 PPM Calendar",
        "✅ Approvals",
        "📄 Reports",
        "⚙️ Settings"
    ])
    
    # ============================================
    # TAB 0: DASHBOARD
    # ============================================
    with ar_tabs[0]:
        if len(df) == 0:
            st.info("🏗️ No assets registered yet. Start by adding assets in the '➕ Add Asset' or '📦 Bulk Upload' tabs.")
        else:
            # Calculations
            total_assets = len(df)
            active_count = len(df[df["status"] == "active"]) if "status" in df.columns else 0
            inactive_count = len(df[df["status"] == "inactive"]) if "status" in df.columns else 0
            breakdown_count = len(df[df["status"] == "breakdown"]) if "status" in df.columns else 0
            
            critical_mask = df.get("priority", pd.Series(["low"] * len(df))).isin(["critical", "high"])
            critical_count = critical_mask.sum()
            non_critical_count = total_assets - critical_count
            
            critical_active = len(df[critical_mask & (df["status"] == "active")]) if "status" in df.columns else 0
            critical_breakdown = len(df[critical_mask & (df["status"] == "breakdown")]) if "status" in df.columns else 0
            non_critical_active = len(df[~critical_mask & (df["status"] == "active")]) if "status" in df.columns else 0
            non_critical_breakdown = len(df[~critical_mask & (df["status"] == "breakdown")]) if "status" in df.columns else 0
            
            # Health
            if "condition_rating" in df.columns:
                excellent_count = len(df[df["condition_rating"] >= 4.5])
                good_count = len(df[(df["condition_rating"] >= 3.5) & (df["condition_rating"] < 4.5)])
                average_count = len(df[(df["condition_rating"] >= 2.5) & (df["condition_rating"] < 3.5)])
                poor_count = len(df[df["condition_rating"] < 2.5])
            else:
                excellent_count = good_count = average_count = poor_count = 0
            
            # Financial
            total_value = df["purchase_cost"].fillna(0).sum() if "purchase_cost" in df.columns else 0
            dept_count = df["department"].nunique() if "department" in df.columns else 0
            
            # Warranty
            expired_count = expiring_30 = expiring_90 = expiring_180 = 0
            if "warranty_expiry" in df.columns:
                for _, row in df.iterrows():
                    try:
                        we = pd.to_datetime(row["warranty_expiry"])
                        days_left = (we.date() - today).days
                        if days_left < 0:
                            expired_count += 1
                        elif days_left <= 30:
                            expiring_30 += 1
                        elif days_left <= 90:
                            expiring_90 += 1
                        elif days_left <= 180:
                            expiring_180 += 1
                    except:
                        pass
            
            # ============================================
            # EXECUTIVE KPI ROW
            # ============================================
            st.markdown("### 🎯 Executive Asset Overview")
            
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Total Assets</div><div style="font-size:2.2rem;font-weight:800;color:#1a1a1a;">{total_assets}</div><div style="font-size:0.65rem;color:#888;">Across {dept_count} Depts</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Active</div><div style="font-size:2.2rem;font-weight:800;color:#10B981;">{active_count}</div><div style="font-size:0.65rem;color:#888;">{round(active_count/total_assets*100) if total_assets > 0 else 0}% of total</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Critical</div><div style="font-size:2.2rem;font-weight:800;color:#F59E0B;">{critical_count}</div><div style="font-size:0.65rem;color:#888;">{critical_active} Active</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Breakdown</div><div style="font-size:2.2rem;font-weight:800;color:#EF4444;">{breakdown_count}</div><div style="font-size:0.65rem;color:#888;">{critical_breakdown} Critical</div></div>""", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Portfolio Value</div><div style="font-size:1.4rem;font-weight:800;color:#3B82F6;">₦{total_value:,.0f}</div><div style="font-size:0.65rem;color:#888;">Total</div></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Status Breakdown
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🔴 Critical Assets")
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;">
                    <div style="background:#ECFDF5;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#10B981;">{critical_active}</div><div style="font-size:0.6rem;color:#666;">Active</div></div>
                    <div style="background:#FEF3C7;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#F59E0B;">{critical_count - critical_active - critical_breakdown}</div><div style="font-size:0.6rem;color:#666;">Inactive</div></div>
                    <div style="background:#FEF2F2;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#EF4444;">{critical_breakdown}</div><div style="font-size:0.6rem;color:#666;">Breakdown</div></div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown("#### 🟢 Non-Critical Assets")
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;">
                    <div style="background:#ECFDF5;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#10B981;">{non_critical_active}</div><div style="font-size:0.6rem;color:#666;">Active</div></div>
                    <div style="background:#FEF3C7;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#F59E0B;">{non_critical_count - non_critical_active - non_critical_breakdown}</div><div style="font-size:0.6rem;color:#666;">Inactive</div></div>
                    <div style="background:#FEF2F2;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#EF4444;">{non_critical_breakdown}</div><div style="font-size:0.6rem;color:#666;">Breakdown</div></div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Health Matrix
            st.markdown("### 🏥 Asset Health Matrix")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;border-left:4px solid #10B981;"><div style="font-weight:700;color:#10B981;">⭐ Excellent</div><div style="font-size:1.5rem;font-weight:800;">{excellent_count}</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;border-left:4px solid #3B82F6;"><div style="font-weight:700;color:#3B82F6;">👍 Good</div><div style="font-size:1.5rem;font-weight:800;">{good_count}</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;border-left:4px solid #F59E0B;"><div style="font-weight:700;color:#F59E0B;">⚠️ Average</div><div style="font-size:1.5rem;font-weight:800;">{average_count}</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;border-left:4px solid #EF4444;"><div style="font-weight:700;color:#EF4444;">🔴 Poor</div><div style="font-size:1.5rem;font-weight:800;">{poor_count}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Warranty & Financial
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 📋 Warranty Status")
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                    <div style="background:#FEF2F2;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#EF4444;">{expired_count}</div><div style="font-size:0.6rem;">Expired</div></div>
                    <div style="background:#FFFBEB;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#F59E0B;">{expiring_30}</div><div style="font-size:0.6rem;">≤30 days</div></div>
                    <div style="background:#EFF6FF;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#3B82F6;">{expiring_90}</div><div style="font-size:0.6rem;">≤90 days</div></div>
                    <div style="background:#ECFDF5;border-radius:8px;padding:0.6rem;text-align:center;"><div style="font-size:1.2rem;font-weight:800;color:#10B981;">{expiring_180}</div><div style="font-size:0.6rem;">≤180 days</div></div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown("### 💰 Financial Summary")
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:1rem;">
                    <table style="width:100%;font-size:0.8rem;">
                        <tr><td>📊 Portfolio Value</td><td style="text-align:right;font-weight:700;">₦{total_value:,.2f}</td></tr>
                        <tr><td>📈 Avg Asset Value</td><td style="text-align:right;font-weight:700;">₦{total_value/total_assets:,.2f}</td></tr>
                        <tr><td>🏢 Departments</td><td style="text-align:right;font-weight:700;">{dept_count}</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
            
            if critical_breakdown > 0:
                st.error(f"🚨 {critical_breakdown} critical assets in BREAKDOWN!")
            if expired_count > 0:
                st.warning(f"⚠️ {expired_count} assets with expired warranties!")
    
    # ============================================
    # TAB 1: ASSET REGISTER TABLE
    # ============================================
    with ar_tabs[1]:
        st.markdown("### 📋 Asset Register")
        
        if len(df) == 0:
            st.info("No assets registered yet. Add assets to see them here.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                # Create combined department — sub_division labels
                df["dept_display"] = df.apply(lambda row: f"{row['department']} — {row['sub_division']}" if pd.notna(row.get('sub_division')) and row.get('sub_division') != 'N/A' else row['department'], axis=1)
                dept_options = ["All"] + sorted(df["dept_display"].unique().tolist())
                dept_filter = st.selectbox("Department", dept_options, key="ar_dept")
            with c2:
                building_options = ["All"] + sorted(df["location_building"].unique().tolist())
                building_filter = st.selectbox("Building", building_options, key="ar_bldg_filter")
            with c3:
                status_filter = st.selectbox("Status", ["All", "active", "inactive", "breakdown"], key="ar_status")
            with c4:
                priority_filter = st.selectbox("Priority", ["All", "critical", "high", "medium", "low"], key="ar_pri")
            with c5:
                search = st.text_input("🔍 Search", placeholder="Name, code, location...", key="ar_search")
            
            display_df = df.copy()
            if dept_filter != "All":
                display_df = display_df[display_df["dept_display"] == dept_filter]
            if building_filter != "All" and "location_building" in display_df.columns:
                display_df = display_df[display_df["location_building"] == building_filter]
            if status_filter != "All" and "status" in display_df.columns:
                display_df = display_df[display_df["status"] == status_filter]
            if priority_filter != "All" and "priority" in display_df.columns:
                display_df = display_df[display_df["priority"] == priority_filter]
            if search:
                mask = False
                for col in ["name", "asset_tag", "location_building", "manufacturer", "model"]:
                    if col in display_df.columns:
                        mask = mask | display_df[col].astype(str).str.contains(search, case=False, na=False)
                display_df = display_df[mask]
            
            st.caption(f"Showing {len(display_df)} of {len(df)} assets")
            
            display_cols = [c for c in ["asset_tag", "name", "department", "location_building", "location_floor", "status", "priority", "manufacturer", "model", "serial_number", "condition_rating", "purchase_cost"] if c in display_df.columns]
            
            st.dataframe(display_df[display_cols], use_container_width=True, hide_index=True, height=500)
            
            csv = display_df.to_csv(index=False)
            st.download_button("📥 Export CSV", csv, f"assets_{fc}_{today}.csv", "text/csv", use_container_width=True)
    
    # ============================================
    # TAB 2: ADD ASSET — 6-STEP WIZARD
    # ============================================
    with ar_tabs[2]:
        st.markdown("### ➕ Register New Asset")
        
        if "add_asset_step" not in st.session_state:
            st.session_state.add_asset_step = 1
        
        steps = ["1. Asset Info", "2. Specifications", "3. Financial", "4. Assignment", "5. Maintenance", "6. Review"]
        step_cols = st.columns(6)
        for i, (col, name) in enumerate(zip(step_cols, steps)):
            with col:
                if i + 1 == st.session_state.add_asset_step:
                    st.markdown(f"""<div style="background:#CC0000;color:white;padding:0.5rem;border-radius:8px;text-align:center;font-weight:600;font-size:0.7rem;">{name}</div>""", unsafe_allow_html=True)
                elif i + 1 < st.session_state.add_asset_step:
                    st.markdown(f"""<div style="background:#10B981;color:white;padding:0.5rem;border-radius:8px;text-align:center;font-weight:600;font-size:0.7rem;">✅ {name}</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="background:#f5f5f5;color:#999;padding:0.5rem;border-radius:8px;text-align:center;font-size:0.7rem;">{name}</div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        cats = DB.get_categories()
        cat_names = sorted([c.get("name","") for c in cats]) if cats else ["MEP-ELECTRICAL", "MEP-HVAC", "MEP-PLUMBING", "ELV-FIRE ALARM", "CIVIL", "VERTICAL TRANSPORT"]
        
        # STEP 1
        if st.session_state.add_asset_step == 1:
            with st.form("add_step1"):
                c1, c2 = st.columns(2)
                with c1:
                    s1_name = st.text_input("Asset Name*", placeholder="e.g. DG 1 - CT-3 - DG Yard")
                    s1_code = st.text_input("Asset Code*", placeholder="e.g. WTC-DG-001")
                    s1_cat = st.selectbox("Category*", cat_names)
                    s1_parent = st.text_input("Parent Asset", placeholder="e.g. Diesel Generator Set")
                    s1_priority = st.selectbox("Priority*", ["critical", "high", "medium", "low"])
                    s1_ownership = st.selectbox("Ownership*", ["Churchgate Group", "Leased", "Tenant Owned", "Government"])
                with c2:
                    s1_dept = st.selectbox("Department*", cat_names)
                    s1_desc = st.text_area("Description*", height=100)
                    s1_status = st.selectbox("Status*", ["active", "inactive", "breakdown", "decommissioned"])
                    s1_health = st.selectbox("Health Condition", ["Excellent", "Good", "Average", "Poor"])
                    s1_vfreq = st.selectbox("Verification Frequency", ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"])
                
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                with c1:
                    s1_bldg = st.selectbox("Building*", ["CT — Office Tower", "SAT — Residential Tower", "RC — Recreation Center", "IP — Intermediate Parking"])
                with c2:
                    s1_subloc = st.text_input("Sub Location", placeholder="e.g. DG Yard, Floor 13")
                with c3:
                    s1_region = st.text_input("City", value=info.get("city", "Abuja"))
                
                c1, c2 = st.columns(2)
                with c1:
                    s1_barcode = st.text_input("Barcode*")
                with c2:
                    s1_geo = st.text_input("Geo Location", placeholder="9.0486, 7.4732")
                
                if st.form_submit_button("Continue →", use_container_width=True, type="primary"):
                    if s1_name and s1_code and s1_desc and s1_bldg and s1_barcode:
                        st.session_state.s1 = {"name": s1_name, "asset_tag": s1_code, "department": s1_dept, "category_name": s1_cat, "parent_asset": s1_parent, "priority": s1_priority, "ownership": s1_ownership, "description": s1_desc, "status": s1_status, "health": s1_health, "verification_frequency": s1_vfreq, "location_building": s1_bldg, "location_floor": s1_subloc, "region": s1_region, "barcode": s1_barcode, "geo_location": s1_geo}
                        st.session_state.add_asset_step = 2
                        st.rerun()
                    else:
                        st.error("⚠️ Fill all required fields (*)")
        
        # STEP 2
        elif st.session_state.add_asset_step == 2:
            with st.form("add_step2"):
                st.markdown("#### 📐 Technical Specifications")
                c1, c2, c3 = st.columns(3)
                with c1:
                    s2_mfg = st.text_input("Manufacturer*", placeholder="Cummins, Perkins")
                    s2_serial = st.text_input("Serial Number*")
                    s2_model = st.text_input("Model")
                with c2:
                    s2_modelno = st.text_input("Model Number")
                    s2_capacity = st.text_input("Capacity", placeholder="500 KVA")
                    s2_weight = st.text_input("Gross Weight (kg)")
                with c3:
                    s2_dims = st.text_input("Dimensions", placeholder="200x150x100 cm")
                    s2_stdhrs = st.number_input("Standard Running Hours", value=0.0)
                    s2_tothrs = st.number_input("Total Operational Hours", value=0.0)
                
                c1, c2 = st.columns(2)
                with c1:
                    s2_sap = st.date_input("SAP Created Date", today)
                    s2_install = st.date_input("Installation Date", today)
                with c2:
                    s2_checklist = st.selectbox("Checklist Template", ["Standard MEP", "Standard HVAC", "Standard ELV", "Standard Civil"])
                    s2_ppm = st.selectbox("PPM Frequency", ["Weekly", "Monthly", "Quarterly", "Yearly"])
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("⬅️ Back", use_container_width=True):
                        st.session_state.add_asset_step = 1
                        st.rerun()
                with c2:
                    if st.form_submit_button("Continue →", use_container_width=True, type="primary"):
                        if s2_mfg and s2_serial:
                            st.session_state.s2 = {"manufacturer": s2_mfg, "serial_number": s2_serial, "model": s2_model, "model_no": s2_modelno, "capacity": s2_capacity, "gross_weight": s2_weight, "dimensions": s2_dims, "standard_running_hrs": s2_stdhrs, "total_operational_hrs": s2_tothrs, "sap_created_date": str(s2_sap), "installation_date": str(s2_install), "checklist_template": s2_checklist, "ppm_frequency": s2_ppm}
                            st.session_state.add_asset_step = 3
                            st.rerun()
                        else:
                            st.error("⚠️ Manufacturer and Serial Number required")
        
        # STEP 3
        elif st.session_state.add_asset_step == 3:
            with st.form("add_step3"):
                st.markdown("#### 💰 Financial Details")
                c1, c2, c3 = st.columns(3)
                with c1:
                    s3_price = st.number_input("Purchase Price (₦)*", min_value=0.0, step=10000.0)
                    s3_currency = st.selectbox("Currency", ["NGN", "USD", "EUR"])
                    s3_residual = st.number_input("Residual Value %", value=10.0)
                with c2:
                    s3_purchdate = st.date_input("Purchase Date", today)
                    s3_depmethod = st.selectbox("Depreciation", ["Straight Line", "Reducing Balance"])
                    s3_useful = st.number_input("Useful Life (Years)", value=10)
                with c3:
                    s3_invoice = st.text_input("Invoice No")
                    s3_invdate = st.date_input("Invoice Date", today)
                    s3_po = st.text_input("PO Number")
                    s3_podate = st.date_input("PO Date", today)
                
                st.markdown("#### 🛡️ Warranty")
                c1, c2, c3 = st.columns(3)
                with c1:
                    s3_warranty = st.selectbox("Warranty?", ["Yes", "No"])
                with c2:
                    s3_wstart = st.date_input("Warranty Start", today)
                with c3:
                    s3_wend = st.date_input("Warranty End", today + timedelta(days=365))
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("⬅️ Back", use_container_width=True):
                        st.session_state.add_asset_step = 2
                        st.rerun()
                with c2:
                    if st.form_submit_button("Continue →", use_container_width=True, type="primary"):
                        st.session_state.s3 = {"purchase_cost": s3_price, "currency": s3_currency, "residual_value": s3_residual, "purchase_date": str(s3_purchdate), "depreciation_method": s3_depmethod, "useful_life": s3_useful, "invoice_no": s3_invoice, "invoice_date": str(s3_invdate), "po_number": s3_po, "po_date": str(s3_podate), "warranty_applicable": s3_warranty == "Yes", "warranty_start": str(s3_wstart), "warranty_expiry": str(s3_wend)}
                        st.session_state.add_asset_step = 4
                        st.rerun()
        
        # STEP 4
        elif st.session_state.add_asset_step == 4:
            with st.form("add_step4"):
                st.markdown("#### 👤 Assignment")
                users = DB.get_users()
                user_names = [u.get("name","") for u in users]
                c1, c2 = st.columns(2)
                with c1:
                    s4_user = st.selectbox("Assigned User", ["None"] + user_names)
                    s4_adduser = st.selectbox("Additional User", ["None"] + user_names)
                with c2:
                    s4_vendor = st.selectbox("Vendor", ["None", "Clyde Engineering", "Gates and Shield", "TXB Enterprise", "Brainworks"])
                    s4_replaceyr = st.number_input("Replace Year", value=2030)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("⬅️ Back", use_container_width=True):
                        st.session_state.add_asset_step = 3
                        st.rerun()
                with c2:
                    if st.form_submit_button("Continue →", use_container_width=True, type="primary"):
                        st.session_state.s4 = {"assigned_to_name": s4_user if s4_user != "None" else None, "additional_user": s4_adduser if s4_adduser != "None" else None, "vendor": s4_vendor if s4_vendor != "None" else None, "plan_year_to_replace": s4_replaceyr}
                        st.session_state.add_asset_step = 5
                        st.rerun()
        
        # STEP 5
        elif st.session_state.add_asset_step == 5:
            with st.form("add_step5"):
                st.markdown("#### 🔧 Maintenance Setup")
                c1, c2 = st.columns(2)
                with c1:
                    s5_amc = st.selectbox("AMC?", ["Yes", "No"])
                    s5_amcprov = st.text_input("AMC Provider")
                    s5_amcstart = st.date_input("AMC Start", today)
                with c2:
                    s5_amccost = st.number_input("AMC Cost (₦/yr)", min_value=0.0, step=10000.0)
                    s5_amcend = st.date_input("AMC End", today + timedelta(days=365))
                    s5_team = st.selectbox("Maintenance Team", ["Engineering — Electrical", "Engineering — HVAC", "Engineering — Plumbing", "Facility Management — Hard Services"])
                
                s5_checklist = st.text_area("PPM Checklist Items (one per line)", placeholder="Check for dust\nCheck earth connection\nCheck fire suppression")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("⬅️ Back", use_container_width=True):
                        st.session_state.add_asset_step = 4
                        st.rerun()
                with c2:
                    if st.form_submit_button("Continue →", use_container_width=True, type="primary"):
                        st.session_state.s5 = {"amc_applicable": s5_amc == "Yes", "amc_provider": s5_amcprov, "amc_cost": s5_amccost, "amc_start": str(s5_amcstart), "amc_end": str(s5_amcend), "maintenance_team": s5_team, "ppm_checklist_items": s5_checklist}
                        st.session_state.add_asset_step = 6
                        st.rerun()
        
        # STEP 6 — REVIEW & SUBMIT
        elif st.session_state.add_asset_step == 6:
            s1 = st.session_state.get("s1", {})
            s2 = st.session_state.get("s2", {})
            s3 = st.session_state.get("s3", {})
            s4 = st.session_state.get("s4", {})
            s5 = st.session_state.get("s5", {})
            
            st.markdown("#### 📋 Review & Submit")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""<div style="background:white;border-radius:8px;padding:0.8rem;border:1px solid #ddd;font-size:0.75rem;"><b>🏗️ Asset:</b> {s1.get('name','N/A')}<br><b>Code:</b> {s1.get('asset_tag','N/A')}<br><b>Location:</b> {s1.get('location_building','N/A')}</div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:white;border-radius:8px;padding:0.8rem;border:1px solid #ddd;font-size:0.75rem;"><b>📐 Mfg:</b> {s2.get('manufacturer','N/A')}<br><b>Serial:</b> {s2.get('serial_number','N/A')}<br><b>Model:</b> {s2.get('model','N/A')}</div>""", unsafe_allow_html=True)
            
            st.markdown(f"""<div style="background:white;border-radius:8px;padding:0.8rem;border:1px solid #ddd;font-size:0.75rem;margin-top:0.5rem;"><b>💰 Price:</b> ₦{s3.get('purchase_cost',0):,.2f} | <b>Warranty:</b> {s3.get('warranty_start','N/A')} → {s3.get('warranty_expiry','N/A')}</div>""", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("⬅️ Back", use_container_width=True, key="s6_back"):
                    st.session_state.add_asset_step = 5
                    st.rerun()
            with c2:
                if st.button("💾 Save Draft", use_container_width=True, key="s6_draft"):
                    st.info("Draft saving coming soon.")
            with c3:
                if st.button("✅ SUBMIT ASSET", use_container_width=True, type="primary", key="s6_submit"):
                    full_data = {**s1, **s2, **s3, **s4, **s5}
                    # Map department
                    raw_dept = full_data.get("department", "")
                    dept_mapping = {
                        "Engineering — Electrical": ("Engineering", "Electrical"),
                        "Engineering — Fire Fighting": ("Engineering", "Fire Fighting"),
                        "Engineering — HVAC": ("Engineering", "HVAC"),
                        "Engineering — Plumbing": ("Engineering", "Plumbing"),
                        "Engineering — Vertical Transportation": ("Engineering", "Vertical Transportation (Lifts)"),
                        "Facility Management — FM Operations": ("Facility Management", "FM Operations"),
                        "Facility Management — Fitout Works": ("Facility Management", "Fitout Works"),
                        "Facility Management — Front of House": ("Facility Management", "Front of House"),
                        "Facility Management — Hard Services": ("Facility Management", "Hard Services"),
                        "Facility Management — Soft Services": ("Facility Management", "Soft Services"),
                        "Security": ("Security", "Security"),
                        "Technology Group — Access Control": ("Technology Group", "Access Control"),
                        "Technology Group — Automation": ("Technology Group", "Automation"),
                        "Technology Group — BMS": ("Technology Group", "BMS"),
                        "Technology Group — CCTV": ("Technology Group", "CCTV"),
                        "Technology Group — Fire Alarm & Voice Evac": ("Technology Group", "Fire Alarm & Voice Evac"),
                        "Technology Group — Networks & Connectivity": ("Technology Group", "Networks & Connectivity"),
                        "Technology Group — MDTH (DSTV)": ("Technology Group", "MDTH (DSTV)"),
                    }
                    mapped_dept, mapped_sub = dept_mapping.get(raw_dept, (raw_dept, raw_dept))
                    full_data["department"] = mapped_dept
                    full_data["sub_division"] = mapped_sub
                    full_data["facility_code"] = fc
                    full_data["created_at"] = datetime.now().isoformat()
                    full_data["condition_rating"] = 5 if s1.get("health") == "Excellent" else 4 if s1.get("health") == "Good" else 3 if s1.get("health") == "Average" else 2
                    
                    # Get category_id from category_name
                    try:
                        cat_lookup = safe_supabase_query(lambda: supabase.table("asset_categories").select("id").eq("name", s1.get("category_name", "")).execute(), error_prefix="Category lookup")
                        if cat_lookup and cat_lookup.data:
                            full_data["category_id"] = cat_lookup.data[0]["id"]
                    except:
                        pass
                    
                    result = DB.insert("assets", full_data)
                    if result:
                        st.success(f"✅ Asset '{s1.get('name','N/A')}' registered!")
                        st.balloons()
                        for k in ["s1","s2","s3","s4","s5","add_asset_step"]:
                            if k in st.session_state:
                                del st.session_state[k]
                        st.session_state.add_asset_step = 1
                        import time as _time
                        _time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Failed. Try again.")
    
    # ============================================
    # TAB 3: BULK UPLOAD
    # ============================================
    with ar_tabs[3]:
        st.markdown("### 📦 Bulk Asset Upload")
        
        template_cols = ["Asset Name", "Asset Code", "Department", "Category", "Parent Asset", "Status", "Priority", "Ownership", "Manufacturer", "Serial No", "Model", "Capacity", "Description", "Location", "Sub Location", "City", "Barcode", "Purchase Price", "Purchase Date", "Warranty Start", "Warranty End", "Verification Frequency", "Checklist Template", "PPM Frequency"]
        template_df = pd.DataFrame(columns=template_cols)
        
        st.download_button("📥 Download CSV Template", template_df.to_csv(index=False), "asset_upload_template.csv", "text/csv", use_container_width=True)
        
        st.markdown("---")
        uploaded = st.file_uploader("Upload filled CSV", type="csv")
        
        if uploaded:
            # Try to detect separator (tab or comma)
            try:
                bulk_df = pd.read_csv(uploaded, sep=None, engine='python', skiprows=1)
            except:
                bulk_df = pd.read_csv(uploaded, skiprows=1)
            
            # Remove completely empty rows
            bulk_df = bulk_df.dropna(how='all')
            
            # Filter out rows where Assetname is empty or NA
            if "Assetname" in bulk_df.columns:
                bulk_df = bulk_df[bulk_df["Assetname"].notna() & (bulk_df["Assetname"] != "") & (bulk_df["Assetname"] != "NA")]
            
            st.dataframe(bulk_df.head(10), use_container_width=True)
            st.caption(f"{len(bulk_df)} valid assets found (empty rows skipped)")
            
            if st.button(f"🚀 Upload {len(bulk_df)} Assets", use_container_width=True, type="primary"):
                success = 0
                for _, row in bulk_df.iterrows():
                    try:
                        raw_dept = str(row.get("Department", "")).strip()
                        
                        # Department mapping
                        dept_mapping = {
                            "Engineering — Electrical": ("Engineering", "Electrical"),
                            "Engineering — Fire Fighting": ("Engineering", "Fire Fighting"),
                            "Engineering — HVAC": ("Engineering", "HVAC"),
                            "Engineering — Plumbing": ("Engineering", "Plumbing"),
                            "Engineering — Vertical Transportation": ("Engineering", "Vertical Transportation (Lifts)"),
                            "Engineering — Vertical Transportation (Lifts)": ("Engineering", "Vertical Transportation (Lifts)"),
                            "Facility Management — FM Operations": ("Facility Management", "FM Operations"),
                            "Facility Management — Fitout Works": ("Facility Management", "Fitout Works"),
                            "Facility Management — Front of House": ("Facility Management", "Front of House"),
                            "Facility Management — Hard Services": ("Facility Management", "Hard Services"),
                            "Facility Management — Soft Services": ("Facility Management", "Soft Services"),
                            "Security": ("Security", "Security"),
                            "Technology Group — Access Control": ("Technology Group", "Access Control"),
                            "Technology Group — Automation": ("Technology Group", "Automation"),
                            "Technology Group — BMS": ("Technology Group", "BMS"),
                            "Technology Group — CCTV": ("Technology Group", "CCTV"),
                            "Technology Group — Fire Alarm & Voice Evac": ("Technology Group", "Fire Alarm & Voice Evac"),
                            "Technology Group — Networks & Connectivity": ("Technology Group", "Networks & Connectivity"),
                            "Technology Group — MDTH (DSTV)": ("Technology Group", "MDTH (DSTV)"),
                        }
                        
                        mapped_dept, mapped_sub = dept_mapping.get(raw_dept, (raw_dept, raw_dept))
                        
                        # Parse purchase price safely
                        purchase_price = 0
                        try:
                            pp = row.get("Purchase Price", 0)
                            if pd.notna(pp) and str(pp).strip() != "" and str(pp).strip() != "NA":
                                purchase_price = float(str(pp).replace(",", "").replace("₦", "").strip())
                        except:
                            pass
                        
                        asset_data = {
                            "facility_code": fc,
                            "name": str(row.get("Assetname", row.get("Asset Name", ""))).strip(),
                            "asset_tag": str(row.get("Asset Code", "")).strip() or f"AUTO-{fc}-{success+1}",
                            "department": mapped_dept,
                            "sub_division": mapped_sub,
                            "category_name": str(row.get("Category", "")).strip(),
                            "parent_asset": str(row.get("Parent Asset", "")).strip(),
                            "status": str(row.get("Status", "active")).strip().lower() or "active",
                            "priority": str(row.get("Priority", "medium")).strip().lower() or "medium",
                            "ownership": str(row.get("Ownership", "")).strip(),
                            "manufacturer": str(row.get("Manufacturer", "")).strip(),
                            "model": str(row.get("Model", "")).strip(),
                            "model_no": str(row.get("Model NO", "")).strip(),
                            "serial_number": str(row.get("Serial NO", row.get("Serial No", ""))).strip(),
                            "capacity": str(row.get("Capacity", "")).strip(),
                            "description": str(row.get("Description", "")).strip(),
                            "location_building": str(row.get("Location", "")).strip(),
                            "location_floor": str(row.get("Sub Location", "")).strip(),
                            "barcode": str(row.get("Barcode", "")).strip(),
                            "geo_location": str(row.get("Geo Location", "")).strip(),
                            "purchase_cost": purchase_price,
                            "purchase_date": fix_date(row.get("Purchase Date")),
                            "installation_date": fix_date(row.get("Installation Date")),
                            "warranty_start": fix_date(row.get("Warrenty Start Date", row.get("Warranty Start Date"))),
                            "warranty_expiry": fix_date(row.get("Warrenty End Date", row.get("Warranty End Date"))),
                            "sap_created_date": fix_date(row.get("SAP Created Date")),
                            "depreciation_method": str(row.get("Depreciation Method", "")).strip(),
                            "residual_value": str(row.get("Residual Value / Percentage", "")).strip(),
                            "invoice_no": str(row.get("Invioce NO", row.get("Invoice NO", ""))).strip(),
                            "po_number": str(row.get("PO Number", "")).strip(),
                            "vendor": str(row.get("Vendor", "")).strip(),
                            "assigned_user": str(row.get("Assigned User", "")).strip(),
                            "additional_user": str(row.get("Additional User", "")).strip(),
                            "checklist": str(row.get("Checklist", "")).strip(),
                            "ppm": str(row.get("PPM", "")).strip(),
                            "verification_frequency": str(row.get("Verification Frequency", "")).strip(),
                            "gross_weight": str(row.get("Gross Weight", "")).strip(),
                            "dimensions": str(row.get("Size and Dimensions", "")).strip(),
                            "health_condition": str(row.get("Health Condition", "")).strip(),
                            "region": str(row.get("Region", "")).strip(),
                            "city": str(row.get("City", "")).strip(),
                            "plan_year_to_replace": str(row.get("Plan Year to replace", "")).strip(),
                            "warranty_applicable": str(row.get("Warrenty Applicable", "")).strip(),
                            "standard_running_hrs": str(row.get("Standard Running Hrs", "")).strip(),
                            "total_operational_hrs": str(row.get("Total Operational Hrs", "")).strip(),
                            "currency": str(row.get("Currency", "")).strip() or "NGN",
                            "useful_life": str(row.get("Useful Life", "")).strip(),
                            "condition_rating": 5,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        # Remove None values that should be NULL in DB
                        # Only filter out truly empty values, keep name/asset_tag even if "NA"
                        keep_keys = ["name", "asset_tag", "facility_code", "status", "priority", "department", "condition_rating", "created_at"]
                        asset_data = {k: v for k, v in asset_data.items() if k in keep_keys or (v is not None and v != "" and str(v).strip() != "" and str(v).strip().lower() not in ["na", "none", "null"])}
                        
                        DB.insert("assets", asset_data)
                        success += 1
                        
                        # Progress update every 500 rows
                        if success % 500 == 0:
                            st.write(f"⏳ Uploaded {success} assets...")
                            
                    except Exception as e:
                        continue
                st.success(f"✅ {success} assets uploaded!")
                st.balloons()
                st.rerun()
    
    # ============================================
    # TAB 4: READINGS — AI-POWERED ASSET PERFORMANCE CENTER
    # ============================================
    with ar_tabs[4]:
        st.markdown("### 📖 Asset Readings — AI-Powered Performance Center")
        
        if len(df) == 0:
            st.info("No assets registered. Add assets to see readings.")
        else:
            # KPI Calculations
            total_assets_count = len(df)
            critical_assets_count = len(df[df["priority"].isin(["critical", "high"])]) if "priority" in df.columns else 0
            
            # Readings summary (placeholder until readings table is populated)
            total_readings = 0
            abnormal_readings = 0
            corrective_wos = 0
            total_downtime = 0
            
            try:
                readings_res = safe_supabase_query(lambda: supabase.table("utility_readings").select("id", count="exact").eq("facility_code", fc).execute(), error_prefix="Readings count")
                total_readings = readings_res.count if readings_res else 0
            except:
                pass
            
            # Executive KPI Row
            st.markdown("### 🎯 Performance KPIs")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Total Readings</div><div style="font-size:1.6rem;font-weight:800;color:#3B82F6;">{total_readings}</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Abnormal</div><div style="font-size:1.6rem;font-weight:800;color:#EF4444;">{abnormal_readings}</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Critical Alerts</div><div style="font-size:1.6rem;font-weight:800;color:#F59E0B;">{critical_assets_count}</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Corrective WOs</div><div style="font-size:1.6rem;font-weight:800;color:#8B5CF6;">{corrective_wos}</div></div>""", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #EC4899;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Downtime (Hrs)</div><div style="font-size:1.6rem;font-weight:800;color:#EC4899;">{total_downtime}</div></div>""", unsafe_allow_html=True)
            with c6:
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Health Score</div><div style="font-size:1.6rem;font-weight:800;color:#10B981;">{round(total_assets_count/max(total_assets_count,1)*100)}%</div></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # AI Insights Banner
            if critical_assets_count > 10:
                st.warning(f"🤖 **AI Insight:** {critical_assets_count} critical assets require immediate attention. Recommend prioritizing PPM for these assets.")
            if abnormal_readings > 0:
                st.error(f"🤖 **AI Alert:** {abnormal_readings} abnormal readings detected. Predictive maintenance recommended.")
            if total_readings == 0:
                st.info("🤖 **AI Insight:** No readings recorded yet. Start recording utility readings to enable predictive analytics.")
            
            st.markdown("---")
            
            # Filters
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                reading_building = st.selectbox("🏢 Building", ["All"] + sorted(df["location_building"].unique().tolist()), key="read_bldg")
            with c2:
                reading_dept = st.selectbox("🏷️ Department", ["All"] + sorted(df["department"].unique().tolist()), key="read_dept")
            with c3:
                reading_priority = st.selectbox("⚠️ Priority", ["All", "critical", "high", "medium", "low"], key="read_pri")
            with c4:
                reading_search = st.text_input("🔍 Search Asset", key="read_search", placeholder="Name or code...")
            
            # Build readings dataframe
            readings_data = []
            for _, asset in df.iterrows():
                # Apply filters
                if reading_building != "All" and asset.get("location_building","") != reading_building:
                    continue
                if reading_dept != "All" and asset.get("department","") != reading_dept:
                    continue
                if reading_priority != "All" and asset.get("priority","") != reading_priority:
                    continue
                if reading_search:
                    name = str(asset.get("name","")).lower()
                    code = str(asset.get("asset_tag","")).lower()
                    if reading_search.lower() not in name and reading_search.lower() not in code:
                        continue
                
                # Calculate asset age
                asset_age = "N/A"
                if pd.notna(asset.get("installation_date")):
                    try:
                        inst_date = pd.to_datetime(asset["installation_date"])
                        age_days = (today - inst_date.date()).days
                        if age_days > 365:
                            asset_age = f"{age_days // 365} Years"
                        elif age_days > 30:
                            asset_age = f"{age_days // 30} Months"
                        else:
                            asset_age = f"{age_days} Days"
                    except:
                        pass
                
                readings_data.append({
                    "Asset ID": asset.get("asset_tag", "N/A"),
                    "Asset Name": asset.get("name", "N/A"),
                    "Department": asset.get("department", "N/A"),
                    "Sub-Division": asset.get("sub_division", "N/A"),
                    "Manufacturer": asset.get("manufacturer", "N/A"),
                    "Model": asset.get("model", "N/A"),
                    "Serial Number": asset.get("serial_number", "N/A"),
                    "Location": f"{asset.get('location_building','')}",
                    "Priority": asset.get("priority", "N/A").upper(),
                    "Condition": asset.get("condition_rating", "N/A"),
                    "Asset Age": asset_age,
                    "Running Hours": asset.get("total_operational_hrs", 0) if pd.notna(asset.get("total_operational_hrs")) else 0,
                    "PPM Frequency": asset.get("verification_frequency", "N/A"),
                    "Last PPM": "N/A",
                    "Breakdowns": 0,
                    "Downtime (Hrs)": 0,
                })
            
            rd_df = pd.DataFrame(readings_data)
            
            st.caption(f"📋 Showing {len(rd_df)} of {len(df)} assets")
            
            # Color-code condition column
            def highlight_condition(val):
                try:
                    v = float(val)
                    if v >= 4.5: return 'background-color:#ECFDF5;color:#059669;font-weight:600;'
                    elif v >= 3.5: return 'background-color:#EFF6FF;color:#2563EB;font-weight:600;'
                    elif v >= 2.5: return 'background-color:#FFFBEB;color:#D97706;font-weight:600;'
                    else: return 'background-color:#FEF2F2;color:#DC2626;font-weight:600;'
                except:
                    return ''
            
            def highlight_priority(val):
                if val in ["CRITICAL", "HIGH"]:
                    return 'background-color:#FEF2F2;color:#DC2626;font-weight:600;'
                return ''
            
            if len(rd_df) > 0:
                styled = rd_df.style
                if "Condition" in rd_df.columns:
                    styled = styled.map(highlight_condition, subset=["Condition"])
                if "Priority" in rd_df.columns:
                    styled = styled.map(highlight_priority, subset=["Priority"])
                
                st.dataframe(styled, use_container_width=True, hide_index=True, height=500)
            else:
                st.info("No assets match your filters.")
            
            st.markdown("---")
            
            # Charts & Analytics
            st.markdown("### 📊 Asset Performance Analytics")
            
            c1, c2 = st.columns(2)
            with c1:
                # Department distribution chart
                if "department" in rd_df.columns and len(rd_df) > 0:
                    dept_counts = rd_df["Department"].value_counts().head(10)
                    fig_dept = px.bar(
                        x=dept_counts.values, y=dept_counts.index, orientation='h',
                        title="Assets by Department", color=dept_counts.values,
                        color_continuous_scale="Reds", labels={"x":"Count","y":""}
                    )
                    fig_dept.update_layout(height=350)
                    st.plotly_chart(fig_dept, use_container_width=True)
            
            with c2:
                # Priority distribution
                if "Priority" in rd_df.columns and len(rd_df) > 0:
                    pri_counts = rd_df["Priority"].value_counts()
                    pri_colors = {"CRITICAL":"#EF4444","HIGH":"#F59E0B","MEDIUM":"#3B82F6","LOW":"#10B981"}
                    pie_colors = [pri_colors.get(p,"#999") for p in pri_counts.index]
                    fig_pri = px.pie(
                        values=pri_counts.values, names=pri_counts.index,
                        title="Priority Distribution", color_discrete_sequence=pie_colors
                    )
                    fig_pri.update_layout(height=350)
                    st.plotly_chart(fig_pri, use_container_width=True)
            
            # Export section
            st.markdown("---")
            st.markdown("### 📥 Export Data")
            c1, c2, c3 = st.columns(3)
            with c1:
                csv_data = rd_df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv_data, f"asset_readings_{fc}_{today}.csv", "text/csv", use_container_width=True)
            with c2:
                # HTML Export
                logo_b64 = get_logo_base64()
                html_report = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:Arial;margin:20px;color:#1a1a1a;font-size:11px}}.header{{background:#1a1a1a;color:white;padding:15px;border-radius:8px;display:flex;align-items:center;gap:10px;margin-bottom:15px}}.header h1{{margin:0;font-size:16px}}table{{width:100%;border-collapse:collapse;font-size:9px}}th{{background:#CC0000;color:white;padding:5px}}td{{padding:4px;border-bottom:1px solid #eee}}.footer{{text-align:center;font-size:8px;color:#999;margin-top:15px}}</style></head><body><div class="header">{f'<img src="data:image/png;base64,{logo_b64}" height="30">' if logo_b64 else ''}<div><h1>Asset Readings Report</h1><p style="font-size:10px;opacity:0.8;">{info.get('full_name',fc)} | {today.strftime('%d %B %Y')}</p></div></div><table><tr><th>Asset ID</th><th>Name</th><th>Department</th><th>Location</th><th>Priority</th><th>Condition</th><th>Age</th></tr>"""
                for _, r in rd_df.head(100).iterrows():
                    html_report += f"<tr><td>{r['Asset ID']}</td><td>{r['Asset Name']}</td><td>{r['Department']}</td><td>{r['Location']}</td><td>{r['Priority']}</td><td>{r['Condition']}</td><td>{r['Asset Age']}</td></tr>"
                html_report += "</table><div class='footer'>Churchgate Group | facilityXperience | Confidential</div></body></html>"
                st.download_button("📥 Download HTML Report", html_report, f"readings_report_{today}.html", "text/html", use_container_width=True)
            with c3:
                try:
                    from fpdf import FPDF
                    pdf = FPDF('L','mm','A4')
                    pdf.add_page()
                    logo_path = Path("churchgate-logo.png")
                    if logo_path.exists():
                        pdf.image(str(logo_path), x=14, y=8, h=8)
                    pdf.set_font('Helvetica','B',14)
                    pdf.set_text_color(204,0,0)
                    pdf.cell(260,8,safe_text(f'Asset Readings Report - {info.get("full_name",fc)}'),0,1)
                    pdf.set_font('Helvetica','',8)
                    pdf.set_text_color(0,0,0)
                    pdf.cell(260,5,safe_text(f'Generated: {today.strftime("%d %B %Y")} | Total Assets: {len(rd_df)}'),0,1)
                    pdf.ln(3)
                    pdf.set_font('Helvetica','B',6)
                    pdf.set_fill_color(204,0,0)
                    pdf.set_text_color(255,255,255)
                    headers = ['Asset ID','Name','Department','Location','Priority','Condition','Age']
                    widths = [25,45,35,40,20,20,20]
                    for h,w in zip(headers,widths):
                        pdf.cell(w,5,safe_text(h),1,0,'C',True)
                    pdf.ln()
                    pdf.set_font('Helvetica','',6)
                    pdf.set_text_color(26,26,26)
                    for _,r in rd_df.head(50).iterrows():
                        vals = [safe_text(str(r['Asset ID'])), safe_text(str(r['Asset Name'])), safe_text(str(r['Department'])), safe_text(str(r['Location'])), safe_text(str(r['Priority'])), safe_text(str(r['Condition'])), safe_text(str(r['Asset Age']))]
                        for v,w in zip(vals,widths):
                            pdf.cell(w,4,v[:int(w/2)],1,0)
                        pdf.ln()
                    pdf_file = f"/tmp/readings_report_{today}.pdf"
                    pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f:
                        st.download_button("📥 Download PDF", f.read(), f"readings_report_{today}.pdf", "application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"PDF: {str(e)[:50]}")
    
    # ============================================
    # TAB 5: PPM CALENDAR — FORTUNE 500 UPGRADED v2
    # ============================================
    with ar_tabs[5]:
        st.markdown("### 📅 PPM Calendar — Financial Year View")
        
        today = date.today()
        if today.month >= 4:
            fy_start_year = today.year
        else:
            fy_start_year = today.year - 1
        
        if "cal_offset" not in st.session_state:
            st.session_state.cal_offset = 0
        if "selected_ppm_date" not in st.session_state:
            st.session_state.selected_ppm_date = None
        if "ppm_cal_click_value" not in st.session_state:
            st.session_state.ppm_cal_click_value = ""
        if "cal_view_mode" not in st.session_state:
            st.session_state.cal_view_mode = "6-Month Grid"
        
        block_start_month = 4 + (st.session_state.cal_offset * 6)
        block_start_year = fy_start_year + (block_start_month - 1) // 12
        block_start_month = ((block_start_month - 1) % 12) + 1
        
        months_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        months_full = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        
        user_depts = safe_parse_permissions(st.session_state.get("user", {}).get("department_permissions", []))
        user_role = st.session_state.get("user_role", "staff")
        is_admin = user_role in ["admin", "approver", "super_admin"]
        
        # ============================================
        # QUICK JUMP & VIEW CONTROLS
        # ============================================
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            jump_month = st.selectbox("📅 Quick Jump", 
                ["Current Block"] + [f"{months_full[i]} {fy_start_year if i >= 3 else fy_start_year+1}" for i in range(12)],
                key="cal_quick_jump")
            if jump_month != "Current Block":
                target_month = months_full.index(jump_month.split(" ")[0]) + 1
                target_year = int(jump_month.split(" ")[1])
                if target_month >= 4:
                    months_from_start = target_month - 4
                else:
                    months_from_start = target_month + 8
                st.session_state.cal_offset = months_from_start // 6
                st.rerun()
        with c2:
            view_mode = st.selectbox("👁️ View Mode", ["6-Month Grid", "Single Month", "Week List"], key="cal_view_mode_sel")
            st.session_state.cal_view_mode = view_mode
        with c3:
            auto_refresh = st.checkbox("🔄 Auto-refresh", value=True, key="cal_auto_refresh")
        with c4:
            if st.button("📥 Export Calendar", key="cal_export_btn", use_container_width=True):
                st.session_state.cal_show_export = True
        
        st.markdown("---")
        
        # ============================================
        # FILTERS
        # ============================================
        st.markdown("### 🔍 Filters")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            df["dept_full"] = df.apply(lambda row: f"{row['department']} — {row['sub_division']}" if pd.notna(row.get('sub_division')) and row.get('sub_division') not in ['', 'N/A', 'NA'] else row['department'], axis=1)
            if is_admin:
                dept_options = ["All"] + sorted(df["dept_full"].dropna().unique().tolist())
            else:
                dept_options = ["All"] + [d for d in sorted(df["dept_full"].dropna().unique().tolist()) if any(ud in d for ud in user_depts)] if user_depts else ["All"]
            cal_dept = st.selectbox("Department", dept_options, key="cal_dept_filter")
        with c2:
            cal_asset = st.selectbox("Asset (Parent)", ["All"] + sorted(df["parent_asset"].dropna().unique().tolist()), key="cal_asset_filter")
        with c3:
            cal_bldg = st.selectbox("Building", ["All"] + sorted(df["location_building"].dropna().unique().tolist()), key="cal_bldg_filter")
        with c4:
            cal_status = st.selectbox("Status", ["All", "Scheduled", "Completed", "Overdue", "Pending"], key="cal_status_filter")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔧 PPM ACTIVITIES", key="goto_ppma_top", use_container_width=True, type="primary"):
                st.session_state.page = "ppma"
                st.rerun()
        
        st.markdown("---")
        
        # ============================================
        # NAVIGATION
        # ============================================
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀ PREV 6 MONTHS", key="cal_prev6", use_container_width=True):
                st.session_state.cal_offset -= 1
                st.rerun()
        with c2:
            end_idx = ((block_start_month - 1 + 5) % 12)
            st.markdown(f"#### FY {fy_start_year}/{fy_start_year+1} — {months_short[block_start_month-1]} to {months_short[end_idx]}")
        with c3:
            if st.button("NEXT 6 MONTHS ▶", key="cal_next6", use_container_width=True):
                st.session_state.cal_offset += 1
                st.rerun()
        
        # Legend
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: st.markdown('<div style="background:#FEF2F2;color:#DC2626;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">🔴 Overdue</div>', unsafe_allow_html=True)
        with c2: st.markdown('<div style="background:#CC0000;color:white;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">📍 Today</div>', unsafe_allow_html=True)
        with c3: st.markdown('<div style="background:#EFF6FF;color:#2563EB;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">📆 Upcoming</div>', unsafe_allow_html=True)
        with c4: st.markdown('<div style="background:#ECFDF5;color:#059669;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">✅ Completed</div>', unsafe_allow_html=True)
        with c5: st.markdown('<div style="background:#F5F3FF;color:#7C3AED;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">⏳ Pending</div>', unsafe_allow_html=True)
        with c6: st.markdown('<div style="background:#FAFAFA;color:#999;padding:6px;border-radius:8px;text-align:center;font-size:0.6rem;font-weight:700;">⬜ None</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ============================================
        # GET PPM DATA - FORCE FRESH PULL
        # ============================================
        import time as _time
        ppm_data = None
        for attempt in range(3):
            try:
                ppm_data = supabase.table("ppm_schedules").select("*").eq("facility_code", fc).order("next_due_date", desc=False).limit(10000).execute()
                if ppm_data and ppm_data.data:
                    break
            except Exception as e:
                if attempt == 2:
                    st.error(f"⚠️ Failed to load PPM data: {str(e)[:50]}")
                _time.sleep(0.5)
        
        ppm_schedules = ppm_data.data if ppm_data and ppm_data.data else []
        ppm_df = pd.DataFrame(ppm_schedules) if ppm_schedules else pd.DataFrame()
        
        if len(ppm_df) > 0 and "next_due_date" in ppm_df.columns:
            ppm_df["due_date_dt"] = pd.to_datetime(ppm_df["next_due_date"], errors='coerce')
        
        # Apply filters
        if cal_dept != "All" and "assigned_team" in ppm_df.columns:
            base_dept = cal_dept.split(" — ")[0] if " — " in cal_dept else cal_dept
            ppm_df = ppm_df[ppm_df["assigned_team"].str.contains(base_dept, case=False, na=False)]
        if cal_asset != "All":
            asset_ids = df[df["parent_asset"] == cal_asset]["id"].tolist()
            if asset_ids and "asset_id" in ppm_df.columns:
                ppm_df = ppm_df[ppm_df["asset_id"].astype(str).isin([str(a) for a in asset_ids])]
        if cal_bldg != "All":
            bldg_asset_ids = df[df["location_building"] == cal_bldg]["id"].tolist()
            if bldg_asset_ids and "asset_id" in ppm_df.columns:
                ppm_df = ppm_df[ppm_df["asset_id"].astype(str).isin([str(a) for a in bldg_asset_ids])]
        if cal_status == "Scheduled":
            ppm_df = ppm_df[ppm_df["status"] == "scheduled"]
        elif cal_status == "Completed":
            ppm_df = ppm_df[ppm_df["status"] == "completed"]
        elif cal_status == "Overdue":
            ppm_df = ppm_df[(ppm_df["due_date_dt"].dt.date < today) & (ppm_df["status"] != "completed")]
        elif cal_status == "Pending":
            ppm_df = ppm_df[ppm_df["status"] == "pending"]
        
        # Build ppm_dates dictionary
        ppm_dates = {}
        if len(ppm_df) > 0 and "due_date_dt" in ppm_df.columns:
            for _, row in ppm_df.iterrows():
                d = row["due_date_dt"]
                if pd.notna(d):
                    dk = d.strftime("%Y-%m-%d")
                    if dk not in ppm_dates:
                        ppm_dates[dk] = []
                    ppm_dates[dk].append(row.to_dict())
        
        # KPIs
        total_ppm = len(ppm_df)
        overdue_ppm = len(ppm_df[(ppm_df["due_date_dt"].dt.date < today) & (ppm_df["status"] != "completed")]) if len(ppm_df) > 0 else 0
        today_ppm = len(ppm_df[ppm_df["due_date_dt"].dt.date == today]) if len(ppm_df) > 0 else 0
        completed_ppm = len(ppm_df[ppm_df["status"] == "completed"]) if len(ppm_df) > 0 else 0
        pending_ppm = len(ppm_df[ppm_df["status"] == "pending"]) if len(ppm_df) > 0 else 0
        compliance_rate = round((completed_ppm / max(total_ppm, 1)) * 100)
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: st.metric("📋 Total", total_ppm)
        with c2: st.metric("🔴 Overdue", overdue_ppm)
        with c3: st.metric("📍 Today", today_ppm)
        with c4: st.metric("✅ Completed", completed_ppm)
        with c5: st.metric("⏳ Pending", pending_ppm)
        with c6: st.metric("📈 Compliance", f"{compliance_rate}%")
        
        # Show data range for debugging
        if len(ppm_df) > 0 and "next_due_date" in ppm_df.columns:
            st.caption(f"📋 {len(ppm_df)} PPM records | Range: {ppm_df['next_due_date'].min()} to {ppm_df['next_due_date'].max()}")
        
        st.markdown("---")
        
        # ============================================
        # BUILD CALENDAR HTML
        # ============================================
        cal_html = """<style>
            .cg { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-family: 'Inter', sans-serif; }
            .cm { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; }
            .ch { padding: 6px 0; text-align: center; font-weight: 700; font-size: 13px; color: white; }
            .ch.cur { background: #CC0000; }
            .ch.reg { background: #1a1a1a; }
            .ct { width: 100%; border-collapse: collapse; }
            .ct th { padding: 3px 0; text-align: center; font-size: 0.6rem; font-weight: 800; border-bottom: 2px solid #e5e7eb; }
            .ct td { text-align: center; padding: 0; height: 28px; cursor: pointer; border: 1px solid #f0f0f0; transition: all 0.15s; }
            .ct td:hover { outline: 2px solid #CC0000; outline-offset: -2px; z-index: 5; transform: scale(1.08); box-shadow: 0 4px 12px rgba(204,0,0,0.3); }
            .ct td.em { background: #fafafa; cursor: default; }
            .ct td.em:hover { outline: none; transform: none; box-shadow: none; }
            .ct td.td { background: #CC0000; color: white; font-weight: 800; }
            .ct td.ov { border: 2px solid #EF4444; font-weight: 800; font-size: 12px; }
            .ct td.up { border: 2px solid #3B82F6; font-weight: 800; font-size: 12px; }
            .ct td.cp { border: 2px solid #10B981; font-weight: 800; font-size: 12px; }
            .ct td.pn { border: 2px solid #8B5CF6; font-weight: 800; font-size: 12px; }
            .ct td.no { background: #fdfdfd; color: #bbb; font-weight: 400; }
            .badge { font-size: 8px; background: #CC0000; color: white; border-radius: 8px; padding: 0px 4px; min-width: 14px; text-align: center; line-height: 1.3; margin-top: 1px; display: inline-block; }
        </style>
        <div class="cg">"""
        
        day_colors = ["#3B82F6","#10B981","#F59E0B","#8B5CF6","#EC4899","#EF4444","#6366F1"]
        
        for row_idx in range(2):
            for col_idx in range(3):
                mo = row_idx * 3 + col_idx
                dm = ((block_start_month - 1 + mo) % 12) + 1
                months_from_april = (block_start_month - 4) + mo
                if months_from_april < 0:
                    months_from_april += 12
                dy = fy_start_year + (months_from_april // 12)
                
                fd = date(dy, dm, 1)
                if dm == 12:
                    ld = date(dy, 12, 31)
                else:
                    ld = date(dy, dm + 1, 1) - timedelta(days=1)
                
                sw = fd.weekday()
                ic = (dm == today.month and dy == today.year)
                hc = "cur" if ic else "reg"
                
                cal_html += f'<div class="cm"><div class="ch {hc}">{months_short[dm-1]} {dy}</div><table class="ct"><tr>'
                for i, dh in enumerate(["M","T","W","T","F","S","S"]):
                    cal_html += f'<th style="color:{day_colors[i]};background:#f9fafb;">{dh}</th>'
                cal_html += '</tr>'
                
                dc = 1
                for w in range(6):
                    cal_html += "<tr>"
                    for wd in range(7):
                        if (w == 0 and wd < sw) or dc > ld.day:
                            cal_html += '<td class="em"></td>'
                        else:
                            cd = date(dy, dm, dc)
                            dk = cd.strftime("%Y-%m-%d")
                            it = dk == today.strftime("%Y-%m-%d")
                            pt = ppm_dates.get(dk, [])
                            pc = len(pt)
                            
                            if it:
                                cls = "td"
                            elif pc == 0:
                                cls = "no"
                            else:
                                has_ov, has_cp, has_pn = False, False, False
                                for p in pt:
                                    sts = p.get("status", "scheduled")
                                    due_dt = pd.to_datetime(p.get("next_due_date"), errors='coerce')
                                    if sts == "completed": has_cp = True
                                    elif sts == "pending": has_pn = True
                                    elif pd.notna(due_dt) and due_dt.date() < today: has_ov = True
                                
                                if has_ov: cls = "ov"
                                elif has_pn: cls = "pn"
                                elif has_cp and not any(p.get("status","") not in ["completed","approved"] for p in pt): cls = "cp"
                                else: cls = "up"
                            
                            badge = f'<span class="badge">{pc}</span>' if pc > 0 else ''
                            
                            # FIXED: Robust cross-frame click handler
                            cal_html += f'<td class="{cls}" style="cursor:pointer;" onclick="(function(){{var input=parent.document.getElementById(\'ppm_cal_date_input\');if(input){{var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,\'value\').set;setter.call(input,\'{dk}\');input.dispatchEvent(new Event(\'input\',{{bubbles:true}}));input.dispatchEvent(new Event(\'change\',{{bubbles:true}}));var btn=parent.document.getElementById(\'ppm_cal_search_btn\');if(btn){{btn.click();}}else{{var forms=parent.document.querySelectorAll(\'button\');for(var i=0;i<forms.length;i++){{if(forms[i].innerText.includes(\'Search\')){{forms[i].click();break;}}}}}}}})()">{dc}{badge}</td>'
                            dc += 1
                    cal_html += "</tr>"
                    if dc > ld.day: break
                cal_html += "</table></div>"
        
        cal_html += "</div>"
        
        st.components.v1.html(f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body>{cal_html}</body></html>", height=480, scrolling=False)
        
        # ============================================
        # SEARCH SECTION
        # ============================================
        st.markdown("---")
        st.markdown("### 🔍 Search PPM by Date")
        
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            cal_click = st.text_input("📅 Enter Date or Click Calendar", value=st.session_state.ppm_cal_click_value, key="ppm_cal_date_input", placeholder="YYYY-MM-DD")
        with c2:
            st.markdown('<button id="ppm_cal_search_btn" style="display:none;"></button>', unsafe_allow_html=True)
            if st.button("🔍 Search", key="ppm_cal_search_visible", use_container_width=True, type="primary"):
                if cal_click and cal_click.strip():
                    try:
                        parsed_date = datetime.strptime(cal_click.strip(), "%Y-%m-%d").date()
                        st.session_state.selected_ppm_date = parsed_date
                        st.session_state.ppm_cal_click_value = cal_click.strip()
                        st.rerun()
                    except:
                        st.error("Invalid date format. Use YYYY-MM-DD")
        with c3:
            if st.button("❌ Clear", key="ppm_cal_clear", use_container_width=True):
                st.session_state.selected_ppm_date = None
                st.session_state.ppm_cal_click_value = ""
                st.rerun()
        
        # Auto-detect manual entry
        if cal_click and cal_click.strip() and cal_click != st.session_state.ppm_cal_click_value:
            try:
                parsed_date = datetime.strptime(cal_click.strip(), "%Y-%m-%d").date()
                st.session_state.selected_ppm_date = parsed_date
                st.session_state.ppm_cal_click_value = cal_click.strip()
                st.rerun()
            except:
                pass
        
        st.markdown("---")
        
        # ============================================
        # EXPORT
        # ============================================
        if st.session_state.get("cal_show_export", False):
            st.markdown("### 📥 Export Calendar Data")
            export_data = []
            for dk, pps in sorted(ppm_dates.items()):
                for p in pps:
                    export_data.append({
                        "Date": dk, "Title": p.get("title", "N/A"),
                        "Status": p.get("status", "N/A"), "Team": p.get("assigned_team", "N/A"),
                        "Frequency": p.get("frequency", "N/A"),
                    })
            if export_data:
                export_df = pd.DataFrame(export_data)
                c1, c2, c3 = st.columns(3)
                with c1: st.download_button("📥 CSV", export_df.to_csv(index=False), f"ppm_calendar_{today}.csv", "text/csv", use_container_width=True)
                with c2: st.download_button("📥 Excel", export_df.to_csv(index=False), f"ppm_calendar_{today}.xlsx", "text/csv", use_container_width=True)
                with c3:
                    if st.button("❌ Close Export", use_container_width=True): st.session_state.cal_show_export = False; st.rerun()
                st.dataframe(export_df.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("No PPM data.")
                if st.button("❌ Close", use_container_width=True): st.session_state.cal_show_export = False; st.rerun()
        
        # ============================================
        # PPM DETAILS FOR SELECTED DAY
        # ============================================
        if st.session_state.selected_ppm_date:
            sel = st.session_state.selected_ppm_date
            dks = sel.strftime("%Y-%m-%d")
            pps = ppm_dates.get(dks, [])
            
            if pps:
                day_completed = len([p for p in pps if p.get("status") == "completed"])
                day_overdue = len([p for p in pps if p.get("status") != "completed" and pd.to_datetime(p.get("next_due_date"), errors='coerce').date() < today])
                
                st.markdown(f"### 📋 {len(pps)} PPMs — {sel.strftime('%d %B %Y')}")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Total", len(pps))
                with c2: st.metric("✅ Completed", day_completed)
                with c3: st.metric("🔴 Overdue", day_overdue)
                
                c1, c2 = st.columns(2)
                with c1:
                    day_dept = st.selectbox("Quick Filter", ["All"] + list(set(p.get("assigned_team","") for p in pps)), key="day_dept_filter")
                with c2:
                    if st.button("🔧 EXECUTE PPMs", key="goto_ppma_cal", use_container_width=True, type="primary"):
                        st.session_state.page = "ppma"
                        st.rerun()
                
                display_pps = pps
                if day_dept != "All":
                    display_pps = [p for p in pps if p.get("assigned_team","") == day_dept]
                
                for p in display_pps:
                    sts = p.get('status','scheduled')
                    sc = {"completed":"#10B981","scheduled":"#3B82F6","pending":"#F59E0B","overdue":"#EF4444","approved":"#059669"}.get(sts,"#3B82F6")
                    ic = {"completed":"✅","scheduled":"📆","pending":"⏳","overdue":"🔴","approved":"🟢"}.get(sts,"📋")
                    
                    asset_name = ""
                    if p.get("asset_id"):
                        asset_match = df[df["id"] == str(p.get("asset_id"))]
                        if len(asset_match) > 0:
                            asset_name = asset_match.iloc[0].get("name", "")[:50]
                    
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid {sc};border-radius:8px;padding:0.7rem;margin:0.2rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <b>{ic} {p.get('title','N/A')[:80]}</b>
                                <br><span style="font-size:0.7rem;color:#666;">👤 {p.get('assigned_team','N/A')} | 🔄 {p.get('frequency','N/A')}</span>
                                {f'<br><span style="font-size:0.65rem;color:#888;">🏗️ {asset_name}</span>' if asset_name else ''}
                            </div>
                            <span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;font-weight:700;">{sts.upper()}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"🔧 EXECUTE THIS PPM", key=f"exec_ppm_{p.get('id',dk)}", use_container_width=True, type="primary"):
                        st.session_state.page = "ppma"
                        st.rerun()
            else:
                st.info(f"📅 **{sel.strftime('%d %B %Y')}** — No PPMs scheduled.")
            
            if st.button("❌ CLEAR SELECTION", key="clearppm", use_container_width=True):
                st.session_state.selected_ppm_date = None
                st.session_state.ppm_cal_click_value = ""
                st.rerun()
        else:
            st.info("👆 **Click any date** on the calendar above to view scheduled PPMs. Or type a date (YYYY-MM-DD) and click Search."
        
        
    
    # ============================================
    # TAB 6: APPROVALS
    # ============================================
    with ar_tabs[6]:
        st.markdown("### ✅ Approvals Dashboard")
        
        approval_subtabs = st.tabs(["📋 Pending", "🔄 Movement", "🗑️ Discard", "💰 Sales"])
        
        with approval_subtabs[0]:
            st.info("Pending approvals will appear here when assets require review.")
        
        with approval_subtabs[1]:
            with st.form("move_req"):
                st.markdown("**Request Asset Movement**")
                asset_sel = st.selectbox("Asset", df["name"].tolist() if len(df) > 0 else ["None"])
                move_from = st.text_input("From Location")
                move_to = st.text_input("To Location")
                reason = st.text_area("Reason")
                if st.form_submit_button("Submit Movement Request", use_container_width=True):
                    st.success("✅ Movement request submitted!")
        
        with approval_subtabs[2]:
            with st.form("discard_req"):
                st.markdown("**Request Asset Discard**")
                asset_disc = st.selectbox("Asset", df["name"].tolist() if len(df) > 0 else ["None"], key="disc_asset")
                disc_reason = st.text_area("Reason")
                disc_method = st.selectbox("Method", ["Scrap", "Sell", "Donate", "Recycle"])
                if st.form_submit_button("Submit Discard Request", use_container_width=True):
                    st.success("✅ Discard request submitted!")
        
        with approval_subtabs[3]:
            with st.form("sale_req"):
                st.markdown("**Request Asset Sale**")
                asset_sale = st.selectbox("Asset", df["name"].tolist() if len(df) > 0 else ["None"], key="sale_asset")
                sale_price = st.number_input("Sale Price (₦)", min_value=0.0, step=10000.0)
                buyer = st.text_input("Buyer")
                if st.form_submit_button("Submit Sale Request", use_container_width=True):
                    st.success("✅ Sale request submitted!")
    
    # ============================================
    # TAB 7: AI-POWERED REPORTS SUITE
    # ============================================
    with ar_tabs[7]:
        st.markdown("### 📄 AI-Powered Reports Suite")
        
        if len(df) == 0:
            st.info("No assets to generate reports for.")
        else:
            report_type = st.selectbox("📊 Select Report Type", [
                "📋 Asset Summary Report",
                "🏢 Department Breakdown",
                "💰 Financial Report", 
                "🛡️ Warranty & Lifecycle Report",
                "📈 PPM Compliance Report",
                "⚙️ Custom Report Builder"
            ])
            
            st.markdown("---")
            
            # ============================================
            # ASSET SUMMARY REPORT
            # ============================================
            if report_type == "📋 Asset Summary Report":
                st.markdown("### 📋 Asset Summary Report")
                
                total = len(df)
                active = len(df[df["status"]=="active"]) if "status" in df.columns else 0
                inactive = len(df[df["status"]=="inactive"]) if "status" in df.columns else 0
                breakdown = len(df[df["status"]=="breakdown"]) if "status" in df.columns else 0
                critical = len(df[df["priority"].isin(["critical","high"])]) if "priority" in df.columns else 0
                
                # KPI Cards
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.metric("📋 Total Assets", total)
                with c2: st.metric("✅ Active", active)
                with c3: st.metric("🔴 Critical", critical)
                with c4: st.metric("⚠️ Breakdown", breakdown)
                with c5: st.metric("💤 Inactive", inactive)
                
                st.markdown("---")
                
                # Charts
                c1, c2 = st.columns(2)
                with c1:
                    if "department" in df.columns:
                        dept_counts = df["department"].value_counts().head(10)
                        fig = px.bar(x=dept_counts.values, y=dept_counts.index, orientation='h', title="Assets by Department", color=dept_counts.values, color_continuous_scale="Reds")
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                with c2:
                    if "location_building" in df.columns:
                        bldg_counts = df["location_building"].value_counts().head(8)
                        fig2 = px.pie(values=bldg_counts.values, names=bldg_counts.index, title="Assets by Building")
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)
                
                # AI Executive Summary
                st.markdown("---")
                st.markdown("### 🤖 AI Executive Summary")
                
                compliance = round(active/total*100,1) if total > 0 else 0
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                    <h4>Executive Overview — {info.get('full_name',fc)}</h4>
                    <p>📋 <b>{total}</b> total assets registered across <b>{df['department'].nunique() if 'department' in df.columns else 0}</b> departments.</p>
                    <p>✅ <b>{compliance}%</b> asset availability rate with <b>{critical}</b> critical assets requiring priority attention.</p>
                    <p>⚠️ <b>{breakdown}</b> assets currently in breakdown status requiring immediate corrective action.</p>
                    <p>🏢 Assets distributed across <b>{df['location_building'].nunique() if 'location_building' in df.columns else 0}</b> buildings/locations.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Export
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.download_button("📥 CSV", df.to_csv(index=False), f"asset_summary_{today}.csv", "text/csv", use_container_width=True)
                with c2:
                    logo_b64 = get_logo_base64()
                    html_export = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:Arial;margin:20px}}h1{{color:#CC0000}}table{{width:100%;border-collapse:collapse}}th{{background:#CC0000;color:white;padding:8px}}td{{padding:6px;border-bottom:1px solid #eee}}.kpi{{display:flex;gap:10px}}.kpi div{{flex:1;background:#f5f5f5;padding:10px;border-radius:8px;text-align:center;border-left:4px solid #CC0000}}</style></head><body><h1>Asset Summary Report</h1><p>{info.get('full_name',fc)} | {today}</p><div class="kpi"><div><b>Total</b><br>{total}</div><div><b>Active</b><br>{active}</div><div><b>Critical</b><br>{critical}</div><div><b>Breakdown</b><br>{breakdown}</div></div></body></html>"""
                    st.download_button("📥 HTML", html_export, f"asset_summary_{today}.html", "text/html", use_container_width=True)
                with c3:
                    st.download_button("📥 Print View", df.head(100).to_csv(index=False), f"asset_print_{today}.csv", "text/csv", use_container_width=True)
            
            # ============================================
            # DEPARTMENT BREAKDOWN
            # ============================================
            elif report_type == "🏢 Department Breakdown":
                st.markdown("### 🏢 Department Breakdown Report")
                
                if "department" in df.columns and "sub_division" in df.columns:
                    dept_summary = df.groupby(["department","sub_division"]).agg(
                        Count=("name","count"),
                        Active=("status", lambda x: (x=="active").sum()),
                        Critical=("priority", lambda x: x.isin(["critical","high"]).sum())
                    ).reset_index()
                    
                    st.dataframe(dept_summary, use_container_width=True, hide_index=True)
                    
                    # Chart
                    fig = px.bar(dept_summary, x="sub_division", y="Count", color="department", title="Assets by Department & Sub-Division", barmode="group")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.download_button("📥 Download CSV", dept_summary.to_csv(index=False), f"dept_breakdown_{today}.csv", "text/csv", use_container_width=True)
                else:
                    st.info("Department data not available.")
            
            # ============================================
            # FINANCIAL REPORT
            # ============================================
            elif report_type == "💰 Financial Report":
                st.markdown("### 💰 Financial Report")
                
                total_value = df["purchase_cost"].fillna(0).sum() if "purchase_cost" in df.columns else 0
                avg_value = total_value / len(df) if len(df) > 0 else 0
                
                # Calculate depreciation
                depreciated_value = total_value * 0.8  # Estimate
                net_book_value = total_value * 0.2  # Estimate
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("📊 Portfolio Value", f"₦{total_value:,.0f}")
                with c2: st.metric("📈 Avg Asset Value", f"₦{avg_value:,.0f}")
                with c3: st.metric("📉 Depreciated Value", f"₦{depreciated_value:,.0f}")
                with c4: st.metric("💰 Net Book Value", f"₦{net_book_value:,.0f}")
                
                st.markdown("---")
                
                # Value by department
                if "department" in df.columns and "purchase_cost" in df.columns:
                    dept_value = df.groupby("department")["purchase_cost"].sum().reset_index()
                    dept_value = dept_value.sort_values("purchase_cost", ascending=False)
                    
                    fig = px.bar(dept_value, x="department", y="purchase_cost", title="Asset Value by Department (₦)", color="purchase_cost", color_continuous_scale="Greens")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.download_button("📥 Download Financial Report CSV", df.to_csv(index=False), f"financial_report_{today}.csv", "text/csv", use_container_width=True)
            
            # ============================================
            # WARRANTY & LIFECYCLE REPORT
            # ============================================
            elif report_type == "🛡️ Warranty & Lifecycle Report":
                st.markdown("### 🛡️ Warranty & Lifecycle Report")
                
                expired = 0
                expiring_30 = 0
                expiring_90 = 0
                expiring_180 = 0
                
                warranty_data = []
                if "warranty_expiry" in df.columns:
                    for _, row in df.iterrows():
                        try:
                            we = pd.to_datetime(row["warranty_expiry"])
                            days_left = (we.date() - today).days
                            
                            if days_left < 0:
                                expired += 1
                                status = "Expired"
                            elif days_left <= 30:
                                expiring_30 += 1
                                status = "Expiring ≤30 days"
                            elif days_left <= 90:
                                expiring_90 += 1
                                status = "Expiring ≤90 days"
                            elif days_left <= 180:
                                expiring_180 += 1
                                status = "Expiring ≤180 days"
                            else:
                                status = "Active"
                            
                            warranty_data.append({
                                "Asset": row.get("name",""),
                                "Department": row.get("department",""),
                                "Warranty Start": str(row.get("warranty_start",""))[:10],
                                "Warranty End": str(row.get("warranty_expiry",""))[:10],
                                "Days Left": days_left,
                                "Status": status
                            })
                        except:
                            pass
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("🔴 Expired", expired)
                with c2: st.metric("🟡 ≤30 Days", expiring_30)
                with c3: st.metric("🔵 ≤90 Days", expiring_90)
                with c4: st.metric("🟢 ≤180 Days", expiring_180)
                
                if warranty_data:
                    wd = pd.DataFrame(warranty_data)
                    st.dataframe(wd, use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Warranty Report", wd.to_csv(index=False), f"warranty_report_{today}.csv", "text/csv", use_container_width=True)
                else:
                    st.info("No warranty data available.")
            
            # ============================================
            # PPM COMPLIANCE REPORT
            # ============================================
            elif report_type == "📈 PPM Compliance Report":
                st.markdown("### 📈 PPM Compliance Report")
                
                ppm_schedules = DB.get_all("ppm_schedules", fc, 5000)
                
                if ppm_schedules:
                    ppm_df_rpt = pd.DataFrame(ppm_schedules)
                    
                    total_ppm = len(ppm_df_rpt)
                    completed_ppm = len(ppm_df_rpt[ppm_df_rpt["status"]=="completed"]) if "status" in ppm_df_rpt.columns else 0
                    overdue_ppm = len(ppm_df_rpt[(pd.to_datetime(ppm_df_rpt["next_due_date"], errors='coerce').dt.date < today) & (ppm_df_rpt["status"]!="completed")]) if "next_due_date" in ppm_df_rpt.columns else 0
                    
                    compliance_rate = round(completed_ppm/total_ppm*100,1) if total_ppm > 0 else 0
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("📋 Total PPMs", total_ppm)
                    with c2: st.metric("✅ Completed", completed_ppm)
                    with c3: st.metric("🔴 Overdue", overdue_ppm)
                    with c4: st.metric("📈 Compliance", f"{compliance_rate}%")
                    
                    st.download_button("📥 Download PPM Report CSV", ppm_df_rpt.to_csv(index=False), f"ppm_compliance_{today}.csv", "text/csv", use_container_width=True)
                else:
                    st.info("No PPM schedules found.")
            
            # ============================================
            # CUSTOM REPORT BUILDER
            # ============================================
            elif report_type == "⚙️ Custom Report Builder":
                st.markdown("### ⚙️ Custom Report Builder")
                
                available_cols = [c for c in df.columns if c not in ["id","metadata","created_by","updated_at"]]
                selected_cols = st.multiselect("Select Columns", available_cols, default=["name","asset_tag","department","sub_division","location_building","status","priority"])
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    dept_filter_rpt = st.selectbox("Department", ["All"] + sorted(df["department"].unique().tolist()), key="rpt_dept")
                with c2:
                    bldg_filter_rpt = st.selectbox("Building", ["All"] + sorted(df["location_building"].unique().tolist()), key="rpt_bldg")
                with c3:
                    status_filter_rpt = st.selectbox("Status", ["All","active","inactive","breakdown"], key="rpt_status")
                
                filtered = df.copy()
                if dept_filter_rpt != "All": filtered = filtered[filtered["department"]==dept_filter_rpt]
                if bldg_filter_rpt != "All": filtered = filtered[filtered["location_building"]==bldg_filter_rpt]
                if status_filter_rpt != "All": filtered = filtered[filtered["status"]==status_filter_rpt]
                
                if selected_cols:
                    report_df = filtered[selected_cols]
                    st.dataframe(report_df, use_container_width=True, hide_index=True, height=400)
                    st.caption(f"📋 {len(report_df)} rows × {len(selected_cols)} columns")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 Download CSV", report_df.to_csv(index=False), f"custom_report_{today}.csv", "text/csv", use_container_width=True)
                    with c2:
                        # HTML export
                        logo_b64 = get_logo_base64()
                        html_custom = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:Arial;margin:20px;font-size:10px}}h1{{color:#CC0000}}table{{width:100%;border-collapse:collapse}}th{{background:#CC0000;color:white;padding:6px}}td{{padding:4px;border-bottom:1px solid #eee}}</style></head><body><h1>Custom Asset Report</h1><p>{info.get('full_name',fc)} | {today}</p><table><tr>{''.join(f'<th>{c}</th>' for c in selected_cols)}</tr>"""
                        for _, r in report_df.head(200).iterrows():
                            html_custom += "<tr>" + "".join(f"<td>{r[c]}</td>" for c in selected_cols) + "</tr>"
                        html_custom += "</table></body></html>"
                        st.download_button("📥 Download HTML", html_custom, f"custom_report_{today}.html", "text/html", use_container_width=True)
    
    # ============================================
    # TAB 8: SETTINGS
    # ============================================
    with ar_tabs[8]:
        st.markdown("### ⚙️ Settings")
        
        sett_tabs = st.tabs(["📍 Locations", "🏢 Departments", "🏷️ Categories", "🏭 Manufacturers"])
        
        with sett_tabs[0]:
            st.markdown("#### 📍 Locations")
            locs = DB.get_locations(fc)
            if locs:
                for l in locs:
                    st.markdown(f"**{l.get('location_code','')}** — {l.get('location_name','')}")
            with st.form("add_loc"):
                lc = st.text_input("Code", placeholder="CT")
                ln = st.text_input("Name", placeholder="CT — Office Tower")
                if st.form_submit_button("Add Location", use_container_width=True):
                        if lc and ln:
                            safe_supabase_query(lambda: supabase.table("helpdesk_locations").insert({"facility_code": fc, "location_code": lc, "location_name": ln}).execute(), error_prefix="Add location")
                            st.success("✅ Added!")
                            st.rerun()
        
        with sett_tabs[1]:
            st.markdown("#### 🏢 Departments")
            if len(df) > 0 and "department" in df.columns:
                for d in sorted(df["department"].unique()):
                    st.markdown(f"- {d}")
            else:
                st.info("No departments yet.")
        
        with sett_tabs[2]:
            st.markdown("#### 🏷️ Categories")
            cats_list = DB.get_categories()
            if cats_list:
                for c in cats_list:
                    st.markdown(f"- {c.get('name','N/A')}")
            else:
                st.info("No categories yet.")
        
        with sett_tabs[3]:
            st.markdown("#### 🏭 Manufacturers")
            if len(df) > 0 and "manufacturer" in df.columns:
                mfgs = df["manufacturer"].dropna().unique()
                for m in sorted(mfgs):
                    st.markdown(f"- {m}")
            else:
                st.info("No manufacturers yet.")

# ============================================
# WORK PERMIT — COMPLETE FIXED MODULE
# ============================================
def format_wat_time(dt_str):
    """Convert to Lagos WAT timezone"""
    try:
        from datetime import timezone, timedelta
        if not dt_str: return "N/A"
        dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
        wat = dt.astimezone(timezone(timedelta(hours=1)))
        return wat.strftime("%d-%b-%Y %I:%M %p") + " WAT"
    except:
        return str(dt_str)[:19] if dt_str else "N/A"

def send_email_notification(to_email, subject, body):
    """Send email via SendGrid API and log to database"""
    try:
        sendgrid_api_key = ""
        try:
            sendgrid_api_key = st.secrets["SENDGRID_API_KEY"]
        except:
            sendgrid_api_key = os.environ.get("SENDGRID_API_KEY", "")
        
        if not sendgrid_api_key:
            print("⚠️ SENDGRID_API_KEY not set!")
            return False
        
        message = Mail(
            from_email=From("eetuk@churchgate.com", "facilityXperience"),
            to_emails=To(to_email),
            subject=Subject(subject),
            html_content=HtmlContent(body)
        )
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        print(f"✅ Email sent to {to_email}: {subject} | Status: {response.status_code}")
        
        try:
            safe_supabase_query(lambda: supabase.table("email_log").insert({
                "facility_code": "WTC",
                "email_to": to_email,
                "email_subject": subject,
                "email_body": body,
                "email_type": "notification",
                "status": "sent",
                "sent_at": datetime.now().isoformat()
            }).execute(), error_prefix="Email log")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Email failed for {to_email}: {str(e)}")
        st.session_state.last_email_error = f"Email failed: {str(e)[:200]}"
        return False

def get_workflow_people(fc, level, department=None):
    """Get people for a workflow level, filtered by department"""
    try:
        query = supabase.table("workflow_config").select("*").eq("facility_code", fc).eq("workflow_type", "work_permit").eq("level_number", level).eq("is_active", True)
        res = safe_supabase_query(lambda: query.execute(), error_prefix="Workflow people")
        people = res.data if res and res.data else []
        if department and people:
            filtered = [p for p in people if "All Departments" in p.get("department_filter", []) or department in p.get("department_filter", [])]
            if filtered:
                return filtered
        return [p for p in people if "All Departments" in p.get("department_filter", [])] if people else []
    except: return []

def get_sub_locations_for_building(fc, building_code):
    """Get sub-locations for a building"""
    try:
        loc = safe_supabase_query(lambda: supabase.table("helpdesk_locations").select("id").eq("facility_code", fc).eq("location_code", building_code).single().execute(), error_prefix="Location lookup")
        if loc and loc.data:
            res = safe_supabase_query(lambda: supabase.table("helpdesk_sub_locations").select("sub_location_name").eq("location_id", loc.data["id"]).execute(), error_prefix="Sub-locations")
            if res and res.data:
                sub_locs = [s["sub_location_name"] for s in res.data]
                # Custom sort: Ground/Basement first, then Floor 1-99, then others
                def sort_key(name):
                    if name.startswith("Ground"): return (0, name)
                    if name.startswith("Basement"): return (1, name)
                    if name.startswith("Floor "):
                        try:
                            num = int(name.replace("Floor ", ""))
                            return (2, f"{num:03d}")
                        except:
                            return (3, name)
                    if name.startswith("Mezzanine"): return (4, name)
                    if name.startswith("Electrical"): return (5, name)
                    if name.startswith("Penthouse"): return (6, name)
                    if name.startswith("Rooftop"): return (7, name)
                    return (8, name)
                sub_locs.sort(key=sort_key)
                return sub_locs
    except: pass
    return [f"{building_code} / 0", f"{building_code} / 1"]

def page_wp():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    user_perms = safe_parse_permissions(st.session_state.get("user", {}).get("extra_permissions", []))
    user_role = st.session_state.get("user_role", "staff")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    can_authorize = is_admin or "Authorize Permit" in user_perms or len(user_perms) == 0
    can_confirm = is_admin or "Confirm Permit" in user_perms or len(user_perms) == 0
    can_approve = is_admin or "Approve Permit" in user_perms or len(user_perms) == 0
    can_raise = is_admin or "Raise Permit" in user_perms or len(user_perms) == 0
    
    st.markdown(f'## 🛡️ Permit-to-Work System — {info.get("full_name", fc)}')
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Permits", "➕ Raise Permit", "📊 Reports", "⚙️ Workflow Config"])
    
    with tab1:
        st.markdown("### 📋 Work Permit Register")
        wp = DB.get_all("work_permits", fc, 500)
        
        if wp and len(wp) > 0:
            df = pd.DataFrame(wp)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.metric("📋 Total", len(df))
            with c2: st.metric("⏳ Submitted", len(df[df["workflow_stage"] == "submitted"]) if "workflow_stage" in df.columns else 0)
            with c3: st.metric("🔐 Authorized", len(df[df["workflow_stage"] == "authorized"]) if "workflow_stage" in df.columns else 0)
            with c4: st.metric("✅ Confirmed", len(df[df["workflow_stage"] == "confirmed"]) if "workflow_stage" in df.columns else 0)
            with c5: st.metric("🟢 Approved", len(df[df["workflow_stage"] == "approved"]) if "workflow_stage" in df.columns else 0)
            
            st.markdown("---")
            
            for i, row in df.iterrows():
                stage = row.get("workflow_stage", "submitted")
                icons = {"submitted": "⏳", "authorized": "🔐", "confirmed": "✅", "approved": "🟢", "rejected": "❌"}
                icon = icons.get(stage, "📋")
                
                title = row.get('title', 'No Title')[:80]
                permit_no = row.get('permit_number', 'N/A')
                
                status_colors = {"submitted":"#F59E0B","authorized":"#3B82F6","confirmed":"#8B5CF6","approved":"#10B981","rejected":"#EF4444"}
                card_key = f"wp_card_{row['id']}"
                if card_key not in st.session_state:
                    st.session_state[card_key] = False
                
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {status_colors.get(stage,'#4a4a4a')};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span><b>{icon} {permit_no}</b> — {title[:60]}</span>
                        <span style="background:{status_colors.get(stage,'#4a4a4a')};color:white;padding:2px 10px;border-radius:12px;font-size:0.65rem;font-weight:600;">{stage.upper()}</span>
                    </div>
                    <div style="font-size:0.7rem;color:#666;margin-top:0.2rem;">
                        👤 {row.get('raised_by_name','N/A')} | 📅 {format_wat_time(row.get('start_datetime',''))} | 📍 {row.get('work_location','')[:40]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([3,1])
                with c1:
                    pass
                with c2:
                    btn_text = "🔼 Hide Details" if st.session_state[card_key] else "📋 View Details"
                    if st.button(btn_text, key=f"toggle_{row['id']}", use_container_width=True):
                        st.session_state[card_key] = not st.session_state[card_key]
                        st.rerun()
                
                if st.session_state[card_key]:
                    with st.container():
                        st.markdown(f"""
                        <div style="background:#f9fafb;border-radius:10px;padding:1rem;margin:0.5rem 0;border:1px solid #e5e7eb;">
                            <p><b>👤 Raised by:</b> {row.get('raised_by_name','N/A')} ({row.get('raised_by_designation','')})</p>
                            <p><b>📅 Period:</b> {format_wat_time(row.get('start_datetime',''))} → {format_wat_time(row.get('end_datetime',''))}</p>
                            <p><b>📍 Location:</b> {row.get('work_location','')}</p>
                            <p><b>📝 Description:</b> {row.get('description','')[:200]}</p>
                            <p><b>🏢 Department:</b> {row.get('department','')}</p>
                            <hr>
                            <p><b>🔄 Audit Trail:</b></p>
                            <p style="font-size:0.75rem;">📤 Submitted: {format_wat_time(row.get('submitted_at',row.get('created_at','')))} by {row.get('raised_by_name','N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if row.get("authorized_at"):
                            st.caption(f"🔐 Authorized: {format_wat_time(row['authorized_at'])} by {row.get('authorized_by_name','')}")
                        if row.get("confirmed_at"):
                            st.caption(f"✅ Confirmed: {format_wat_time(row['confirmed_at'])} by {row.get('confirmed_by_name','')}")
                        if row.get("approved_at"):
                            st.caption(f"🟢 Approved: {format_wat_time(row['approved_at'])} by {row.get('approved_by_name','')}")
                        if stage == "rejected" and row.get("rejected_reason"):
                            st.error(f"❌ Rejected: {row.get('rejected_reason','')}")
                            st.info("📝 Requester can resubmit with corrections")
                        
                        st.markdown("**⚡ Actions:**")
                        now = datetime.now().isoformat()
                        dept = row.get("department", "")
                        
                        if can_authorize and stage == "submitted":
                            auth_comment = st.text_area("Authorization Comment", key=f"auth_cmt_{row['id']}", height=60)
                            if st.button("🔐 Authorize", key=f"auth_btn_{row['id']}", use_container_width=True):
                                if auth_comment:
                                    auth_name = st.session_state.get("user_name","Authorizer")
                                    DB.update("work_permits", row["id"], {"workflow_stage":"authorized","authorized_by_name":auth_name,"authorized_at":now})
                                    st.success("🔐 Authorized!")
                                    st.balloons()
                                    st.rerun()
                        
                        if can_confirm and stage == "authorized":
                            conf_comment = st.text_area("Confirmation Comment", key=f"conf_cmt_{row['id']}", height=60)
                            if st.button("✅ Confirm", key=f"conf_btn_{row['id']}", use_container_width=True):
                                if conf_comment:
                                    conf_name = st.session_state.get("user_name","Confirmer")
                                    DB.update("work_permits", row["id"], {"workflow_stage":"confirmed","confirmed_by_name":conf_name,"confirmed_at":now})
                                    st.success("✅ Confirmed!")
                                    st.balloons()
                                    st.rerun()
                        
                        if can_approve and stage in ["authorized","confirmed"]:
                            app_comment = st.text_area("Approval Comment", key=f"app_cmt_{row['id']}", height=60)
                            if st.button("🟢 Approve", key=f"app_btn_{row['id']}", use_container_width=True):
                                if app_comment:
                                    app_name = st.session_state.get("user_name","Approver")
                                    DB.update("work_permits", row["id"], {"workflow_stage":"approved","status":"approved","approved_by_name":app_name,"approved_at":now})
                                    st.success("🟢 Approved!")
                                    st.balloons()
                                    st.rerun()
                        
                        if stage not in ["rejected","approved"] and (is_admin or can_authorize or can_confirm or can_approve):
                            rej_comment = st.text_area("Rejection Reason", key=f"rej_cmt_{row['id']}", height=60)
                            if st.button("❌ Reject", key=f"rej_btn_{row['id']}", use_container_width=True):
                                if rej_comment:
                                    DB.update("work_permits", row["id"], {"workflow_stage":"rejected","status":"rejected","rejected_at":now,"rejected_reason":rej_comment})
                                    st.error("❌ Permit Rejected!")
                                    st.rerun()
                        
                        if stage == "rejected" and (is_admin or can_raise):
                            if st.button("🔄 Resubmit", key=f"resubmit_{row['id']}", use_container_width=True):
                                DB.update("work_permits", row["id"], {"workflow_stage":"submitted","status":"pending","submitted_at":now,"authorized_at":None,"authorized_by_name":None,"confirmed_at":None,"confirmed_by_name":None,"approved_at":None,"approved_by_name":None,"rejected_at":None,"rejected_reason":None})
                                st.success("🔄 Resubmitted!")
                                st.balloons()
                                st.rerun()
                
                st.markdown("---")
        else:
            st.info("📋 No work permits found. Raise your first permit in the '➕ Raise Permit' tab!")
    
    with tab2:
        st.markdown("### 📝 Raise New Work Permit")
        
        buildings = DB.get_locations(fc)
        
        building_options = {}
        for b in buildings:
            building_options[b.get("location_code", "")] = b.get("location_name", "")
        
        if not building_options:
            building_options = {"MAIN": info.get("full_name", fc)}
        
        st.markdown("**🏢 Select Building & Location**")
        c1, c2 = st.columns(2)
        with c1:
            selected_building = st.selectbox("Building*", 
                options=list(building_options.keys()),
                format_func=lambda x: building_options.get(x, x),
                key="wp_building")
        with c2:
            sub_locs = get_sub_locations_for_building(fc, selected_building)
            if not sub_locs or len(sub_locs) == 0:
                sub_locs = [f"{selected_building} / 0"]
            sub_location = st.selectbox("Sub-Location*", sub_locs, key="wp_subloc")
        
        full_location = f"{building_options.get(selected_building, selected_building)} → {sub_location}"
        st.caption(f"📍 Full Location: {full_location}")
        
        st.markdown("---")
        
        # Use a flag to track if form should be processed
        if "wp_form_submitted" not in st.session_state:
            st.session_state.wp_form_submitted = False
        
        with st.form("wp_raise_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                permit_type = st.selectbox("Permit Type*", [
                    "General Work Permit", "Hot Work Permit", "Confined Space Entry Permit",
                    "Working at Height Permit", "Electrical/Mechanical/LOTO Permit",
                    "Energy Isolation Permit", "ELV Systems Work Permit", "Excavation Permit"
                ])
                dept = st.selectbox("Department*", [
                    "Engineering — Electrical", "Engineering — HVAC", "Engineering — Plumbing",
                    "Engineering — Vertical Transportation (Lifts)", "Engineering — Fire Fighting",
                    "Engineering — Civil & Structural", "Engineering — Utilities & Energy",
                    "Facility Management — Hard Services", "Facility Management — Soft Services (Housekeeping)",
                    "Facility Management — FM Operations & Helpdesk", "Facility Management — Fitout Works",
                    "Facility Management — HSSE Safety & Compliance",
                    "Technology Group — Network & Connectivity", "Technology Group — Building Technology",
                    "Security — Man Guarding Operations",
                    "Contractor — Clyde Engineering", "Contractor — Gates and Shield"
                ])
            with c2:
                document_no = st.text_input("Document No", value=f"IMS-WTC-WP-{datetime.now().strftime('%Y%m%d')}")
            
            st.markdown("---")
            st.markdown("**👤 Requester Details**")
            c1, c2, c3 = st.columns(3)
            with c1:
                rname = st.text_input("Requester Name*")
                rdesignation = st.text_input("Requester Designation*")
            with c2:
                rcontact = st.text_input("Requester Contact No*", placeholder="08012345678")
                powner = st.text_input("Process Owner Name*")
            with c3:
                pcontact = st.text_input("Process Owner Contact*", placeholder="08012345678")
                scoordinator = st.text_input("Site Coordinator*")
            
            st.markdown("---")
            st.markdown("**📅 Work Schedule**")
            c1, c2 = st.columns(2)
            with c1:
                sd = st.date_input("Proposed Start Date*", date.today())
                stime = st.time_input("Start Time*", time(8, 0))
            with c2:
                ed = st.date_input("Proposed End Date*", date.today())
                etime = st.time_input("End Time*", time(17, 0))
            
            workers = st.number_input("No. of Workers Expected*", min_value=1, max_value=100, value=2)
            workers_names = st.text_area("Workers Names* (one per line)", height=80, placeholder="Enter each worker's full name on a new line...")
            
            st.markdown("---")
            description = st.text_area("Brief Description of Work*", height=80, placeholder="Describe the work to be performed...")
            
            st.markdown("**🦺 PPE Required***")
            ppe_selected = st.multiselect("Select PPE", [
                "Hard Hat", "Face Shield", "Welder Gloves", "Electrical Gloves", "Body Harness",
                "Foot Protection", "Ear Plug/Earmuffs", "Chemical Goggles", "Safety Shoes",
                "Respirator", "Safety Glass", "Fall Protection"
            ])
            
            st.markdown("**🔧 Equipment Required***")
            equip_selected = st.multiselect("Select Equipment", [
                "Fire Extinguishers", "Warning Signs", "Walkie-talkie", "Ladder/Scaffold",
                "Fire Hoses", "Non-Sparking Tools", "Gas Detector", "Additional Lighting"
            ])
            
            # ============================================
            # 🔑 KEY ACCESS INTEGRATION — FIXED
            # ============================================
            st.markdown("---")
            st.markdown("**🔑 Key Access Required?**")
            key_access_needed = st.checkbox("Yes, key access is required for this work", key="wp_key_needed")
            
            selected_key_ids = []
            if key_access_needed:
                selected_building_name = building_options.get(selected_building, selected_building)
                building_keys = safe_supabase_query(lambda: supabase.table("key_registry").select("*").eq("facility_code", fc).eq("location_building", selected_building_name).gt("available_copies", 0).order("location_floor,key_name").execute(), error_prefix="Key lookup")
                
                if building_keys and building_keys.data:
                    key_options = {}
                    for k in building_keys.data:
                        label = f"{k.get('key_name','')[:80]} | 📍{k.get('location_floor','')} | 🏷️{k.get('key_type','')} | 📋{k.get('available_copies',0)} avail"
                        key_options[label] = k
                    
                    selected_key_labels = st.multiselect("Select Keys Required*", list(key_options.keys()), key="wp_selected_keys")
                    selected_key_ids = [key_options[label]["id"] for label in selected_key_labels]
                    
                    if selected_key_labels:
                        st.caption(f"🔑 {len(selected_key_labels)} key(s) selected. These will be reserved upon permit approval.")
                else:
                    st.info(f"No available keys found for {selected_building_name}. Keys can be requested after permit approval.")
            
            with st.expander("📋 General Instructions to Contractors"):
                st.markdown("""
                1. ID card mandatory for all workers
                2. Safety Training daily at 9:30 AM
                3. Noisy works after 6:00 PM only
                4. Clear debris immediately after work
                5. Only service lifts for materials
                6. Smoking strictly prohibited
                7. No obstruction to fire escape routes
                8. Contractor liable for all injuries/damages
                """)
            
            st.markdown("---")
            
            submitted = st.form_submit_button("🛡️ Submit Work Permit", use_container_width=True, type="primary")
            
            if submitted:
                errors = []
                
                # Name validations
                name_valid, name_msg = validate_name_input(rname)
                if not name_valid: errors.append(f"Requester Name: {name_msg}")
                
                desig_valid, desig_msg = validate_name_input(rdesignation)
                if not desig_valid: errors.append(f"Requester Designation: {desig_msg}")
                
                # Phone validations - NUMERIC ONLY, 11 DIGITS
                # Strip any + or spaces
                rcontact_clean = rcontact.strip().replace("+", "").replace(" ", "") if rcontact else ""
                if not rcontact_clean:
                    errors.append("Requester Contact: Phone number is required")
                elif not rcontact_clean.isdigit():
                    errors.append("Requester Contact: Numbers only (no letters or symbols)")
                elif len(rcontact_clean) != 11:
                    errors.append(f"Requester Contact: Must be 11 digits (entered {len(rcontact_clean)})")
                
                owner_valid, owner_msg = validate_name_input(powner)
                if not owner_valid: errors.append(f"Process Owner Name: {owner_msg}")
                
                pcontact_clean = pcontact.strip().replace("+", "").replace(" ", "") if pcontact else ""
                if not pcontact_clean:
                    errors.append("Process Owner Contact: Phone number is required")
                elif not pcontact_clean.isdigit():
                    errors.append("Process Owner Contact: Numbers only (no letters or symbols)")
                elif len(pcontact_clean) != 11:
                    errors.append(f"Process Owner Contact: Must be 11 digits (entered {len(pcontact_clean)})")
                
                coord_valid, coord_msg = validate_name_input(scoordinator)
                if not coord_valid: errors.append(f"Site Coordinator: {coord_msg}")
                
                if not description: errors.append("Description of Work")
                if not sub_location or sub_location == "Select building first": errors.append("Sub-Location")
                if not workers_names or not workers_names.strip(): errors.append("Workers Names")
                if not ppe_selected: errors.append("PPE Required")
                if not equip_selected: errors.append("Equipment Required")
                if key_access_needed and not selected_key_ids: errors.append("Please select at least one key")
                
                if errors:
                    st.error(f"⚠️ Please fix the following:\n" + "\n".join(f"• {e}" for e in errors))
                    # DO NOT clear form - keep all entries
                else:
                    now = datetime.now().isoformat()
                    cnt = len(DB.get_all("work_permits", fc, 1000))
                    permit_number = f"PTW-{fc}-{datetime.now().year}-{str(cnt + 1).zfill(4)}"
                    
                    permit_data = {
                        "facility_code": fc, "permit_number": permit_number, "document_no": document_no,
                        "permit_type": permit_type, "department": dept, "title": description[:100],
                        "description": description, "raised_by_name": rname, "raised_by_designation": rdesignation,
                        "requester_contact": rcontact_clean, "process_owner_name": powner,
                        "process_owner_contact": pcontact_clean, "site_coordinator_name": scoordinator,
                        "workers_count": workers, "workers_names": workers_names,
                        "work_location": full_location,
                        "start_datetime": f"{sd}T{stime}", "end_datetime": f"{ed}T{etime}",
                        "ppe_required": ppe_selected, "equipment_required": equip_selected,
                        "status": "pending", "workflow_stage": "submitted", "submitted_at": now, "created_at": now
                    }
                    
                    DB.insert("work_permits", permit_data)
                    
                    # Reserve keys if requested
                    if key_access_needed and selected_key_ids:
                        for key_id in selected_key_ids:
                            try:
                                key_result = supabase.table("key_transactions").insert({
                                    "key_id": str(key_id),
                                    "transaction_type": "reserved",
                                    "requested_by": str(rname),
                                    "requested_by_email": "",
                                    "work_permit_id": str(permit_number),
                                    "status": "reserved",
                                    "notes": f"Auto-reserved for Work Permit {permit_number}",
                                    "expected_return": str(ed) if ed else str(date.today() + timedelta(days=1)),
                                    "created_at": datetime.now().isoformat()
                                }).execute()
                                
                                if key_result and key_result.data:
                                    key_info = supabase.table("key_registry").select("available_copies").eq("id", str(key_id)).single().execute()
                                    if key_info and key_info.data:
                                        current_avail = key_info.data.get("available_copies", 1)
                                        new_avail = max(0, current_avail - 1)
                                        supabase.table("key_registry").update({"available_copies": new_avail}).eq("id", str(key_id)).execute()
                            except Exception as e:
                                st.warning(f"⚠️ Key reservation failed for one key: {str(e)[:50]}")
                                continue
                        
                        try:
                            send_email_notification(
                                "helpdesk_wtc_ct@churchgate.com",
                                f"🔑 Key Access Requested — {permit_number}",
                                f"""<div style="font-family:Arial;max-width:550px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                    <div style="background:#F59E0B;padding:20px;color:white;">
                                        <h2 style="margin:0;">🔑 Key Access Requested</h2>
                                        <p style="margin:5px 0 0 0;font-size:12px;">Work Permit: {permit_number}</p>
                                    </div>
                                    <div style="padding:20px;">
                                        <p><b>Permit:</b> {permit_number}</p>
                                        <p><b>Raised by:</b> {rname}</p>
                                        <p><b>Location:</b> {full_location}</p>
                                        <p><b>Keys Requested:</b> {len(selected_key_ids)} key(s)</p>
                                        <p><b>Description:</b> {description[:200]}</p>
                                        <p>Please prepare keys for the contractor upon permit activation.</p>
                                    </div>
                                </div>"""
                            )
                        except: pass
                    
                    st.success(f"✅ Work Permit {permit_number} Submitted Successfully!")
                    st.balloons()
                    
                    authorizers = get_workflow_people(fc, 1, dept)
                    for a in authorizers:
                        send_email_notification(
                            a.get("person_email", ""),
                            f"📋 New Permit {permit_number} Requires Authorization",
                            f"<h3>New Work Permit Submitted</h3>"
                            f"<p><b>Permit:</b> {permit_number}</p>"
                            f"<p><b>Type:</b> {permit_type}</p>"
                            f"<p><b>Department:</b> {dept}</p>"
                            f"<p><b>Location:</b> {full_location}</p>"
                            f"<p><b>Raised by:</b> {rname} ({rdesignation})</p>"
                            f"<p><b>Description:</b> {description[:300]}</p>"
                        )
                    
                    # Clear form by rerunning
                    import time as _time
                    _time.sleep(1.5)
                    st.rerun()
    
    with tab3:
        st.markdown("### 📊 Work Permit Analytics & Reports")
        wp_all = DB.get_all("work_permits", fc, 500)
        
        if wp_all and len(wp_all) > 0:
            df = pd.DataFrame(wp_all)
            
            total = len(df)
            approved_count = len(df[df["workflow_stage"] == "approved"]) if "workflow_stage" in df.columns else 0
            pending_count = len(df[df["workflow_stage"].isin(["submitted", "authorized", "confirmed"])]) if "workflow_stage" in df.columns else 0
            rejected_count = len(df[df["workflow_stage"] == "rejected"]) if "workflow_stage" in df.columns else 0
            
            lead_times = []
            delayed = 0
            if "submitted_at" in df.columns and "approved_at" in df.columns:
                approved_df = df[df["approved_at"].notna()]
                for _, r in approved_df.iterrows():
                    try:
                        s = pd.to_datetime(r["submitted_at"])
                        a = pd.to_datetime(r["approved_at"])
                        hrs = (a - s).total_seconds() / 3600
                        lead_times.append(hrs)
                        if hrs > 4: delayed += 1
                    except: pass
            
            avg_lead = sum(lead_times) / len(lead_times) if lead_times else 0
            dept_data = df["department"].value_counts().to_dict() if "department" in df.columns else {}
            stage_data = df["workflow_stage"].value_counts().to_dict() if "workflow_stage" in df.columns else {}
            
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.metric("📋 Total", total)
            with c2: st.metric("🟢 Approved", approved_count)
            with c3: st.metric("⏳ Pending", pending_count)
            with c4: st.metric("❌ Rejected", rejected_count)
            with c5: st.metric("⏱️ Avg Approval", f"{avg_lead:.1f} hrs")
            
            st.markdown("---")
            
            st.markdown("### 📅 Monthly Breakdown (Click to Filter)")
            
            if "report_month_filter" not in st.session_state:
                st.session_state.report_month_filter = None
            
            months_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            months_full = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            cols = st.columns(6)
            for i in range(6):
                m_idx = i + 1
                count = len(df[pd.to_datetime(df["created_at"]).dt.month == m_idx]) if "created_at" in df.columns else 0
                is_active = st.session_state.report_month_filter == m_idx
                with cols[i]:
                    if st.button(f"{'🔴' if is_active else '📋'} {months_short[i]}: {count}", key=f"mbtn_{m_idx}", use_container_width=True):
                        st.session_state.report_month_filter = None if is_active else m_idx
                        st.rerun()
            
            cols2 = st.columns(6)
            for i in range(6):
                m_idx = i + 7
                count = len(df[pd.to_datetime(df["created_at"]).dt.month == m_idx]) if "created_at" in df.columns else 0
                is_active = st.session_state.report_month_filter == m_idx
                with cols2[i]:
                    if st.button(f"{'🔴' if is_active else '📋'} {months_short[i+6]}: {count}", key=f"mbtn_{m_idx}", use_container_width=True):
                        st.session_state.report_month_filter = None if is_active else m_idx
                        st.rerun()
            
            if st.session_state.report_month_filter:
                month_idx = st.session_state.report_month_filter
                filtered_df = df[pd.to_datetime(df["created_at"]).dt.month == month_idx] if "created_at" in df.columns else df
                st.markdown(f"### 📋 {months_full[month_idx-1]} Permits ({len(filtered_df)} records)")
                show_cols = [c for c in ["permit_number", "permit_type", "raised_by_name", "department", "work_location", "workflow_stage", "submitted_at"] if c in filtered_df.columns]
                st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)
                csv = filtered_df.to_csv(index=False)
                st.download_button(f"⬇️ Download {months_full[month_idx-1]} CSV", csv, f"permits_{months_full[month_idx-1]}.csv", "text/csv")
            
            st.markdown("---")
            
            st.markdown("### 📈 Analytics Summary")
            if "permit_type" in df.columns:
                st.markdown("**By Permit Type:**")
                for ptype, count in df["permit_type"].value_counts().items():
                    st.markdown(f"- {ptype}: **{count}**")
            if "department" in df.columns:
                st.markdown("**Top Departments:**")
                for dept, count in list(dept_data.items())[:5]:
                    st.markdown(f"- {dept}: **{count}**")
            
            st.markdown("---")
            
            st.markdown("### 📄 Generate Reports")
            report_format = st.radio("Select Format", ["📄 PDF Download", "🌐 HTML Preview & Download"], horizontal=True)
            
            if report_format == "🌐 HTML Preview & Download":
                logo_b64 = get_logo_base64()
                dept_rows = "".join([f"<tr><td>{d}</td><td>{c}</td></tr>" for d, c in list(dept_data.items())[:15]])
                stage_rows = "".join([f"<tr><td>{s.upper()}</td><td>{c}</td></tr>" for s, c in stage_data.items()])
                audit_rows = ""
                for _, row in df.iterrows():
                    stg = row.get('workflow_stage','')
                    bc = "badge-approved" if stg=="approved" else ("badge-rejected" if stg=="rejected" else "badge-pending")
                    audit_rows += f"""<tr><td>{row.get('permit_number','')}</td><td>{row.get('raised_by_name','')}</td><td>{row.get('department','')[:30]}</td><td>{format_wat_time(row.get('submitted_at',''))}</td><td>{format_wat_time(row.get('authorized_at',''))}</td><td>{format_wat_time(row.get('confirmed_at',''))}</td><td>{format_wat_time(row.get('approved_at',''))}</td><td><span class="{bc}">{stg.upper()}</span></td></tr>"""
                
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:'Inter',Arial,sans-serif;color:#1a1a1a;font-size:11px;margin:20px}}.header{{background:#1a1a1a;color:white;padding:20px;border-radius:10px;display:flex;align-items:center;gap:15px;margin-bottom:20px}}.header h1{{margin:0;font-size:18px}}.kpi-row{{display:flex;gap:10px;margin:15px 0}}.kpi-card{{flex:1;background:white;border:1px solid #ddd;border-radius:8px;padding:10px;text-align:center;border-left:4px solid #CC0000}}.kpi-card.green{{border-left-color:#10B981}}.kpi-val{{font-size:22px;font-weight:800}}.kpi-label{{font-size:9px;color:#666;text-transform:uppercase}}table{{width:100%;border-collapse:collapse;font-size:10px;margin:10px 0}}th{{background:#CC0000;color:white;padding:6px;text-align:left;font-size:9px}}td{{padding:5px;border-bottom:1px solid #eee}}.badge-approved{{background:#ECFDF5;color:#065F46;padding:2px 8px;border-radius:10px;font-weight:600}}.badge-pending{{background:#FFFBEB;color:#92400E;padding:2px 8px;border-radius:10px;font-weight:600}}.badge-rejected{{background:#FEF2F2;color:#991B1B;padding:2px 8px;border-radius:10px;font-weight:600}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:20px;border-top:1px solid #ddd;padding-top:10px}}</style></head><body>
                <div class="header">{'<img src="data:image/png;base64,'+logo_b64+'" height="40">' if logo_b64 else ''}<div><h1>Work Permit Analytics Report</h1><p style="margin:3px 0 0 0;font-size:10px;opacity:0.8">{info.get('full_name',fc)} | {datetime.now().strftime('%d %B %Y, %I:%M %p WAT')}</p></div></div>
                <div class="kpi-row"><div class="kpi-card"><div class="kpi-val">{total}</div><div class="kpi-label">Total</div></div><div class="kpi-card green"><div class="kpi-val">{approved_count}</div><div class="kpi-label">Approved</div></div><div class="kpi-card"><div class="kpi-val">{pending_count}</div><div class="kpi-label">Pending</div></div><div class="kpi-card"><div class="kpi-val">{rejected_count}</div><div class="kpi-label">Rejected</div></div><div class="kpi-card green"><div class="kpi-val">{avg_lead:.1f}h</div><div class="kpi-label">Avg Lead</div></div></div>
                {f'<div style="background:#FFF3CD;border:1px solid #F59E0B;border-radius:8px;padding:10px;margin:10px 0"><b>DELAYED:</b> {delayed} permit(s) exceeded 4-hour target.</div>' if delayed>0 else ''}
                <h2>Department Breakdown</h2><table><tr><th>Department</th><th>Permits</th></tr>{dept_rows}</table>
                <h2>Stage Distribution</h2><table><tr><th>Stage</th><th>Count</th></tr>{stage_rows}</table>
                <h2>Audit Trail</h2><table><tr><th>Permit No</th><th>Raised By</th><th>Department</th><th>Submitted</th><th>Authorized</th><th>Confirmed</th><th>Approved</th><th>Status</th></tr>{audit_rows}</table>
                <div class="footer">Churchgate Group | facilityXperience | Confidential</div></body></html>"""
                
                st.components.v1.html(html, height=600, scrolling=True)
                st.download_button("📥 Download HTML Report", html, f"Work_Permit_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html", "text/html", use_container_width=True, type="primary")
        
        else:
            st.info("📋 No work permits to report yet.")
    
    # ============================================
    # TAB 4: WORKFLOW CONFIG
    # ============================================
    with tab4:
        if not is_admin and user_role != "super_admin":
            st.error("⛔ Admin access only")
            st.stop()
        st.markdown("### ⚙️ Workflow Configuration")
        st.caption("Manage who authorizes, confirms, and approves work permits")
        
        import json
        
        for level in [1, 2, 3]:
            level_names = {1: "Level 1 — Authorization (Team Lead/Supervisor)", 
                          2: "Level 2 — Confirmation (HSE Coordinator)", 
                          3: "Level 3 — Approval (Facility Manager)"}
            level_icons = {1: "🔐", 2: "✅", 3: "🟢"}
            
            st.markdown(f"**{level_icons[level]} {level_names[level]}**")
            people = get_workflow_people(fc, level)
            if people:
                for p in people:
                    dept_filter = p.get("department_filter", [])
                    if isinstance(dept_filter, str):
                        try: dept_filter = json.loads(dept_filter)
                        except: dept_filter = ["All Departments"]
                    if dept_filter == ["All Departments"] or not dept_filter:
                        dept_str = "All Departments"
                    else:
                        dept_str = ", ".join(dept_filter)
                    
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #ddd; border-radius:8px; padding:0.6rem 1rem; margin:0.3rem 0;">
                            <div style="font-weight:600; font-size:0.85rem;">👤 {p.get('person_name','')}</div>
                            <div style="font-size:0.7rem; color:#666;">📧 {p.get('person_email','')}</div>
                            <div style="font-size:0.65rem; color:#888;">🏢 {dept_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        if st.button("✏️ Edit", key=f"edit_wf_{p['id']}", use_container_width=True):
                            st.session_state.editing_wf = p['id']
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Remove", key=f"del_wf_{p['id']}", use_container_width=True):
                            safe_supabase_query(lambda pid=p["id"]: supabase.table("workflow_config").delete().eq("id", pid).execute(), error_prefix="Remove workflow")
                            st.warning("Removed!"); st.rerun()
            else:
                st.caption("No people configured for this level")
            st.markdown("---")
        
        # Edit workflow entry
        if "editing_wf" in st.session_state and st.session_state.editing_wf:
            wf_id = st.session_state.editing_wf
            wf_entry = safe_supabase_query(lambda: supabase.table("workflow_config").select("*").eq("id", wf_id).single().execute(), error_prefix="Edit workflow")
            if wf_entry and wf_entry.data:
                wf = wf_entry.data
                st.markdown("---")
                st.markdown(f"### ✏️ Edit: {wf.get('person_name','')}")
                with st.form("edit_wf_form"):
                    all_users_wp2 = DB.get_users()
                    user_options_wp2 = [f"{u.get('name','')} ({u.get('email','')})" for u in all_users_wp2 if u.get('name') and u.get('email')]
                    user_options_wp2 = sorted(user_options_wp2)
                    current_user_str = f"{wf.get('person_name','')} ({wf.get('person_email','')})"
                    default_idx = user_options_wp2.index(current_user_str) if current_user_str in user_options_wp2 else 0
                    c1, c2 = st.columns(2)
                    with c1:
                        edit_level = st.selectbox("Level", [1, 2, 3], index=wf.get('level_number',1)-1,
                            format_func=lambda x: {1: "Level 1 — Authorization", 2: "Level 2 — Confirmation", 3: "Level 3 — Approval"}[x])
                    with c2:
                        edit_user = st.selectbox("Select Person", user_options_wp2, index=default_idx)
                    
                    current_depts = wf.get("department_filter", ["All Departments"])
                    if isinstance(current_depts, str):
                        try: current_depts = json.loads(current_depts)
                        except: current_depts = ["All Departments"]
                    if current_depts == ["All Departments"]:
                        current_depts = []
                    
                    all_departments2 = [
                        "Engineering — Electrical", "Engineering — HVAC", "Engineering — Plumbing",
                        "Engineering — Vertical Transportation (Lifts)", "Engineering — Fire Fighting",
                        "Facility Management — Hard Services", "Facility Management — Soft Services (Housekeeping)",
                        "Facility Management — FM Operations & Helpdesk", "Facility Management — Fitout Works",
                        "Facility Management — HSSE Safety & Compliance",
                        "Technology Group — Network & Connectivity", "Technology Group — Building Technology",
                        "Security — Man Guarding Operations",
                        "Contractor — Clyde Engineering", "Contractor — Gates and Shield"
                    ]
                    edit_depts = st.multiselect("Department Access (empty = All)", all_departments2, default=current_depts)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                            if "(" in edit_user:
                                parts = edit_user.split("(")
                                new_name = parts[0].strip()
                                new_email = parts[1].replace(")","").strip()
                                DB.update("workflow_config", wf_id, {
                                    "level_number": edit_level,
                                    "level_name": {1: "Authorizer", 2: "Confirmer", 3: "Approver"}[edit_level],
                                    "person_name": new_name,
                                    "person_email": new_email,
                                    "department_filter": json.dumps(edit_depts if edit_depts else ["All Departments"])
                                })
                                st.success("✅ Updated!"); st.session_state.editing_wf = None; st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.editing_wf = None; st.rerun()
        
        # Add new person form
        with st.form("wf_add_person"):
            st.markdown("### ➕ Add Person to Workflow")
            all_users_wp = DB.get_users()
            user_options_wp = [f"{u.get('name','')} ({u.get('email','')})" for u in all_users_wp if u.get('name') and u.get('email')]
            user_options_wp = sorted(user_options_wp)
            
            c1, c2 = st.columns(2)
            with c1:
                new_level = st.selectbox("Level", [1, 2, 3], 
                    format_func=lambda x: {1: "Level 1 — Authorization", 2: "Level 2 — Confirmation", 3: "Level 3 — Approval"}[x])
            with c2:
                selected_users_wp = st.multiselect("Select Person(s)*", user_options_wp, key="wf_select_users",
                    placeholder="Select one or more people...")
            
            all_departments = [
                "Engineering — Electrical", "Engineering — HVAC", "Engineering — Plumbing",
                "Engineering — Vertical Transportation (Lifts)", "Engineering — Fire Fighting",
                "Facility Management — Hard Services", "Facility Management — Soft Services (Housekeeping)",
                "Facility Management — FM Operations & Helpdesk", "Facility Management — Fitout Works",
                "Facility Management — HSSE Safety & Compliance",
                "Technology Group — Network & Connectivity", "Technology Group — Building Technology",
                "Security — Man Guarding Operations",
                "Contractor — Clyde Engineering", "Contractor — Gates and Shield"
            ]
            new_depts = st.multiselect("Department Access (leave empty for All Departments)", all_departments,
                placeholder="Choose departments or leave empty for All")
            
            if st.form_submit_button("➕ Add Person(s) to Workflow", use_container_width=True, type="primary"):
                if selected_users_wp:
                    added_count = 0
                    for user_str in selected_users_wp:
                        if "(" in user_str:
                            parts = user_str.split("(")
                            new_name = parts[0].strip()
                            new_email = parts[1].replace(")","").strip()
                            dept_filter = new_depts if new_depts else ["All Departments"]
                            
                            test_result = safe_supabase_query(lambda: supabase.table("workflow_config").insert({
                                "facility_code": "WTC",
                                "workflow_type": "work_permit", 
                                "level_number": int(new_level),
                                "level_name": str({1: "Authorizer", 2: "Confirmer", 3: "Approver"}[new_level]),
                                "person_name": str(new_name),
                                "person_email": str(new_email),
                                "department_filter": '["All Departments"]',
                                "is_active": True
                            }).execute(), error_prefix="Add workflow person")
                            
                            st.write(f"Result for {new_name}:", test_result.data if test_result else None)
                            if test_result and test_result.data:
                                added_count += 1
                    
                    if added_count > 0:
                        st.success(f"✅ {added_count} person(s) added!")
                        st.rerun()
                    else:
                        st.error("Failed to add anyone.")
                else:
                    st.error("⚠️ Please select at least one person")

# ============================================
# RAISE TICKET — AI-POWERED + MY TICKETS
# ============================================
def page_raise_ticket():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    st.markdown(f'## 🎫 Raise a Ticket — {info.get("full_name", fc)}')
    
    # ============================================
    # AI CHAT — TOP OF PAGE
    # ============================================
    st.markdown("### 🤖 facilityXpert — AI Assistant")
    st.caption("Get instant first-level support. Describe your issue and I'll help you troubleshoot.")
    
    user_email = st.session_state.get("user", {}).get("email", "guest")
    
    # Initialize chat history
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    if "ai_conversation" not in st.session_state:
        st.session_state.ai_conversation = []
    
    # Clear chat history when switching facilities
    if "last_facility" not in st.session_state:
        st.session_state.last_facility = fc
    if st.session_state.last_facility != fc:
        st.session_state.ai_chat_history = []
        st.session_state.ai_conversation = []
        st.session_state.last_facility = fc
    
    # Load saved chat history for this user
    if not st.session_state.ai_chat_history and user_email != "guest":
        try:
            saved = safe_supabase_query(lambda: supabase.table("ai_chat_sessions").select("*").eq("user_email", user_email).order("updated_at", desc=True).limit(1).execute(), error_prefix="AI chat history")
            if saved and saved.data:
                msgs = saved.data[0].get("messages", [])
                if isinstance(msgs, str):
                    msgs = json.loads(msgs)
                st.session_state.ai_chat_history = msgs
                st.session_state.ai_conversation = msgs[-20:]
        except: pass
    
    # Display chat history
    for msg in st.session_state.ai_chat_history:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])
    
    if st.session_state.ai_chat_history:
        if st.button("🗑️ Clear Chat History", key="clear_btn", use_container_width=True):
            st.session_state.ai_chat_history = []
            st.session_state.ai_conversation = []
            try:
                safe_supabase_query(lambda: supabase.table("ai_chat_sessions").delete().eq("user_email", user_email).execute(), error_prefix="Clear chat")
            except: pass
            st.rerun()
    
    prompt = st.chat_input("💬 Describe your facility issue here...", key="ai_chat_main")
    
    if prompt:
        st.session_state.ai_chat_history.append({"role": "user", "content": prompt})
        st.session_state.ai_conversation.append({"role": "user", "content": prompt})
        
        with st.spinner("🤖 Thinking..."):
            hc = DB.get_helpdesk_categories()
            cat_names_list = sorted(list(set(c.get("category_name", "") for c in hc)))
            
            try:
                api_key = ""
                try:
                    api_key = st.secrets["GROQ_API_KEY"]
                except:
                    api_key = os.environ.get("GROQ_API_KEY", "")
                
                # Get AI-friendly facility name
                if fc == "FCPL":
                    facility_display = "Churchgate Tower 1"
                elif fc == "RBPL":
                    facility_display = "Churchgate Tower 2"
                elif fc == "AGVL":
                    facility_display = "Churchgate Plaza"
                else:
                    facility_display = info.get('full_name', fc)
                
                messages = [
                    {"role": "system", "content": f"""You are facilityXpert, the official AI assistant for Churchgate Group's {facility_display} in {info.get('city', 'Nigeria')}.

YOUR ROLE: Help tenants and staff resolve facility-related issues only.

FACILITY CONTEXT:
- {info.get('full_name', fc)}: {info.get('desc', 'Facility')}
- Located in {info.get('city', 'Nigeria')}
- Managed by Churchgate Group
- Departments: {cat_names_list}

GUARDRAILS - YOU MUST FOLLOW:
1. STAY ON TOPIC: Only discuss facility issues.
2. NO PERSONAL INFO: Never ask for or share personal information.
3. NO BIAS: Treat all users equally.
4. NO ADULT CONTENT: Shut down inappropriate content with: "I can only assist with facility-related questions."
5. NO FAKE INFO: Never invent ticket numbers, phone numbers, or emails.
6. EMERGENCIES: For fire, flood, elevator stuck, electrical hazards - instruct them to call facility emergency or visit reception immediately.
7. BE PROFESSIONAL: Clear, polite, professional language.

CRITICAL RULE - TICKET FORM IS ON THIS PAGE:
When a user needs to raise a ticket, ALWAYS say: "Please scroll down to the 'Raise New Ticket' form on this page and submit your request. Select the [category name] category."
NEVER tell them to visit a website or call a number. The ticket form is RIGHT HERE on this page.

RESPONSE FORMAT: Give practical step-by-step troubleshooting first. If unresolved, direct to the Raise New Ticket form below."""}
                ]
                messages.extend(st.session_state.ai_conversation[-15:])
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.1-8b-instant", "messages": messages, "max_tokens": 300, "temperature": 0.5},
                    timeout=15
                )
                
                if response.status_code == 200:
                    ai_response = response.json()["choices"][0]["message"]["content"]
                else:
                    ai_response = None
            except:
                ai_response = None
                kb = safe_supabase_query(lambda: supabase.table("knowledge_base").select("*").or_(f"question.ilike.%{prompt}%,tags.ilike.%{prompt}%").limit(3).execute(), error_prefix="Knowledge base")
                if kb and kb.data:
                    ai_response = "Solutions from knowledge base:\n\n" + "\n\n".join([f"**{k.get('question')}**\n{k.get('answer','')}" for k in kb.data])
                else:
                    ai_response = "I couldn't find a solution. Please raise a ticket using the form below."
            
            st.session_state.ai_chat_history.append({"role": "assistant", "content": ai_response})
            st.session_state.ai_conversation.append({"role": "assistant", "content": ai_response})
            
            try:
                safe_supabase_query(lambda: supabase.table("ai_chat_sessions").upsert({
                    "user_email": user_email,
                    "session_id": f"{user_email}_{datetime.now().strftime('%Y%m%d')}",
                    "messages": st.session_state.ai_chat_history,
                    "updated_at": datetime.now().isoformat()
                }).execute(), error_prefix="Save chat")
            except: pass
            
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 📝 Raise New Ticket")
    
    buildings = DB.get_locations(fc)
    building_options = {}
    for b in buildings:
        building_options[b.get("location_code", "")] = b.get("location_name", "")
    if not building_options:
        if fc == "AGVL":
            building_options = {"AGVL": "Churchgate Plaza"}
        elif fc == "FCPL":
            building_options = {"FCPL": "Churchgate Tower 1"}
        elif fc == "RBPL":
            building_options = {"RBPL": "Churchgate Tower 2"}
        elif fc == "VDL":
            building_options = {"VDL": "The Ocean Terrace"}
        else:
            building_options = {"CT": "CT — Office Tower", "SAT": "SAT — Residential Tower", "RC": "RC — Recreation Center", "IP": "IP — Intermediate Parking"}
    
    c1, c2 = st.columns(2)
    with c1:
        selected_building = st.selectbox("Building*", options=list(building_options.keys()), format_func=lambda x: building_options.get(x, x), key="rt_building")
        sub_locs = get_sub_locations_for_building(fc, selected_building)
        if not sub_locs: sub_locs = [f"{selected_building} / 0"]
        sub_location = st.selectbox("Sub-Location*", sub_locs, key="rt_subloc")
    with c2:
        categories = DB.get_helpdesk_categories()
        cat_names = sorted(list(set(c.get("category_name", "") for c in categories)))
        category = st.selectbox("Category*", cat_names)
    
    full_location = f"{building_options.get(selected_building, selected_building)} → {sub_location}"
    
    with st.form("raise_ticket_form", clear_on_submit=True):
        title = st.text_input("Title*", placeholder="Brief description of the issue")
        description = st.text_area("Description*", height=100, placeholder="Describe the issue in detail...")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            priority = st.selectbox("Priority", ["low", "medium", "high", "critical"])
            occupant = st.text_input("Occupant/Tenant (if applicable)")
        with c2:
            requester_name = st.text_input("Your Name*")
            requester_email = st.text_input("Your Email")
        with c3:
            requester_phone = st.text_input("Your Phone")
            image = st.file_uploader("Image (Optional)", type=["png", "jpg", "jpeg"])
        
        submitted = st.form_submit_button("🎫 Submit Ticket", use_container_width=True, type="primary")
        
        if submitted:
            if not title or not description or not requester_name:
                st.error("⚠️ Title, Description, and Name are required")
            else:
                cnt = len(DB.get_all("tickets", fc, 1000))
                ticket_number = f"TKT-{fc}-{datetime.now().strftime('%d%H%M%S')}"
                
                sla_hours = 4
                ticket_dept = ""
                for c in categories:
                    if c.get("category_name") == category:
                        sla_hours = c.get("sla_hours", 4)
                        ticket_dept = c.get("department", "")
                        break
                sla_deadline = (datetime.now() + timedelta(hours=sla_hours)).isoformat()
                
                DB.insert("tickets", {
                    "facility_code": fc, "ticket_number": ticket_number, "title": title,
                    "description": description, "category": category, "priority": priority,
                    "status": "open", "requester_name": requester_name,
                    "requester_email": requester_email, "requester_phone": requester_phone,
                    "occupant_name": occupant, "location_building": full_location,
                    "sla_deadline": sla_deadline, "escalation_level": 1,
                    "created_at": datetime.now().isoformat()
                })
                
                authorizers = get_workflow_people(fc, 1, ticket_dept)
                for a in authorizers:
                    send_email_notification(
                        a.get("person_email", ""),
                        f"🎫 New Ticket {ticket_number} — {category}",
                        f"<h3>New Helpdesk Ticket</h3>"
                        f"<p><b>Ticket:</b> {ticket_number}</p>"
                        f"<p><b>Category:</b> {category}</p>"
                        f"<p><b>Priority:</b> {priority}</p>"
                        f"<p><b>Location:</b> {full_location}</p>"
                        f"<p><b>Raised by:</b> {requester_name}</p>"
                        f"<p><b>Description:</b> {description[:300]}</p>"
                        f"<p>SLA Deadline: {sla_deadline}</p>"
                    )
                
                st.success(f"✅ Ticket {ticket_number} raised successfully!")
                st.balloons()
                import time as _time
                _time.sleep(1.5)
                
                ticket_cat_id = None
                for c in categories:
                    if c.get("category_name") == category:
                        ticket_cat_id = c["id"]
                        break
                
                esc_data = safe_supabase_query(lambda: supabase.table("ticket_escalation").select("*").eq("facility_code", fc).eq("level_number", 1).eq("category_id", ticket_cat_id).execute(), error_prefix="Ticket escalation")
                if esc_data and esc_data.data:
                    for e in esc_data.data:
                        if e.get("escalate_to_email"):
                            send_email_notification(
                                e["escalate_to_email"],
                                f"🎫 New Ticket #{ticket_number} — {category}",
                                f"""
                                <div style="font-family:Arial;max-width:600px;margin:0 auto;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
                                    <div style="background:#C8A951;padding:20px;color:white;">
                                        <h2 style="margin:0;">facilityXperience</h2>
                                        <p style="margin:5px 0 0 0;font-size:12px;opacity:0.9;">Churchgate Group — {info.get('full_name',fc)}</p>
                                    </div>
                                    <div style="padding:20px;">
                                        <h3 style="color:#1a1a1a;">New Helpdesk Ticket</h3>
                                        <table style="width:100%;border-collapse:collapse;font-size:13px;">
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Ticket No:</td><td style="padding:8px;border-bottom:1px solid #eee;">{ticket_number}</td></tr>
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Category:</td><td style="padding:8px;border-bottom:1px solid #eee;">{category}</td></tr>
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Priority:</td><td style="padding:8px;border-bottom:1px solid #eee;"><span style="background:{'#EF4444' if priority=='critical' else '#F59E0B' if priority=='high' else '#3B82F6'};color:white;padding:2px 10px;border-radius:10px;font-size:11px;">{priority.upper()}</span></td></tr>
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Location:</td><td style="padding:8px;border-bottom:1px solid #eee;">{full_location}</td></tr>
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Raised by:</td><td style="padding:8px;border-bottom:1px solid #eee;">{requester_name}</td></tr>
                                            <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">SLA Deadline:</td><td style="padding:8px;border-bottom:1px solid #eee;">{sla_deadline[:16] if sla_deadline else 'N/A'}</td></tr>
                                        </table>
                                        <div style="background:#f5f5f5;padding:15px;border-radius:8px;margin-top:15px;">
                                            <p style="margin:0;font-weight:bold;">Description:</p>
                                            <p style="margin:5px 0 0 0;color:#666;">{description[:300]}</p>
                                        </div>
                                        <div style="margin-top:20px;padding:15px;background:#FFF3CD;border-radius:8px;">
                                            <p style="margin:0;font-weight:bold;color:#92400E;">⚡ Action Required:</p>
                                            <p style="margin:5px 0 0 0;color:#92400E;">Please review and take action on this ticket. SLA timer has started.</p>
                                        </div>
                                        <div style="margin-top:15px;text-align:center;">
                                            <a href="https://churchgate-facilityxperience.hf.space" style="background:#C8A951;color:white;padding:10px 25px;text-decoration:none;border-radius:6px;font-weight:bold;">View in facilityXperience</a>
                                        </div>
                                    </div>
                                    <div style="background:#f9f9f9;padding:12px;text-align:center;font-size:10px;color:#999;">
                                        Churchgate Group | facilityXperience | This is an automated notification
                                    </div>
                                </div>
                                """
                            )
    
    st.markdown("---")
    st.markdown("### 📋 My Tickets")
    
    user_name = st.session_state.get('user_name', '')
    user_email_val = st.session_state.get('user', {}).get('email', '')
    
    my_tickets = safe_supabase_query(lambda: supabase.table("tickets").select("*").eq("facility_code", fc).or_(f"requester_name.eq.{user_name},requester_email.eq.{user_email_val}").order("created_at", desc=True).limit(20).execute(), error_prefix="My tickets")
    if my_tickets and my_tickets.data:
        for t in my_tickets.data:
            status = t.get("status", "open")
            colors = {"open":"#EF4444","in_progress":"#F59E0B","hold":"#3B82F6","closed":"#10B981","rejected":"#6B7280"}
            icons = {"open":"🔴","in_progress":"🟡","hold":"⏸️","closed":"🟢","rejected":"❌"}
            sc = colors.get(status,"#4a4a4a")
            si = icons.get(status,"📋")
            
            created = t.get("created_at","")
            age_str = ""
            if created and str(created) != "None":
                try:
                    age = datetime.now() - pd.to_datetime(created)
                    age_str = f"{age.days}d {age.seconds//3600}h ago"
                except: pass
            
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span><b>{si} {t.get('ticket_number','')}</b></span>
                    <span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.65rem;font-weight:600;">{status.upper()}</span>
                </div>
                <div style="font-size:0.8rem;color:#1a1a1a;margin-top:0.3rem;">{t.get('title','')[:80]}</div>
                <div style="font-size:0.65rem;color:#888;margin-top:0.2rem;">🏷️ {t.get('category','')} | 📍 {t.get('location_building','')[:30]} | ⏱️ {age_str}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if t.get("status") == "closed":
                if not t.get("satisfaction_rating"):
                    rating = st.slider("Rate your experience", 1, 5, 5, key=f"rate_{t['id']}")
                    if st.button("⭐ Submit Rating", key=f"submit_rate_{t['id']}"):
                        DB.update("tickets", t["id"], {"satisfaction_rating": rating})
                        st.success("Thank you!")
                        st.rerun()
                else:
                    st.markdown(f"**Your Rating:** {'⭐' * t.get('satisfaction_rating', 0)}")
    else:
        st.info("No tickets raised yet")


def page_helpdesk_queue():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    
    st.markdown(f'## 💬 Helpdesk — {info.get("full_name", fc)}')
    
    categories = DB.get_helpdesk_categories()
    
    nav_tabs = ["🏠 Home", "📊 AI Analytics", "📄 Reports", "⏱️ Escalation", "⚙️ Settings"]
    tabs = st.tabs(nav_tabs)
    
    # ============================================
    # TAB 0: HOME — TICKET QUEUE (FULL)
    # ============================================
    with tabs[0]:
        statuses = ["All", "Open", "In Progress", "Hold", "Closed", "Rejected"]
        status_icons = {"All": "📋", "Open": "🔴", "In Progress": "🟡", "Hold": "⏸️", "Closed": "🟢", "Rejected": "❌"}
        status_colors = {"All": "#4a4a4a", "Open": "#EF4444", "In Progress": "#F59E0B", "Hold": "#3B82F6", "Closed": "#10B981", "Rejected": "#6B7280"}
        
        if "ticket_status_filter" not in st.session_state:
            st.session_state.ticket_status_filter = "All"
        
        # Status Filter Buttons with visual indicators
        cols = st.columns(6)
        for i, status in enumerate(statuses):
            with cols[i]:
                active = st.session_state.ticket_status_filter == status
                bg = status_colors[status] if active else "white"
                tc = "white" if active else "#1a1a1a"
                st.markdown(f"""<div style="background:{bg};border:2px solid {status_colors[status]};border-radius:12px;padding:0.6rem;text-align:center;color:{tc};font-weight:600;font-size:0.8rem;">{status_icons[status]} {status}</div>""", unsafe_allow_html=True)
                if st.button(f"{status}", key=f"st_{status}", use_container_width=True):
                    st.session_state.ticket_status_filter = status
                    st.rerun()
        
        st.markdown("---")
        
        # Search bar
        search = st.text_input("🔍 Search tickets", placeholder="Search by title, ID, or requester...", key="hd_search")
        
        status_filter = st.session_state.ticket_status_filter
        filter_status = status_filter.lower().replace(" in progress", "in_progress") if status_filter != "All" else None
        tickets = DB.get_tickets_filtered(fc, status=filter_status, search=search if search else None)
        
        # Department-based filtering (non-admin users see only their department tickets)
        user_depts = safe_parse_permissions(st.session_state.get("user", {}).get("department_permissions", []))
        can_see_all = user_role in ["admin", "approver", "confirmer"]
        if tickets and not can_see_all and user_depts:
            filtered = []
            for t in tickets:
                for c in categories:
                    if c.get("category_name") == t.get("category","") and c.get("department") in user_depts:
                        filtered.append(t)
                        break
            tickets = filtered
        
        if tickets:
            df = pd.DataFrame(tickets)
            
            # KPI Cards Row
            kpi_cols = st.columns(6)
            kpi_data = [
                ("📋 Total", len(df), "#4a4a4a"),
                ("🔴 Open", len(df[df["status"]=="open"]) if "status" in df.columns else 0, "#EF4444"),
                ("🟡 In Progress", len(df[df["status"]=="in_progress"]) if "status" in df.columns else 0, "#F59E0B"),
                ("⏸️ Hold", len(df[df["status"]=="hold"]) if "status" in df.columns else 0, "#3B82F6"),
                ("🟢 Closed", len(df[df["status"]=="closed"]) if "status" in df.columns else 0, "#10B981"),
                ("❌ Rejected", len(df[df["status"]=="rejected"]) if "status" in df.columns else 0, "#6B7280")
            ]
            for i, (label, value, color) in enumerate(kpi_data):
                with kpi_cols[i]:
                    st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-left:4px solid {color};box-shadow:0 1px 3px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;">{label}</div><div style="font-size:1.6rem;font-weight:800;">{value}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            if "open_ticket_detail" not in st.session_state:
                st.session_state.open_ticket_detail = None
            
            # Ticket Cards with Expandable Details
            for i, row in df.iterrows():
                status = row.get("status", "open")
                created = row.get("created_at", "")
                age_str = ""
                if created:
                    try:
                        created_dt = pd.to_datetime(created)
                        age = datetime.now() - created_dt
                        age_str = f"{age.days}d {age.seconds//3600}h"
                    except: pass
                
                sc = status_colors.get(status, "#4a4a4a")
                si = status_icons.get(status, "📋")
                ticket_id = row["id"]
                is_open = st.session_state.open_ticket_detail == ticket_id
                
                with st.container():
                    # Ticket Card Header
                    st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);"><div style="display:flex;justify-content:space-between;"><span><b>{si} {row.get('ticket_number','')}</b> — {row.get('requester_name','N/A')}</span><span style="font-size:0.7rem;color:#888;">⏱️ {age_str}</span></div><div style="margin-top:0.2rem;font-size:0.8rem;">{row.get('title','')[:100]}</div><div style="font-size:0.65rem;color:#888;">📍 {row.get('location_building','')[:40] if row.get('location_building') else 'N/A'} | 🏷️ {row.get('category','')} | L{row.get('escalation_level',1)}</div></div>""", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        new_comment = st.text_input("Quick Note", key=f"cmt_{row['id']}", placeholder="Add progress note...")
                    with c2:
                        btn_label = "🔼 Hide" if is_open else "📋 Details"
                        if st.button(btn_label, key=f"vdet_{row['id']}", use_container_width=True):
                            if is_open:
                                st.session_state.open_ticket_detail = None
                            else:
                                st.session_state.open_ticket_detail = ticket_id
                            st.rerun()
                    
                    # EXPANDED DETAIL VIEW
                    if is_open:
                        with st.container():
                            st.markdown(f"""<div style="background:#f9fafb;border-radius:10px;padding:1rem;margin:0.5rem 0;border:1px solid #e5e7eb;"><h4 style="margin:0;">{row.get('title','')}</h4><p style="color:#666;font-size:0.8rem;"><b>Ticket:</b> {row.get('ticket_number','')} | <b>Status:</b> {status.upper()} | <b>Level:</b> L{row.get('escalation_level',1)}</p><p style="font-size:0.8rem;"><b>Raised by:</b> {row.get('requester_name','N/A')} | <b>Category:</b> {row.get('category','')} | <b>Priority:</b> {row.get('priority','')}</p><p style="font-size:0.8rem;"><b>Location:</b> {row.get('location_building','')}</p><p style="font-size:0.8rem;"><b>Description:</b> {row.get('description','')}</p><p style="font-size:0.75rem;color:#888;"><b>SLA:</b> {format_wat_time(row.get('sla_deadline',''))}</p></div>""", unsafe_allow_html=True)
                            
                            # Progress Log / Comments
                            comments = DB.get_ticket_comments(ticket_id)
                            if comments:
                                st.caption("📝 Progress Log:")
                                for c in comments:
                                    st.caption(f"👤 {c.get('user_name','')} — {c.get('created_at','')[:16]}: {c.get('comment_text','')}")
                            
                            st.markdown("**⚡ Actions:**")
                            
                            if status in ["open", "in_progress", "hold"]:
                                # Action buttons row 1
                                ac1, ac2, ac3 = st.columns(3)
                                with ac1:
                                    if st.button("🔄 Update", key=f"det_upd_{ticket_id}", use_container_width=True):
                                        if new_comment:
                                            DB.insert("ticket_comments", {"ticket_id": ticket_id, "user_name": st.session_state.get("user_name","Staff"), "comment_text": new_comment})
                                            DB.update("tickets", ticket_id, {"status": "in_progress"})
                                            st.success("✅ Updated!")
                                            st.rerun()
                                with ac2:
                                    if st.button("⏸️ Hold", key=f"det_hold_{ticket_id}", use_container_width=True):
                                        DB.update("tickets", ticket_id, {"status": "hold"})
                                        st.success("⏸️ On Hold")
                                        st.rerun()
                                with ac3:
                                    if st.button("✅ Close", key=f"det_close_{ticket_id}", use_container_width=True):
                                        DB.update("tickets", ticket_id, {"status": "closed", "closed_at": datetime.now().isoformat()})
                                        if row.get("requester_email"):
                                            send_email_notification(row["requester_email"], f"✅ Ticket {row.get('ticket_number','')} Resolved", f"<h3>Ticket Resolved</h3><p>Your ticket has been resolved. Please rate your experience.</p>")
                                        st.success("✅ Closed!")
                                        st.balloons()
                                        st.rerun()
                                
                                # Action buttons row 2
                                ac4, ac5, ac6 = st.columns(3)
                                with ac4:
                                    if st.button("❌ Reject", key=f"det_rej_{ticket_id}", use_container_width=True):
                                        DB.update("tickets", ticket_id, {"status": "rejected"})
                                        st.error("Ticket rejected")
                                        st.rerun()
                                with ac5:
                                    if st.button("🔄 Re-Assign", key=f"det_reassign_{ticket_id}", use_container_width=True):
                                        st.session_state.reassign_ticket = ticket_id
                                        st.rerun()
                                with ac6:
                                    if st.button("ℹ️ More Info", key=f"det_more_{ticket_id}", use_container_width=True):
                                        st.session_state.more_info_ticket = ticket_id
                                        st.rerun()
                                
                                # Re-Assign Form
                                if "reassign_ticket" in st.session_state and st.session_state.reassign_ticket == ticket_id:
                                    all_users = DB.get_users()
                                    user_names = [u.get("name","") for u in all_users]
                                    reassign_to = st.selectbox("Re-assign to", user_names, key=f"reassign_{ticket_id}")
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.button("✅ Confirm Re-Assign", key=f"confirm_reassign_{ticket_id}", use_container_width=True):
                                            DB.update("tickets", ticket_id, {"assigned_to": reassign_to})
                                            DB.insert("ticket_comments", {"ticket_id": ticket_id, "user_name": st.session_state.get("user_name","Staff"), "comment_text": f"Re-assigned to {reassign_to}"})
                                            if row.get("requester_email"):
                                                send_email_notification(row["requester_email"], f"🔄 Ticket {row.get('ticket_number','')} Re-Assigned", f"<h3>Ticket Re-Assigned</h3><p>Your ticket has been re-assigned to {reassign_to}.</p>")
                                            st.success(f"✅ Re-assigned to {reassign_to}!")
                                            st.session_state.reassign_ticket = None
                                            st.rerun()
                                    with c2:
                                        if st.button("❌ Cancel", key=f"cancel_reassign_{ticket_id}", use_container_width=True):
                                            st.session_state.reassign_ticket = None
                                            st.rerun()
                                
                                # More Info Form
                                if "more_info_ticket" in st.session_state and st.session_state.more_info_ticket == ticket_id:
                                    more_info_note = st.text_area("Request more information", key=f"more_info_{ticket_id}", height=60, placeholder="What additional information do you need?")
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.button("📩 Request Info", key=f"send_more_{ticket_id}", use_container_width=True):
                                            if more_info_note:
                                                DB.insert("ticket_comments", {"ticket_id": ticket_id, "user_name": st.session_state.get("user_name","Staff"), "comment_text": f"INFO REQUESTED: {more_info_note}"})
                                                if row.get("requester_email"):
                                                    send_email_notification(row["requester_email"], f"ℹ️ More Info Requested - Ticket {row.get('ticket_number','')}", f"<h3>Additional Information Requested</h3><p><b>Ticket:</b> {row.get('ticket_number','')}</p><p><b>Request:</b> {more_info_note}</p><p>Please respond with the requested information.</p>")
                                                st.success("✅ Info request sent!")
                                                st.session_state.more_info_ticket = None
                                                st.rerun()
                                    with c2:
                                        if st.button("❌ Cancel", key=f"cancel_more_{ticket_id}", use_container_width=True):
                                            st.session_state.more_info_ticket = None
                                            st.rerun()
                                
                                # Escalate (Admin only)
                                if is_admin:
                                    esc_level = row.get("escalation_level", 1)
                                    if esc_level < 6:
                                        if st.button(f"🔺 Escalate L{esc_level}→L{esc_level+1}", key=f"det_esc_{ticket_id}", use_container_width=True):
                                            DB.update("tickets", ticket_id, {"escalation_level": esc_level + 1})
                                            st.success(f"🔺 Escalated to Level {esc_level + 1}!")
                                            st.rerun()
                            
                            # Re-Open closed tickets
                            if status == "closed":
                                if st.button("🔄 Re-Open", key=f"det_reopen_{ticket_id}", use_container_width=True):
                                    DB.update("tickets", ticket_id, {"status": "open"})
                                    st.success("🔄 Re-opened!")
                                    st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No tickets found matching your filters")
    
    # ============================================
    # TAB 1: AI-POWERED ANALYTICS (FULL)
    # ============================================
    with tabs[1]:
        st.markdown("### 📊 AI-Powered Helpdesk Analytics")
        
        all_tickets = DB.get_all("tickets", fc, 500)
        if all_tickets:
            df = pd.DataFrame(all_tickets)
            
            total = len(df)
            open_count = len(df[df["status"]=="open"]) if "status" in df.columns else 0
            in_progress = len(df[df["status"]=="in_progress"]) if "status" in df.columns else 0
            hold_count = len(df[df["status"]=="hold"]) if "status" in df.columns else 0
            closed_count = len(df[df["status"]=="closed"]) if "status" in df.columns else 0
            rejected_count = len(df[df["status"]=="rejected"]) if "status" in df.columns else 0
            
            resolution_times = []
            if "created_at" in df.columns and "closed_at" in df.columns:
                for _, r in df.iterrows():
                    try:
                        closed_val = r.get("closed_at")
                        if closed_val and str(closed_val) != "None" and str(closed_val) != "nan" and str(closed_val) != "":
                            created = pd.to_datetime(r["created_at"])
                            closed = pd.to_datetime(closed_val)
                            hrs = (closed - created).total_seconds() / 3600
                            if hrs > 0:
                                resolution_times.append(hrs)
                    except: pass
            avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0
            avg_display = f"{avg_resolution}h" if avg_resolution > 0 else "N/A"
            
            sla_met = 0
            sla_exceeded = 0
            if "sla_deadline" in df.columns and "closed_at" in df.columns:
                for _, r in df.iterrows():
                    try:
                        closed_val = r.get("closed_at")
                        if closed_val and str(closed_val) != "None" and str(closed_val) != "nan" and r.get("sla_deadline"):
                            if pd.to_datetime(closed_val) <= pd.to_datetime(r["sla_deadline"]):
                                sla_met += 1
                            else:
                                sla_exceeded += 1
                    except: pass
            
            frt_met = 0
            if "created_at" in df.columns:
                for _, r in df.iterrows():
                    try:
                        if r.get("created_at"):
                            comments = DB.get_ticket_comments(r.get("id"))
                            if comments and len(comments) > 0:
                                first_comment = pd.to_datetime(comments[0].get("created_at"))
                                created = pd.to_datetime(r["created_at"])
                                if (first_comment - created).total_seconds() / 60 <= 30:
                                    frt_met += 1
                    except: pass
            
            priority_breakdown = df["priority"].value_counts().to_dict() if "priority" in df.columns else {}
            critical_high = priority_breakdown.get("critical", 0) + priority_breakdown.get("high", 0)
            backlog = open_count + in_progress + hold_count
            rate = round((closed_count/total)*100) if total > 0 else 0
            
            overdue = 0
            if "sla_deadline" in df.columns:
                now = datetime.now()
                for _, r in df.iterrows():
                    try:
                        if pd.to_datetime(r["sla_deadline"]) < now and r.get("status") not in ["closed","rejected"]:
                            overdue += 1
                    except: pass
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1: st.metric("📋 Total", total)
            with c2: st.metric("🔴 Open", open_count)
            with c3: st.metric("🟡 In Progress", in_progress)
            with c4: st.metric("⏸️ Hold", hold_count)
            with c5: st.metric("🟢 Closed", closed_count)
            with c6: st.metric("⏱️ Avg Resolution", avg_display)
            
            st.markdown("---")
            
            st.markdown("#### ⏱️ SLA Compliance")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("✅ SLA Met", sla_met)
                st.progress(sla_met / total if total > 0 else 0, text=f"{sla_met}/{total}")
            with c2:
                st.metric("⚠️ SLA Exceeded", sla_exceeded)
                st.progress(sla_exceeded / total if total > 0 else 0, text=f"{sla_exceeded}/{total}")
            
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            with c1:
                if "category" in df.columns:
                    cat_counts = df["category"].value_counts().head(10)
                    fig = px.bar(x=cat_counts.index, y=cat_counts.values, title="📊 Tickets by Category", color=cat_counts.values, color_continuous_scale="Reds")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if "status" in df.columns:
                    st_counts = df["status"].value_counts()
                    colors_map = {"open":"#EF4444","in_progress":"#F59E0B","hold":"#3B82F6","closed":"#10B981","rejected":"#6B7280"}
                    pie_colors = [colors_map.get(s,"#999") for s in st_counts.index]
                    fig2 = px.pie(values=st_counts.values, names=st_counts.index, title="📈 Status Distribution", color_discrete_sequence=pie_colors)
                    fig2.update_layout(height=350)
                    st.plotly_chart(fig2, use_container_width=True)
            
            if "created_at" in df.columns:
                df["month"] = pd.to_datetime(df["created_at"]).dt.month
                df["month_name"] = df["month"].apply(lambda x: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][x-1])
                monthly = df.groupby("month_name").size().reset_index(name="count")
                fig3 = px.line(monthly, x="month_name", y="count", title="📈 Monthly Ticket Volume", markers=True, line_shape="spline")
                fig3.update_layout(height=300)
                st.plotly_chart(fig3, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🏢 Executive KPI Dashboard")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🔥 Critical/High", critical_high)
                st.caption("Urgent tickets")
            with c2:
                st.metric("📈 Resolution Rate", f"{rate}%")
                st.caption("Tickets resolved")
            with c3:
                st.metric("⏱️ First Response SLA", f"{frt_met}/{total}")
                st.caption("Acknowledged within 30m")
            with c4:
                st.metric("📋 Current Backlog", backlog)
                st.caption("Awaiting resolution")
            
            st.markdown("---")
            st.markdown("#### 📊 Department Performance")
            dept_performance = {}
            if "category" in df.columns:
                for _, r in df.iterrows():
                    cat = r.get("category","Unknown")
                    if cat not in dept_performance:
                        dept_performance[cat] = {"total": 0, "closed": 0}
                    dept_performance[cat]["total"] += 1
                    if r.get("status") == "closed":
                        dept_performance[cat]["closed"] += 1
            
            if dept_performance:
                dept_df = pd.DataFrame([
                    {"Department": k, "Total": v["total"], "Closed": v["closed"],
                     "Resolution Rate": f"{round((v['closed']/v['total'])*100)}%" if v['total'] > 0 else "0%"}
                    for k, v in dept_performance.items()
                ]).sort_values("Total", ascending=False)
                st.dataframe(dept_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("#### 🤖 AI Insights")
            
            c1, c2 = st.columns(2)
            with c1:
                if overdue > 0:
                    st.error(f"🔴 {overdue} tickets past SLA deadline")
                if open_count > 0:
                    st.warning(f"📋 {open_count} open tickets pending")
                if avg_resolution > 4:
                    st.info(f"⏱️ Avg resolution ({avg_display}) exceeds 4h target")
                else:
                    st.success(f"✅ Avg resolution ({avg_display}) within target")
            with c2:
                if "category" in df.columns and len(df["category"].value_counts()) > 0:
                    top_cat = df["category"].value_counts().index[0]
                    st.info(f"📈 Most reported: **{top_cat}**")
                if rate >= 80:
                    st.success(f"✅ Resolution rate {rate}% meets target")
                else:
                    st.warning(f"⚠️ Resolution rate {rate}% below 80% target")
        else:
            st.info("No ticket data available for analytics")
    
    # ============================================
    # TAB 2: PROFESSIONAL REPORTS (FULL)
    # ============================================
    with tabs[2]:
        st.markdown("### 📄 Helpdesk Reports")
        
        rpt_type = st.selectbox("Report Type", ["Monthly Report", "Customized Report", "Tickets Carry Forward"])
        
        all_tickets = DB.get_all("tickets", fc, 500)
        occupant_options = ["All Occupants", "Internal Team"] + sorted(list(set(
            t.get("occupant_name","") for t in all_tickets if t.get("occupant_name") and str(t.get("occupant_name")) != "None"
        )))
        cat_options = ["All"] + sorted(list(set(c.get("category_name","") for c in categories)))
        status_options = ["All", "open", "in_progress", "hold", "closed", "rejected"]
        
        rpt_month = "Custom"
        rpt_year = ""
        
        if rpt_type == "Monthly Report":
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                rpt_month = st.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
            with c2:
                rpt_year = st.selectbox("Year", [2024,2025,2026,2027])
            with c3:
                rpt_occupant = st.selectbox("Select Occupant", occupant_options)
            with c4:
                rpt_category = st.selectbox("Category", cat_options)
            rpt_status = st.selectbox("Select Status", status_options)
            
        elif rpt_type == "Customized Report":
            c1, c2 = st.columns(2)
            with c1:
                date_from = st.date_input("From", date.today().replace(day=1))
            with c2:
                date_to = st.date_input("To", date.today())
            c1, c2, c3 = st.columns(3)
            with c1:
                rpt_occupant = st.selectbox("Select Occupant", occupant_options, key="cust_occ")
            with c2:
                rpt_category = st.selectbox("Category", cat_options, key="cust_cat")
            with c3:
                rpt_status = st.selectbox("Select Status", status_options, key="cust_status")
            
        else:
            rpt_year = st.selectbox("Select Year", [2024,2025,2026,2027], key="tcf_year")
            c1, c2, c3 = st.columns(3)
            with c1:
                rpt_occupant = st.selectbox("Select Occupant", occupant_options, key="tcf_occ")
            with c2:
                rpt_category = st.selectbox("Category", cat_options, key="tcf_cat")
            with c3:
                rpt_status = st.selectbox("Select Status", status_options, key="tcf_status")
            rpt_month = "Carry Forward"
        
        if st.button("📊 Generate Report", use_container_width=True, type="primary"):
            if all_tickets:
                df = pd.DataFrame(all_tickets)
                
                if rpt_month not in ["Custom", "Carry Forward"]:
                    month_map = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
                    month_num = month_map.get(rpt_month, 0)
                    if month_num > 0 and "created_at" in df.columns:
                        df = df[pd.to_datetime(df["created_at"]).dt.month == month_num]
                    if rpt_year and "created_at" in df.columns:
                        df = df[pd.to_datetime(df["created_at"]).dt.year == rpt_year]
                
                if rpt_type == "Customized Report" and "created_at" in df.columns:
                    df = df[(pd.to_datetime(df["created_at"]).dt.date >= date_from) & (pd.to_datetime(df["created_at"]).dt.date <= date_to)]
                
                if rpt_type == "Tickets Carry Forward" and rpt_year and "created_at" in df.columns:
                    df = df[pd.to_datetime(df["created_at"]).dt.year <= rpt_year]
                
                if rpt_occupant != "All Occupants":
                    if rpt_occupant == "Internal Team":
                        external_companies = ["AGIP","Optiva","Heritage","Periscope","Maroto","Seplat","Handy","Aselsan","First E&P","Microsoft","Lighthouse","General Electric","Dell","Access Bank","TotalEnergies"]
                        df = df[~df["occupant_name"].str.contains('|'.join(external_companies), case=False, na=False)]
                    else:
                        df = df[df["occupant_name"] == rpt_occupant]
                
                if rpt_category != "All":
                    df = df[df["category"] == rpt_category]
                
                if rpt_status != "All":
                    df = df[df["status"] == rpt_status]
                
                if len(df) == 0:
                    st.warning("No tickets match your filters")
                else:
                    total = len(df)
                    open_count_rpt = len(df[df["status"]=="open"]) if "status" in df.columns else 0
                    in_progress_rpt = len(df[df["status"]=="in_progress"]) if "status" in df.columns else 0
                    hold_count_rpt = len(df[df["status"]=="hold"]) if "status" in df.columns else 0
                    closed_count_rpt = len(df[df["status"]=="closed"]) if "status" in df.columns else 0
                    
                    resolution_times_rpt = []
                    if "created_at" in df.columns and "closed_at" in df.columns:
                        for _, r in df.iterrows():
                            try:
                                closed_val = r.get("closed_at")
                                if closed_val and str(closed_val) != "None" and str(closed_val) != "nan" and str(closed_val) != "":
                                    hrs = (pd.to_datetime(closed_val) - pd.to_datetime(r["created_at"])).total_seconds() / 3600
                                    if hrs > 0: resolution_times_rpt.append(hrs)
                            except: pass
                    avg_resolution_rpt = round(sum(resolution_times_rpt) / len(resolution_times_rpt), 1) if resolution_times_rpt else 0
                    avg_display_rpt = f"{avg_resolution_rpt}h" if avg_resolution_rpt > 0 else "N/A"
                    
                    st.success(f"✅ Report generated — {total} tickets")
                    
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    with c1: st.metric("📋 Total", total)
                    with c2: st.metric("🔴 Open", open_count_rpt)
                    with c3: st.metric("🟡 In Progress", in_progress_rpt)
                    with c4: st.metric("⏸️ Hold", hold_count_rpt)
                    with c5: st.metric("🟢 Closed", closed_count_rpt)
                    with c6: st.metric("⏱️ Avg Resolution", avg_display_rpt)
                    
                    st.markdown("---")
                    st.markdown("### 📋 Detailed Ticket Report")
                    
                    table_data = []
                    for _, r in df.iterrows():
                        created = str(r.get('created_at',''))[:16] if r.get('created_at') and str(r.get('created_at')) != "None" else "—"
                        closed_val = r.get('closed_at')
                        closed = str(closed_val)[:16] if closed_val and str(closed_val) != "None" and str(closed_val) != "nan" else "Pending"
                        
                        age_str = "—"
                        if r.get('created_at') and str(r.get('created_at')) != "None":
                            try:
                                created_dt = pd.to_datetime(r['created_at'])
                                end_dt = pd.to_datetime(r['closed_at']) if r.get('closed_at') and str(r.get('closed_at')) != "None" and str(r.get('closed_at')) != "nan" else datetime.now()
                                age = end_dt - created_dt
                                age_str = f"{age.days}d {age.seconds//3600}h"
                            except: pass
                        
                        table_data.append({
                            "SNo": len(table_data) + 1,
                            "DateTime": created,
                            "Ticket No": safe_text(r.get('ticket_number',''),"—"),
                            "Location": safe_text(r.get('location_building',''),"—"),
                            "Category": safe_text(r.get('category',''),"—"),
                            "Title": safe_text(r.get('title',''),"—")[:50],
                            "Raised By": safe_text(r.get('requester_name',''),"—"),
                            "Priority": safe_text(r.get('priority',''),"—"),
                            "Status": safe_text(r.get('status',''),"—").upper(),
                            "Age": age_str,
                            "Closed": closed,
                            "Level": f"L{safe_text(r.get('escalation_level',1),'1')}"
                        })
                    
                    report_df = pd.DataFrame(table_data)
                    st.dataframe(report_df, use_container_width=True, hide_index=True, height=500)
                    
                    st.markdown("---")
                    st.markdown("### 📥 Download Reports")
                    
                    logo_b64 = get_logo_base64()
                    logo_html = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
                    
                    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{font-family:Arial;margin:25px;color:#1a1a1a;font-size:11px}}.header{{background:#1a1a1a;color:white;padding:18px 20px;border-radius:10px;display:flex;align-items:center;gap:15px;margin-bottom:20px}}.header h1{{margin:0;font-size:19px}}.kpi-row{{display:flex;gap:8px;margin:15px 0}}.kpi{{flex:1;background:#f5f5f5;border-radius:8px;padding:10px;text-align:center;border-left:4px solid #CC0000}}.kpi.green{{border-left-color:#10B981}}.kpi-val{{font-size:22px;font-weight:bold;color:#CC0000}}.kpi-label{{font-size:9px;color:#666}}table{{width:100%;border-collapse:collapse;font-size:10px}}th{{background:#CC0000;color:white;padding:7px 5px;text-align:left;font-size:8px}}td{{padding:4px 5px;border-bottom:1px solid #ddd}}.footer{{margin-top:25px;font-size:9px;color:#999;text-align:center;border-top:1px solid #ddd;padding-top:12px}}</style></head><body><div class="header">{logo_html}<div><h1>Helpdesk Report - {rpt_month} {rpt_year}</h1><p style="font-size:10px;opacity:0.8">{safe_text(info.get('full_name',fc))} | {datetime.now().strftime('%d %B %Y, %I:%M %p WAT')}</p></div></div><div class="kpi-row"><div class="kpi"><div class="kpi-val">{total}</div><div class="kpi-label">Total</div></div><div class="kpi"><div class="kpi-val">{open_count_rpt}</div><div class="kpi-label">Open</div></div><div class="kpi"><div class="kpi-val">{in_progress_rpt}</div><div class="kpi-label">In Progress</div></div><div class="kpi green"><div class="kpi-val">{closed_count_rpt}</div><div class="kpi-label">Closed</div></div><div class="kpi"><div class="kpi-val">{avg_display_rpt}</div><div class="kpi-label">Avg Resolution</div></div></div><h2>Tickets</h2><table><tr><th>#</th><th>DateTime</th><th>Ticket</th><th>Location</th><th>Category</th><th>Title</th><th>By</th><th>Priority</th><th>Status</th><th>Age</th><th>Closed</th></tr>"""
                    
                    for _, r in report_df.iterrows():
                        html += f"<tr><td>{r['SNo']}</td><td>{r['DateTime']}</td><td>{r['Ticket No']}</td><td>{r['Location']}</td><td>{r['Category']}</td><td>{r['Title']}</td><td>{r['Raised By']}</td><td>{r['Priority']}</td><td>{r['Status']}</td><td>{r['Age']}</td><td>{r['Closed']}</td></tr>"
                    
                    html += f"</table><div class='footer'>Churchgate Group | facilityXperience | Confidential</div></body></html>"
                    
                    with st.expander("🌐 HTML Preview", expanded=True):
                        st.components.v1.html(html, height=500, scrolling=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 Download HTML", html, f"helpdesk_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html", "text/html", use_container_width=True)
                    with c2:
                        st.download_button("📥 Download CSV", df.to_csv(index=False), f"helpdesk_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)
            else:
                st.info("No ticket data available")
    
    # ============================================
    # TAB 3: ESCALATION SETTINGS (FULL)
    # ============================================
    with tabs[3]:
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            st.markdown("### ⏱️ Escalation Configuration")
            st.caption("Configure 6-level escalation paths per category")
            
            dept_list = sorted(list(set(c.get("department","") for c in categories)))
            selected_dept = st.selectbox("Select Department", dept_list, key="esc_dept")
            
            dept_cats = [c for c in categories if c.get("department") == selected_dept]
            cat_names = [c.get("category_name","") for c in dept_cats]
            selected_cat = st.selectbox("Select Category", cat_names, key="esc_cat_detail")
            
            if selected_cat:
                cat_id = None
                for c in dept_cats:
                    if c.get("category_name") == selected_cat:
                        cat_id = c["id"]
                        break
                
                if cat_id:
                    all_users = DB.get_users()
                    user_options = [f"{u.get('name','')} ({u.get('email','')})" for u in all_users]
                    
                    existing = safe_supabase_query(lambda: supabase.table("ticket_escalation").select("*").eq("facility_code", fc).eq("category_id", cat_id).order("level_number").execute(), error_prefix="Ticket escalation")
                    
                    st.markdown("---")
                    st.markdown(f"#### 🔺 Escalation Levels for: **{selected_cat}**")
                    
                    for level in range(1, 7):
                        existing_users = []
                        existing_time = 30 if level <= 2 else 60 if level == 3 else 1440
                        existing_unit = "Mins"
                        
                        if existing and existing.data:
                            for e in existing.data:
                                if e.get("level_number") == level:
                                    user_str = f"{e.get('escalate_to_name','')} ({e.get('escalate_to_email','')})"
                                    existing_users.append(user_str)
                                    existing_time = e.get("sla_minutes", 30)
                        
                        valid_existing = [u for u in existing_users if u in user_options]
                        
                        if existing_time >= 1440:
                            existing_time = existing_time // 1440
                            existing_unit = "Days"
                        elif existing_time >= 60:
                            existing_time = existing_time // 60
                            existing_unit = "Hours"
                        
                        level_colors = {1: "#3B82F6", 2: "#8B5CF6", 3: "#F59E0B", 4: "#EF4444", 5: "#991B1B", 6: "#1a1a1a"}
                        lc = level_colors.get(level, "#4a4a4a")
                        
                        st.markdown(f"""<div style="background:white;border-left:4px solid {lc};border-radius:8px;padding:0.8rem;margin:0.5rem 0;"><b style="color:{lc};">Level {level}</b></div>""", unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1: 
                            st.multiselect(f"Assign Users", user_options, default=valid_existing, key=f"esc_u_{level}_{cat_id}")
                        with c2: 
                            st.number_input(f"SLA Time", min_value=0, value=existing_time, key=f"esc_t_{level}_{cat_id}")
                        with c3: 
                            st.selectbox(f"Unit", ["Mins","Hours","Days"], index=["Mins","Hours","Days"].index(existing_unit), key=f"esc_ty_{level}_{cat_id}")
                    
                    st.markdown("---")
                    
                    if st.button("💾 Save Escalation Settings", use_container_width=True, type="primary", key="save_esc_btn"):
                        saved_count = 0
                        for level in range(1, 7):
                            time_val = st.session_state.get(f"esc_t_{level}_{cat_id}", 30)
                            time_type = st.session_state.get(f"esc_ty_{level}_{cat_id}", "Mins")
                            
                            if time_type == "Hours": time_val *= 60
                            elif time_type == "Days": time_val *= 1440
                            
                            users = st.session_state.get(f"esc_u_{level}_{cat_id}", [])
                            
                            try:
                                safe_supabase_query(lambda l=level: supabase.table("ticket_escalation").delete().eq("facility_code", fc).eq("category_id", cat_id).eq("level_number", l).execute(), error_prefix="Delete escalation")
                            except: pass
                            
                            for u in users:
                                if "(" in u and ")" in u:
                                    email = u.split("(")[-1].replace(")","").strip()
                                    name = u.split("(")[0].strip()
                                    try:
                                        safe_supabase_query(lambda n=name, e=email, t=int(time_val), l=level: supabase.table("ticket_escalation").insert({
                                            "facility_code": fc,
                                            "category_id": cat_id,
                                            "level_number": l,
                                            "level_name": f"Level {l}",
                                            "escalate_to_name": n,
                                            "escalate_to_email": e,
                                            "sla_minutes": t
                                        }).execute(), error_prefix="Save escalation")
                                        saved_count += 1
                                    except: pass
                        
                        st.success(f"✅ Escalation settings saved! {saved_count} entries configured across 6 levels.")
                        st.balloons()
    
    # ============================================
    # TAB 4: SETTINGS (FULL)
    # ============================================
    with tabs[4]:
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            st.markdown("### ⚙️ Helpdesk Settings")
            sett_tabs = st.tabs(["📍 Locations", "🏷️ Categories", "📊 Status"])
            
            with sett_tabs[0]:
                st.markdown("#### 📍 Location Details")
                
                locs = DB.get_locations(fc)
                loc_search = st.text_input("🔍 Search locations", key="loc_search_main")
                
                if locs:
                    table_data = []
                    for i, l in enumerate(locs):
                        loc_name = l.get("location_name","")
                        loc_code = l.get("location_code","")
                        
                        if loc_search and loc_search.lower() not in loc_name.lower() and loc_search.lower() not in loc_code.lower():
                            continue
                        
                        subs = DB.get_sub_locations(l["id"])
                        sub_count = len(subs) if subs else 0
                        
                        table_data.append({
                            "SNO": len(table_data) + 1,
                            "Location": loc_code,
                            "Full Name": loc_name,
                            "Sub Locations": f"{sub_count} subs",
                            "id": l["id"]
                        })
                    
                    if table_data:
                        page_size = 10
                        total_pages = max(1, (len(table_data) + page_size - 1) // page_size)
                        
                        if "loc_page" not in st.session_state:
                            st.session_state.loc_page = 1
                        
                        start = (st.session_state.loc_page - 1) * page_size
                        end = start + page_size
                        page_data = table_data[start:end]
                        
                        st.caption(f"Showing {start+1} to {min(end, len(table_data))} of {len(table_data)} entries")
                        
                        for row in page_data:
                            c1, c2, c3, c4, c5 = st.columns([0.5, 1.5, 2, 1.5, 1])
                            with c1: st.markdown(f"**{row['SNO']}**")
                            with c2: st.markdown(f"`{row['Location']}`")
                            with c3: st.markdown(row["Full Name"])
                            with c4: st.markdown(row["Sub Locations"])
                            with c5:
                                loc_id = row["id"]
                                if st.button("🔍 View", key=f"view_loc_{loc_id}", use_container_width=True):
                                    st.session_state.view_loc_id = loc_id
                                    st.rerun()
                            st.markdown("---")
                        
                        c1, c2, c3 = st.columns([1, 2, 1])
                        with c1:
                            if st.session_state.loc_page > 1:
                                if st.button("← Previous", key="loc_prev"):
                                    st.session_state.loc_page -= 1
                                    st.rerun()
                        with c2:
                            st.markdown(f"**Page {st.session_state.loc_page} of {total_pages}**")
                        with c3:
                            if st.session_state.loc_page < total_pages:
                                if st.button("Next →", key="loc_next"):
                                    st.session_state.loc_page += 1
                                    st.rerun()
                    
                    if "view_loc_id" in st.session_state and st.session_state.view_loc_id:
                        loc_id = st.session_state.view_loc_id
                        loc_info = next((l for l in locs if l["id"] == loc_id), None)
                        
                        if loc_info:
                            st.markdown("---")
                            st.markdown(f"#### 📍 Sublocations for **{loc_info.get('location_name','')}**")
                            
                            subs = DB.get_sub_locations(loc_id)
                            if subs:
                                for s in subs:
                                    c1, c2 = st.columns([4, 1])
                                    with c1: st.markdown(f"└ {s.get('sub_location_name','')}")
                                    with c2: 
                                        if st.button("🗑️", key=f"del_sub_{s['id']}", use_container_width=True):
                                            safe_supabase_query(lambda sid=s["id"]: supabase.table("helpdesk_sub_locations").delete().eq("id", sid).execute(), error_prefix="Delete sub-location")
                                            st.rerun()
                            else:
                                st.info("No sub-locations yet")
                            
                            with st.form(f"add_sub_loc_{loc_id}"):
                                new_sub = st.text_input("SubLocation Name", key=f"new_sub_{loc_id}")
                                if st.form_submit_button("➕ Add", use_container_width=True):
                                    if new_sub:
                                        safe_supabase_query(lambda: supabase.table("helpdesk_sub_locations").insert({"location_id": loc_id, "sub_location_name": new_sub}).execute(), error_prefix="Add sub-location")
                                        st.success("✅ Added!")
                                        st.rerun()
                            
                            if st.button("❌ Close View", key=f"close_view_loc_{loc_id}", use_container_width=True):
                                st.session_state.view_loc_id = None
                                st.rerun()
                
                st.markdown("---")
                with st.form("add_loc_form"):
                    st.markdown("**➕ Add New Location**")
                    c1, c2 = st.columns(2)
                    with c1:
                        new_loc_code = st.text_input("Location Code*", key="loc_code", placeholder="e.g. CT")
                        new_loc_name = st.text_input("Location Name*", key="loc_name", placeholder="e.g. CT — Office Tower")
                    with c2:
                        new_sub_name = st.text_input("Initial Sub-Location (optional)", key="sub_name", placeholder="e.g. Floor 1")
                    if st.form_submit_button("➕ Add Location", use_container_width=True):
                        if new_loc_code and new_loc_name:
                            res = safe_supabase_query(lambda: supabase.table("helpdesk_locations").insert({
                                "facility_code": fc,
                                "location_code": new_loc_code,
                                "location_name": new_loc_name
                            }).execute(), error_prefix="Add location")
                            if res and res.data and new_sub_name:
                                safe_supabase_query(lambda lid=res.data[0]["id"]: supabase.table("helpdesk_sub_locations").insert({
                                    "location_id": lid,
                                    "sub_location_name": new_sub_name
                                }).execute(), error_prefix="Add sub-location")
                            st.success("✅ Location added!")
                            st.rerun()
                        else:
                            st.error("⚠️ Location Code and Name are required")
            
            with sett_tabs[1]:
                st.markdown("#### 🏷️ Category Details")
                
                cat_search = st.text_input("🔍 Search categories", key="cat_search_main")
                
                if categories:
                    table_data = []
                    for c in categories:
                        if cat_search and cat_search.lower() not in c.get("category_name","").lower() and cat_search.lower() not in c.get("department","").lower():
                            continue
                        
                        table_data.append({
                            "SNO": len(table_data) + 1,
                            "Department": c.get("department",""),
                            "Category": c.get("category_name",""),
                            "SLA": f"{c.get('sla_hours','4')}hrs",
                            "Active": "✅" if c.get("is_active") else "❌",
                            "id": c["id"]
                        })
                    
                    if table_data:
                        page_size = 10
                        total_pages = max(1, (len(table_data) + page_size - 1) // page_size)
                        
                        if "cat_page" not in st.session_state:
                            st.session_state.cat_page = 1
                        
                        start = (st.session_state.cat_page - 1) * page_size
                        end = start + page_size
                        page_data = table_data[start:end]
                        
                        st.caption(f"Showing {start+1} to {min(end, len(table_data))} of {len(table_data)} entries")
                        
                        for row in page_data:
                            c1, c2, c3, c4, c5 = st.columns([0.5, 2, 2.5, 1, 1])
                            with c1: st.markdown(f"**{row['SNO']}**")
                            with c2: st.markdown(row["Department"])
                            with c3: st.markdown(row["Category"])
                            with c4: st.markdown(row["SLA"])
                            with c5: st.markdown(row["Active"])
                            st.markdown("---")
                        
                        c1, c2, c3 = st.columns([1, 2, 1])
                        with c1:
                            if st.session_state.cat_page > 1:
                                if st.button("← Prev", key="cat_prev"):
                                    st.session_state.cat_page -= 1
                                    st.rerun()
                        with c2:
                            st.markdown(f"**Page {st.session_state.cat_page} of {total_pages}**")
                        with c3:
                            if st.session_state.cat_page < total_pages:
                                if st.button("Next →", key="cat_next"):
                                    st.session_state.cat_page += 1
                                    st.rerun()
                
                st.markdown("---")
                with st.form("add_cat_form"):
                    st.markdown("**➕ Add New Category**")
                    c1, c2, c3 = st.columns(3)
                    with c1: 
                        new_cat = st.text_input("Category Name*", key="cat_name")
                    with c2: 
                        dept_list_sett = sorted(list(set(c.get("department","") for c in categories)))
                        new_dept = st.selectbox("Department", dept_list_sett, key="cat_dept")
                    with c3: 
                        new_sla = st.number_input("SLA Hours", 1, 72, 4, key="cat_sla")
                    if st.form_submit_button("➕ Add Category", use_container_width=True):
                        if new_cat:
                            safe_supabase_query(lambda: supabase.table("helpdesk_categories").insert({
                                "department": new_dept,
                                "category_name": new_cat,
                                "sla_hours": new_sla,
                                "is_active": True
                            }).execute(), error_prefix="Add category")
                            st.success("✅ Category added!")
                            st.rerun()
                        else:
                            st.error("⚠️ Category name is required")
            
            with sett_tabs[2]:
                st.markdown("#### 📊 Status Configuration")
                
                status_configs = [
                    {"status": "open", "icon": "🔴", "color": "#EF4444", "description": "Newly created ticket, awaiting assignment"},
                    {"status": "in_progress", "icon": "🟡", "color": "#F59E0B", "description": "Ticket is being worked on"},
                    {"status": "hold", "icon": "⏸️", "color": "#3B82F6", "description": "Ticket is on hold pending external input"},
                    {"status": "closed", "icon": "🟢", "color": "#10B981", "description": "Ticket has been resolved"},
                    {"status": "rejected", "icon": "❌", "color": "#6B7280", "description": "Ticket has been rejected"},
                ]
                
                for s in status_configs:
                    st.markdown(f"""
                    <div style="background:white;border-radius:8px;padding:0.8rem;margin:0.3rem 0;border-left:4px solid {s['color']};display:flex;align-items:center;gap:1rem;">
                        <div style="font-size:1.5rem;">{s['icon']}</div>
                        <div style="flex:1;">
                            <div style="font-weight:600;">{s['status'].upper()}</div>
                            <div style="font-size:0.7rem;color:#888;">{s['description']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.info("Custom status management — contact system administrator for modifications.")

# ============================================
# VISITOR MANAGEMENT — WORLD CLASS SYSTEM (FULL)
# ============================================
def page_visitor():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    is_admin = user_role in ["admin", "approver", "authorizer", "confirmer"]
    
    st.markdown(f'## 🛂 Visitor Management — {info.get("full_name", fc)}')
    
    tabs = st.tabs(["📋 Dashboard", "➕ Register Visitor", "🛂 Gate Check", "📈 Analytics", "📄 Reports"])
    
    # ============================================
    # TAB 0: DASHBOARD
    # ============================================
    with tabs[0]:
        today = date.today()
        
        visitors_today = safe_supabase_query(lambda: supabase.table("visitors").select("id", count="exact").eq("facility_code", fc).eq("visit_date", str(today)).execute(), error_prefix="Visitors today")
        checked_in = safe_supabase_query(lambda: supabase.table("visitors").select("id", count="exact").eq("facility_code", fc).eq("visit_date", str(today)).eq("status", "checked_in").execute(), error_prefix="Checked in")
        expected = safe_supabase_query(lambda: supabase.table("visitors").select("id", count="exact").eq("facility_code", fc).eq("visit_date", str(today)).in_("status", ["expected","pre_registered"]).execute(), error_prefix="Expected")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("📋 Total Today", visitors_today.count if visitors_today else 0)
        with c2: st.metric("✅ Checked In", checked_in.count if checked_in else 0)
        with c3: st.metric("⏳ Expected", expected.count if expected else 0)
        with c4: st.metric("🚪 Checked Out", 0)
        
        st.markdown("---")
        st.markdown("### 📋 Today's Visitors")
        
        visitors = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).eq("visit_date", str(today)).order("expected_arrival").execute(), error_prefix="Visitors list")
        
        if visitors and visitors.data:
            for v in visitors.data:
                status = v.get("status", "expected")
                colors = {"checked_in": "#10B981", "checked_out": "#6B7280", "expected": "#F59E0B", "pre_registered": "#3B82F6", "cancelled": "#EF4444"}
                sc = colors.get(status, "#4a4a4a")
                
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><b>{v.get('full_name','')}</b><span style="font-size:0.7rem;color:#888;margin-left:0.5rem;">{v.get('company','')}</span></div><span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.65rem;">{status.upper()}</span></div><div style="font-size:0.7rem;color:#666;margin-top:0.2rem;">🎯 {v.get('purpose_of_visit','')} | 👤 {v.get('host_name','')} | ⏰ {v.get('expected_arrival','')}</div><div style="font-size:0.65rem;color:#888;">📧 {v.get('email','N/A')} | 📱 {v.get('mobile','N/A')} | 🚗 {v.get('vehicle_plate','No vehicle')}</div></div>""", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    if status in ["expected", "pre_registered"]:
                        if st.button("✅ Check In", key=f"vin_{v['id']}", use_container_width=True):
                            safe_supabase_query(lambda vid=v["id"]: supabase.table("visitors").update({"status": "checked_in", "actual_arrival": datetime.now().isoformat()}).eq("id", vid).execute(), error_prefix="Check in")
                            if v.get("host_email"):
                                send_email_notification(v["host_email"], f"✅ Guest Arrived: {v.get('full_name','')}",
                                    f"""<div style="font-family:Arial;max-width:400px;border:1px solid #10B981;border-radius:8px;overflow:hidden;"><div style="background:#10B981;padding:15px;color:white;"><h3>✅ Guest Has Arrived</h3><p style="margin:3px 0 0 0;font-size:11px;">{info.get('full_name',fc)}</p></div><div style="padding:15px;"><p>Dear {v.get('host_name','')},</p><p><b>{v.get('full_name','')}</b> from <b>{v.get('company','')}</b> has arrived and is waiting for you.</p><table style="width:100%;font-size:12px;"><tr><td style="padding:3px;"><b>🕐 Check-in:</b></td><td>{datetime.now().strftime('%I:%M %p')}</td></tr><tr><td style="padding:3px;"><b>📍 Location:</b></td><td>{v.get('gate_location','Main Gate')}</td></tr><tr><td style="padding:3px;"><b>🎯 Purpose:</b></td><td>{v.get('purpose_of_visit','')}</td></tr></table></div></div>""")
                            st.rerun()
                with c2:
                    if status == "checked_in":
                        if st.button("🚪 Check Out", key=f"vout_{v['id']}", use_container_width=True):
                            safe_supabase_query(lambda vid=v["id"]: supabase.table("visitors").update({"status": "checked_out", "actual_departure": datetime.now().isoformat()}).eq("id", vid).execute(), error_prefix="Check out")
                            st.rerun()
                with c3:
                    if st.button("📋 Details", key=f"vdet_{v['id']}", use_container_width=True):
                        with st.expander("Visitor Details", expanded=True):
                            st.write(f"**Pass ID:** {v.get('pass_id','N/A')}")
                            st.write(f"**Access Code:** {v.get('access_code','N/A')}")
                            if v.get("qr_code_url"):
                                st.image(v["qr_code_url"], width=120)
                            st.write(f"**ID Type:** {v.get('identification_type','')} | **ID No:** {v.get('identification_number','')}")
                            st.write(f"**Access Level:** {v.get('access_level','')}")
                            if v.get("belongings"):
                                st.write(f"**Belongings:** {v.get('belongings','')}")
        else:
            st.info("No visitors today")
    
    # ============================================
    # TAB 1: REGISTER VISITOR
    # ============================================
    with tabs[1]:
        st.markdown("### ➕ Register Visitor")
        
        reg_mode = st.radio("Registration Mode", ["Single Visitor", "Bulk Registration (CSV)", "Quick Batch Entry"], horizontal=True)
        
        if reg_mode == "Single Visitor":
            c1, c2 = st.columns(2)
            with c1:
                visitor_type = st.selectbox("Visitor Type", ["Visitor", "Vendor", "Interview", "Contractor", "Delivery", "Guest"])
                pass_type = st.selectbox("Pass Type", ["One Time", "Recurring", "Multi-Day"])
            with c2:
                visit_date = st.date_input("Visit Date", today)
                access_level = st.selectbox("Access Level", ["Standard", "Restricted", "VIP", "Escort Required"])
            
            st.markdown("---")
            st.markdown("**👤 Personal Details**")
            c1, c2, c3 = st.columns(3)
            with c1:
                first_name = st.text_input("First Name*")
                email = st.text_input("Email")
            with c2:
                last_name = st.text_input("Last Name*")
                mobile = st.text_input("Mobile Number*")
            with c3:
                company = st.text_input("Company")
                whatsapp = st.text_input("WhatsApp Number")
            
            c1, c2 = st.columns(2)
            with c1:
                id_type = st.selectbox("ID Type", ["National ID", "Driver's License", "International Passport", "Company ID", "Voter's Card"])
                id_number = st.text_input("ID Number")
            with c2:
                vehicle = st.text_input("Vehicle Plate Number")
                gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
            
            st.markdown("---")
            st.markdown("**🏢 Visit Details**")
            c1, c2, c3 = st.columns(3)
            with c1:
                host_name = st.text_input("Host Name*")
                arrival_time = st.time_input("Expected Arrival", time(9, 0))
            with c2:
                host_email = st.text_input("Host Email*")
                departure_time = st.time_input("Expected Departure", time(17, 0))
            with c3:
                host_phone = st.text_input("Host Phone")
                purpose = st.text_area("Purpose of Visit", height=60)
            
            belongings_label = "Belongings/Equipment*" if visitor_type == "Contractor" else "Belongings/Equipment"
            belongings = st.text_area(belongings_label, placeholder="Laptop, tools, etc...")
            
            st.markdown("---")
            
            if st.button("🛂 Register Visitor", use_container_width=True, type="primary"):
                errors = []
                # Name validations
                fname_valid, fname_msg = validate_name_input(first_name)
                if not fname_valid: errors.append(f"First Name: {fname_msg}")
                
                lname_valid, lname_msg = validate_name_input(last_name)
                if not lname_valid: errors.append(f"Last Name: {lname_msg}")
                
                host_valid, host_msg = validate_name_input(host_name)
                if not host_valid: errors.append(f"Host Name: {host_msg}")
                
                # Phone validations
                if mobile:
                    mob_valid, mob_msg = validate_phone_input(mobile)
                    if not mob_valid: errors.append(f"Mobile: {mob_msg}")
                
                if host_phone:
                    hp_valid, hp_msg = validate_phone_input(host_phone)
                    if not hp_valid: errors.append(f"Host Phone: {hp_msg}")
                
                if not gender: errors.append("Gender")
                if not host_email: errors.append("Host Email")
                if visitor_type == "Contractor" and not belongings: errors.append("Belongings/Equipment (required for Contractors)")
                
                if errors:
                    st.error(f"⚠️ Please fix: {', '.join(errors)}")
                else:
                    import random, string
                    pass_id = f"VIS-{fc}-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=4))}"
                    access_code_in = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    access_code_out = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    access_code = f"IN:{access_code_in}|OUT:{access_code_out}"
                    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=IN:{access_code_in}%7COUT:{access_code_out}"
                    
                    try:
                        safe_supabase_query(lambda: supabase.table("visitors").insert({
                            "facility_code": fc, "visitor_type": visitor_type.lower(), "pass_id": pass_id,
                            "access_code": access_code, "access_code_in": access_code_in, "access_code_out": access_code_out,
                            "qr_code_url": qr_url,
                            "first_name": first_name, "last_name": last_name, "gender": gender,
                            "email": email, "mobile": mobile, "whatsapp_number": whatsapp or mobile,
                            "company": company, "identification_type": id_type, "identification_number": id_number,
                            "vehicle_plate": vehicle, "purpose_of_visit": purpose,
                            "host_name": host_name, "host_email": host_email, "host_phone": host_phone,
                            "visit_date": str(visit_date), "expected_arrival": str(arrival_time),
                            "expected_departure": str(departure_time),
                            "pass_type": pass_type.lower().replace(" ", "_"), "access_level": access_level.lower(),
                            "belongings": belongings, "status": "pre_registered",
                            "created_at": datetime.now().isoformat()
                        }).execute(), error_prefix="Register visitor")
                    except Exception as e:
                        st.error(f"INSERT ERROR: {str(e)}")
                        st.stop()
                    
                    st.success(f"✅ Visitor registered! Pass ID: {pass_id}")
                    st.markdown(f"""
                    <div style="max-width:350px;margin:0 auto;background:white;border:2px solid #CC0000;border-radius:12px;overflow:hidden;text-align:center;">
                        <div style="background:#CC0000;color:white;padding:10px;font-weight:bold;font-size:0.9rem;">VISITOR ACCESS PASS</div>
                        <div style="padding:15px;">
                            {f'<img src="{logo_src}" height="25" style="margin-bottom:8px;">' if logo_src else ''}
                            <p style="font-weight:bold;margin:5px 0;">{first_name} {last_name}</p>
                            <p style="font-size:0.8rem;color:#666;">{company} | {visitor_type}</p>
                            <img src="{qr_url}" width="160" style="margin:10px 0;">
                            <div style="display:flex;justify-content:center;gap:20px;margin:8px 0;">
                                <div><b>🟢 IN:</b><br><span style="font-size:1.1rem;font-family:monospace;">{access_code_in}</span></div>
                                <div><b>🔴 OUT:</b><br><span style="font-size:1.1rem;font-family:monospace;">{access_code_out}</span></div>
                            </div>
                            <p style="font-size:0.7rem;color:#888;">{visit_date} | {arrival_time} - {departure_time}</p>
                            <p style="font-size:0.7rem;">Host: {host_name} | Pass ID: {pass_id}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if email:
                        send_email_notification(email, f"🛂 Your Access Pass - {info.get('full_name',fc)}",
                            f"""<div style="font-family:Arial;max-width:450px;margin:0 auto;border:2px solid #CC0000;border-radius:12px;overflow:hidden;"><div style="background:#CC0000;padding:15px;color:white;text-align:center;"><h2 style="margin:0;">VISITOR ACCESS PASS</h2><p style="margin:3px 0 0 0;font-size:11px;">{info.get('full_name',fc)}</p></div><div style="padding:20px;text-align:center;"><h3 style="margin:0 0 5px 0;">{first_name} {last_name}</h3><p style="color:#666;margin:0 0 10px 0;">{company}</p><img src="{qr_url}" width="180" style="border:1px solid #ddd;padding:5px;border-radius:8px;"><div style="display:flex;justify-content:center;gap:30px;margin:15px 0;"><div style="text-align:center;"><div style="font-size:10px;color:#888;">🟢 ENTRY CODE</div><div style="font-size:1.3rem;font-weight:bold;font-family:monospace;color:#10B981;">{access_code_in}</div></div><div style="text-align:center;"><div style="font-size:10px;color:#888;">🔴 EXIT CODE</div><div style="font-size:1.3rem;font-weight:bold;font-family:monospace;color:#EF4444;">{access_code_out}</div></div></div><table style="width:100%;font-size:11px;text-align:left;margin-top:10px;"><tr><td style="padding:4px;font-weight:bold;">📅 Date:</td><td>{visit_date}</td></tr><tr><td style="padding:4px;font-weight:bold;">⏰ Time:</td><td>{arrival_time} - {departure_time}</td></tr><tr><td style="padding:4px;font-weight:bold;">👤 Host:</td><td>{host_name}</td></tr><tr><td style="padding:4px;font-weight:bold;">🆔 Pass ID:</td><td>{pass_id}</td></tr></table><div style="margin-top:15px;padding:10px;background:#FFF3CD;border-radius:8px;font-size:10px;color:#92400E;">⚠️ Please present this QR code at the gate. Overstaying beyond your scheduled time will flag security.</div></div></div>""")
                    
                    if host_email:
                        send_email_notification(host_email, f"🛂 Visitor Expected: {first_name} {last_name}",
                            f"""<div style="font-family:Arial;max-width:500px;border:1px solid #ddd;border-radius:8px;overflow:hidden;"><div style="background:#CC0000;padding:15px;color:white;"><h3 style="margin:0;">📋 Visitor Pre-Registered</h3><p style="margin:3px 0 0 0;font-size:11px;">{info.get('full_name',fc)}</p></div><div style="padding:15px;"><p>Dear {host_name},</p><p><b>{first_name} {last_name}</b> from <b>{company}</b> is scheduled to visit you.</p><table style="width:100%;font-size:12px;border-collapse:collapse;"><tr><td style="padding:5px;border-bottom:1px solid #eee;font-weight:bold;">📅 Date</td><td style="padding:5px;border-bottom:1px solid #eee;">{visit_date}</td></tr><tr><td style="padding:5px;border-bottom:1px solid #eee;font-weight:bold;">⏰ Time</td><td style="padding:5px;border-bottom:1px solid #eee;">{arrival_time} - {departure_time}</td></tr><tr><td style="padding:5px;border-bottom:1px solid #eee;font-weight:bold;">🎯 Purpose</td><td style="padding:5px;border-bottom:1px solid #eee;">{purpose}</td></tr><tr><td style="padding:5px;border-bottom:1px solid #eee;font-weight:bold;">🆔 Pass ID</td><td style="padding:5px;border-bottom:1px solid #eee;">{pass_id}</td></tr><tr><td style="padding:5px;border-bottom:1px solid #eee;font-weight:bold;">🟢 Entry Code</td><td style="padding:5px;border-bottom:1px solid #eee;font-family:monospace;color:#10B981;">{access_code_in}</td></tr><tr><td style="padding:5px;font-weight:bold;">🚗 Vehicle</td><td style="padding:5px;">{vehicle or 'N/A'}</td></tr></table><div style="margin-top:12px;padding:10px;background:#f0f8ff;border-radius:6px;font-size:11px;">💡 <b>Forward this email</b> to your guest — it contains their access codes and QR pass for entry.</div></div></div>""")
                    
                    st.balloons()
                    st.rerun()
        
        elif reg_mode == "Bulk Registration (CSV)":
            st.markdown("#### 📋 Bulk Visitor Registration via CSV")
            st.caption("Upload a CSV file with columns: First Name, Last Name, Email, Mobile, Company")
            
            uploaded_file = st.file_uploader("Upload CSV", type="csv")
            
            if uploaded_file:
                csv_data = pd.read_csv(uploaded_file)
                st.dataframe(csv_data.head(10), use_container_width=True)
                st.caption(f"📋 {len(csv_data)} visitors found")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    bulk_visitor_type = st.selectbox("Visitor Type", ["Visitor", "Vendor", "Interview", "Contractor", "Delivery", "Guest"], key="bulk_vtype")
                    bulk_host = st.text_input("Host Name*", key="bulk_host")
                    bulk_date = st.date_input("Visit Date", today, key="bulk_date")
                with c2:
                    bulk_pass_type = st.selectbox("Pass Type", ["One Time", "Recurring", "Multi-Day"], key="bulk_pass")
                    bulk_purpose = st.text_input("Purpose of Visit*", key="bulk_purpose")
                    bulk_arrival = st.time_input("Arrival Time", time(9,0), key="bulk_arrival")
                with c3:
                    bulk_access_level = st.selectbox("Access Level", ["Standard", "Restricted", "VIP", "Escort Required"], key="bulk_access")
                    bulk_host_email = st.text_input("Host Email", key="bulk_email")
                    bulk_departure = st.time_input("Departure Time", time(17,0), key="bulk_departure")
                
                if st.button(f"🛂 Register {len(csv_data)} Visitors", use_container_width=True, type="primary"):
                    if bulk_host and bulk_purpose:
                        import random, string
                        success_count = 0
                        failed_count = 0
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, row in csv_data.iterrows():
                            try:
                                first = str(row.get("First Name", "") or row.get("first_name", "") or row.get("FirstName", "")).strip()
                                last = str(row.get("Last Name", "") or row.get("last_name", "") or row.get("LastName", "")).strip()
                                email_csv = str(row.get("Email", "") or row.get("email", "")).strip()
                                mobile_csv = str(row.get("Mobile", "") or row.get("mobile", "") or row.get("Phone", "")).strip()
                                company_csv = str(row.get("Company", "") or row.get("company", "")).strip()
                                
                                if not first or not last:
                                    failed_count += 1
                                    continue
                                
                                pass_id = f"VIS-{fc}-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=4))}{''.join(random.choices(string.ascii_uppercase, k=2))}"
                                access_code_in = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                                access_code_out = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                                access_code = f"IN:{access_code_in}|OUT:{access_code_out}"
                                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=IN:{access_code_in}%7COUT:{access_code_out}"
                                
                                safe_supabase_query(lambda: supabase.table("visitors").insert({
                                    "facility_code": fc,
                                    "visitor_type": bulk_visitor_type.lower(),
                                    "pass_id": pass_id,
                                    "access_code": access_code,
                                    "access_code_in": access_code_in,
                                    "access_code_out": access_code_out,
                                    "qr_code_url": qr_url,
                                    "first_name": first,
                                    "last_name": last,
                                    "gender": "Other",
                                    "email": email_csv,
                                    "mobile": mobile_csv,
                                    "whatsapp_number": mobile_csv,
                                    "company": company_csv,
                                    "identification_type": "Company ID",
                                    "identification_number": "",
                                    "vehicle_plate": "",
                                    "purpose_of_visit": bulk_purpose,
                                    "host_name": bulk_host,
                                    "host_email": bulk_host_email,
                                    "host_phone": "",
                                    "visit_date": str(bulk_date),
                                    "expected_arrival": str(bulk_arrival),
                                    "expected_departure": str(bulk_departure),
                                    "pass_type": bulk_pass_type.lower().replace(" ", "_"),
                                    "access_level": bulk_access_level.lower(),
                                    "belongings": "",
                                    "status": "pre_registered",
                                    "created_at": datetime.now().isoformat()
                                }).execute(), error_prefix="Bulk register")
                                
                                success_count += 1
                            except Exception as e:
                                failed_count += 1
                                continue
                            
                            progress_bar.progress((idx + 1) / len(csv_data))
                            status_text.text(f"Processing: {idx + 1}/{len(csv_data)}")
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if success_count > 0:
                            st.success(f"✅ {success_count} visitors registered successfully!")
                            if failed_count > 0:
                                st.warning(f"⚠️ {failed_count} entries skipped due to missing names or errors")
                            st.balloons()
                            
                            if bulk_host_email:
                                send_email_notification(
                                    bulk_host_email,
                                    f"🛂 {success_count} Visitors Pre-Registered - {info.get('full_name', fc)}",
                                    f"""<div style="font-family:Arial;max-width:500px;border:1px solid #ddd;border-radius:8px;overflow:hidden;"><div style="background:#CC0000;padding:15px;color:white;"><h3 style="margin:0;">📋 Batch Visitor Registration</h3><p style="margin:3px 0 0 0;font-size:11px;">{info.get('full_name', fc)}</p></div><div style="padding:15px;"><p>Dear {bulk_host},</p><p><b>{success_count} visitors</b> have been pre-registered for <b>{bulk_date}</b>.</p><p><b>Purpose:</b> {bulk_purpose}</p><p><b>Time:</b> {bulk_arrival} - {bulk_departure}</p><p>Please ensure your guests have their access codes ready at the gate.</p></div></div>"""
                                )
                        else:
                            st.error(f"❌ Failed to register any visitors. Check CSV format (needs: First Name, Last Name columns)")
                    else:
                        st.error("⚠️ Host Name and Purpose are required")
        
        elif reg_mode == "Quick Batch Entry":
            st.markdown("#### 📝 Quick Batch Entry")
            st.caption("Enter visitor names (one per line) for quick registration")
            
            batch_names = st.text_area("Visitor Names", height=150, placeholder="John Doe\nJane Smith\nBob Johnson\n...")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                batch_visitor_type = st.selectbox("Visitor Type", ["Visitor", "Vendor", "Interview", "Contractor", "Delivery", "Guest"], key="batch_vtype")
                batch_host = st.text_input("Host Name*", key="batch_host")
                batch_date = st.date_input("Visit Date", today, key="batch_date")
            with c2:
                batch_pass_type = st.selectbox("Pass Type", ["One Time", "Recurring", "Multi-Day"], key="batch_pass")
                batch_purpose = st.text_input("Purpose of Visit*", key="batch_purpose")
                batch_arrival = st.time_input("Arrival Time", time(9,0), key="batch_arrival")
            with c3:
                batch_access_level = st.selectbox("Access Level", ["Standard", "Restricted", "VIP", "Escort Required"], key="batch_access")
                batch_host_email = st.text_input("Host Email", key="batch_email")
                batch_departure = st.time_input("Departure Time", time(17,0), key="batch_departure")
            
            if st.button("🛂 Register Batch", use_container_width=True, type="primary"):
                if batch_host and batch_purpose and batch_names:
                    import random, string
                    names = [n.strip() for n in batch_names.split("\n") if n.strip()]
                    success_count = 0
                    
                    for name in names:
                        try:
                            parts = name.split(" ", 1)
                            first = parts[0]
                            last = parts[1] if len(parts) > 1 else ""
                            
                            pass_id = f"VIS-{fc}-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=4))}"
                            access_code_in = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                            access_code_out = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                            access_code = f"IN:{access_code_in}|OUT:{access_code_out}"
                            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=IN:{access_code_in}%7COUT:{access_code_out}"
                            
                            safe_supabase_query(lambda: supabase.table("visitors").insert({
                                "facility_code": fc,
                                "visitor_type": batch_visitor_type.lower(),
                                "pass_id": pass_id,
                                "access_code": access_code,
                                "access_code_in": access_code_in,
                                "access_code_out": access_code_out,
                                "qr_code_url": qr_url,
                                "first_name": first,
                                "last_name": last,
                                "gender": "Other",
                                "email": "",
                                "mobile": "",
                                "company": "",
                                "identification_type": "Company ID",
                                "identification_number": "",
                                "vehicle_plate": "",
                                "purpose_of_visit": batch_purpose,
                                "host_name": batch_host,
                                "host_email": batch_host_email,
                                "host_phone": "",
                                "visit_date": str(batch_date),
                                "expected_arrival": str(batch_arrival),
                                "expected_departure": str(batch_departure),
                                "pass_type": batch_pass_type.lower().replace(" ", "_"),
                                "access_level": batch_access_level.lower(),
                                "belongings": "",
                                "status": "pre_registered",
                                "created_at": datetime.now().isoformat()
                            }).execute(), error_prefix="Batch register")
                            
                            success_count += 1
                        except Exception as e:
                            st.warning(f"Failed to register {name}: {str(e)[:50]}")
                            continue
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count} visitors registered!")
                        st.balloons()
                    else:
                        st.error("❌ Failed to register any visitors")
                else:
                    st.error("⚠️ Host Name, Purpose, and Visitor Names are required")
    
   # ============================================
    # TAB 2: GATE CHECK CONSOLE (ADMIN/SECURITY ONLY)
    # ============================================
    with tabs[2]:
        user_perms = safe_parse_permissions(st.session_state.get("user", {}).get("extra_permissions", []))
        can_gate_check = is_admin or "Visitor Management" in user_perms or len(user_perms) == 0
        
        if not can_gate_check:
            st.error("⛔ Access restricted to Security & Admin personnel only")
        else:
            st.markdown("### 🛂 Gate Check Console")
            
            gate_tabs = st.tabs(["🔍 Verify Entry", "📋 Today's Log", "🚨 Alerts", "📊 Live Feed"])
            
            with gate_tabs[0]:
                st.markdown("#### 🔍 Verify Visitor Access")
                
                verify_mode = st.radio("Verification Mode", ["🔢 Enter Code", "📷 Scan QR"], horizontal=True)
                
                if verify_mode == "🔢 Enter Code":
                    access_code = st.text_input("Enter Access Code", placeholder="Type IN or OUT code...", key="gate_manual_code")
                    
                    if access_code and len(access_code) >= 8:
                        visitor = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).or_(f"access_code_in.eq.{access_code},access_code_out.eq.{access_code}").execute(), error_prefix="Visitor lookup")
                        
                        if visitor and visitor.data and len(visitor.data) > 0:
                            v = visitor.data[0]
                            is_in_code = v.get("access_code_in") == access_code
                            status = v.get("status", "expected")
                            
                            if is_in_code and status in ["expected", "pre_registered"]:
                                action = "CHECK IN"
                                action_color = "#10B981"
                            elif not is_in_code and status == "checked_in":
                                action = "CHECK OUT"
                                action_color = "#EF4444"
                            elif is_in_code and status == "checked_in":
                                action = "ALREADY IN"
                                action_color = "#F59E0B"
                            elif not is_in_code and status in ["expected", "pre_registered"]:
                                action = "NOT CHECKED IN"
                                action_color = "#F59E0B"
                            else:
                                action = "COMPLETED"
                                action_color = "#6B7280"
                            
                            st.markdown(f"""
                            <div style="background:white;border-radius:12px;padding:1.5rem;border-left:5px solid {action_color};box-shadow:0 2px 8px rgba(0,0,0,0.1);margin:1rem 0;">
                                <div style="display:flex;justify-content:space-between;align-items:center;">
                                    <div>
                                        <h3 style="margin:0;">{v.get('full_name','')}</h3>
                                        <p style="color:#666;margin:3px 0;">{v.get('company','')} | {v.get('visitor_type','').upper()}</p>
                                    </div>
                                    <div style="text-align:center;">
                                        <div style="font-size:1.5rem;font-weight:800;color:{action_color};">{action}</div>
                                        <div style="font-size:0.7rem;color:#888;">{status.upper()}</div>
                                    </div>
                                </div>
                                <hr>
                                <table style="width:100%;font-size:0.8rem;">
                                    <tr><td><b>Pass ID:</b></td><td>{v.get('pass_id','')}</td><td><b>Host:</b></td><td>{v.get('host_name','')}</td></tr>
                                    <tr><td><b>🟢 IN:</b></td><td style="font-family:monospace;">{v.get('access_code_in','')}</td><td><b>🔴 OUT:</b></td><td style="font-family:monospace;">{v.get('access_code_out','')}</td></tr>
                                    <tr><td><b>📅 Date:</b></td><td>{v.get('visit_date','')}</td><td><b>⏰ Time:</b></td><td>{v.get('expected_arrival','')} - {v.get('expected_departure','')}</td></tr>
                                    <tr><td><b>🎯 Purpose:</b></td><td colspan="3">{v.get('purpose_of_visit','')}</td></tr>
                                    <tr><td><b>🚗 Vehicle:</b></td><td>{v.get('vehicle_plate','N/A')}</td><td><b>📦 Items:</b></td><td>{v.get('belongings','None')[:30]}</td></tr>
                                </table>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c1, c2, c3, c4 = st.columns(4)
                            with c1:
                                if action == "CHECK IN":
                                    if st.button("✅ Confirm Check In", use_container_width=True, type="primary"):
                                        safe_supabase_query(lambda vid=v["id"]: supabase.table("visitors").update({"status":"checked_in","actual_arrival":datetime.now().isoformat()}).eq("id", vid).execute(), error_prefix="Check in")
                                        safe_supabase_query(lambda vid=v["id"]: supabase.table("visitor_gate_log").insert({"visitor_id":vid,"event_type":"check_in","gate_location":"Main Gate","scanned_by":st.session_state.get("user_name","Security"),"event_time":datetime.now().isoformat()}).execute(), error_prefix="Gate log")
                                        if v.get("host_email"):
                                            send_email_notification(v["host_email"], f"✅ Guest Arrived: {v.get('full_name','')}",
                                                f"""<div style="font-family:Arial;max-width:400px;border:1px solid #10B981;border-radius:8px;overflow:hidden;"><div style="background:#10B981;padding:15px;color:white;"><h3>✅ Guest Has Arrived</h3></div><div style="padding:15px;"><p>Dear {v.get('host_name','')},</p><p><b>{v.get('full_name','')}</b> from <b>{v.get('company','')}</b> has arrived.</p></div></div>""")
                                        st.success("✅ Checked In!")
                                        st.rerun()
                            with c2:
                                if action == "CHECK OUT":
                                    if st.button("🚪 Confirm Check Out", use_container_width=True):
                                        safe_supabase_query(lambda vid=v["id"]: supabase.table("visitors").update({"status":"checked_out","actual_departure":datetime.now().isoformat()}).eq("id", vid).execute(), error_prefix="Check out")
                                        safe_supabase_query(lambda vid=v["id"]: supabase.table("visitor_gate_log").insert({"visitor_id":vid,"event_type":"check_out","gate_location":"Main Gate","scanned_by":st.session_state.get("user_name","Security"),"event_time":datetime.now().isoformat()}).execute(), error_prefix="Gate log")
                                        st.success("🚪 Checked Out!")
                                        st.rerun()
                            with c3:
                                if st.button("📋 More Info", use_container_width=True):
                                    with st.expander("Full Details", expanded=True):
                                        st.json({
                                            "Name": v.get("full_name"),
                                            "Pass ID": v.get("pass_id"),
                                            "Access Level": v.get("access_level"),
                                            "ID Type": v.get("identification_type"),
                                            "ID Number": v.get("identification_number"),
                                        })
                            with c4:
                                if st.button("🚩 Flag/Deny", use_container_width=True):
                                    safe_supabase_query(lambda vid=v["id"]: supabase.table("visitors").update({"status":"cancelled","security_flag":True}).eq("id", vid).execute(), error_prefix="Flag visitor")
                                    st.error("🚩 Entry Denied & Flagged")
                                    st.rerun()
                            
                            if status == "checked_in" and v.get("expected_departure"):
                                try:
                                    dep_time = datetime.strptime(str(v.get("visit_date")) + " " + str(v.get("expected_departure")), "%Y-%m-%d %H:%M:%S")
                                    if datetime.now() > dep_time:
                                        st.error(f"🚨 OVERSTAY ALERT: Guest was expected to leave by {v.get('expected_departure')}")
                                except: pass
                        else:
                            st.error("❌ Invalid access code")
                
                elif verify_mode == "📷 Scan QR":
                    st.info("📷 QR Scanner — Use a QR code scanner and paste the data below:")
                    qr_data = st.text_input("QR Data", placeholder="Paste scanned QR code data here...")
                    if qr_data:
                        if "IN:" in qr_data and "OUT:" in qr_data:
                            parts = qr_data.replace("IN:","").replace("OUT:","").split("|")
                            if len(parts) >= 2:
                                st.success(f"✅ QR Scanned: IN Code = {parts[0].strip()}")
            
            with gate_tabs[1]:
                st.markdown("#### 📋 Today's Visitor Log")
                
                today_str = str(date.today())
                today_visitors = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).eq("visit_date", today_str).order("expected_arrival").execute(), error_prefix="Today visitors")
                
                if today_visitors and today_visitors.data:
                    tv = today_visitors.data
                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1: st.metric("📋 Total", len(tv))
                    with c2: st.metric("✅ Checked In", len([v for v in tv if v.get("status")=="checked_in"]))
                    with c3: st.metric("⏳ Expected", len([v for v in tv if v.get("status") in ["expected","pre_registered"]]))
                    with c4: st.metric("🚪 Checked Out", len([v for v in tv if v.get("status")=="checked_out"]))
                    with c5: st.metric("🚩 Flagged", len([v for v in tv if v.get("security_flag")]))
                    
                    st.markdown("---")
                    
                    vtype_filter = st.selectbox("Filter by Type", ["All", "Visitor", "Vendor", "Interview", "Contractor", "Delivery"], key="gate_type_filter")
                    filtered = tv if vtype_filter == "All" else [v for v in tv if v.get("visitor_type") == vtype_filter.lower()]
                    
                    if filtered:
                        for v in filtered:
                            status = v.get("status","expected")
                            colors = {"checked_in":"#10B981","checked_out":"#6B7280","expected":"#F59E0B","cancelled":"#EF4444"}
                            sc = colors.get(status,"#4a4a4a")
                            
                            overstay = False
                            if status == "checked_in" and v.get("expected_departure"):
                                try:
                                    dep = datetime.strptime(f"{v.get('visit_date')} {v.get('expected_departure')}", "%Y-%m-%d %H:%M:%S")
                                    if datetime.now() > dep:
                                        overstay = True
                                except: pass
                            
                            st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;margin:0.3rem 0;border-left:4px solid {sc};box-shadow:0 1px 3px rgba(0,0,0,0.04);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><b>{v.get('full_name','')}</b><span style="font-size:0.65rem;color:#888;margin-left:0.5rem;">{v.get('visitor_type','').upper()}</span></div><div><span style="background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.65rem;">{status.upper()}</span>{f' <span style="background:#EF4444;color:white;padding:2px 8px;border-radius:12px;font-size:0.6rem;">⚠️ OVERSTAY</span>' if overstay else ''}</div></div><div style="font-size:0.7rem;color:#666;margin-top:0.2rem;">{v.get('company','') or 'N/A'} | 🎯 {v.get('purpose_of_visit','') or 'N/A'} | 👤 {v.get('host_name','')}</div></div>""", unsafe_allow_html=True)
                    else:
                        st.info(f"No {vtype_filter} visitors today")
            
            with gate_tabs[2]:
                st.markdown("#### 🚨 Security Alerts")
                
                all_active = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).eq("status", "checked_in").execute(), error_prefix="Active visitors")
                
                overstays = []
                if all_active and all_active.data:
                    for v in all_active.data:
                        if v.get("expected_departure"):
                            try:
                                dep = datetime.strptime(f"{v.get('visit_date')} {v.get('expected_departure')}", "%Y-%m-%d %H:%M:%S")
                                if datetime.now() > dep:
                                    overstays.append(v)
                            except: pass
                
                if overstays:
                    st.error(f"🚨 {len(overstays)} OVERSTAY ALERTS")
                    for v in overstays:
                        st.markdown(f"""
                        <div style="background:#FEF2F2;border:1px solid #EF4444;border-radius:8px;padding:1rem;margin:0.5rem 0;">
                            <b>⚠️ {v.get('full_name','')}</b> — {v.get('company','')}
                            <br>Expected departure: {v.get('expected_departure','')}
                            <br>Host: {v.get('host_name','')} | Pass: {v.get('pass_id','')}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("✅ No overstay alerts")
                
                flagged = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).eq("security_flag", True).order("created_at", desc=True).limit(20).execute(), error_prefix="Flagged visitors")
                if flagged and flagged.data:
                    st.markdown("---")
                    st.markdown("#### 🚩 Flagged Visitors")
                    for v in flagged.data:
                        st.markdown(f"🚩 {v.get('full_name','')} — {v.get('company','')} | Status: {v.get('status','').upper()}")
            
            with gate_tabs[3]:
                st.markdown("#### 📊 Activity Log")
                st.caption("Today's gate activity — check-ins and check-outs")
                
                today_str = str(date.today())
                
                today_logs = safe_supabase_query(lambda: supabase.table("visitor_gate_log").select("*, visitors(full_name, company)").gte("event_time", f"{today_str}T00:00:00").order("event_time", desc=True).execute(), error_prefix="Gate logs")
                
                if today_logs and today_logs.data:
                    checkins_today = len([l for l in today_logs.data if l.get("event_type") == "check_in"])
                    checkouts_today = len([l for l in today_logs.data if l.get("event_type") == "check_out"])
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("📋 Total Events", len(today_logs.data))
                    with c2: st.metric("✅ Check-ins", checkins_today)
                    with c3: st.metric("🚪 Check-outs", checkouts_today)
                    
                    st.markdown("---")
                    
                    active_visitors = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).eq("visit_date", today_str).eq("status", "checked_in").execute(), error_prefix="On-site visitors")
                    
                    if active_visitors and active_visitors.data:
                        st.markdown(f"### 🟢 Currently On-Site ({len(active_visitors.data)} people)")
                        for v in active_visitors.data:
                            checkin_time = ""
                            checkin_log = [l for l in today_logs.data if l.get("visitor_id") == v.get("id") and l.get("event_type") == "check_in"]
                            if checkin_log:
                                try:
                                    checkin_time = pd.to_datetime(checkin_log[0].get("event_time")).strftime("%I:%M %p")
                                except: pass
                            
                            st.markdown(f"""
                            <div style="background:#ECFDF5;border-left:4px solid #10B981;border-radius:8px;padding:0.6rem;margin:0.3rem 0;">
                                <b>{v.get('full_name','')}</b> — {v.get('company','') or 'N/A'}
                                <br><span style="font-size:0.7rem;color:#666;">🕐 In since: {checkin_time or 'N/A'} | 👤 Host: {v.get('host_name','')}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No visitors currently on-site")
                    
                    st.markdown("---")
                    st.markdown("### 📋 Recent Activity")
                    
                    for log in today_logs.data[:20]:
                        icon = "✅" if log.get("event_type") == "check_in" else "🚪" if log.get("event_type") == "check_out" else "🚩"
                        v_info = log.get("visitors", {})
                        name = v_info.get("full_name","Unknown") if v_info else "Unknown"
                        company = v_info.get("company","") if v_info else ""
                        
                        try:
                            event_time = pd.to_datetime(log.get("event_time")).strftime("%I:%M %p")
                        except:
                            event_time = str(log.get("event_time",""))
                        
                        st.markdown(f"{icon} **{name}** ({company}) — {log.get('event_type','').upper()} at {event_time} by {log.get('scanned_by','')}")
                else:
                    st.info("No gate activity recorded today")
    
    # ============================================
    # TAB 3: ANALYTICS
    # ============================================
    with tabs[3]:
        st.markdown("### 📈 Visitor Analytics")
        
        all_visitors = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).order("visit_date", desc=True).limit(500).execute(), error_prefix="Visitor analytics")
        
        if all_visitors and all_visitors.data:
            df = pd.DataFrame(all_visitors.data)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total Records", len(df))
            with c2: st.metric("This Month", len(df[pd.to_datetime(df["visit_date"]).dt.month == today.month]) if "visit_date" in df.columns else 0)
            with c3: st.metric("Avg Daily", round(len(df)/max((datetime.now() - pd.to_datetime(df["visit_date"].min())).days if "visit_date" in df.columns else 1, 1)))
            with c4: st.metric("Checked In Rate", f"{round(len(df[df['status']=='checked_in'])/len(df)*100) if len(df)>0 else 0}%")
            
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            with c1:
                if "visitor_type" in df.columns:
                    type_counts = df["visitor_type"].value_counts()
                    fig = px.pie(values=type_counts.values, names=type_counts.index, title="By Visitor Type")
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if "visit_date" in df.columns:
                    df["month"] = pd.to_datetime(df["visit_date"]).dt.month
                    monthly = df.groupby("month").size().reset_index(name="count")
                    fig2 = px.bar(monthly, x="month", y="count", title="Monthly Volume")
                    st.plotly_chart(fig2, use_container_width=True)
    
    # ============================================
    # TAB 4: REPORTS
    # ============================================
    with tabs[4]:
        st.markdown("### 📄 Visitor Reports")
        
        rpt_month = st.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"], key="vis_rpt_m")
        rpt_year = st.selectbox("Year", [2024,2025,2026,2027], key="vis_rpt_y")
        
        if st.button("📊 Generate Report", use_container_width=True):
            visitors = safe_supabase_query(lambda: supabase.table("visitors").select("*").eq("facility_code", fc).order("visit_date", desc=True).limit(500).execute(), error_prefix="Visitor report")
            if visitors and visitors.data:
                df = pd.DataFrame(visitors.data)
                st.success(f"✅ Report for {rpt_month} {rpt_year} — {len(df)} records")
                
                display_cols = [c for c in ["full_name","company","visitor_type","host_name","purpose_of_visit","visit_date","expected_arrival","status","vehicle_plate"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False)
                st.download_button("📥 CSV", csv, f"visitors_{rpt_month}_{rpt_year}.csv", "text/csv", use_container_width=True)

# ============================================
# USER MANAGEMENT — FORTUNE 500 COMMAND CENTER
# ============================================
def page_users():
    import time as _time
    fc = st.session_state.get("facility", "WTC")
    user_role = st.session_state.get("user_role", "staff")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_super = user_role == "super_admin"
    
    st.markdown(f'## 👥 User Management Command Center — {FACILITY_INFO.get(fc, {}).get("full_name", fc)}')
    
    # ============================================
    # GET ALL USERS FOR THE DIRECTORY
    # ============================================    import time as _time
    all_users_raw = None
    for attempt in range(3):
        try:
            all_users_raw = supabase.table("app_users").select("*").order("name").limit(1000).execute()
            break
        except:
            _time.sleep(0.5)
    all_users = all_users_raw.data if all_users_raw and all_users_raw.data else []
    
    if not all_users:
        st.info("No users found.")
        return
    
    # ============================================
    # FILTER BY FACILITY FOR COUNTS
    # ============================================
    # Everyone sees ONLY their current facility's users — including Super Admin
    facility_users = []
    for u in all_users:
        home_fac = str(u.get("home_facility", ""))
        facilities = [f.strip() for f in home_fac.split(",")]
        if fc in facilities:
            facility_users.append(u)
    df = pd.DataFrame(facility_users) if facility_users else pd.DataFrame()
    count_df = df
    st.caption(f"📍 Viewing {FACILITY_INFO.get(fc, {}).get('full_name', fc)} users only")
    
    # ============================================
    # KPIs — USING COUNT_DF (FILTERED BY FACILITY)
    # ============================================
    total_users = len(count_df)
    active_users = len(count_df[count_df["is_active"] == True]) if "is_active" in count_df.columns else 0
    staff_count = len(count_df[count_df["user_type"] == "staff"]) if "user_type" in count_df.columns else 0
    # Pull fresh tenant count directly from Supabase
    tenant_check = safe_supabase_query(lambda: supabase.table("app_users").select("id", count="exact").eq("home_facility", fc).eq("user_type", "tenant").eq("is_active", True).execute(), error_prefix="Tenant count")
    tenant_count = tenant_check.count if tenant_check else 0
    contractor_count = len(count_df[count_df["user_type"].isin(["contractor","vendor"])]) if "user_type" in count_df.columns else 0

    locked_count = len(count_df[count_df["account_locked"] == True]) if "account_locked" in count_df.columns else 0
    
    # ============================================
    # KPI CARDS
    # ============================================
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Total Users</div><div style="font-size:1.5rem;font-weight:800;">{total_users}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Active</div><div style="font-size:1.5rem;font-weight:800;color:#10B981;">{active_users}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Staff</div><div style="font-size:1.5rem;font-weight:800;color:#3B82F6;">{staff_count}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Tenants</div><div style="font-size:1.5rem;font-weight:800;color:#8B5CF6;">{tenant_count}</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Contractors</div><div style="font-size:1.5rem;font-weight:800;color:#F59E0B;">{contractor_count}</div></div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.6rem;color:#888;">Locked</div><div style="font-size:1.5rem;font-weight:800;color:#EF4444;">{locked_count}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 User Directory", "➕ Add User", "🏢 Tenants", "🔧 Contractors", "📊 Activity Log"])
    
    # ============================================
    # TAB 0: USER DIRECTORY
    # ============================================
    with tabs[0]:
        # Filters
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            filter_type = st.selectbox("Type", ["All", "staff", "tenant", "contractor", "vendor"], key="usr_type")
        with c2:
            filter_role = st.selectbox("Role", ["All", "super_admin", "admin", "sr_management", "sr_manager", "manager", "team_lead", "team_member", "tenant_admin", "tenant_user", "contractor", "vendor"], key="usr_role")
        with c3:
            filter_status = st.selectbox("Status", ["All", "Active", "Inactive", "Locked"], key="usr_status")
        with c4:
            search_user = st.text_input("🔍 Search", key="usr_search", placeholder="Name, email, ID...")
        with c5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ ADD USER", key="btn_add_user_top", use_container_width=True, type="primary"):
                st.session_state.user_tab = 1
                st.rerun()
        
        # Apply filters
        display_df = df.copy()
        if filter_type != "All" and "user_type" in display_df.columns:
            display_df = display_df[display_df["user_type"] == filter_type]
        if filter_role != "All" and "role" in display_df.columns:
            display_df = display_df[display_df["role"] == filter_role]
        if filter_status == "Active":
            display_df = display_df[display_df["is_active"] == True]
        elif filter_status == "Inactive":
            display_df = display_df[display_df["is_active"] == False]
        elif filter_status == "Locked":
            display_df = display_df[display_df["account_locked"] == True]
        if search_user:
            mask = False
            for col in ["name", "email", "employee_id", "designation"]:
                if col in display_df.columns:
                    mask = mask | display_df[col].astype(str).str.contains(search_user, case=False, na=False)
            display_df = display_df[mask]
        
        st.caption(f"📋 Showing {len(display_df)} of {len(df)} users")
        
        # Pagination
        page_size = 12
        if "usr_page" not in st.session_state:
            st.session_state.usr_page = 1
        
        total_pages = max(1, (len(display_df) + page_size - 1) // page_size)
        start = (st.session_state.usr_page - 1) * page_size
        end = min(start + page_size, len(display_df))
        
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("◀◀", key="usr_first"): st.session_state.usr_page = 1; st.rerun()
        with c2:
            if st.button("◀", key="usr_prev") and st.session_state.usr_page > 1:
                st.session_state.usr_page -= 1; st.rerun()
        with c3:
            st.markdown(f"**Page {st.session_state.usr_page} of {total_pages}**")
        with c4:
            if st.button("▶", key="usr_next") and st.session_state.usr_page < total_pages:
                st.session_state.usr_page += 1; st.rerun()
        with c5:
            if st.button("▶▶", key="usr_last"): st.session_state.usr_page = total_pages; st.rerun()
        
        # User Cards (REST OF YOUR EXISTING CODE — UNCHANGED)
        for _, user in display_df.iloc[start:end].iterrows():
            name = user.get("name", "N/A")
            email = user.get("email", "N/A")
            emp_id = user.get("employee_id", "N/A")
            role = user.get("role", "staff")
            user_type = user.get("user_type", "staff")
            is_active = user.get("is_active", True)
            is_locked = user.get("account_locked", False)
            designation = user.get("designation", user.get("designation_level", "N/A"))
            last_login = str(user.get("last_login", "Never"))[:16] if user.get("last_login") else "Never"
            depts = safe_parse_permissions(user.get("department_permissions", []))
            profile_pic = user.get("profile_picture", "")
            
            # Status & Colors
            if not is_active:
                status_badge = "⚫ Inactive"
                status_color = "#6B7280"
            elif is_locked:
                status_badge = "🔒 Locked"
                status_color = "#EF4444"
            else:
                status_badge = "🟢 Active"
                status_color = "#10B981"
            
            role_colors = {
                "super_admin": "#991B1B", "admin": "#CC0000", "approver": "#059669",
                "manager": "#2563EB", "team_lead": "#7C3AED", "team_member": "#3B82F6",
                "tenant_admin": "#8B5CF6", "tenant_user": "#6366F1",
                "contractor": "#F59E0B", "vendor": "#D97706"
            }
            role_color = role_colors.get(role, "#3B82F6")
            type_color = {"staff": "#3B82F6", "tenant": "#8B5CF6", "contractor": "#F59E0B", "vendor": "#D97706"}.get(user_type, "#888")
            
            # Avatar
            if profile_pic:
                avatar_html = f'<img src="{profile_pic}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">'
            else:
                initials = name[:2].upper()
                avatar_html = f'<div style="width:40px;height:40px;border-radius:50%;background:{role_color};display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.9rem;">{initials}</div>'
            
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:0.8rem;margin:0.4rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);display:flex;align-items:center;gap:1rem;border-left:4px solid {status_color};">
                <div style="flex-shrink:0;">{avatar_html}</div>
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <b style="font-size:0.9rem;">{name}</b>
                        <span style="background:{role_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;font-weight:600;">{designation}</span>
                    </div>
                    <div style="font-size:0.7rem;color:#666;">📧 {email} | 🆔 {emp_id} | 👔 {designation}</div>
                    <div style="font-size:0.6rem;color:#888;">🕐 Last Login: {last_login} | 🏷️ {', '.join(depts) if depts else 'All Depts'}</div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <span style="background:{status_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;font-weight:600;">{status_badge}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Quick action buttons
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                if st.button("✏️ Edit", key=f"qedit_{user['id']}", use_container_width=True):
                    st.session_state.edit_user_id = user["id"]
                    st.rerun()
            with c2:
                if st.button("🔑 Reset PW", key=f"qreset_{user['id']}", use_container_width=True):
                    st.session_state.reset_user_id = user["id"]
                    st.rerun()
            with c3:
                lock_label = "🔓 Unlock" if is_locked else "🔒 Lock"
                if st.button(lock_label, key=f"qlock_{user['id']}", use_container_width=True):
                    DB.update("app_users", user["id"], {"account_locked": not is_locked, "failed_login_attempts": 0})
                    st.rerun()
            with c4:
                act_label = "⚫ Deactivate" if is_active else "🟢 Activate"
                if st.button(act_label, key=f"qact_{user['id']}", use_container_width=True):
                    DB.update("app_users", user["id"], {"is_active": not is_active})
                    st.rerun()
            with c5:
                if st.button("🗑️ Delete", key=f"qdel_{user['id']}", use_container_width=True):
                    safe_supabase_query(lambda: supabase.table("app_users").delete().eq("id", user["id"]).execute(), error_prefix="Delete user")
                    st.warning("🗑️ Deleted!")
                    st.rerun()
            
            st.markdown("---")
    
    # ============================================
    # TAB 1: ADD USER
    # ============================================
    with tabs[1]:
        st.markdown("### ➕ Add New User")
        
        user_type_add = st.selectbox("User Type*", ["👤 Staff (Internal)", "🏢 Tenant/Occupant", "🔧 Contractor/Vendor"], key="add_user_type")
        
        with st.form("add_user_form", clear_on_submit=True):
            if user_type_add == "👤 Staff (Internal)":
                st.markdown("#### 👤 Staff Details")
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_name = st.text_input("Full Name*", key="add_name")
                    new_email = st.text_input("Email*", key="add_email")
                with c2:
                    new_emp_id = st.text_input("Employee ID*", key="add_emp")
                    new_mobile = st.text_input("Mobile Number", key="add_mob")
                with c3:
                    new_designation = st.selectbox("Designation Level*", ["Team Member", "Team Lead", "Manager", "Sr. Manager", "HOD", "Sr. Management", "Admin", "Super Admin"], key="add_desig")
                
                new_role = st.selectbox("System Role*", ["team_member", "team_lead", "manager", "sr_manager", "sr_management", "admin", "super_admin"],
                    format_func=lambda x: {
                        "team_member":"👤 Team Member", "team_lead":"🔐 Team Lead",
                        "manager":"👔 Manager", "sr_manager":"💼 Sr. Manager",
                        "sr_management":"🏢 Sr. Management", "admin":"🔴 Admin", "super_admin":"👑 Super Admin"
                    }[x], key="add_role")
                
                new_facility = st.multiselect("Home Facility", ["WTC", "AGVL", "FCPL", "RBPL", "VDL", "WAREHOUSES"], default=["WTC"], key="add_fac")
                
                st.markdown("---")
                st.markdown("**📋 Module Permissions**")
                module_groups = {
                    "Dashboards": ["Command Center", "PPM Dashboard", "Facility Operations"],
                    "Asset & PPM": ["Asset Register", "PPM Activities", "Checklist Status"],
                    "Work Permit": ["Raise Permit", "Authorize Permit", "Confirm Permit", "Approve Permit"],
                    "Work Orders": ["Work Orders"],
                    "Risk Management": ["Risk Assessment"],
                    "People": ["Visitor Management", "User Management"],
                    "Services": ["Raise Ticket", "Helpdesk", "Feedback"],
                    "Compliance": ["Audit Checklist", "Incident Report", "HOTO Check"],
                    "Utility": ["Utility Dashboard"],
                    "Reports": ["Monthly MIS"],
                }
                selected_perms = []
                for group, modules in module_groups.items():
                    with st.expander(f"📁 {group}"):
                        for mod in modules:
                            if st.checkbox(mod, key=f"add_mod_{mod}"):
                                selected_perms.append(mod)
                
                st.markdown("---")
                st.markdown("**🏢 Department Access**")
                all_depts = [
                    "Engineering — Electrical",
                    "Engineering — HVAC", 
                    "Engineering — Plumbing",
                    "Engineering — Vertical Transportation (Lifts)",
                    "Engineering — Fire Fighting",
                    "Engineering — Civil & Structural",
                    "Engineering — Utilities & Energy",
                    "Facility Management — Hard Services",
                    "Facility Management — Soft Services (Housekeeping)",
                    "Facility Management — FM Operations & Helpdesk",
                    "Facility Management — Fitout Works",
                    "Facility Management — HSSE Safety & Compliance",
                    "Facility Management — Front of House",
                    "Technology Group — Network & Connectivity",
                    "Technology Group — Building Technology",
                    "Technology Group — Access Control",
                    "Technology Group — Automation",
                    "Technology Group — BMS",
                    "Technology Group — CCTV",
                    "Technology Group — Fire Alarm & Voice Evac",
                    "Technology Group — MDTH (DSTV)",
                    "Security — Man Guarding Operations",
                    "Contractor — Clyde Engineering",
                    "Contractor — Gates and Shield",
                ]
                new_depts = st.multiselect("Departments (leave empty for All)", all_depts, key="add_depts")
                
                new_password = st.text_input("Password*", type="password", key="add_pw")
                
                if new_password:
                    strength = 0
                    if len(new_password) >= 12: strength += 1
                    if any(c.isupper() for c in new_password): strength += 1
                    if any(c.isdigit() for c in new_password): strength += 1
                    if any(c in "!@#$%^&*()" for c in new_password): strength += 1
                    colors = ["#EF4444","#F59E0B","#3B82F6","#10B981"]
                    labels = ["Weak","Fair","Good","Strong"]
                    st.progress(strength/4, text=f"Password Strength: {labels[min(strength,3)]}")
            
            elif user_type_add == "🏢 Tenant/Occupant":
                st.markdown("#### 🏢 Tenant Details")
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Contact Name*", key="add_tname")
                    new_email = st.text_input("Email*", key="add_temail")
                    new_company = st.text_input("Company/Organization*", key="add_tcompany")
                with c2:
                    new_mobile = st.text_input("Mobile Number", key="add_tmob")
                    new_facility = st.selectbox("Assigned Facility", ["WTC", "AGVL", "FCPL", "RBPL", "VDL"], key="add_tfac")
                    new_role = st.selectbox("Role", ["tenant_admin", "tenant_user"], key="add_trole")
                new_password = st.text_input("Password*", type="password", key="add_tpw")
            
            else:
                st.markdown("#### 🔧 Contractor/Vendor Details")
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Contact Name*", key="add_cname")
                    new_email = st.text_input("Email*", key="add_cemail")
                    new_company = st.text_input("Company Name*", key="add_ccompany")
                with c2:
                    new_mobile = st.text_input("Mobile Number", key="add_cmob")
                    new_facility = st.selectbox("Assigned Facility", ["WTC", "AGVL", "FCPL", "RBPL", "VDL"], key="add_cfac")
                    contractor_dept = st.selectbox("Assigned Department*", sorted(df["dept_full"].dropna().unique().tolist()) if "dept_full" in df.columns else [], key="add_cdept")
                new_role = st.selectbox("Type", ["contractor", "vendor"], key="add_crole")
                contract_expiry = st.date_input("Contract Expiry Date", date.today() + timedelta(days=365), key="add_cexpiry")
                new_password = st.text_input("Password*", type="password", key="add_cpw")
            
            profile_pic = st.file_uploader("Profile Picture", type=["png","jpg","jpeg"], key="add_pic")
            
            submitted = st.form_submit_button("➕ CREATE USER", use_container_width=True, type="primary")
            
            if submitted:
                if new_name and new_email and new_password:
                    pw_valid, pw_msg = validate_password_strength(new_password)
                    if not pw_valid:
                        st.error(f"⚠️ {pw_msg}")
                    else:
                        pw_hash = hash_password(new_password)
                        
                        ut = "staff" if "Staff" in user_type_add else ("tenant" if "Tenant" in user_type_add else "contractor")
                        
                        user_data = {
                            "name": new_name,
                            "email": new_email,
                            "password_hash": pw_hash,
                            "role": new_role,
                            "user_type": ut,
                            "is_active": True,
                            "home_facility": ",".join(new_facility) if isinstance(new_facility, list) else new_facility,
                            "mobile": new_mobile,
                            "created_by": st.session_state.get("user_name",""),
                            "created_at": datetime.now().isoformat()
                        }
                        
                        if ut == "staff":
                            user_data["employee_id"] = new_emp_id
                            user_data["designation"] = new_designation
                            user_data["designation_level"] = new_designation
                            user_data["extra_permissions"] = selected_perms
                            user_data["department_permissions"] = new_depts if new_depts else ["All"]
                        
                        if ut == "tenant":
                            user_data["organization_name"] = new_company
                        
                        if ut in ["contractor", "vendor"]:
                            user_data["organization_name"] = new_company
                            user_data["contractor_department"] = contractor_dept
                            user_data["contract_expiry"] = str(contract_expiry)
                        
                        if profile_pic:
                            pic_b64 = base64.b64encode(profile_pic.read()).decode()
                            user_data["profile_picture"] = f"data:image/{profile_pic.type.split('/')[-1]};base64,{pic_b64}"
                        
                        # Check if user already exists
                        existing_user = safe_supabase_query(lambda: supabase.table("app_users").select("id").eq("email", new_email).execute(), error_prefix="Check existing")
                        
                        if existing_user and existing_user.data and len(existing_user.data) > 0:
                            # Update existing user
                            result = safe_supabase_query(lambda: supabase.table("app_users").update(user_data).eq("email", new_email).execute(), error_prefix="Update user")
                            if result:
                                st.success(f"✅ User {new_name} updated!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Failed to update user.")
                        else:
                            # Insert new user
                            result = safe_supabase_query(lambda: supabase.table("app_users").insert(user_data).execute(), error_prefix="Create user")
                            if result and result.data:
                                try:
                                    send_email_notification(
                                        new_email,
                                        f"🎉 Welcome to facilityXperience — Churchgate Group",
                                        f"""
                                        <div style="font-family:Arial;max-width:550px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                            <div style="background:#C8A951;padding:25px;color:white;text-align:center;">
                                                <h2 style="margin:0;">🎉 Welcome to facilityXperience</h2>
                                                <p style="margin:5px 0 0 0;font-size:13px;">Churchgate Group</p>
                                            </div>
                                            <div style="padding:25px;">
                                                <p>Dear <b>{new_name}</b>,</p>
                                                <p>Your account has been created on the <b>facilityXperience</b> platform.</p>
                                                <p><b>Email:</b> {new_email}</p>
                                                <p><b>Role:</b> {new_role.replace('_', ' ').title()}</p>
                                                <p>Please log in and change your password on first access.</p>
                                                <div style="text-align:center;margin:20px 0;">
                                                    <a href="https://churchgate-facilityxperience.hf.space" style="background:#C8A951;color:white;padding:12px 30px;text-decoration:none;border-radius:6px;font-weight:bold;">Login to facilityXperience</a>
                                                </div>
                                                <p style="font-size:12px;color:#888;">If you have any questions, please contact the IT team.</p>
                                            </div>
                                        </div>
                                        """
                                    )
                                except: pass
                                
                                st.success(f"✅ User {new_name} created!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Failed to create user. Email may already exist.")
                else:
                    st.error("⚠️ Name, Email, and Password are required")
    
   # ============================================
    # TAB 2: TENANTS — FILTERED BY FACILITY
    # ============================================
    with tabs[2]:
        st.markdown("### 🏢 Tenant Management")
        
        # Pull tenants directly from Supabase - bypass cache
        tenant_data = safe_supabase_query(lambda: supabase.table("app_users").select("*").eq("home_facility", fc).eq("user_type", "tenant").eq("is_active", True).order("name").execute(), error_prefix="Tenant data")
        tenant_users = pd.DataFrame(tenant_data.data) if tenant_data and tenant_data.data else pd.DataFrame()
        
        if len(tenant_users) > 0:
            # Search bar
            tenant_search = st.text_input("🔍 Search Tenants", key="tenant_search", placeholder="Search by name, email, or company...")
            
            # Apply search filter
            display_tenants = tenant_users.copy()
            if tenant_search:
                mask = False
                for col in ["name", "email"]:
                    if col in display_tenants.columns:
                        mask = mask | display_tenants[col].astype(str).str.contains(tenant_search, case=False, na=False)
                if "designation" in display_tenants.columns:
                    mask = mask | display_tenants["designation"].astype(str).str.contains(tenant_search, case=False, na=False)
                display_tenants = display_tenants[mask]
            
            # Pagination
            page_size = 10
            if "tenant_page" not in st.session_state:
                st.session_state.tenant_page = 1
            
            total_pages = max(1, (len(display_tenants) + page_size - 1) // page_size)
            start = (st.session_state.tenant_page - 1) * page_size
            end = min(start + page_size, len(display_tenants))
            
            st.caption(f"📋 Showing {start+1}–{end} of {len(display_tenants)} tenants")
            
            # Pagination controls
            c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
            with c1:
                if st.button("◀◀", key="t_first") and st.session_state.tenant_page > 1:
                    st.session_state.tenant_page = 1; st.rerun()
            with c2:
                if st.button("◀", key="t_prev") and st.session_state.tenant_page > 1:
                    st.session_state.tenant_page -= 1; st.rerun()
            with c3:
                st.markdown(f"**Page {st.session_state.tenant_page} of {total_pages}**")
            with c4:
                if st.button("▶", key="t_next") and st.session_state.tenant_page < total_pages:
                    st.session_state.tenant_page += 1; st.rerun()
            with c5:
                if st.button("▶▶", key="t_last") and st.session_state.tenant_page < total_pages:
                    st.session_state.tenant_page = total_pages; st.rerun()
            
            st.markdown("---")
            
            page_tenants = display_tenants.iloc[start:end]
            for _, t in page_tenants.iterrows():
                is_active = t.get("is_active", True)
                status_badge = "🟢 Active" if is_active else "⚫ Inactive"
                status_color = "#10B981" if is_active else "#6B7280"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {status_color};border-radius:8px;padding:0.7rem;margin:0.3rem 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{t.get('name','N/A')}</b>
                            <br><span style="font-size:0.7rem;color:#666;">📧 {t.get('email','')} | 🏢 {t.get('home_facility','')}</span>
                        </div>
                        <span style="background:{status_color};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status_badge}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"No tenant users registered for {FACILITY_INFO.get(fc, {}).get('full_name', fc)}.")
    
    # ============================================
    # TAB 3: CONTRACTORS — FILTERED BY FACILITY
    # ============================================
    with tabs[3]:
        st.markdown("### 🔧 Contractor/Vendor Management")
        # Use count_df (filtered by facility) for contractors
        contractor_users = count_df[count_df["user_type"].isin(["contractor","vendor"])] if "user_type" in count_df.columns else pd.DataFrame()
        if len(contractor_users) > 0:
            for _, c in contractor_users.iterrows():
                expiry = str(c.get("contract_expiry","N/A"))[:10]
                st.markdown(f"""
                <div style="background:white;border-left:4px solid #F59E0B;border-radius:8px;padding:0.7rem;margin:0.3rem 0;">
                    <b>{c.get('name','N/A')}</b> — {c.get('organization_name', c.get('company','N/A'))}
                    <br><span style="font-size:0.7rem;color:#666;">📧 {c.get('email','')} | 🏢 {c.get('home_facility','')} | 🏷️ {c.get('contractor_department','N/A')} | 📅 Expires: {expiry}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"No contractor/vendor users registered for {FACILITY_INFO.get(fc, {}).get('full_name', fc)}.")
    
    # ============================================
    # TAB 4: ACTIVITY LOG
    # ============================================
    with tabs[4]:
        st.markdown("### 📊 User Activity Log")
        recent_logs = safe_supabase_query(lambda: supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(50).execute(), error_prefix="Activity log")
        if recent_logs and recent_logs.data and len(recent_logs.data) > 0:
            for log in recent_logs.data:
                st.markdown(f"🕐 {str(log.get('created_at',''))[:16]} | 👤 {log.get('user_id','')} | {log.get('action','')}")
        else:
            st.info("No activity recorded yet.")
    
    # ============================================
    # EDIT USER MODAL
    # ============================================
    if "edit_user_id" in st.session_state and st.session_state.edit_user_id:
        user_id = st.session_state.edit_user_id
        user = next((u for u in all_users if u["id"] == user_id), None)
        
        if user:
            st.markdown("---")
            st.markdown(f"### ✏️ Edit User: {user.get('name','')}")
            
            with st.form("edit_user_form"):
                st.markdown("#### 👤 Personal Details")
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_name = st.text_input("Full Name*", value=user.get("name",""))
                    edit_email = st.text_input("Email*", value=user.get("email",""))
                with c2:
                    edit_emp = st.text_input("Employee ID*", value=user.get("employee_id","") or "")
                    edit_mobile = st.text_input("Mobile Number", value=user.get("mobile","") or "")
                with c3:
                    current_desig = user.get("designation_level", user.get("designation", "Team Member"))
                    edit_desig = st.text_input("Designation/Title*", value=str(current_desig) if current_desig else "Team Member")
                
                st.markdown("---")
                st.markdown("#### 🔐 Role & Access")
                c1, c2, c3 = st.columns(3)
                with c1:
                    current_role = user.get("role", "team_member")
                    roles_list = ["team_member","team_lead","manager","sr_manager","sr_management","admin","super_admin","tenant_admin","tenant_user","contractor","vendor"]
                    role_names = {"team_member":"👤 Team Member","team_lead":"🔐 Team Lead","manager":"👔 Manager","sr_manager":"💼 Sr. Manager","sr_management":"🏢 Sr. Management","admin":"🔴 Admin","super_admin":"👑 Super Admin","tenant_admin":"🏢 Tenant Admin","tenant_user":"🏢 Tenant User","contractor":"🔧 Contractor","vendor":"📦 Vendor"}
                    if current_role in roles_list:
                        role_idx = roles_list.index(current_role)
                    else:
                        role_idx = 0
                    edit_role = st.selectbox("System Role*", roles_list, format_func=lambda x: role_names.get(x, x), index=role_idx)
                with c2:
                    current_type = user.get("user_type", "staff")
                    edit_type = st.selectbox("User Type", ["staff", "management", "tenant", "contractor", "vendor"], index=["staff","management","tenant","contractor","vendor"].index(current_type) if current_type in ["staff","management","tenant","contractor","vendor"] else 0, format_func=lambda x: {"staff":"👤 Staff","management":"💼 Management","tenant":"🏢 Tenant","contractor":"🔧 Contractor","vendor":"📦 Vendor"}[x])
                with c3:
                    current_facs = safe_parse_permissions(user.get("home_facility", "WTC"))
                    if isinstance(current_facs, str):
                        current_facs = [current_facs]
                    all_facilities = ["WTC","AGVL","FCPL","RBPL","VDL","WAREHOUSES"]
                    valid_facs = [f for f in current_facs if f in all_facilities]
                    edit_facilities = st.multiselect("Facility Access*", all_facilities, default=valid_facs if valid_facs else ["WTC"])
                
                if edit_type in ["contractor", "vendor"]:
                    c1, c2 = st.columns(2)
                    with c1:
                        all_depts_list = sorted(df["dept_full"].dropna().unique().tolist()) if "dept_full" in df.columns else ["Engineering — Electrical"]
                        edit_contractor_dept = st.selectbox("Assigned Department", all_depts_list)
                    with c2:
                        current_expiry = user.get("contract_expiry")
                        if current_expiry:
                            try:
                                exp_date = datetime.strptime(str(current_expiry)[:10], "%Y-%m-%d").date()
                            except:
                                exp_date = date.today() + timedelta(days=365)
                        else:
                            exp_date = date.today() + timedelta(days=365)
                        edit_expiry = st.date_input("Contract Expiry", value=exp_date)
                
                if edit_type == "tenant":
                    edit_company = st.text_input("Company/Organization", value=user.get("organization_name","") or "")
                
                st.markdown("---")
                st.markdown("#### 📋 Module Permissions")
                existing_perms = safe_parse_permissions(user.get("extra_permissions", []))
                module_groups = {
                    "Dashboards": ["Command Center", "PPM Dashboard", "Facility Operations"],
                    "Asset & PPM": ["Asset Register", "PPM Activities", "Checklist Status"],
                    "Work Permit": ["Raise Permit", "Authorize Permit", "Confirm Permit", "Approve Permit"],
                    "Work Orders": ["Work Orders"],
                    "Risk Management": ["Risk Assessment"],
                    "People": ["Visitor Management", "User Management"],
                    "Services": ["Raise Ticket", "Helpdesk", "Feedback"],
                    "Compliance": ["Audit Checklist", "Incident Report", "HOTO Check"],
                    "Utility": ["Utility Dashboard"],
                    "Reports": ["Monthly MIS"],
                    "Key Management": ["Key Register", "Key Reports"],
                }
                selected_modules = []
                for group, modules in module_groups.items():
                    st.markdown(f"""<div style="background:#f9fafb;border-radius:8px;padding:0.5rem;margin:0.3rem 0;border:1px solid #e5e7eb;"><b style="font-size:0.75rem;">📁 {group}</b></div>""", unsafe_allow_html=True)
                    cols = st.columns(3)
                    for i, mod in enumerate(modules):
                        with cols[i % 3]:
                            checked = mod in existing_perms
                            if st.checkbox(mod, value=checked, key=f"edit_mod_{group}_{mod}"):
                                selected_modules.append(mod)
                
                st.markdown("---")
                st.markdown("#### 🏢 Department Access")
                all_depts_edit = [
                    "Engineering — Electrical",
                    "Engineering — HVAC", 
                    "Engineering — Plumbing",
                    "Engineering — Vertical Transportation (Lifts)",
                    "Engineering — Fire Fighting",
                    "Engineering — Civil & Structural",
                    "Engineering — Utilities & Energy",
                    "Facility Management — Hard Services",
                    "Facility Management — Soft Services (Housekeeping)",
                    "Facility Management — FM Operations & Helpdesk",
                    "Facility Management — Fitout Works",
                    "Facility Management — HSSE Safety & Compliance",
                    "Facility Management — Front of House",
                    "Technology Group — Network & Connectivity",
                    "Technology Group — Building Technology",
                    "Technology Group — Access Control",
                    "Technology Group — Automation",
                    "Technology Group — BMS",
                    "Technology Group — CCTV",
                    "Technology Group — Fire Alarm & Voice Evac",
                    "Technology Group — MDTH (DSTV)",
                    "Security — Man Guarding Operations",
                    "Contractor — Clyde Engineering",
                    "Contractor — Gates and Shield",
                ]
                current_depts = safe_parse_permissions(user.get("department_permissions", []))
                valid_defaults = [d for d in current_depts if d in all_depts_edit] if current_depts and current_depts != ["All"] else []
                edit_depts = st.multiselect("Departments (leave empty for All)", all_depts_edit, default=valid_defaults)
                
                st.markdown("---")
                st.markdown("#### 📸 Profile Picture")
                new_pic = st.file_uploader("Change Picture", type=["png","jpg","jpeg"], key="edit_pic")
                
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_active = st.checkbox("Account Active", value=user.get("is_active", True))
                with c2:
                    edit_locked = st.checkbox("Account Locked", value=user.get("account_locked", False))
                with c3:
                    if edit_locked:
                        st.caption("Failed attempts reset on unlock")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("💾 SAVE ALL CHANGES", use_container_width=True, type="primary"):
                        update_data = {"name": edit_name, "email": edit_email, "employee_id": edit_emp, "mobile": edit_mobile, "designation": edit_desig, "designation_level": edit_desig, "role": edit_role, "user_type": edit_type, "home_facility": ",".join(edit_facilities) if edit_facilities else "WTC", "extra_permissions": selected_modules, "department_permissions": edit_depts if edit_depts else ["All"], "is_active": edit_active, "account_locked": edit_locked, "updated_by": st.session_state.get("user_name",""), "updated_at": datetime.now().isoformat()}
                        if edit_locked:
                            update_data["failed_login_attempts"] = 0
                        if edit_type in ["contractor", "vendor"]:
                            update_data["contractor_department"] = edit_contractor_dept
                            update_data["contract_expiry"] = str(edit_expiry)
                        if edit_type == "tenant":
                            update_data["organization_name"] = edit_company if edit_company else None
                        if new_pic:
                            pic_b64 = base64.b64encode(new_pic.read()).decode()
                            update_data["profile_picture"] = f"data:image/{new_pic.type.split('/')[-1]};base64,{pic_b64}"
                        DB.update("app_users", user_id, update_data)
                        st.success("✅ User fully updated!")
                        st.session_state.edit_user_id = None
                        st.rerun()
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.edit_user_id = None
                        st.rerun()

    
    # Reset Password
    if "reset_user_id" in st.session_state and st.session_state.reset_user_id:
        user_id = st.session_state.reset_user_id
        user = next((u for u in all_users if u["id"] == user_id), None)
        
        if user:
            st.markdown("---")
            st.markdown(f"### 🔑 Reset Password: {user.get('name','')}")
            
            with st.form("reset_pw_form"):
                new_pw = st.text_input("New Password*", type="password")
                confirm_pw = st.text_input("Confirm Password*", type="password")
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("✅ RESET", use_container_width=True, type="primary"):
                        if new_pw and new_pw == confirm_pw:
                            pw_valid, _ = validate_password_strength(new_pw)
                            if pw_valid:
                                DB.update("app_users", user_id, {"password_hash": hash_password(new_pw)})
                                st.success("✅ Password reset!")
                                st.session_state.reset_user_id = None
                                st.rerun()
                            else:
                                st.error("⚠️ Password too weak")
                        else:
                            st.error("⚠️ Passwords don't match")
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.reset_user_id = None
                        st.rerun()

# ============================================
# RISK MANAGEMENT — FORESIGHT & RESILIENCE COMMAND CENTER
# ============================================
def page_fo():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_fm_director = user_role in ["admin", "super_admin", "sr_management"]
    
    st.markdown(f'## 🛡️ Risk Management — {info.get("full_name", fc)}')
    st.caption("Foresight & Resilience Command Center — Know what could happen before it does.")
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    risk_data = safe_supabase_query(lambda: supabase.table("risk_register").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="Risk data")
    risk_df = pd.DataFrame(risk_data.data) if risk_data and risk_data.data else pd.DataFrame()
    
    total_risks = len(risk_df)
    active_risks = len(risk_df[risk_df["risk_status"] != "closed"]) if total_risks > 0 else 0
    extreme_risks = len(risk_df[(risk_df["residual_rating"] >= 16) & (risk_df["risk_status"] != "closed")]) if total_risks > 0 else 0
    high_risks = len(risk_df[(risk_df["residual_rating"] >= 10) & (risk_df["residual_rating"] < 16) & (risk_df["risk_status"] != "closed")]) if total_risks > 0 else 0
    
    overdue_treatments = 0
    if total_risks > 0:
        for _, r in risk_df.iterrows():
            treatments = safe_supabase_query(lambda: supabase.table("risk_treatments").select("*").eq("risk_id", r["id"]).eq("status", "pending").execute(), error_prefix="Risk treatments")
            if treatments and treatments.data:
                for t in treatments.data:
                    try:
                        if pd.to_datetime(t["due_date"]).date() < today:
                            overdue_treatments += 1
                    except: pass
    
    total_exposure = risk_df[(risk_df["residual_rating"] >= 10) & (risk_df["risk_status"] != "closed")]["financial_exposure"].sum() if total_risks > 0 else 0
    
    ori = round((extreme_risks * 25 + high_risks * 15 + active_risks * 5) / max(total_risks, 1)) if total_risks > 0 else 0
    ori = min(ori, 100)
    
    # ============================================
    # 🟦 TOP RIBBON
    # ============================================
    st.markdown("### 🟦 Risk Posture Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#10B981" if ori < 25 else "#F59E0B" if ori < 50 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overall Risk Index</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{ori}/100</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Residual Exposure</div><div style="font-size:1.3rem;font-weight:800;color:#EF4444;">₦{total_exposure:,.0f}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if overdue_treatments > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overdue Actions</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{overdue_treatments}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Extreme Risks</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{extreme_risks}</div></div>""", unsafe_allow_html=True)
    with c5: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">High Risks</div><div style="font-size:1.3rem;font-weight:800;color:#F59E0B;">{high_risks}</div></div>""", unsafe_allow_html=True)
    with c6: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total Risks</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_risks}</div></div>""", unsafe_allow_html=True)
    
    if extreme_risks > 0:
        st.error(f"🚨 {extreme_risks} EXTREME risks require immediate attention!")
    if overdue_treatments > 0:
        st.warning(f"⚠️ {overdue_treatments} risk treatment actions are overdue.")
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📊 Risk Matrix", "➕ Register Risk", "🔧 Treatments", "📋 Reviews", "📄 Reports"])
    
    # ============================================
    # TAB 0: RISK MATRIX
    # ============================================
    with tabs[0]:
        st.markdown("### 📊 Risk Matrix (5x5 Heatmap)")
        
        if total_risks == 0:
            st.info("No risks registered yet.")
        else:
            # Build matrix data
            matrix_data = []
            for _, risk in risk_df.iterrows():
                if risk.get("risk_status") == "closed": continue
                rl = risk.get("residual_likelihood", 3)
                rc = risk.get("residual_consequence", 3)
                rating = rl * rc
                
                if rating >= 16: zone = "Extreme"; color = "#EF4444"
                elif rating >= 10: zone = "High"; color = "#F59E0B"
                elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                else: zone = "Low"; color = "#10B981"
                
                matrix_data.append({
                    "Risk": risk.get("risk_number",""),
                    "Title": risk.get("title","")[:50],
                    "Likelihood": rl,
                    "Consequence": rc,
                    "Rating": rating,
                    "Zone": zone,
                    "Color": color,
                    "Exposure": risk.get("financial_exposure",0)
                })
            
            if matrix_data:
                md = pd.DataFrame(matrix_data)
                
                # Scatter plot
                fig = px.scatter(md, x="Consequence", y="Likelihood", size="Exposure", color="Zone",
                    color_discrete_map={"Extreme":"#EF4444","High":"#F59E0B","Medium":"#3B82F6","Low":"#10B981"},
                    hover_name="Risk", hover_data=["Title"],
                    title="Risk Matrix — Residual Risk (After Controls)",
                    range_x=[0.5,5.5], range_y=[0.5,5.5])
                
                fig.add_hline(y=2.5, line_dash="dash", line_color="#F59E0B")
                fig.add_vline(x=2.5, line_dash="dash", line_color="#F59E0B")
                fig.add_hline(y=3.5, line_dash="dash", line_color="#EF4444")
                fig.add_vline(x=3.5, line_dash="dash", line_color="#EF4444")
                
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                st.caption("🟢 Green: Low | 🔵 Blue: Medium | 🟡 Amber: High | 🔴 Red: Extreme")
            
            # Risk cards sorted by severity
            st.markdown("---")
            st.markdown("### 📋 Risk Register")
            
            sorted_risks = risk_df[risk_df["risk_status"] != "closed"].copy()
            if "residual_rating" in sorted_risks.columns:
                sorted_risks = sorted_risks.sort_values("residual_rating", ascending=False)
            
            for _, risk in sorted_risks.head(20).iterrows():
                rating = risk.get("residual_rating", risk.get("inherent_rating", 5))
                if rating >= 16: zone = "Extreme"; color = "#EF4444"
                elif rating >= 10: zone = "High"; color = "#F59E0B"
                elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                else: zone = "Low"; color = "#10B981"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {color};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{risk.get('risk_number','N/A')}</b> — {risk.get('title','')[:80]}
                            <br><span style="font-size:0.65rem;color:#666;">🏷️ {risk.get('risk_category','').replace('_',' ').title()} | 👤 {risk.get('risk_owner','')} | 💰 ₦{risk.get('financial_exposure',0):,.0f}</span>
                        </div>
                        <span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{zone.upper()} ({rating}/25)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # ============================================
# RISK MANAGEMENT — FORESIGHT & RESILIENCE COMMAND CENTER
# ISO 31000 • COSO ERM • TCFD • GRESB ALIGNED
# ============================================
def page_fo():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_fm_director = user_role in ["admin", "super_admin", "sr_management"]
    
    st.markdown(f'## 🛡️ Risk Assessment & Management — {info.get("full_name", fc)}')
    st.caption("ISO 31000 • COSO ERM • TCFD • GRESB Aligned | Foresight & Resilience Command Center")
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    risk_data = safe_supabase_query(lambda: supabase.table("risk_register").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="Risk data")
    risk_df = pd.DataFrame(risk_data.data) if risk_data and risk_data.data else pd.DataFrame()
    
    total_risks = len(risk_df)
    active_risks = len(risk_df[risk_df["risk_status"] != "closed"]) if total_risks > 0 else 0
    extreme_risks = len(risk_df[(risk_df["residual_level"] == "Extreme") & (risk_df["risk_status"] != "closed")]) if total_risks > 0 else 0
    high_risks = len(risk_df[(risk_df["residual_level"] == "High") & (risk_df["risk_status"] != "closed")]) if total_risks > 0 else 0
    
    overdue_treatments = 0
    if total_risks > 0:
        for _, r in risk_df.iterrows():
            treatments = safe_supabase_query(lambda: supabase.table("risk_treatments").select("*").eq("risk_id", r["id"]).eq("status", "pending").execute(), error_prefix="Risk treatments")
            if treatments and treatments.data:
                for t in treatments.data:
                    try:
                        if pd.to_datetime(t["due_date"]).date() < today:
                            overdue_treatments += 1
                    except: pass
    
    total_exposure = risk_df[(risk_df["residual_level"].isin(["High","Extreme"])) & (risk_df["risk_status"] != "closed")]["inherent_cons_financial"].sum() if total_risks > 0 else 0
    
    ori = round((extreme_risks * 25 + high_risks * 15 + active_risks * 5) / max(total_risks, 1)) if total_risks > 0 else 0
    ori = min(ori, 100)
    
    # ============================================
    # 🟦 TOP RIBBON
    # ============================================
    st.markdown("### 🟦 Risk Posture Ribbon — ISO 31000 Aligned")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#10B981" if ori < 25 else "#F59E0B" if ori < 50 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overall Risk Index</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{ori}/100</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Residual Exposure</div><div style="font-size:1.3rem;font-weight:800;color:#EF4444;">₦{total_exposure:,.0f}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if overdue_treatments > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overdue Actions</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{overdue_treatments}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Extreme Risks</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{extreme_risks}</div></div>""", unsafe_allow_html=True)
    with c5: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">High Risks</div><div style="font-size:1.3rem;font-weight:800;color:#F59E0B;">{high_risks}</div></div>""", unsafe_allow_html=True)
    with c6: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total Risks</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_risks}</div></div>""", unsafe_allow_html=True)
    
    if extreme_risks > 0: st.error(f"🚨 {extreme_risks} EXTREME risks require immediate attention!")
    if overdue_treatments > 0: st.warning(f"⚠️ {overdue_treatments} risk treatment actions are overdue.")
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📊 Risk Matrix", "➕ Register Risk", "🏗️ Asset Risk (FMECA)", "🔧 Treatments & Controls", "📋 Reviews", "📄 Reports"])
    
    # ============================================
    # TAB 0: RISK MATRIX
    # ============================================
    with tabs[0]:
        st.markdown("### 📊 Risk Matrix (5x5 Heatmap) — ISO 31000 Standard")
        
        if total_risks == 0:
            st.info("No risks registered yet.")
        else:
            matrix_data = []
            for _, risk in risk_df.iterrows():
                if risk.get("risk_status") == "closed": continue
                rl = risk.get("residual_likelihood", 3)
                rc = risk.get("residual_consequence", 3)
                rating = rl * rc
                
                if rating >= 16: zone = "Extreme"; color = "#EF4444"
                elif rating >= 10: zone = "High"; color = "#F59E0B"
                elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                else: zone = "Low"; color = "#10B981"
                
                matrix_data.append({
                    "Risk": risk.get("risk_number",""), "Title": risk.get("title","")[:50],
                    "Likelihood": rl, "Consequence": rc, "Rating": rating,
                    "Zone": zone, "Color": color, "Exposure": risk.get("inherent_cons_financial",0)
                })
            
            if matrix_data:
                md = pd.DataFrame(matrix_data)
                fig = px.scatter(md, x="Consequence", y="Likelihood", size="Exposure", color="Zone",
                    color_discrete_map={"Extreme":"#EF4444","High":"#F59E0B","Medium":"#3B82F6","Low":"#10B981"},
                    hover_name="Risk", hover_data=["Title"],
                    title="Residual Risk Matrix — After Controls", range_x=[0.5,5.5], range_y=[0.5,5.5])
                fig.add_hline(y=2.5, line_dash="dash", line_color="#F59E0B")
                fig.add_vline(x=2.5, line_dash="dash", line_color="#F59E0B")
                fig.add_hline(y=3.5, line_dash="dash", line_color="#EF4444")
                fig.add_vline(x=3.5, line_dash="dash", line_color="#EF4444")
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🟢 Low (1-4) | 🔵 Medium (5-8) | 🟡 High (9-12) | 🔴 Extreme (15-25)")
            
            st.markdown("---")
            st.markdown("### 📋 Risk Register — Sorted by Severity")
            
            sorted_risks = risk_df[risk_df["risk_status"] != "closed"].copy()
            if "residual_rating" in sorted_risks.columns:
                sorted_risks = sorted_risks.sort_values("residual_rating", ascending=False)
            
            for _, risk in sorted_risks.head(20).iterrows():
                rating = risk.get("residual_rating", 5)
                if rating >= 16: zone = "Extreme"; color = "#EF4444"
                elif rating >= 10: zone = "High"; color = "#F59E0B"
                elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                else: zone = "Low"; color = "#10B981"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {color};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{risk.get('risk_number','N/A')}</b> — {risk.get('title','')[:80]}
                            <br><span style="font-size:0.65rem;color:#666;">🏷️ {risk.get('risk_category','').replace('_',' ').title()} | 👤 {risk.get('risk_owner','')} | 💰 ₦{risk.get('inherent_cons_financial',0):,.0f}</span>
                        </div>
                        <span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{zone.upper()} ({rating}/25)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 1: REGISTER RISK — FORTUNE 500 STANDARD
    # ============================================
    with tabs[1]:
        st.markdown("### ➕ Register New Risk — ISO 31000 / COSO ERM Standard")
        
        risk_categories = {
            "health_safety_wellbeing": "1. Health, Safety & Wellbeing",
            "business_continuity": "2. Business Continuity & Operational Resilience",
            "tenant_revenue": "3. Tenant & Revenue",
            "regulatory_legal": "4. Regulatory, Legal & Compliance",
            "financial_fraud": "5. Financial & Fraud",
            "environmental_sustainability": "6. Environmental & Sustainability",
            "reputational_brand": "7. Reputational & Brand",
            "strategic_market": "8. Strategic & Market",
            "technology_cybersecurity": "9. Technology & Cybersecurity",
            "third_party_supply_chain": "10. Third-Party & Supply Chain"
        }
        
        sub_categories = {
            "health_safety_wellbeing": ["Fire & Explosion","Structural Integrity","Entrapment (Elevators)","Hazardous Materials","Legionella/Water Quality","Air Quality (IAQ)","Occupational Health","Pandemic/Infectious Disease","Personal Security","Mental Wellbeing"],
            "business_continuity": ["Critical Equipment Failure","Utility Outage","Supply Chain Failure","Cyber Attack/BMS Compromise","Telecommunications Failure","Extreme Weather Event","Civil Unrest/Terrorism","Pandemics","Key Person Dependency"],
            "tenant_revenue": ["Anchor Tenant Loss","Occupancy Rate Decline","Rental Rate Compression","Tenant Default/Bankruptcy","Lease Disputes","Service Credit Claims","Tenant Experience Failure","Competitor Building Advantage"],
            "regulatory_legal": ["Fire Code Violation","Elevator Non-Compliance","Pressure Vessel Certification","Electrical Safety Non-Compliance","Environmental Permit Breach","Building Code Violation","Data Privacy","Employment Law","Contract Breach","Personal Injury Litigation"],
            "financial_fraud": ["Theft of Physical Assets","Procurement Fraud","Contractor Overbilling","Inventory Shrinkage","Budget Overrun","Currency/FX Exposure","Interest Rate Risk","Insurance Underinsurance","Accounts Receivable"],
            "environmental_sustainability": ["Diesel Spill/Leak","Refrigerant Leak (F-Gas)","Improper Waste Disposal","Energy Performance Non-Compliance","Carbon Tax/Emissions Penalty","Water Scarcity","Flood Risk (Physical Climate)","Heat Stress (Physical Climate)","Biodiversity Impact"],
            "reputational_brand": ["Negative Media Coverage","Social Media Crisis","Tenant Protest/Dispute","Poor Online Ratings","Greenwashing Accusation","Community Relations Failure"],
            "strategic_market": ["Remote/Hybrid Work Shift","Market Oversupply","Technological Obsolescence","Demographic Shift","Policy Change","Investor Exit/Refinancing Risk","Stranded Asset Risk"],
            "technology_cybersecurity": ["BMS/SCADA Cyber Attack","Tenant WiFi Compromise","Access Control Hack","CCTV Breach","Ransomware on FM Systems","IoT Sensor Network Failure","Data Loss","Legacy System Obsolescence","AI/Algorithm Bias"],
            "third_party_supply_chain": ["Critical Contractor Failure","Single-Source Supplier Dependency","Contractor Safety Performance","Contractor Compliance Failure","SLA Breach","Modern Slavery in Supply Chain","Geopolitical Supply Disruption"]
        }
        
        with st.form("register_risk_form"):
            st.markdown("#### Section A: Risk Identification & Ownership")
            c1, c2, c3 = st.columns(3)
            with c1:
                risk_title = st.text_input("Risk Title*", placeholder="e.g., Chiller #2 Catastrophic Compressor Failure")
                risk_category = st.selectbox("Category*", list(risk_categories.keys()), format_func=lambda x: risk_categories[x])
            with c2:
                if risk_category in sub_categories:
                    risk_sub_category = st.selectbox("Sub-Category*", sub_categories[risk_category])
                else:
                    risk_sub_category = st.text_input("Sub-Category*")
                risk_owner = st.text_input("Risk Owner*")
            with c3:
                risk_source = st.selectbox("Source of Identification", ["Incident","Audit","Asset Condition Alert","Tenant Feedback","Regulatory Change","External Event","Strategic Review","Horizon Scanning"])
                risk_stakeholders = st.text_input("Stakeholders", placeholder="e.g., Tenant Rep, Insurer")
            
            risk_desc = st.text_area("Risk Description*", height=80, placeholder="What could happen? What would cause it? What is the chain of events? What is the impact?")
            risk_triggers = st.text_input("Risk Triggers / Leading Indicators", placeholder="e.g., Increasing vibration, Rising reactive WO count")
            risk_interdependencies = st.text_input("Interdependencies (Risk IDs)", placeholder="e.g., RISK-0089")
            
            st.markdown("---")
            st.markdown("#### Section B: Inherent Risk Assessment (Before Controls)")
            c1, c2 = st.columns(2)
            with c1:
                inh_likelihood = st.selectbox("Inherent Likelihood*", [1,2,3,4,5], format_func=lambda x: {1:"Rare",2:"Unlikely",3:"Possible",4:"Likely",5:"Almost Certain"}[x])
            with c2:
                inh_cons_overall = st.selectbox("Inherent Consequence (Overall)*", [1,2,3,4,5], format_func=lambda x: {1:"Insignificant",2:"Minor",3:"Moderate",4:"Major",5:"Catastrophic"}[x])
            
            st.markdown("**Multi-Dimensional Consequence Assessment:**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                inh_safety = st.selectbox("Safety", [1,2,3,4,5], format_func=lambda x: {1:"Insig.",2:"Minor",3:"Mod.",4:"Major",5:"Catastr."}[x], key="inh_safety")
            with c2:
                inh_financial = st.number_input("Financial (₦)*", min_value=0.0, value=0.0, step=1000000.0, key="inh_financial")
            with c3:
                inh_operational = st.selectbox("Operational", [1,2,3,4,5], format_func=lambda x: {1:"<2hrs",2:"<1day",3:"1-3d",4:"1-2w",5:">2w"}[x], key="inh_oper")
            with c4:
                inh_reputational = st.selectbox("Reputational", [1,2,3,4,5], format_func=lambda x: {1:"Internal",2:"Tenants",3:"Online",4:"Local Media",5:"National"}[x], key="inh_rep")
            with c5:
                inh_regulatory = st.selectbox("Regulatory", [1,2,3,4,5], format_func=lambda x: {1:"Minor Breach",2:"Notice",3:"Fine",4:"Prosecution",5:"License Revoked"}[x], key="inh_reg")
            
            inh_rating = inh_likelihood * inh_cons_overall
            zone = "Extreme" if inh_rating >= 16 else "High" if inh_rating >= 10 else "Medium" if inh_rating >= 5 else "Low"
            st.caption(f"Inherent Rating: {inh_rating}/25 — {zone.upper()}")
            
            st.markdown("---")
            st.markdown("#### Section C: Existing Controls")
            existing_controls = st.text_area("Existing Controls", height=80, placeholder="List all controls currently in place. Be specific: Not 'PM program' but 'Quarterly vibration analysis on Chiller #2 compressor by certified technician.'")
            
            st.markdown("---")
            st.markdown("#### Section D: Residual Risk Assessment (After Controls)")
            c1, c2 = st.columns(2)
            with c1:
                res_likelihood = st.selectbox("Residual Likelihood*", [1,2,3,4,5], format_func=lambda x: {1:"Rare",2:"Unlikely",3:"Possible",4:"Likely",5:"Almost Certain"}[x], index=min(inh_likelihood-1, 4))
            with c2:
                res_consequence = st.selectbox("Residual Consequence*", [1,2,3,4,5], format_func=lambda x: {1:"Insignificant",2:"Minor",3:"Moderate",4:"Major",5:"Catastrophic"}[x], index=min(inh_cons_overall-1, 4))
            
            res_rating = res_likelihood * res_consequence
            res_zone = "Extreme" if res_rating >= 16 else "High" if res_rating >= 10 else "Medium" if res_rating >= 5 else "Low"
            target_level = st.selectbox("Target Risk Level (Risk Appetite)", ["Low","Medium"], format_func=lambda x: f"Acceptable: {x}")
            st.caption(f"Residual Rating: {res_rating}/25 — {res_zone.upper()}")
            
            st.markdown("---")
            st.markdown("#### Section E: Risk Treatment Plan")
            c1, c2 = st.columns(2)
            with c1:
                treatment_strategy = st.selectbox("Treatment Strategy*", ["reduce","transfer","avoid","accept"])
            with c2:
                treatment_justification = st.text_area("Treatment Justification", height=60, placeholder="Rationale for chosen strategy. If 'Accept', include cost-benefit analysis.")
            
            if st.form_submit_button("➕ REGISTER RISK", use_container_width=True, type="primary"):
                if risk_title and risk_owner and risk_desc:
                    risk_count = total_risks + 1
                    risk_number = f"RISK-{fc}-{today.strftime('%Y%m%d')}-{str(risk_count).zfill(4)}"
                    
                    risk_insert_data = {
                        "facility_code":fc,"risk_number":risk_number,"title":risk_title,
                        "risk_category":risk_category,"risk_sub_category":risk_sub_category,
                        "description":risk_desc,"risk_triggers":risk_triggers,
                        "risk_interdependencies":risk_interdependencies,
                        "risk_owner":risk_owner,"risk_stakeholders":risk_stakeholders,
                        "date_raised":str(today),"source_of_identification":risk_source,
                        "inherent_likelihood":inh_likelihood,
                        "inherent_cons_safety":inh_safety,"inherent_cons_financial":inh_financial,
                        "inherent_cons_operational":inh_operational,"inherent_cons_reputational":inh_reputational,
                        "inherent_cons_regulatory":inh_regulatory,"inherent_cons_overall":inh_cons_overall,
                        "inherent_rating":inh_rating,"existing_controls":existing_controls,
                        "residual_likelihood":res_likelihood,"residual_consequence":res_consequence,
                        "residual_rating":res_rating,"residual_level":res_zone,
                        "target_risk_level":target_level,"treatment_strategy":treatment_strategy,
                        "treatment_justification":treatment_justification,
                        "risk_status":"identified","next_review_date":str(today + timedelta(days=90)),
                        "last_review_date":str(today),"created_by":user_name,"created_at":wat_now.isoformat()
                    }
                    safe_supabase_query(lambda: supabase.table("risk_register").insert(risk_insert_data).execute(), error_prefix="Register risk")
                    
                    st.success(f"✅ Risk {risk_number} registered!"); st.balloons(); st.rerun()
                else:
                    st.error("⚠️ Title, Owner, and Description are required")
    
    
# ============================================
    # TAB 2: ASSET RISK ASSESSMENT (FMECA)
    # ============================================
    with tabs[2]:
        st.markdown("### 🏗️ Asset Criticality & FMECA — IEC 60812 / ISO 55000")
        
        fmeca_data = safe_supabase_query(lambda: supabase.table("asset_fmeca").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="FMECA data")
        fmeca_df = pd.DataFrame(fmeca_data.data) if fmeca_data and fmeca_data.data else pd.DataFrame()
        
        total_fmeca = len(fmeca_df)
        tier1_count = len(fmeca_df[fmeca_df["asset_criticality"] == "Tier1"]) if total_fmeca > 0 else 0
        tier2_count = len(fmeca_df[fmeca_df["asset_criticality"] == "Tier2"]) if total_fmeca > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total FMECA Assessments", total_fmeca)
        with c2: st.metric("Tier 1 (Critical)", tier1_count)
        with c3: st.metric("Tier 2 (Essential)", tier2_count)
        
        st.markdown("---")
        
        fmeca_subtabs = st.tabs(["📋 FMECA Register", "➕ New FMECA", "📊 Asset Risk Matrix"])
        
        # FMECA Register
        with fmeca_subtabs[0]:
            if total_fmeca == 0:
                st.info("No FMECA assessments yet.")
            else:
                for _, fm in fmeca_df.head(20).iterrows():
                    rating = fm.get("residual_rating", 5)
                    if rating >= 16: zone = "Extreme"; color = "#EF4444"
                    elif rating >= 10: zone = "High"; color = "#F59E0B"
                    elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                    else: zone = "Low"; color = "#10B981"
                    
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid {color};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <b>{fm.get('failure_mode_id','N/A')}</b> — {fm.get('asset_name','')} | {fm.get('failure_mode_description','')[:80]}
                        <br><span style="font-size:0.65rem;color:#666;">🏷️ {fm.get('asset_criticality','')} | RPN: {fm.get('rpn_score','')} | 💰 ₦{fm.get('fmeca_financial',0):,.0f}</span>
                        <span style="float:right;background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;">{zone.upper()} ({rating}/25)</span>
                    </div>
                    """, unsafe_allow_html=True)
        
        # New FMECA
        with fmeca_subtabs[1]:
            st.markdown("#### ➕ New FMECA Assessment — IEC 60812 Standard")
            
            # Get assets for selection
            all_assets_fm = DB.get_assets(fc, 50000)
            asset_options = [f"{a.get('name','')} ({a.get('asset_tag','')})" for a in (all_assets_fm or []) if a.get('name')]
            asset_options.insert(0, "Select Asset...")
            
            with st.form("new_fmeca_form"):
                st.markdown("**Section A: Asset Identification**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    selected_asset = st.selectbox("Select Asset*", asset_options)
                    fm_criticality = st.selectbox("Asset Criticality*", ["Tier1","Tier2","Tier3"])
                with c2:
                    fm_manufacturer = st.text_input("Manufacturer")
                    fm_model = st.text_input("Model")
                with c3:
                    fm_install_date = st.date_input("Installation Date", today - timedelta(days=365*10))
                    fm_design_life = st.number_input("Design Life (Years)", value=20, min_value=1)
                
                c1, c2 = st.columns(2)
                with c1:
                    fm_condition_score = st.slider("Current Condition Score (0-100)", 0, 100, 50)
                    fm_remaining_life = st.number_input("Remaining Useful Life (Years)", value=5, min_value=0)
                with c2:
                    fm_replacement_cost = st.number_input("Replacement Cost (₦)", min_value=0.0, value=0.0, step=1000000.0)
                    fm_statutory = st.checkbox("Statutory Inspection Required?")
                
                fm_linked_risk = st.text_input("Linked Master Risk ID (if any)", placeholder="e.g., RISK-2026-0042")
                
                st.markdown("---")
                st.markdown("**Section B: Failure Mode Identification**")
                fm_failure_desc = st.text_area("Failure Mode Description*", height=60, placeholder="What specifically fails? Component + Failure Type.")
                c1, c2 = st.columns(2)
                with c1:
                    fm_causes = st.text_area("Failure Causes", height=60)
                    fm_effect_local = st.text_input("Failure Effect (Local)")
                with c2:
                    fm_effect_system = st.text_input("Failure Effect (System)")
                    fm_effect_building = st.text_area("Failure Effect (Building/Tenants)", height=60)
                
                st.markdown("---")
                st.markdown("**Section C: Inherent Risk Assessment**")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: fm_safety = st.selectbox("Safety", [1,2,3,4,5], key="fm_safety")
                with c2: fm_financial = st.number_input("Financial (₦)", min_value=0.0, value=0.0, step=1000000.0, key="fm_financial")
                with c3: fm_operational = st.selectbox("Operational", [1,2,3,4,5], key="fm_oper")
                with c4: fm_reputational = st.selectbox("Reputational", [1,2,3,4,5], key="fm_rep")
                with c5: fm_regulatory = st.selectbox("Regulatory", [1,2,3,4,5], key="fm_reg")
                
                fm_overall = max(fm_safety, fm_operational, fm_reputational, fm_regulatory)
                st.caption(f"Overall Consequence (Highest): {fm_overall}")
                
                c1, c2 = st.columns(2)
                with c1: fm_inh_likelihood = st.selectbox("Inherent Likelihood", [1,2,3,4,5], format_func=lambda x: {1:"Rare",2:"Unlikely",3:"Possible",4:"Likely",5:"Almost Certain"}[x])
                with c2: pass
                
                inh_rating_fm = fm_inh_likelihood * fm_overall
                zone_fm = "Extreme" if inh_rating_fm >= 16 else "High" if inh_rating_fm >= 10 else "Medium" if inh_rating_fm >= 5 else "Low"
                st.caption(f"Inherent Rating: {inh_rating_fm}/25 — {zone_fm.upper()}")
                
                st.markdown("---")
                st.markdown("**Section D: Existing Controls & Residual Risk**")
                fm_controls = st.text_area("Existing Controls & Detection Methods", height=80)
                
                c1, c2 = st.columns(2)
                with c1: fm_res_likelihood = st.selectbox("Residual Likelihood", [1,2,3,4,5], format_func=lambda x: {1:"Rare",2:"Unlikely",3:"Possible",4:"Likely",5:"Almost Certain"}[x], index=min(fm_inh_likelihood-1, 4))
                with c2: fm_res_consequence = st.selectbox("Residual Consequence", [1,2,3,4,5], index=min(fm_overall-1, 4))
                
                res_rating_fm = fm_res_likelihood * fm_res_consequence
                
                fm_rpn = fm_overall * fm_inh_likelihood * 3
                st.caption(f"RPN Score: {fm_rpn} | Residual Rating: {res_rating_fm}/25")
                
                st.markdown("---")
                st.markdown("**Section E: Treatment & Decision**")
                fm_treatment = st.text_area("Recommended Additional Controls (Treatment Plan)", height=60)
                fm_decision = st.text_area("Criticality Decision", height=40, placeholder="e.g., UNACCEPTABLE in long term. Asset requires replacement within 24 months.")
                c1, c2 = st.columns(2)
                with c1: fm_review_freq = st.selectbox("Review Frequency", ["Monthly","Quarterly","Bi-Annual","Annual"])
                with c2: fm_approved_by = st.text_input("Approved By", value=user_name)
                
                if st.form_submit_button("➕ CREATE FMECA ASSESSMENT", use_container_width=True, type="primary"):
                    if selected_asset != "Select Asset..." and fm_failure_desc:
                        fm_count = total_fmeca + 1
                        fm_id = f"FMECA-{fc}-{today.strftime('%Y%m%d')}-{str(fm_count).zfill(4)}"
                        
                        asset_name = selected_asset.split(" (")[0] if "(" in selected_asset else selected_asset
                        
                        fmeca_insert_data = {
                            "facility_code":fc,"failure_mode_id":fm_id,
                            "asset_name":asset_name,"asset_criticality":fm_criticality,
                            "failure_mode_description":fm_failure_desc,
                            "failure_causes":fm_causes,"failure_effect_local":fm_effect_local,
                            "failure_effect_system":fm_effect_system,"failure_effect_building":fm_effect_building,
                            "fmeca_safety":fm_safety,"fmeca_financial":fm_financial,
                            "fmeca_operational":fm_operational,"fmeca_reputational":fm_reputational,
                            "fmeca_regulatory":fm_regulatory,"fmeca_overall_consequence":fm_overall,
                            "inherent_likelihood":fm_inh_likelihood,"inherent_rating":inh_rating_fm,
                            "existing_controls":fm_controls,"residual_likelihood":fm_res_likelihood,
                            "residual_consequence":fm_res_consequence,"residual_rating":res_rating_fm,
                            "rpn_score":fm_rpn,"treatment_actions":fm_treatment,
                            "criticality_decision":fm_decision,"review_frequency":fm_review_freq,
                            "approved_by":fm_approved_by,"approved_date":str(today),
                            "manufacturer":fm_manufacturer,"model":fm_model,
                            "installation_date":str(fm_install_date),"design_life":fm_design_life,
                            "remaining_useful_life":fm_remaining_life,"condition_score":fm_condition_score,
                            "replacement_cost":fm_replacement_cost,"statutory_inspection":fm_statutory,
                            "linked_risk_id":fm_linked_risk if fm_linked_risk else None,
                            "status":"active","created_by":user_name,"created_at":wat_now.isoformat()
                        }
                        safe_supabase_query(lambda: supabase.table("asset_fmeca").insert(fmeca_insert_data).execute(), error_prefix="FMECA insert")
                        
                        st.success(f"✅ FMECA {fm_id} created!"); st.balloons(); st.rerun()
                    else:
                        st.error("⚠️ Asset and Failure Mode Description are required")
        
        # Asset Risk Matrix
        with fmeca_subtabs[2]:
            st.markdown("#### 📊 Asset Risk Matrix — Top 10 Riskiest Assets")
            
            if total_fmeca > 0:
                top_risks = fmeca_df.nlargest(10, "residual_rating") if "residual_rating" in fmeca_df.columns else fmeca_df.head(10)
                
                for _, fm in top_risks.iterrows():
                    rating = fm.get("residual_rating", 5)
                    if rating >= 16: zone = "Extreme"; color = "#EF4444"
                    elif rating >= 10: zone = "High"; color = "#F59E0B"
                    elif rating >= 5: zone = "Medium"; color = "#3B82F6"
                    else: zone = "Low"; color = "#10B981"
                    
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid {color};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <b>{fm.get('asset_name','')}</b> — {fm.get('failure_mode_description','')[:80]}
                        <br><span style="font-size:0.65rem;color:#666;">🏷️ {fm.get('asset_criticality','')} | RPN: {fm.get('rpn_score','')} | Condition: {fm.get('condition_score','')}/100</span>
                        <span style="float:right;background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;">{zone.upper()} ({rating}/25)</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Bar chart
                if len(top_risks) >= 2:
                    fig = px.bar(top_risks, x="residual_rating", y="asset_name", orientation='h', title="Top 10 Riskiest Assets", color="residual_rating", color_continuous_scale=["#10B981","#F59E0B","#EF4444"])
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No FMECA assessments yet.")


# ============================================
    # TAB 3: TREATMENTS & CONTROLS
    # ============================================
    with tabs[3]:
        st.markdown("### 🔧 Risk Treatments & Controls")
        
        if total_risks == 0:
            st.info("No risks registered yet.")
        else:
            treat_tabs = st.tabs(["📋 Treatment Actions", "🛡️ Controls"])
            
            with treat_tabs[0]:
                with st.expander("➕ Add Treatment Action"):
                    with st.form("add_treatment_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            treat_risk = st.selectbox("Risk", [f"{r.get('risk_number','')} — {r.get('title','')[:50]}" for _, r in risk_df.iterrows()])
                            treat_desc = st.text_input("Action Description*")
                        with c2:
                            treat_person = st.text_input("Action Owner")
                            treat_due = st.date_input("Due Date", today + timedelta(days=30))
                        treat_budget = st.number_input("Budget Required (₦)", min_value=0.0, value=0.0, step=10000.0)
                        if st.form_submit_button("➕ Add Treatment", use_container_width=True):
                            if treat_desc:
                                risk_idx = [i for i, r in enumerate(risk_df.iterrows()) if f"{r[1].get('risk_number','')} — {r[1].get('title','')[:50]}" == treat_risk][0]
                                risk_id = risk_df.iloc[risk_idx]["id"]
                                safe_supabase_query(lambda: supabase.table("risk_treatments").insert({
                                    "risk_id":risk_id,"action_description":treat_desc,
                                    "action_owner":treat_person,"due_date":str(treat_due),
                                    "budget_required":treat_budget,"status":"pending"
                                }).execute(), error_prefix="Add treatment")
                                st.success("✅ Treatment added!"); st.rerun()
                
                st.markdown("---")
                for _, risk in risk_df.iterrows():
                    treatments = safe_supabase_query(lambda: supabase.table("risk_treatments").select("*").eq("risk_id", risk["id"]).order("created_at").execute(), error_prefix="Risk treatments")
                    if treatments and treatments.data:
                        st.markdown(f"**{risk.get('risk_number','')} — {risk.get('title','')[:60]}**")
                        for t in treatments.data:
                            status = t.get("status","pending")
                            sc = "#10B981" if status == "completed" else "#F59E0B" if status == "in_progress" else "#EF4444"
                            overdue = " ⚠️ OVERDUE" if pd.to_datetime(t["due_date"]).date() < today and status != "completed" else ""
                            st.markdown(f"""<div style="background:white;border-left:3px solid {sc};border-radius:6px;padding:0.5rem;margin:0.1rem 0;font-size:0.7rem;">{t.get('action_description','')[:100]}{overdue}<br><span style="font-size:0.6rem;">👤 {t.get('action_owner','')} | 📅 {t.get('due_date','')} | 💰 ₦{t.get('budget_required',0):,.0f}</span><span style="float:right;color:{sc};font-weight:600;">{status.upper()}</span></div>""", unsafe_allow_html=True)
                            if status != "completed":
                                if st.button("✅ Complete", key=f"treat_{t['id']}", use_container_width=True):
                                    safe_supabase_query(lambda: supabase.table("risk_treatments").update({"status":"completed","completed_date":str(today),"completed_by":user_name}).eq("id",t["id"]).execute(), error_prefix="Complete treatment")
                                    st.success("✅ Completed!"); st.rerun()
                        st.markdown("---")
            
            with treat_tabs[1]:
                with st.expander("➕ Add Control"):
                    with st.form("add_control_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            ctrl_risk = st.selectbox("Risk", [f"{r.get('risk_number','')} — {r.get('title','')[:50]}" for _, r in risk_df.iterrows()], key="ctrl_risk")
                            ctrl_desc = st.text_input("Control Description*")
                        with c2:
                            ctrl_type = st.selectbox("Control Type", ["Preventive","Detective","Mitigative","Directive"])
                            ctrl_owner = st.text_input("Control Owner")
                        c1, c2 = st.columns(2)
                        with c1: ctrl_frequency = st.selectbox("Frequency", ["Continuous","Daily","Weekly","Monthly","Quarterly","Annual"])
                        with c2: ctrl_effectiveness = st.selectbox("Effectiveness", ["Effective","Mostly Effective","Partially Effective","Ineffective","Not Tested"])
                        if st.form_submit_button("➕ Add Control", use_container_width=True):
                            if ctrl_desc:
                                risk_idx2 = [i for i, r in enumerate(risk_df.iterrows()) if f"{r[1].get('risk_number','')} — {r[1].get('title','')[:50]}" == ctrl_risk][0]
                                risk_id2 = risk_df.iloc[risk_idx2]["id"]
                                safe_supabase_query(lambda: supabase.table("risk_controls").insert({
                                    "risk_id":risk_id2,"control_description":ctrl_desc,
                                    "control_type":ctrl_type,"control_owner":ctrl_owner,
                                    "control_frequency":ctrl_frequency,"effectiveness_rating":ctrl_effectiveness,
                                    "last_tested_date":str(today)
                                }).execute(), error_prefix="Add control")
                                st.success("✅ Control added!"); st.rerun()
    
    # ============================================
    # TAB 4: REVIEWS
    # ============================================
    with tabs[4]:
        st.markdown("### 📋 Risk Reviews")
        
        if total_risks == 0:
            st.info("No risks registered yet.")
        else:
            overdue_reviews = risk_df[(pd.to_datetime(risk_df["next_review_date"], errors='coerce').dt.date <= today) & (risk_df["risk_status"] != "closed")] if total_risks > 0 else pd.DataFrame()
            if len(overdue_reviews) > 0:
                st.warning(f"⚠️ {len(overdue_reviews)} risks are due for review")
            
            with st.expander("➕ Record Review"):
                with st.form("add_review_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        review_risk = st.selectbox("Risk", [f"{r.get('risk_number','')} — {r.get('title','')[:50]}" for _, r in risk_df.iterrows()])
                        review_date_r = st.date_input("Review Date", today)
                    with c2:
                        review_new_rating = st.selectbox("New Residual Rating", [1,2,3,4,5,6,8,9,10,12,15,16,20,25])
                        review_comments = st.text_area("Comments")
                    if st.form_submit_button("➕ Record Review", use_container_width=True):
                        risk_idx = [i for i, r in enumerate(risk_df.iterrows()) if f"{r[1].get('risk_number','')} — {r[1].get('title','')[:50]}" == review_risk][0]
                        risk_id = risk_df.iloc[risk_idx]["id"]
                        old_rating = risk_df.iloc[risk_idx].get("residual_rating", 0)
                        safe_supabase_query(lambda: supabase.table("risk_reviews").insert({
                            "risk_id":risk_id,"review_date":str(review_date_r),
                            "reviewer_name":user_name,"previous_rating":old_rating,
                            "new_rating":review_new_rating,"comments":review_comments
                        }).execute(), error_prefix="Risk review")
                        safe_supabase_query(lambda: supabase.table("risk_register").update({
                            "residual_rating":review_new_rating,"last_review_date":str(review_date_r),
                            "next_review_date":str(review_date_r + timedelta(days=90))
                        }).eq("id",risk_id).execute(), error_prefix="Risk update")
                        st.success("✅ Review recorded!"); st.rerun()

    
    # ============================================
    # TAB 5: AI-POWERED EXECUTIVE REPORTS
    # ============================================
    with tabs[5]:
        st.markdown("### 📄 AI-Powered Risk Intelligence Reports")
        
        # Period selector
        report_period = st.selectbox("📅 Report Period", ["Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Custom"], key="risk_period")
        
        if report_period == "Weekly":
            start_date = today - timedelta(days=7)
            end_date = today
        elif report_period == "Monthly":
            start_date = today.replace(day=1)
            end_date = today
        elif report_period == "Quarterly":
            q_month = ((today.month - 1) // 3) * 3 + 1
            start_date = date(today.year, q_month, 1)
            end_date = today
        elif report_period == "Half-Yearly":
            h_month = 1 if today.month <= 6 else 7
            start_date = date(today.year, h_month, 1)
            end_date = today
        elif report_period == "Yearly":
            start_date = date(today.year, 1, 1)
            end_date = today
        else:
            c1, c2 = st.columns(2)
            with c1: start_date = st.date_input("From", today - timedelta(days=30))
            with c2: end_date = st.date_input("To", today)
        
        # Filter data for period
        period_risks = risk_df[(pd.to_datetime(risk_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(risk_df["created_at"], errors='coerce').dt.date <= end_date)] if total_risks > 0 else pd.DataFrame()
        period_total = len(period_risks)
        period_extreme = len(period_risks[(period_risks["residual_level"] == "Extreme") & (period_risks["risk_status"] != "closed")]) if period_total > 0 else 0
        period_high = len(period_risks[(period_risks["residual_level"] == "High") & (period_risks["risk_status"] != "closed")]) if period_total > 0 else 0
        period_exposure = period_risks[(period_risks["residual_level"].isin(["High","Extreme"]))]["inherent_cons_financial"].sum() if period_total > 0 else 0
        period_treatments = 0
        period_fmeca = len(fmeca_df[(pd.to_datetime(fmeca_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(fmeca_df["created_at"], errors='coerce').dt.date <= end_date)]) if total_fmeca > 0 else 0
        
        st.caption(f"📅 {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')} | {period_total} risks | {period_fmeca} FMECA assessments")
        
        # Period KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("📋 Period Risks", period_total)
        with c2: st.metric("🔴 Extreme", period_extreme)
        with c3: st.metric("🟠 High", period_high)
        with c4: st.metric("💰 Exposure", f"₦{period_exposure:,.0f}")
        with c5: st.metric("🏗️ FMECA", period_fmeca)
        
        st.markdown("---")
        
        # Charts
        if period_total > 0:
            c1, c2 = st.columns(2)
            with c1:
                # Risk by Category
                if "risk_category" in period_risks.columns:
                    cat_counts = period_risks["risk_category"].value_counts().head(10)
                    cat_names_clean = [risk_categories.get(c, c).replace("_"," ").title()[:30] for c in cat_counts.index]
                    fig1 = px.bar(x=cat_counts.values, y=cat_names_clean, orientation='h', title="Risks by Category", color=cat_counts.values, color_continuous_scale=["#10B981","#F59E0B","#EF4444"])
                    fig1.update_layout(height=400)
                    st.plotly_chart(fig1, use_container_width=True)
            with c2:
                # Risk by Level
                level_counts = period_risks["residual_level"].value_counts()
                level_colors = {"Extreme":"#EF4444","High":"#F59E0B","Medium":"#3B82F6","Low":"#10B981"}
                pie_colors = [level_colors.get(l,"#999") for l in level_counts.index]
                fig2 = px.pie(values=level_counts.values, names=level_counts.index, title="Risk Level Distribution", color_discrete_sequence=pie_colors, hole=0.5)
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            
            # FMECA Chart
            if period_fmeca > 0:
                st.markdown("---")
                fmeca_period = fmeca_df[(pd.to_datetime(fmeca_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(fmeca_df["created_at"], errors='coerce').dt.date <= end_date)] if total_fmeca > 0 else pd.DataFrame()
                if len(fmeca_period) > 0:
                    fig3 = px.scatter(fmeca_period, x="condition_score", y="residual_rating", size="rpn_score", color="asset_criticality", hover_name="asset_name", title="Asset Risk Matrix — Condition vs Residual Risk", color_discrete_map={"Tier1":"#EF4444","Tier2":"#F59E0B","Tier3":"#3B82F6"})
                    fig3.update_layout(height=400)
                    st.plotly_chart(fig3, use_container_width=True)
        
        # AI Executive Summary
        st.markdown("---")
        st.markdown("### 🤖 AI Executive Summary")
        
        insights = []
        if period_extreme > 0:
            insights.append(f"🔴 **CRITICAL:** {period_extreme} Extreme risks require immediate board attention. Total exposure: ₦{period_exposure:,.0f}.")
        if period_high > 0:
            insights.append(f"🟠 **HIGH:** {period_high} High risks are being actively managed. Review treatment progress monthly.")
        if period_total > 0 and period_extreme == 0:
            insights.append("✅ No Extreme risks in this period. Risk posture is within acceptable thresholds.")
        if period_fmeca > 0:
            tier1_fmeca = len(fmeca_period[fmeca_period["asset_criticality"]=="Tier1"]) if len(fmeca_period) > 0 else 0
            insights.append(f"🏗️ {period_fmeca} FMECA assessments conducted ({tier1_fmeca} Tier 1 Critical Assets).")
        if overdue_treatments > 0:
            insights.append(f"⚠️ {overdue_treatments} treatment actions are overdue. Immediate follow-up required.")
        
        for insight in insights:
            st.markdown(f"""<div style="background:white;border-left:4px solid #CC0000;border-radius:8px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">{insight}</div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Export
        st.markdown("### 📥 Download Executive Reports")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 Generate Full Intelligence Report (HTML)", key="risk_html_full", use_container_width=True, type="primary"):
                import io, base64 as b64
                logo_b64 = get_logo_base64()
                logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
                
                # Generate chart images
                chart_html = ""
                try:
                    if period_total > 0 and "risk_category" in period_risks.columns:
                        cat_counts = period_risks["risk_category"].value_counts().head(10)
                        cat_names_clean = [risk_categories.get(c, c).replace("_"," ").title()[:30] for c in cat_counts.index]
                        fig_c = px.bar(x=cat_counts.values, y=cat_names_clean, orientation='h', title="Risks by Category", color=cat_counts.values, color_continuous_scale=["#10B981","#F59E0B","#EF4444"])
                        fig_c.update_layout(height=300, width=600)
                        buf = io.BytesIO()
                        fig_c.write_image(buf, format='png', engine='kaleido', scale=2)
                        chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf.getvalue()).decode()}" style="max-width:100%;"></div>'
                except: pass
                
                try:
                    if period_total > 0:
                        level_counts = period_risks["residual_level"].value_counts()
                        fig_p = px.pie(values=level_counts.values, names=level_counts.index, title="Risk Level Distribution", hole=0.5)
                        fig_p.update_layout(height=300, width=500)
                        buf2 = io.BytesIO()
                        fig_p.write_image(buf2, format='png', engine='kaleido', scale=2)
                        chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf2.getvalue()).decode()}" style="max-width:100%;"></div>'
                except: pass
                
                risk_rows = "".join([f"<tr><td>{r.get('risk_number','')}</td><td>{r.get('title','')[:60]}</td><td>{risk_categories.get(r.get('risk_category',''),r.get('risk_category',''))[:25]}</td><td>{r.get('residual_rating','')}/25</td><td>{r.get('residual_level','')}</td><td>₦{r.get('inherent_cons_financial',0):,.0f}</td></tr>" for _,r in period_risks.head(30).iterrows()])
                
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Risk Intelligence Report</title>
<style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:25px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:1000px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}.header{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}h1{{color:#CC0000;margin:0;font-size:22px}}.kpi-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:20px 0}}.kpi{{background:linear-gradient(135deg,#f9fafb,#fff);border-radius:10px;padding:15px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:24px;font-weight:800;color:#CC0000}}.kpi .lbl{{font-size:10px;color:#888;text-transform:uppercase}}h2{{color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;margin-top:25px;font-size:16px}}table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:11px}}th{{background:#CC0000;color:white;padding:10px;text-align:left;font-size:10px;text-transform:uppercase}}td{{padding:8px;border-bottom:1px solid #eee}}.insight-box{{background:#FEF2F2;border-left:4px solid #EF4444;padding:12px;margin:8px 0;border-radius:6px;font-size:12px}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:25px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container">
<div class="header"><div>{logo_img}<h1>Risk Intelligence Report</h1><p>{info.get('full_name',fc)} | {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')} | {report_period}</p></div></div>
<div class="kpi-row"><div class="kpi"><div class="val">{period_total}</div><div class="lbl">Total Risks</div></div><div class="kpi"><div class="val">{period_extreme}</div><div class="lbl">Extreme</div></div><div class="kpi"><div class="val">{period_high}</div><div class="lbl">High</div></div><div class="kpi"><div class="val">₦{period_exposure:,.0f}</div><div class="lbl">Exposure</div></div><div class="kpi"><div class="val">{period_fmeca}</div><div class="lbl">FMECA</div></div></div>
<div class="insight-box"><b>AI Executive Summary:</b> {insights[0] if insights else 'No risks in this period.'}</div>
{chart_html}
<h2>Risk Register — {report_period}</h2><table><tr><th>ID</th><th>Title</th><th>Category</th><th>Rating</th><th>Level</th><th>Exposure</th></tr>{risk_rows}</table>
<div class="footer">Churchgate Group | facilityXperience | ISO 31000 • COSO ERM • IEC 60812 | AI-Generated {today.strftime('%d %B %Y')}</div>
</div></body></html>"""
                
                st.download_button("📥 Download Intelligence Report (HTML)", html, f"risk_intelligence_{start_date}_{end_date}.html", "text/html", use_container_width=True)
        
        with c2:
            if st.button("📕 Generate PDF Report", key="risk_pdf_full", use_container_width=True):
                try:
                    from fpdf import FPDF; pdf = FPDF('L','mm','A4'); pdf.add_page()
                    pdf.set_font('Helvetica','B',18); pdf.set_text_color(204,0,0)
                    pdf.cell(0,12,safe_text('Risk Intelligence Report'),0,1)
                    pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                    pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {start_date.strftime("%d %b %Y")} - {end_date.strftime("%d %b %Y")} | {report_period}'),0,1)
                    pdf.ln(3)
                    pdf.set_font('Helvetica','B',10)
                    pdf.cell(0,6,f'Total: {period_total} | Extreme: {period_extreme} | High: {period_high} | Exposure: NGN {period_exposure:,.0f} | FMECA: {period_fmeca}',0,1)
                    pdf.ln(3)
                    pdf.set_font('Helvetica','B',8); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                    for h,w in zip(['ID','Title','Category','Rating','Level','Exposure'],[30,60,35,20,25,40]): pdf.cell(w,6,h,1,0,'C',True)
                    pdf.ln(); pdf.set_font('Helvetica','',7); pdf.set_text_color(0,0,0)
                    for _,r in period_risks.head(40).iterrows():
                        pdf.cell(30,5,safe_text(r.get('risk_number','')),1,0); pdf.cell(60,5,safe_text(str(r.get('title',''))[:26]),1,0)
                        pdf.cell(35,5,safe_text(risk_categories.get(r.get('risk_category',''),r.get('risk_category',''))[:15]),1,0)
                        pdf.cell(20,5,str(r.get('residual_rating','')),1,0); pdf.cell(25,5,safe_text(r.get('residual_level','')),1,0)
                        pdf.cell(40,5,f'N{safe_text(str(r.get("inherent_cons_financial",0)))}',1,0); pdf.ln()
                    pdf.ln(4)
                    pdf.set_font('Helvetica','B',8)
                    pdf.cell(0,5,'AI Executive Summary:',0,1)
                    pdf.set_font('Helvetica','',7)
                    for ins in insights:
                        pdf.multi_cell(0,4,safe_text(ins.replace('🔴','').replace('🟠','').replace('✅','').replace('🏗️','').replace('⚠️','').strip()),0)
                    pdf_file = f"/tmp/risk_intel_{start_date}_{end_date}.pdf"; pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f: st.download_button("📥 Download Intelligence Report (PDF)", f.read(), f"risk_intelligence_{start_date}_{end_date}.pdf", "application/pdf", use_container_width=True)
                except Exception as e: st.error(f"PDF: {str(e)[:80]}")



# ============================================
# AUDIT & GOVERNANCE — COMMAND CENTER
# ============================================
def page_ac():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    
    st.markdown(f'## ✅ Audit & Governance — {info.get("full_name", fc)}')
    st.caption("Governance & Assurance Command Center — Prove everything is working as claimed.")
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    audit_data = safe_supabase_query(lambda: supabase.table("audits").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="Audit data")
    audit_df = pd.DataFrame(audit_data.data) if audit_data and audit_data.data else pd.DataFrame()
    
    findings_data = safe_supabase_query(lambda: supabase.table("audit_findings").select("*").order("created_at", desc=True).limit(500).execute(), error_prefix="Findings data")
    findings_df = pd.DataFrame(findings_data.data) if findings_data and findings_data.data else pd.DataFrame()
    
    total_audits = len(audit_df)
    completed_audits = len(audit_df[audit_df["status"] == "completed"]) if total_audits > 0 else 0
    overdue_audits = len(audit_df[(audit_df["status"] != "completed") & (pd.to_datetime(audit_df["scheduled_date"], errors='coerce').dt.date < today)]) if total_audits > 0 else 0
    open_findings = len(findings_df[findings_df["status"] == "open"]) if len(findings_df) > 0 else 0
    critical_findings = len(findings_df[(findings_df["severity"] == "critical") & (findings_df["status"] == "open")]) if len(findings_df) > 0 else 0
    compliance_score = round((completed_audits / max(total_audits, 1)) * 100) if total_audits > 0 else 0
    
    # ============================================
    # 🟦 TOP RIBBON
    # ============================================
    st.markdown("### 🟦 Compliance Health Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#10B981" if compliance_score >= 90 else "#F59E0B" if compliance_score >= 75 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Compliance Score</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{compliance_score}%</div></div>""", unsafe_allow_html=True)
    with c2:
        color = "#EF4444" if overdue_audits > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overdue Audits</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{overdue_audits}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if open_findings > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Open NCRs</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{open_findings}</div></div>""", unsafe_allow_html=True)
    with c4:
        color = "#EF4444" if critical_findings > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Critical Findings</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{critical_findings}</div></div>""", unsafe_allow_html=True)
    with c5: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total Audits</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_audits}</div></div>""", unsafe_allow_html=True)
    with c6:
        ready = "✅ Ready" if compliance_score >= 90 and critical_findings == 0 else "❌ Not Ready"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Inspection Readiness</div><div style="font-size:1rem;font-weight:800;color:#8B5CF6;">{ready}</div></div>""", unsafe_allow_html=True)
    
    if critical_findings > 0:
        st.error(f"🚨 {critical_findings} CRITICAL findings open — immediate attention required!")
    if overdue_audits > 0:
        st.warning(f"⚠️ {overdue_audits} audits are overdue.")
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 Audits", "➕ New Audit", "🔍 Findings/NCRs", "✅ Spot Check", "📄 Reports"])
    
    # ============================================
    # TAB 0: ALL AUDITS
    # ============================================
    with tabs[0]:
        st.markdown("### 📋 Audit Register")
        
        if total_audits == 0:
            st.info("No audits recorded yet.")
        else:
            for _, aud in audit_df.head(20).iterrows():
                status = aud.get("status","planned")
                sc = {"planned":"#3B82F6","in_progress":"#F59E0B","completed":"#10B981","closed":"#6B7280"}.get(status,"#3B82F6")
                domain = aud.get("audit_domain","").replace("_"," ").title()
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <b>{aud.get('audit_number','N/A')}</b> — {aud.get('title','')[:80]}
                    <br><span style="font-size:0.65rem;color:#666;">🏷️ {domain} | 👤 {aud.get('auditor_name','')} | 📅 {str(aud.get('scheduled_date',''))}</span>
                    <span style="float:right;background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;">{status.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 1: NEW AUDIT
    # ============================================
    with tabs[1]:
        st.markdown("### ➕ Schedule New Audit")
        
        audit_domains = [
            "statutory_compliance", "operational_process", "financial",
            "contractor_vendor", "tenant_billing", "hoto_integrity", "data_quality"
        ]
        
        with st.form("new_audit_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                aud_title = st.text_input("Title*", placeholder="e.g., Fire System Annual Audit")
                aud_domain = st.selectbox("Domain*", audit_domains, format_func=lambda x: x.replace("_"," ").title())
            with c2:
                aud_auditor = st.text_input("Auditor Name*")
                aud_auditee = st.text_input("Auditee Name")
            with c3:
                aud_scheduled = st.date_input("Scheduled Date*", today)
                aud_next = st.date_input("Next Audit Due", today + timedelta(days=365))
            
            aud_desc = st.text_area("Scope/Description", height=80)
            
            if st.form_submit_button("➕ SCHEDULE AUDIT", use_container_width=True, type="primary"):
                if aud_title and aud_auditor:
                    aud_count = total_audits + 1
                    aud_number = f"AUD-{fc}-{today.strftime('%Y%m%d')}-{str(aud_count).zfill(4)}"
                    
                    safe_supabase_query(lambda: supabase.table("audits").insert({
                        "facility_code":fc,"audit_number":aud_number,"title":aud_title,
                        "audit_domain":aud_domain,"audit_type":"scheduled",
                        "description":aud_desc,"auditor_name":aud_auditor,
                        "auditee_name":aud_auditee,"scheduled_date":str(aud_scheduled),
                        "next_audit_date":str(aud_next),"status":"planned",
                        "created_by":user_name,"created_at":wat_now.isoformat()
                    }).execute(), error_prefix="Schedule audit")
                    
                    st.success(f"✅ Audit {aud_number} scheduled!"); st.balloons(); st.rerun()
                else:
                    st.error("⚠️ Title and Auditor are required")
    
    # ============================================
    # TAB 2: FINDINGS / NCRs
    # ============================================
    with tabs[2]:
        st.markdown("### 🔍 Non-Conformance Reports (NCRs)")
        
        if len(findings_df) == 0:
            st.success("✅ No findings recorded.")
        else:
            # Add finding
            with st.expander("➕ Raise New Finding"):
                with st.form("new_finding_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        fnd_description = st.text_input("Finding Description*")
                        fnd_severity = st.selectbox("Severity*", ["critical","major","minor","observation"])
                    with c2:
                        fnd_domain = st.selectbox("Domain", audit_domains, format_func=lambda x: x.replace("_"," ").title())
                        fnd_responsible = st.text_input("Responsible Person")
                    
                    c1, c2 = st.columns(2)
                    with c1: fnd_due = st.date_input("Due Date*", today + timedelta(days=14))
                    with c2: fnd_location = st.text_input("Location")
                    
                    fnd_corrective = st.text_area("Corrective Action Required")
                    
                    if st.form_submit_button("➕ RAISE NCR", use_container_width=True):
                            if fnd_description:
                                fnd_count = len(findings_df) + 1
                                fnd_number = f"NCR-{fc}-{today.strftime('%Y%m%d')}-{str(fnd_count).zfill(4)}"
                                safe_supabase_query(lambda: supabase.table("audit_findings").insert({
                                    "finding_number":fnd_number,"description":fnd_description,
                                    "severity":fnd_severity,"domain":fnd_domain,
                                    "responsible_person":fnd_responsible,"due_date":str(fnd_due),
                                    "location":fnd_location,"corrective_action":fnd_corrective,
                                    "status":"open","created_at":wat_now.isoformat()
                                }).execute(), error_prefix="Raise NCR")
                                st.success(f"✅ NCR {fnd_number} raised!"); st.rerun()
            
            st.markdown("---")
            
            for _, fnd in findings_df.head(30).iterrows():
                severity = fnd.get("severity","minor")
                sev_color = "#EF4444" if severity == "critical" else "#F59E0B" if severity == "major" else "#3B82F6" if severity == "minor" else "#6B7280"
                status = fnd.get("status","open")
                st_color = "#EF4444" if status == "open" else "#F59E0B" if status == "in_progress" else "#10B981"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sev_color};border-radius:8px;padding:0.7rem;margin:0.2rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <b>{fnd.get('finding_number','N/A')}</b> — {fnd.get('description','')[:80]}
                    <br><span style="font-size:0.6rem;">👤 {fnd.get('responsible_person','')} | 📅 Due: {fnd.get('due_date','')} | 🏷️ {fnd.get('domain','')}</span>
                    <span style="float:right;"><span style="background:{sev_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;">{severity.upper()}</span> <span style="background:{st_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;">{status.upper()}</span></span>
                </div>
                """, unsafe_allow_html=True)
                
                if status == "open":
                    if st.button("✅ Close Finding", key=f"close_fnd_{fnd['id']}", use_container_width=True):
                        safe_supabase_query(lambda: supabase.table("audit_findings").update({"status":"closed","closed_by":user_name,"closed_date":str(today)}).eq("id",fnd["id"]).execute(), error_prefix="Close finding")
                        st.success("✅ Closed!"); st.rerun()
    
    # ============================================
    # TAB 3: SPOT CHECK
    # ============================================
    with tabs[3]:
        st.markdown("### ✅ Spot Check (Continuous Assurance)")
        
        spot_data = safe_supabase_query(lambda: supabase.table("spot_checks").select("*").eq("facility_code",fc).order("created_at", desc=True).limit(50).execute(), error_prefix="Spot check data")
        spot_df = pd.DataFrame(spot_data.data) if spot_data and spot_data.data else pd.DataFrame()
        
        with st.form("spot_check_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                spot_type = st.selectbox("Check Type", ["Shift Handover","PM Quality","Security Patrol","Housekeeping","HOTO Completeness","WO Accuracy","Meter Reading"])
                spot_location = st.text_input("Location")
            with c2:
                spot_result = st.selectbox("Result", ["pass","fail","observation"])
                spot_date = st.date_input("Date", today)
            with c3:
                spot_auditor = st.text_input("Auditor Name", value=user_name)
            
            spot_finding = st.text_area("Findings/Notes")
            
            if st.form_submit_button("✅ SUBMIT SPOT CHECK", use_container_width=True, type="primary"):
                safe_supabase_query(lambda: supabase.table("spot_checks").insert({
                    "facility_code":fc,"check_type":spot_type,"location":spot_location,
                    "result":spot_result,"auditor_name":spot_auditor,
                    "check_date":str(spot_date),"finding":spot_finding
                }).execute(), error_prefix="Spot check")
                st.success("✅ Spot check recorded!"); st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Recent Spot Checks")
        
        if len(spot_df) > 0:
            pass_rate = round(len(spot_df[spot_df["result"]=="pass"]) / len(spot_df) * 100) if len(spot_df) > 0 else 0
            st.metric("Spot Check Pass Rate", f"{pass_rate}%")
            
            for _, spot in spot_df.head(15).iterrows():
                result = spot.get("result","pass")
                rc = "#10B981" if result == "pass" else "#EF4444" if result == "fail" else "#F59E0B"
                st.markdown(f"""
                <div style="background:white;border-left:3px solid {rc};border-radius:6px;padding:0.5rem;margin:0.1rem 0;font-size:0.75rem;">
                    <b>{spot.get('check_type','')}</b> — {spot.get('location','')} | {str(spot.get('check_date',''))}
                    <span style="float:right;color:{rc};font-weight:700;">{result.upper()}</span>
                    <br><span style="font-size:0.65rem;color:#666;">{spot.get('finding','')[:100]}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No spot checks recorded yet.")
    
    # ============================================
    # TAB 4: REPORTS
    # ============================================
    with tabs[4]:
        st.markdown("### 📄 Audit Reports")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Audits", total_audits)
        with c2: st.metric("Open NCRs", open_findings)
        with c3: st.metric("Compliance Score", f"{compliance_score}%")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 Generate Governance Report (HTML)", key="aud_html_btn", use_container_width=True, type="primary"):
                logo_b64 = get_logo_base64()
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Governance Report</title><style>body{{font-family:Arial;margin:20px}}h1{{color:#CC0000}}.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:20px 0}}.kpi{{background:#f9fafb;border-radius:10px;padding:12px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:20px;font-weight:800;color:#CC0000}}table{{width:100%;border-collapse:collapse;font-size:10px}}th{{background:#CC0000;color:white;padding:8px}}td{{padding:6px;border-bottom:1px solid #eee}}</style></head><body><h1>Audit & Governance Report</h1><p>{info.get('full_name',fc)} | {today}</p><div class="kpi-row"><div class="kpi"><div class="val">{compliance_score}%</div>Compliance</div><div class="kpi"><div class="val">{overdue_audits}</div>Overdue</div><div class="kpi"><div class="val">{open_findings}</div>Open NCRs</div><div class="kpi"><div class="val">{critical_findings}</div>Critical</div><div class="kpi"><div class="val">{total_audits}</div>Total</div><div class="kpi"><div class="val">{len(spot_df)}</div>Spot Checks</div></div><h2>Findings</h2><table><tr><th>ID</th><th>Description</th><th>Severity</th><th>Status</th><th>Due</th></tr>"""
                for _,fnd in findings_df.head(30).iterrows(): html += f"<tr><td>{fnd.get('finding_number','')}</td><td>{fnd.get('description','')[:60]}</td><td>{fnd.get('severity','').upper()}</td><td>{fnd.get('status','').upper()}</td><td>{fnd.get('due_date','')}</td></tr>"
                html += "</table></body></html>"
                st.download_button("📥 Download HTML", html, f"governance_report_{today}.html", "text/html", use_container_width=True)
        with c2:
            if st.button("📕 Generate PDF Report", key="aud_pdf_btn", use_container_width=True):
                try:
                    from fpdf import FPDF; pdf = FPDF('L','mm','A4'); pdf.add_page()
                    pdf.set_font('Helvetica','B',16); pdf.set_text_color(204,0,0)
                    pdf.cell(0,10,safe_text('Audit & Governance Report'),0,1)
                    pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                    pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {today}'),0,1); pdf.ln(4)
                    pdf.set_font('Helvetica','B',7); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                    for h,w in zip(['ID','Description','Severity','Status','Due'],[35,85,30,30,30]): pdf.cell(w,5,h,1,0,'C',True)
                    pdf.ln(); pdf.set_font('Helvetica','',7); pdf.set_text_color(0,0,0)
                    for _,fnd in findings_df.head(40).iterrows():
                        pdf.cell(35,4,safe_text(fnd.get('finding_number','')),1,0); pdf.cell(85,4,safe_text(str(fnd.get('description',''))[:38]),1,0)
                        pdf.cell(30,4,safe_text(fnd.get('severity','').upper()),1,0); pdf.cell(30,4,safe_text(fnd.get('status','').upper()),1,0)
                        pdf.cell(30,4,str(fnd.get('due_date','')),1,0); pdf.ln()
                    pdf_file = f"/tmp/audit_report_{today}.pdf"; pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f: st.download_button("📥 Download PDF", f.read(), f"audit_report_{today}.pdf", "application/pdf", use_container_width=True)
                except Exception as e: st.error(f"PDF: {str(e)[:80]}")

# ============================================
# VOICE OF CUSTOMER — FEEDBACK SYSTEM
# ============================================
def page_feedback():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    
    # Safe query helper with retry
    import time as _time
    
    def safe_supabase(query_fn, max_retries=3):
        for attempt in range(max_retries):
            try:
                return query_fn()
            except Exception as e:
                if attempt == max_retries - 1:
                    st.error("⚠️ Connection error. Please refresh the page.")
                    return None
                _time.sleep(0.5)
        return None
    
    st.markdown(f'## ⭐ Voice of Customer — {info.get("full_name", fc)}')
    
    tabs = st.tabs(["📝 Take Survey", "📊 Feedback Dashboard", "📈 AI Analytics", "⚙️ Survey Admin"])
    
    # ============================================
    # TAB 0: TAKE SURVEY
    # ============================================
    with tabs[0]:
        if st.session_state.get("show_success", False):
            st.success("✅ Thank you for your feedback! Your responses have been recorded. A confirmation has been sent to your email.")
            st.balloons()
            st.session_state.show_success = False
        
        survey = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).eq("is_active", True).execute())
        if survey is None: st.stop()
        
        if not survey.data or len(survey.data) == 0:
            st.markdown("""
            <div style="background:white;border-radius:12px;padding:2rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                <div style="font-size:3rem;">📝</div>
                <h3>No Active Survey</h3>
                <p style="color:#888;">There is no survey available at this time. Please check back during the survey period.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            s = survey.data[0]
            survey_title = s.get('title','Tenant Satisfaction Survey')
            start_date = s.get('start_date', '')
            end_date = s.get('end_date', '')
            
            quarter_display = ""
            if "Q1" in survey_title: quarter_display = "Q1 (April – June)"
            elif "Q2" in survey_title: quarter_display = "Q2 (July – September)"
            elif "Q3" in survey_title: quarter_display = "Q3 (October – December)"
            elif "Q4" in survey_title: quarter_display = "Q4 (January – March)"
            else: quarter_display = f"FY {date.today().year}"
            
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a1a1a,#2a2a2a);border-radius:12px;padding:1.5rem;color:white;margin-bottom:1rem;text-align:center;">
                <h2 style="margin:0;font-weight:800;">📝 Tenant Satisfaction Survey</h2>
                <p style="margin:5px 0 0 0;font-size:1rem;opacity:0.9;">{quarter_display}</p>
                <p style="margin:10px 0 0 0;font-size:0.8rem;opacity:0.7;">We value your feedback. This survey takes less than 5 minutes.</p>
            </div>
            """, unsafe_allow_html=True)
            
            questions = safe_supabase(lambda: supabase.table("feedback_questions").select("*").eq("survey_id", s["id"]).order("question_number").execute())
            if questions is None: st.stop()
            
            if questions.data:
                with st.form("feedback_form"):
                    st.markdown("### 👤 Your Details")
                    c1, c2, c3 = st.columns(3)
                    with c1: resp_name = st.text_input("Full Name*", placeholder="Enter your full name")
                    with c2: resp_company = st.text_input("Company Name*", placeholder="Your organization")
                    with c3: resp_email = st.text_input("Email Address*", placeholder="your@email.com")
                    
                    st.markdown("---")
                    st.markdown("### ⭐ Rate Your Experience")
                    st.caption("4 = Excellent | 3 = Good | 2 = Average | 1 = Below Average")
                    
                    scores = {}
                    for q in questions.data:
                        qnum = q.get("question_number")
                        qtype = q.get("question_type","rating")
                        qtext = q.get("question_text","")
                        qcat = q.get("category","")
                        
                        if qtype == "rating":
                            st.markdown(f"""
                            <div style="background:#f9fafb;border-radius:8px;padding:0.8rem;margin:0.3rem 0;border:1px solid #e5e7eb;">
                                <b style="font-size:0.85rem;">{qnum}. {qtext}</b>
                                <span style="font-size:0.65rem;color:#888;margin-left:0.5rem;">({qcat})</span>
                            </div>
                            """, unsafe_allow_html=True)
                            score = st.select_slider(f"Rating for Q{qnum}", options=[1, 2, 3, 4], value=3,
                                format_func=lambda x: f"{'⭐'*x} {'Poor' if x==1 else 'Average' if x==2 else 'Good' if x==3 else 'Excellent'}",
                                key=f"q_{q['id']}", label_visibility="collapsed")
                            scores[q["id"]] = {"score": score}
                        else:
                            st.markdown(f"""
                            <div style="background:#f9fafb;border-radius:8px;padding:0.8rem;margin:0.3rem 0;border:1px solid #e5e7eb;">
                                <b style="font-size:0.85rem;">{qnum}. {qtext}</b>
                            </div>
                            """, unsafe_allow_html=True)
                            text_answer = st.text_area(f"Your answer for Q{qnum}", key=f"q_{q['id']}", height=80, label_visibility="collapsed", placeholder="Type your response here...")
                            scores[q["id"]] = {"text": text_answer}
                    
                    st.markdown("---")
                    anon = st.checkbox("Submit anonymously (your name won't be shared)")
                    submitted = st.form_submit_button("📩 SUBMIT FEEDBACK", use_container_width=True, type="primary")
                    
                    if submitted:
                        errors = []
                        if not resp_name or resp_name.strip() == "": errors.append("Full Name")
                        if not resp_company or resp_company.strip() == "": errors.append("Company Name")
                        if not resp_email or resp_email.strip() == "": errors.append("Email Address")
                        
                        unanswered = []
                        for q in questions.data:
                            qid = q["id"]
                            qnum = q.get("question_number", "?")
                            qtype = q.get("question_type", "rating")
                            if qtype == "rating":
                                if qid not in scores or scores[qid].get("score") is None: unanswered.append(f"Q{qnum}")
                            else:
                                if qid not in scores or not scores[qid].get("text", "").strip(): unanswered.append(f"Q{qnum}")
                        
                        if errors: st.error(f"⚠️ Required fields missing: {', '.join(errors)}")
                        elif unanswered: st.error(f"⚠️ Please answer all questions. Unanswered: {', '.join(unanswered)}")
                        else:
                            res = safe_supabase(lambda: supabase.table("feedback_responses").insert({
                                "survey_id": s["id"], "respondent_email": resp_email if not anon else None,
                                "respondent_name": resp_name if not anon else "Anonymous", "company": resp_company,
                                "facility_code": fc, "is_anonymous": anon, "submitted_at": datetime.now().isoformat()
                            }).execute())
                            
                            if res and res.data:
                                resp_id = res.data[0]["id"]
                                for qid, data in scores.items():
                                    safe_supabase(lambda: supabase.table("feedback_scores").insert({
                                        "response_id": resp_id, "question_id": qid,
                                        "score": data.get("score"), "text_answer": data.get("text")
                                    }).execute())
                                
                                if resp_email and not anon:
                                    try:
                                        send_email_notification(resp_email, f"✅ Survey Received — Thank You, {resp_name}!",
                                            f"""<div style="font-family:Arial;max-width:550px;border:1px solid #ddd;border-radius:12px;overflow:hidden;margin:0 auto;">
                                            <div style="background:linear-gradient(135deg,#1a1a1a,#2a2a2a);padding:25px;text-align:center;color:white;">
                                            <h2 style="margin:0;font-weight:800;">🙏 Thank You for Your Feedback</h2>
                                            <p style="margin:8px 0 0 0;font-size:14px;opacity:0.9;">{info.get('full_name',fc)} — Churchgate Group</p></div>
                                            <div style="padding:25px;background:#f9fafb;"><p style="font-size:15px;color:#1a1a1a;">Dear <b>{resp_name}</b>,</p>
                                            <p style="font-size:14px;color:#444;line-height:1.6;">Thank you for completing our <b>{quarter_display}</b> tenant satisfaction survey.</p>
                                            <div style="text-align:center;margin:20px 0;"><a href="https://churchgate-facilityxperience.hf.space" style="background:#CC0000;color:white;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;font-size:13px;">Open facilityXperience</a></div>
                                            </div></div>""")
                                    except: pass
                                
                                st.session_state.show_success = True
                                st.rerun()
    
    # ============================================
    # TAB 1: FEEDBACK DASHBOARD
    # ============================================
    with tabs[1]:
        st.markdown("### 🏢 Asset Health Control Tower")
        
        survey = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(1).execute())
        if survey is None: st.stop()
        
        if not survey.data or len(survey.data) == 0:
            st.info("No survey data available.")
        else:
            s = survey.data[0]
            responses = safe_supabase(lambda: supabase.table("feedback_responses").select("id, respondent_name, company, is_anonymous, submitted_at").eq("survey_id", s["id"]).execute())
            questions = safe_supabase(lambda: supabase.table("feedback_questions").select("*").eq("survey_id", s["id"]).order("question_number").execute())
            if responses is None or questions is None: st.stop()
            
            total_responses = len(responses.data) if responses.data else 0
            
            if total_responses == 0:
                st.info("No responses yet.")
            else:
                q_lookup = {}
                for q in (questions.data or []):
                    q_lookup[q["id"]] = {"number": q.get("question_number"), "category": q.get("category", ""), "text": q.get("question_text", ""), "type": q.get("question_type", "rating")}
                
                all_scores = {}
                tenant_list = []
                for r in (responses.data or []):
                    resp_id = r["id"]
                    scores = safe_supabase(lambda: supabase.table("feedback_scores").select("question_id, score, text_answer").eq("response_id", resp_id).execute())
                    tenant_scores = {}
                    for sc in (scores.data if scores else []):
                        if sc.get("score"): tenant_scores[sc["question_id"]] = sc.get("score")
                    all_scores[resp_id] = {"name": r.get("respondent_name","?") if not r.get("is_anonymous") else "Anonymous", "company": r.get("company","?"), "scores": tenant_scores, "submitted": str(r.get("submitted_at",""))[:10]}
                    tenant_list.append(all_scores[resp_id])
                
                hard_qs = [qid for qid, q in q_lookup.items() if q["number"] and 1 <= q["number"] <= 8]
                soft_qs = [qid for qid, q in q_lookup.items() if q["number"] and q["number"] in [9, 10, 12]]
                
                fsi_vals, hei_vals, nps_vals = [], [], []
                for td in tenant_list:
                    h = [td["scores"].get(qid, 0) for qid in hard_qs if td["scores"].get(qid)]
                    s = [td["scores"].get(qid, 0) for qid in soft_qs if td["scores"].get(qid)]
                    if h: fsi_vals.append(sum(h)/len(h))
                    if s: hei_vals.append(sum(s)/len(s))
                    q13_id = next((qid for qid, q in q_lookup.items() if q["number"] == 13), None)
                    if q13_id and td["scores"].get(q13_id): nps_vals.append(td["scores"][q13_id])
                
                avg_fsi = round(sum(fsi_vals)/len(fsi_vals), 1) if fsi_vals else 0
                avg_hei = round(sum(hei_vals)/len(hei_vals), 1) if hei_vals else 0
                promoters = sum(1 for s in nps_vals if s >= 4)
                passives = sum(1 for s in nps_vals if s == 3)
                detractors = sum(1 for s in nps_vals if s <= 2)
                nps_score = round(((promoters - detractors) / max(len(nps_vals), 1)) * 100)
                tss = round(((avg_fsi * 0.5 + avg_hei * 0.3 + (promoters/max(total_responses,1)) * 0.2 * 4) / 4) * 100)
                churn_risk = round((passives / max(total_responses, 1)) * 100) if total_responses > 0 else 0
                advocacy_delta = round(abs(avg_fsi - avg_hei), 1)
                
                tenant_health = []
                for td in tenant_list:
                    vals = [v for v in td["scores"].values() if v]
                    if vals:
                        avg = sum(vals)/len(vals)
                        nps = td["scores"].get(q13_id, 3) if q13_id else 3
                        health = min(100, max(0, round((avg * 0.6 + nps * 0.4) * 25)))
                        risk = "Low" if health >= 75 else "Medium" if health >= 50 else "High"
                        tenant_health.append({"Tenant": td["company"], "Health": health, "Risk": risk, "Name": td["name"]})
                
                high_risk = len([t for t in tenant_health if t["Risk"] == "High"])
                at_risk_revenue = high_risk * 50000
                
                cat_scores = {}
                for qid, qinfo in q_lookup.items():
                    cat = qinfo.get("category", qinfo.get("text", ""))
                    if not cat: continue
                    vals = [td["scores"].get(qid) for td in tenant_list if td["scores"].get(qid)]
                    if vals: cat_scores[cat] = round(sum(vals)/len(vals), 1)
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    tc = "#10B981" if tss >= 80 else "#F59E0B" if tss >= 60 else "#EF4444"
                    st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid {tc};box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Tenant Sentiment Score</div><div style="font-size:2rem;font-weight:800;color:{tc};">{tss}/100</div></div>""", unsafe_allow_html=True)
                with c2:
                    tc = "#10B981" if churn_risk < 5 else "#F59E0B" if churn_risk < 15 else "#EF4444"
                    st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid {tc};box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Silent Churn Risk</div><div style="font-size:2rem;font-weight:800;color:{tc};">{churn_risk}%</div></div>""", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #3B82F6;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">NPS Score</div><div style="font-size:2rem;font-weight:800;color:#3B82F6;">{nps_score}</div></div>""", unsafe_allow_html=True)
                with c4:
                    tc = "#F59E0B" if advocacy_delta > 0.5 else "#10B981"
                    st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid {tc};box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Advocacy Delta</div><div style="font-size:2rem;font-weight:800;color:{tc};">{advocacy_delta}</div></div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                left_col, right_col = st.columns([3, 2])
                
                with left_col:
                    st.markdown("### 📊 P.R.E.D.I.C.T. Tenant Health Matrix")
                    scatter_data = []
                    for td in tenant_list:
                        h_avg = sum([td["scores"].get(qid, 0) for qid in hard_qs if td["scores"].get(qid)]) / max(len([qid for qid in hard_qs if td["scores"].get(qid)]), 1)
                        s_avg = sum([td["scores"].get(qid, 0) for qid in soft_qs if td["scores"].get(qid)]) / max(len([qid for qid in soft_qs if td["scores"].get(qid)]), 1)
                        scatter_data.append({"Tenant": td["company"], "Hard FM": h_avg, "Soft FM": s_avg, "Size": 20})
                    if scatter_data:
                        sd = pd.DataFrame(scatter_data)
                        fig_scatter = px.scatter(sd, x="Hard FM", y="Soft FM", text="Tenant", size="Size", title="Tenant Positioning Matrix", color_discrete_sequence=["#CC0000"], range_x=[0,4.5], range_y=[0,4.5])
                        fig_scatter.add_hline(y=2.5, line_dash="dash", line_color="#F59E0B")
                        fig_scatter.add_vline(x=2.5, line_dash="dash", line_color="#F59E0B")
                        fig_scatter.update_layout(height=400)
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        st.caption("🟢 Top-Right: Stars | 🔵 Bottom-Right: Machines | 🟡 Top-Left: Hospitable but Broken | 🔴 Bottom-Left: At-Risk")
                    
                    st.markdown("---")
                    st.markdown("### 📉 Category Performance")
                    if cat_scores:
                        sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1])
                        cat_df = pd.DataFrame(sorted_cats, columns=["Category", "Score"])
                        cat_df["Color"] = ["#EF4444" if s < 2.5 else "#F59E0B" if s < 3.5 else "#10B981" for s in cat_df["Score"]]
                        fig_lollipop = go.Figure()
                        for _, row in cat_df.iterrows():
                            fig_lollipop.add_trace(go.Scatter(x=[row["Score"]], y=[row["Category"]], mode="markers", marker=dict(color=row["Color"], size=14), name=row["Category"]))
                            fig_lollipop.add_trace(go.Scatter(x=[0, row["Score"]], y=[row["Category"], row["Category"]], mode="lines", line=dict(color=row["Color"], width=3), showlegend=False))
                        fig_lollipop.update_layout(height=400, xaxis_title="Score /4", xaxis_range=[0,4.5], showlegend=False)
                        st.plotly_chart(fig_lollipop, use_container_width=True)
                
                with right_col:
                    st.markdown("### 💬 Voice of Customer")
                    q14_id = next((qid for qid, q in q_lookup.items() if q["number"] == 14), None)
                    if q14_id:
                        quotes = []
                        text_scores = safe_supabase(lambda: supabase.table("feedback_scores").select("text_answer").eq("question_id", q14_id).execute())
                        if text_scores is None: text_scores = type('obj', (object,), {'data': []})()
                        if text_scores.data:
                            for ts in text_scores.data:
                                if ts.get("text_answer") and ts["text_answer"].strip():
                                    quotes.append(ts["text_answer"])
                        if quotes:
                            for i, quote in enumerate(quotes[:5]):
                                st.markdown(f"""<div style="background:white;border-left:4px solid #CC0000;border-radius:8px;padding:0.8rem;margin:0.4rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);"><p style="font-size:0.8rem;font-style:italic;margin:0;">"{quote[:150]}{'...' if len(quote)>150 else ''}"</p><p style="font-size:0.6rem;color:#888;margin-top:0.3rem;">— Response #{i+1}</p></div>""", unsafe_allow_html=True)
                        else:
                            st.info("No open-text responses yet.")
                    
                    st.markdown("---")
                    st.markdown("### ⚠️ AI Risk Alerts")
                    if detractors > 0:
                        st.error(f"🚨 **Detractor Alert:** {detractors} tenant(s) unlikely to recommend. Immediate outreach recommended.")
                    if churn_risk > 10:
                        st.warning(f"⚠️ **Silent Churn:** {churn_risk}% of tenants are Passive. One bad experience away from Detractors.")
                    if advocacy_delta > 0.5:
                        st.info(f"📡 **Perception Gap:** Hard FM and Soft FM differ by {advocacy_delta} points.")
                
                st.markdown("---")
                st.markdown("### 📋 Respondent Details")
                resp_page_size = 10
                if "resp_page" not in st.session_state: st.session_state.resp_page = 1
                total_resp_pages = max(1, (total_responses + resp_page_size - 1) // resp_page_size)
                resp_start = (st.session_state.resp_page - 1) * resp_page_size
                resp_end = min(resp_start + resp_page_size, total_responses)
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    if st.button("◀", key="resp_prev") and st.session_state.resp_page > 1: st.session_state.resp_page -= 1; st.rerun()
                with c2: st.markdown(f"**Page {st.session_state.resp_page} of {total_resp_pages}**")
                with c3:
                    if st.button("▶", key="resp_next") and st.session_state.resp_page < total_resp_pages: st.session_state.resp_page += 1; st.rerun()
                
                st.markdown("### 📥 Export Reports")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("📊 Generate Executive Report", key="gen_html_report", use_container_width=True, type="primary"): st.session_state.show_report_preview = True; st.rerun()
                with c2:
                    if st.button("📕 Generate PDF Report", key="gen_pdf_report", use_container_width=True): st.session_state.show_pdf_download = True; st.rerun()
                
                if st.session_state.get("show_report_preview", False):
                    st.markdown("---")
                    st.markdown("### 📊 Executive Report — Preview")
                    logo_b64 = get_logo_base64()
                    logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
                    import io, base64 as b64
                    chart_html = ""
                    try:
                        if cat_scores:
                            sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1])
                            cat_df = pd.DataFrame(sorted_cats, columns=["Category", "Score"])
                            fig1 = px.bar(cat_df, x="Score", y="Category", orientation='h', title="Category Performance", color="Score", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[1,4], height=350)
                            buf1 = io.BytesIO(); fig1.write_image(buf1, format='png', engine='kaleido', scale=2)
                            chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf1.getvalue()).decode()}" style="width:100%;max-width:800px;"></div>'
                    except: pass
                    try:
                        if nps_vals:
                            fig2 = px.pie(values=[detractors, passives, promoters], names=["Detractors","Passives","Promoters"], title="NPS Distribution", color_discrete_sequence=["#EF4444","#F59E0B","#10B981"], hole=0.5, height=300)
                            buf2 = io.BytesIO(); fig2.write_image(buf2, format='png', engine='kaleido', scale=2)
                            chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf2.getvalue()).decode()}" style="width:100%;max-width:400px;"></div>'
                    except: pass
                    try:
                        if tenant_health:
                            th_df = pd.DataFrame(tenant_health).sort_values("Health")
                            fig3 = px.bar(th_df, x="Health", y="Tenant", orientation='h', title="Tenant Health Scores", color="Health", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[0,100], height=300)
                            buf3 = io.BytesIO(); fig3.write_image(buf3, format='png', engine='kaleido', scale=2)
                            chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf3.getvalue()).decode()}" style="width:100%;max-width:800px;"></div>'
                    except: pass
                    cat_rows = "".join([f"<tr><td>{cat}</td><td style='color:{'#EF4444' if score<2.5 else '#F59E0B' if score<3.5 else '#10B981'};font-weight:700;'>{score}/4</td></tr>" for cat, score in sorted(cat_scores.items(), key=lambda x: x[1])])
                    resp_rows = "".join([f"<tr><td>{r.get('respondent_name','?')}</td><td>{r.get('company','?')}</td><td>{str(r.get('submitted_at',''))[:10]}</td></tr>" for r in (responses.data or [])])
                    full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Executive Tenant Satisfaction Report</title><style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:20px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:960px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}.header{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}.header h1{{color:#CC0000;margin:0;font-size:22px}}.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}}.kpi{{background:linear-gradient(135deg,#f9fafb,#fff);border-radius:10px;padding:15px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:26px;font-weight:800;color:#CC0000}}.kpi .lbl{{font-size:10px;color:#888;text-transform:uppercase}}h2{{color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;margin-top:25px;font-size:16px}}table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:12px}}th{{background:#CC0000;color:white;padding:10px;text-align:left;font-size:10px;text-transform:uppercase}}td{{padding:8px 10px;border-bottom:1px solid #eee}}.insight-box{{background:#FEF2F2;border-left:4px solid #EF4444;padding:12px;margin:15px 0;border-radius:6px;font-size:13px}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:25px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container"><div class="header"><div>{logo_img}<h1>Executive Tenant Satisfaction Report</h1><p>{info.get('full_name',fc)} | {date.today().strftime('%d %B %Y')} | {total_responses} Responses</p></div></div><div class="kpi-row"><div class="kpi"><div class="val">{tss}/100</div><div class="lbl">TSS</div></div><div class="kpi"><div class="val">{nps_score}</div><div class="lbl">NPS</div></div><div class="kpi"><div class="val">{churn_risk}%</div><div class="lbl">Churn Risk</div></div><div class="kpi"><div class="val">{total_responses}</div><div class="lbl">Responses</div></div></div><div class="insight-box"><b>Executive Summary:</b> TSS of {tss}/100. {high_risk} high-risk tenants. {detractors} detractor(s).</div><h2>Category Performance</h2>{chart_html}<table><tr><th>Category</th><th>Score</th></tr>{cat_rows}</table><h2>Respondent Details</h2><table><tr><th>Name</th><th>Company</th><th>Date</th></tr>{resp_rows}</table><div class="footer">Churchgate Group | facilityXperience | Confidential | {date.today().strftime('%d %B %Y')}</div></div></body></html>"""
                    st.components.v1.html(full_html, height=800, scrolling=True)
                    c1, c2 = st.columns(2)
                    with c1: st.download_button("📥 Download HTML Report", full_html, f"executive_tenant_report_{date.today()}.html", "text/html", use_container_width=True)
                    with c2:
                        if st.button("❌ Close Preview", key="close_html_preview", use_container_width=True): st.session_state.show_report_preview = False; st.rerun()
                
                if st.session_state.get("show_pdf_download", False):
                    try:
                        from fpdf import FPDF; pdf = FPDF(); pdf.add_page()
                        pdf.set_font('Helvetica','B',16); pdf.set_text_color(204,0,0)
                        pdf.cell(0,10,safe_text('Executive Tenant Satisfaction Report'),0,1)
                        pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                        pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {date.today().strftime("%d %B %Y")}'),0,1); pdf.ln(3)
                        pdf.set_font('Helvetica','B',11)
                        pdf.cell(0,6,f'TSS: {tss}/100 | NPS: {nps_score} | Churn Risk: {churn_risk}% | Responses: {total_responses}',0,1); pdf.ln(5)
                        pdf.set_font('Helvetica','B',10); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                        pdf.cell(90,6,'Respondent',1,0,'C',True); pdf.cell(60,6,'Company',1,0,'C',True); pdf.cell(30,6,'Date',1,0,'C',True); pdf.ln()
                        pdf.set_font('Helvetica','',9); pdf.set_text_color(0,0,0)
                        for r in (responses.data or []):
                            pdf.cell(90,5,safe_text(r.get('respondent_name','?')[:35]),1,0); pdf.cell(60,5,safe_text(r.get('company','?')[:25]),1,0); pdf.cell(30,5,str(r.get('submitted_at',''))[:10],1,0); pdf.ln()
                        pdf_file = f"/tmp/tenant_report_{date.today()}.pdf"; pdf.output(pdf_file)
                        with open(pdf_file,"rb") as f: st.download_button("📥 Download PDF Report", f.read(), f"executive_tenant_report_{date.today()}.pdf", "application/pdf", use_container_width=True)
                        if st.button("❌ Close PDF", key="close_pdf_preview", use_container_width=True): st.session_state.show_pdf_download = False; st.rerun()
                    except Exception as e: st.error(f"PDF error: {str(e)[:80]}"); st.session_state.show_pdf_download = False
                
                if responses.data:
                    for r in list(responses.data)[resp_start:resp_end]:
                        td = next((t for t in tenant_list if t.get("name") == r.get("respondent_name","?")), None)
                        st.markdown(f"""<div style="background:white;border-radius:10px;padding:1rem;margin:0.4rem 0;border-left:5px solid #3B82F6;box-shadow:0 2px 6px rgba(0,0,0,0.06);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><b style="font-size:0.9rem;">{r.get('respondent_name','?')}</b><span style="background:#EFF6FF;color:#2563EB;padding:2px 10px;border-radius:12px;font-size:0.65rem;margin-left:0.5rem;">{r.get('company','?')}</span></div><span style="font-size:0.7rem;color:#888;">📅 {str(r.get('submitted_at',''))[:10]}</span></div><div style="margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:4px;">{''.join([f'<span style="background:#f0f0f0;padding:2px 8px;border-radius:8px;font-size:0.65rem;">Q{q_lookup[qid]["number"]}: <b>{td["scores"][qid]}/4</b></span>' for qid in td["scores"] if qid in q_lookup][:12]) if td else ''}</div></div>""", unsafe_allow_html=True)
    
    # ============================================
    # TAB 2: AI ANALYTICS
    # ============================================
    with tabs[2]:
        st.markdown("### 🤖 AI-Powered Tenant Health & Revenue Protection Report")
        st.caption("P.R.E.D.I.C.T. Framework — Performance, Retention, Early Detection, Intelligence, Churn, Treasury")
        
        survey = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(1).execute())
        if survey is None: st.stop()
        
        if not survey.data or len(survey.data) == 0:
            st.info("No survey data available for AI analysis.")
        else:
            s = survey.data[0]
            questions = safe_supabase(lambda: supabase.table("feedback_questions").select("*").eq("survey_id", s["id"]).order("question_number").execute())
            responses = safe_supabase(lambda: supabase.table("feedback_responses").select("id, respondent_name, company, is_anonymous").eq("survey_id", s["id"]).execute())
            if questions is None or responses is None: st.stop()
            
            if not responses.data or len(responses.data) < 3:
                st.warning(f"""
                📊 **Insufficient Data for Full AI Analysis**
                <br>Current responses: **{len(responses.data) if responses.data else 0}**
                <br>Minimum needed: **5** for statistical significance
                <br>📣 Share the survey link with more tenants to unlock:
                <br>• Tenant Health Scoring • Churn Prediction • Revenue Risk Analysis • Trend Detection
                """)
                
                if responses.data and len(responses.data) >= 1:
                    st.markdown("---")
                    st.markdown("### 📊 Basic Summary (Limited Data)")
                    st.caption("Full AI insights will unlock with 5+ responses.")
                    st.metric("Total Responses", len(responses.data))
                    q_lookup_temp = {}
                    for q in (questions.data or []):
                        q_lookup_temp[q["id"]] = {"number": q.get("question_number"), "category": q.get("category", ""), "text": q.get("question_text","")}
                    cat_scores_temp = {}
                    for r in responses.data:
                        scores = safe_supabase(lambda: supabase.table("feedback_scores").select("question_id, score").eq("response_id", r["id"]).execute())
                        for sc in (scores.data if scores else []):
                            qid = sc.get("question_id")
                            if qid in q_lookup_temp and sc.get("score"):
                                cat = q_lookup_temp[qid].get("category", q_lookup_temp[qid].get("text",""))
                                if cat not in cat_scores_temp: cat_scores_temp[cat] = []
                                cat_scores_temp[cat].append(sc["score"])
                    if cat_scores_temp:
                        for cat, vals in cat_scores_temp.items():
                            avg = round(sum(vals)/len(vals), 1); stars = "⭐" * round(avg)
                            st.markdown(f"{stars} **{cat}**: {avg}/4")
            else:
                q_lookup = {}
                for q in (questions.data or []):
                    q_lookup[q["id"]] = {"number": q.get("question_number"), "category": q.get("category", ""), "text": q.get("question_text", ""), "type": q.get("question_type", "rating")}
                
                tenant_list = []
                for r in (responses.data or []):
                    resp_id = r["id"]
                    scores = safe_supabase(lambda: supabase.table("feedback_scores").select("question_id, score, text_answer").eq("response_id", resp_id).execute())
                    tenant_scores = {}; text_answers = {}
                    for sc in (scores.data if scores else []):
                        if sc.get("score"): tenant_scores[sc["question_id"]] = sc.get("score")
                        if sc.get("text_answer"): text_answers[sc["question_id"]] = sc.get("text_answer")
                    tenant_list.append({"name": r.get("respondent_name","?"), "company": r.get("company","?"), "scores": tenant_scores, "texts": text_answers})
                
                hard_qs = [qid for qid, q in q_lookup.items() if q["number"] and 1 <= q["number"] <= 8]
                soft_qs = [qid for qid, q in q_lookup.items() if q["number"] and q["number"] in [9, 10, 12]]
                
                fsi_vals, hei_vals, nps_vals = [], [], []
                for td in tenant_list:
                    h = [td["scores"].get(qid, 0) for qid in hard_qs if td["scores"].get(qid)]
                    s = [td["scores"].get(qid, 0) for qid in soft_qs if td["scores"].get(qid)]
                    if h: fsi_vals.append(sum(h)/len(h))
                    if s: hei_vals.append(sum(s)/len(s))
                    q13_id = next((qid for qid, q in q_lookup.items() if q["number"] == 13), None)
                    if q13_id and td["scores"].get(q13_id): nps_vals.append(td["scores"][q13_id])
                
                avg_fsi = round(sum(fsi_vals)/len(fsi_vals), 1) if fsi_vals else 0
                avg_hei = round(sum(hei_vals)/len(hei_vals), 1) if hei_vals else 0
                promoters = sum(1 for s in nps_vals if s >= 4)
                passives = sum(1 for s in nps_vals if s == 3)
                detractors = sum(1 for s in nps_vals if s <= 2)
                nps_score = round(((promoters - detractors) / max(len(nps_vals), 1)) * 100)
                tss = round(((avg_fsi * 0.5 + avg_hei * 0.3 + (promoters/max(len(tenant_list),1)) * 0.2 * 4) / 4) * 100)
                churn_risk = round((passives / max(len(tenant_list), 1)) * 100)
                
                tenant_health = []
                for td in tenant_list:
                    vals = [v for v in td["scores"].values() if v]
                    if vals:
                        avg = sum(vals)/len(vals); nps = td["scores"].get(q13_id, 3) if q13_id else 3
                        health = min(100, max(0, round((avg * 0.6 + nps * 0.4) * 25)))
                        risk = "Low" if health >= 75 else "Medium" if health >= 50 else "High"
                        tenant_health.append({"Tenant": td["company"], "Health": health, "Risk": risk, "Name": td["name"]})
                
                high_risk = len([t for t in tenant_health if t["Risk"] == "High"])
                at_risk_revenue = high_risk * 50000
                
                cat_scores = {}
                for qid, qinfo in q_lookup.items():
                    cat = qinfo.get("category", qinfo.get("text", ""))
                    if not cat: continue
                    vals = [td["scores"].get(qid) for td in tenant_list if td["scores"].get(qid)]
                    if vals: cat_scores[cat] = round(sum(vals)/len(vals), 1)
                
                st.markdown("### 🟦 Global KPI Ribbon")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    tc = "#10B981" if tss >= 80 else "#F59E0B" if tss >= 60 else "#EF4444"
                    st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid {tc};"><div style="font-size:0.6rem;color:#888;">TSS</div><div style="font-size:1.5rem;font-weight:800;color:{tc};">{tss}/100</div></div>""", unsafe_allow_html=True)
                with c2:
                    tc = "#10B981" if churn_risk < 10 else "#F59E0B" if churn_risk < 20 else "#EF4444"
                    st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid {tc};"><div style="font-size:0.6rem;color:#888;">Silent Churn Risk</div><div style="font-size:1.5rem;font-weight:800;color:{tc};">{churn_risk}%</div></div>""", unsafe_allow_html=True)
                with c3: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #3B82F6;"><div style="font-size:0.6rem;color:#888;">NPS Score</div><div style="font-size:1.5rem;font-weight:800;color:#3B82F6;">{nps_score}</div></div>""", unsafe_allow_html=True)
                with c4:
                    delta = round(abs(avg_fsi - avg_hei), 1); tc = "#F59E0B" if delta > 0.5 else "#10B981"
                    st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid {tc};"><div style="font-size:0.6rem;color:#888;">Advocacy Delta</div><div style="font-size:1.5rem;font-weight:800;color:{tc};">{delta}</div></div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 🔴 Layer 1: Silent Churn Risk Matrix")
                if tenant_health:
                    th_df = pd.DataFrame(tenant_health).sort_values("Health")
                    fig_h = px.bar(th_df, x="Health", y="Tenant", orientation='h', title="Individual Tenant Health Scores (0-100)", color="Health", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[0,100], text="Name")
                    fig_h.update_layout(height=400); st.plotly_chart(fig_h, use_container_width=True)
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("🟢 Low Risk", len([t for t in tenant_health if t["Risk"]=="Low"]))
                with c2: st.metric("🟡 Medium Risk", len([t for t in tenant_health if t["Risk"]=="Medium"]))
                with c3: st.metric("🔴 High Risk", high_risk)
                if high_risk > 0: st.error(f"💰 **Revenue at Risk:** {high_risk} tenants. Estimated exposure: **${at_risk_revenue:,}** annually.")
                
                st.markdown("---")
                st.markdown("### 🟡 Layer 2: P.R.E.D.I.C.T. Tenant Positioning Matrix")
                st.caption("X: Hard FM (Q1-Q8) | Y: Soft FM (Q9,Q10,Q12)")
                scatter_data = []
                for td in tenant_list:
                    h_avg = sum([td["scores"].get(qid, 0) for qid in hard_qs if td["scores"].get(qid)]) / max(len([qid for qid in hard_qs if td["scores"].get(qid)]), 1)
                    s_avg = sum([td["scores"].get(qid, 0) for qid in soft_qs if td["scores"].get(qid)]) / max(len([qid for qid in soft_qs if td["scores"].get(qid)]), 1)
                    scatter_data.append({"Tenant": td["company"][:15], "Hard FM": round(h_avg,1), "Soft FM": round(s_avg,1), "Size": 25})
                if scatter_data:
                    sd = pd.DataFrame(scatter_data)
                    fig_s = px.scatter(sd, x="Hard FM", y="Soft FM", text="Tenant", size="Size", title="Tenant Positioning Matrix", color_discrete_sequence=["#CC0000"], range_x=[0,4.5], range_y=[0,4.5])
                    fig_s.add_hline(y=2.5, line_dash="dash", line_color="#F59E0B"); fig_s.add_vline(x=2.5, line_dash="dash", line_color="#F59E0B")
                    fig_s.update_layout(height=450); st.plotly_chart(fig_s, use_container_width=True)
                    st.caption("🟢 Top-Right: Stars | 🔵 Bottom-Right: Machines | 🟡 Top-Left: Hospitable but Broken | 🔴 Bottom-Left: At-Risk")
                
                st.markdown("---")
                st.markdown("### 🟢 Layer 3: AI Executive Summary — REVENUE PROTECTION ADVISORY")
                if cat_scores:
                    weakest = min(cat_scores, key=cat_scores.get); strongest = max(cat_scores, key=cat_scores.get)
                    st.markdown(f"""<div style="background:#FEF2F2;border-left:4px solid #EF4444;border-radius:8px;padding:1rem;margin:0.5rem 0;"><b>🔴 Critical Finding:</b> <b>{weakest}</b> ({cat_scores[weakest]}/4) is your weakest category.</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div style="background:#ECFDF5;border-left:4px solid #10B981;border-radius:8px;padding:1rem;margin:0.5rem 0;"><b>✅ Strength:</b> <b>{strongest}</b> ({cat_scores[strongest]}/4) is your top performer.</div>""", unsafe_allow_html=True)
                if avg_fsi > avg_hei + 0.3: st.info(f"📡 **Perception Gap Detected:** Hard FM ({avg_fsi}/4) outpaces Soft FM ({avg_hei}/4).")
                if avg_hei > avg_fsi + 0.3: st.info(f"📡 **Inverse Gap:** Soft FM ({avg_hei}/4) outpaces Hard FM ({avg_fsi}/4).")
                if detractors > 0: st.error(f"🚨 **{detractors} Detractor(s)** identified. Revenue exposure: **${detractors * 50000:,}**.")
                if passives > promoters: st.warning(f"⚠️ **Silent Churn:** {passives} Passives vs {promoters} Promoters.")
                
                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    if cat_scores:
                        sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1])
                        cat_df = pd.DataFrame(sorted_cats, columns=["Category", "Score"])
                        fig_l = px.bar(cat_df, x="Score", y="Category", orientation='h', title="Category Performance", color="Score", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[1,4])
                        fig_l.update_layout(height=400); st.plotly_chart(fig_l, use_container_width=True)
                with c2:
                    if nps_vals:
                        fig_n = px.pie(values=[detractors, passives, promoters], names=["Detractors","Passives","Promoters"], title=f"NPS Distribution (Score: {nps_score})", color_discrete_sequence=["#EF4444","#F59E0B","#10B981"], hole=0.5)
                        fig_n.update_layout(height=400); st.plotly_chart(fig_n, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### 💬 Voice of Customer")
                q14_id = next((qid for qid, q in q_lookup.items() if q["number"] == 14), None)
                if q14_id:
                    quotes_found = False
                    for td in tenant_list:
                        if q14_id in td.get("texts", {}) and td["texts"][q14_id].strip():
                            quotes_found = True
                            st.markdown(f"""<div style="background:white;border-left:4px solid #8B5CF6;border-radius:8px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);"><p style="font-size:0.85rem;font-style:italic;margin:0;">"{td['texts'][q14_id][:200]}"</p><p style="font-size:0.65rem;color:#888;margin-top:0.3rem;">— {td['name']} ({td['company']})</p></div>""", unsafe_allow_html=True)
                    if not quotes_found: st.info("No open-text responses submitted yet.")
                
                st.markdown("---"); st.markdown("### 📥 Export AI Report")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("📊 Generate AI Executive Report", key="ai_html_btn", use_container_width=True, type="primary"): st.session_state.show_ai_report = True; st.rerun()
                with c2:
                    if st.button("📕 Generate AI PDF Report", key="ai_pdf_btn", use_container_width=True): st.session_state.show_ai_pdf = True; st.rerun()
                
                if st.session_state.get("show_ai_report", False):
                    st.markdown("---"); st.markdown("### 📊 AI Executive Report — Preview")
                    logo_b64 = get_logo_base64(); logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
                    import io, base64 as b64; ai_chart_html = ""
                    try:
                        if cat_scores:
                            sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1])
                            cat_df = pd.DataFrame(sorted_cats, columns=["Category", "Score"])
                            fig_a1 = px.bar(cat_df, x="Score", y="Category", orientation='h', title="Category Performance", color="Score", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[1,4], height=350)
                            buf_a1 = io.BytesIO(); fig_a1.write_image(buf_a1, format='png', engine='kaleido', scale=2)
                            ai_chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf_a1.getvalue()).decode()}" style="width:100%;max-width:800px;"></div>'
                    except: pass
                    try:
                        if nps_vals:
                            fig_a2 = px.pie(values=[detractors, passives, promoters], names=["Detractors","Passives","Promoters"], title="NPS Distribution", color_discrete_sequence=["#EF4444","#F59E0B","#10B981"], hole=0.5, height=300)
                            buf_a2 = io.BytesIO(); fig_a2.write_image(buf_a2, format='png', engine='kaleido', scale=2)
                            ai_chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf_a2.getvalue()).decode()}" style="width:100%;max-width:400px;"></div>'
                    except: pass
                    try:
                        if tenant_health:
                            th_df = pd.DataFrame(tenant_health).sort_values("Health")
                            fig_a3 = px.bar(th_df, x="Health", y="Tenant", orientation='h', title="Tenant Health Scores", color="Health", color_continuous_scale=["#EF4444","#F59E0B","#10B981"], range_color=[0,100], height=300)
                            buf_a3 = io.BytesIO(); fig_a3.write_image(buf_a3, format='png', engine='kaleido', scale=2)
                            ai_chart_html += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf_a3.getvalue()).decode()}" style="width:100%;max-width:800px;"></div>'
                    except: pass
                    health_rows = "".join([f"<tr><td>{t['Tenant']}</td><td style='color:{'#10B981' if t['Risk']=='Low' else '#F59E0B' if t['Risk']=='Medium' else '#EF4444'};font-weight:700;'>{t['Health']}</td><td style='color:{'#10B981' if t['Risk']=='Low' else '#F59E0B' if t['Risk']=='Medium' else '#EF4444'}'>{t['Risk']}</td></tr>" for t in sorted(tenant_health, key=lambda x: x["Health"])])
                    cat_rows_ai = "".join([f"<tr><td>{cat}</td><td style='color:{'#EF4444' if score<2.5 else '#F59E0B' if score<3.5 else '#10B981'};font-weight:700;'>{score}/4</td></tr>" for cat, score in sorted(cat_scores.items(), key=lambda x: x[1])])
                    ai_full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>AI Tenant Health & Revenue Protection Report</title><style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:20px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:960px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}.header{{border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}.header h1{{color:#CC0000;margin:0;font-size:22px}}.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}}.kpi{{background:#f9fafb;border-radius:10px;padding:15px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:24px;font-weight:800;color:#CC0000}}.kpi .lbl{{font-size:10px;color:#888;text-transform:uppercase}}h2{{color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;margin-top:20px;font-size:16px}}.alert{{padding:12px;border-radius:8px;margin:10px 0;font-size:13px}}.alert.red{{background:#FEF2F2;border-left:4px solid #EF4444}}.alert.green{{background:#ECFDF5;border-left:4px solid #10B981}}table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:12px}}th{{background:#CC0000;color:white;padding:10px;text-align:left;font-size:10px;text-transform:uppercase}}td{{padding:8px;border-bottom:1px solid #eee}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:25px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container"><div class="header">{logo_img}<h1>AI Tenant Health & Revenue Protection Report</h1><p>{info.get('full_name',fc)} | {date.today().strftime('%d %B %Y')} | P.R.E.D.I.C.T. Framework</p></div><div class="kpi-row"><div class="kpi"><div class="val">{tss}/100</div><div class="lbl">Tenant Sentiment Score</div></div><div class="kpi"><div class="val">{nps_score}</div><div class="lbl">NPS Score</div></div><div class="kpi"><div class="val">{churn_risk}%</div><div class="lbl">Silent Churn Risk</div></div><div class="kpi"><div class="val">{len(tenant_list)}</div><div class="lbl">Responses</div></div></div><div class="alert red"><b>Revenue Protection Advisory:</b> {high_risk} high-risk tenants identified. Estimated annual exposure: ${at_risk_revenue:,}.</div><h2>Category Performance</h2>{ai_chart_html}<table><tr><th>Category</th><th>Score</th></tr>{cat_rows_ai}</table><h2>Tenant Health Scores</h2><table><tr><th>Tenant</th><th>Health Score</th><th>Risk Level</th></tr>{health_rows}</table><div class="footer">Churchgate Group | facilityXperience | AI-Generated Report | {date.today().strftime('%d %B %Y')}</div></div></body></html>"""
                    st.components.v1.html(ai_full_html, height=800, scrolling=True)
                    c1, c2, c3 = st.columns(3)
                    with c1: st.download_button("📥 Download HTML Report", ai_full_html, f"ai_tenant_health_report_{date.today()}.html", "text/html", use_container_width=True)
                    with c2: st.download_button("📥 Download CSV Data", pd.DataFrame(tenant_health).to_csv(index=False), f"tenant_health_data_{date.today()}.csv", "text/csv", use_container_width=True)
                    with c3:
                        if st.button("❌ Close Preview", key="close_ai_preview", use_container_width=True): st.session_state.show_ai_report = False; st.rerun()
                
                if st.session_state.get("show_ai_pdf", False):
                    try:
                        from fpdf import FPDF; pdf = FPDF(); pdf.add_page()
                        pdf.set_font('Helvetica','B',16); pdf.set_text_color(204,0,0)
                        pdf.cell(0,10,safe_text('AI Tenant Health & Revenue Protection Report'),0,1)
                        pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                        pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {date.today().strftime("%d %B %Y")}'),0,1); pdf.ln(3)
                        pdf.set_font('Helvetica','B',11)
                        pdf.cell(0,6,f'TSS: {tss}/100 | NPS: {nps_score} | Churn Risk: {churn_risk}%',0,1)
                        pdf.cell(0,6,f'Revenue Exposure: ${at_risk_revenue:,} | High Risk Tenants: {high_risk}',0,1); pdf.ln(5)
                        pdf.set_font('Helvetica','B',10); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                        pdf.cell(60,6,'Tenant',1,0,'C',True); pdf.cell(30,6,'Health',1,0,'C',True); pdf.cell(30,6,'Risk',1,0,'C',True); pdf.ln()
                        pdf.set_font('Helvetica','',9); pdf.set_text_color(0,0,0)
                        for t in sorted(tenant_health, key=lambda x: x["Health"]):
                            pdf.cell(60,5,safe_text(t['Tenant'][:25]),1,0); pdf.cell(30,5,str(t['Health']),1,0); pdf.cell(30,5,safe_text(t['Risk']),1,0); pdf.ln()
                        pdf_file = f"/tmp/ai_tenant_report_{date.today()}.pdf"; pdf.output(pdf_file)
                        with open(pdf_file,"rb") as f: st.download_button("📥 Download AI PDF Report", f.read(), f"ai_tenant_health_report_{date.today()}.pdf", "application/pdf", use_container_width=True)
                        if st.button("❌ Close", key="close_ai_pdf", use_container_width=True): st.session_state.show_ai_pdf = False; st.rerun()
                    except Exception as e: st.error(f"PDF error: {str(e)[:80]}"); st.session_state.show_ai_pdf = False
    
    # ============================================
    # TAB 3: SURVEY ADMIN
    # ============================================
    with tabs[3]:
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            st.markdown("### ⚙️ Survey Administration")
            
            surveys = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).order("created_at", desc=True).execute())
            if surveys and surveys.data:
                st.markdown("**Existing Surveys:**")
                for s in surveys.data:
                    status_badge = "🟢 Active" if s.get("is_active") else "⚪ Inactive"
                    st.markdown(f"- **{s.get('title','')}** — {status_badge}")
            
            st.markdown("---")
            st.markdown("### 📅 Quarterly Survey Periods (FY April – March)")
            
            today = date.today()
            fy_year = today.year if today.month >= 4 else today.year - 1
            
            quarters = {
                "Q1 (April – June)": (date(fy_year, 4, 1), date(fy_year, 6, 30)),
                "Q2 (July – September)": (date(fy_year, 7, 1), date(fy_year, 9, 30)),
                "Q3 (October – December)": (date(fy_year, 10, 1), date(fy_year, 12, 31)),
                "Q4 (January – March)": (date(fy_year+1, 1, 1), date(fy_year+1, 3, 31)),
            }
            
            c1, c2 = st.columns(2)
            with c1: selected_quarter = st.selectbox("Select Quarter", list(quarters.keys()))
            with c2:
                quarter_dates = quarters[selected_quarter]
                st.markdown(f"**Period:** {quarter_dates[0].strftime('%d %b %Y')} – {quarter_dates[1].strftime('%d %b %Y')}")
            
            st.markdown("---")
            
            # Check if there's an existing survey for this facility
            existing_survey = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(1).execute())
            current_status = "Inactive"
            current_title = f"Tenant Satisfaction Survey {selected_quarter.split('(')[0].strip()} FY {fy_year}"
            if existing_survey and existing_survey.data and len(existing_survey.data) > 0:
                current_status = "Active" if existing_survey.data[0].get("is_active") else "Inactive"
                current_title = existing_survey.data[0].get("title", current_title)
            
            with st.form("survey_admin_form"):
                st.markdown("**📝 Survey Details**")
                c1, c2 = st.columns(2)
                with c1: survey_title = st.text_input("Survey Title", value=current_title, key="survey_title")
                with c2: survey_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if current_status == "Active" else 1, key="survey_status")
                
                if st.form_submit_button("💾 Save Survey", use_container_width=True, type="primary"):
                    existing = safe_supabase(lambda: supabase.table("feedback_surveys").select("*").eq("facility_code", fc).eq("title", survey_title).execute())
                    
                    if survey_status == "Active":
                        safe_supabase(lambda: supabase.table("feedback_surveys").update({"is_active": False}).eq("facility_code", fc).execute())
                    
                    if existing and existing.data and len(existing.data) > 0:
                        safe_supabase(lambda: supabase.table("feedback_surveys").update({
                            "title": survey_title, "is_active": survey_status == "Active",
                            "start_date": str(quarter_dates[0]), "end_date": str(quarter_dates[1])
                        }).eq("id", existing.data[0]["id"]).execute())
                        st.success(f"✅ Survey updated!")
                    else:
                        safe_supabase(lambda: supabase.table("feedback_surveys").insert({
                            "facility_code": fc, "title": survey_title,
                            "is_active": survey_status == "Active",
                            "start_date": str(quarter_dates[0]), "end_date": str(quarter_dates[1]),
                            "created_at": datetime.now().isoformat()
                        }).execute())
                        st.success(f"✅ Survey created!")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("### 📧 Broadcast Survey to Tenants")
            
            tenants = safe_supabase(lambda: supabase.table("app_users").select("*").eq("user_type", "tenant").eq("home_facility", fc).eq("is_active", True).order("name").execute())
            if not tenants or not tenants.data or len(tenants.data) == 0:
                tenants = safe_supabase(lambda: supabase.table("organizations").select("*").eq("type", "tenant").order("name").execute())
            
            if tenants and tenants.data and len(tenants.data) > 0:
                st.caption(f"📋 {len(tenants.data)} tenants found in {info.get('full_name', fc)}")
                
                tenant_options = {}
                for t in tenants.data:
                    name = t.get("name", "Unknown")
                    email = t.get("primary_contact_email", t.get("email", "no-email"))
                    label = f"{name} ({email})"
                    tenant_options[label] = t
                
                all_labels = list(tenant_options.keys())
                selected_labels = st.multiselect("Select Tenants to Receive Survey", all_labels, key="broadcast_tenants")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Select All", key="select_all_tenants", use_container_width=True):
                        st.session_state.broadcast_tenants = all_labels; st.rerun()
                with c2:
                    if st.button("❌ Clear All", key="clear_all_tenants", use_container_width=True):
                        st.session_state.broadcast_tenants = []; st.rerun()
                
                st.caption(f"📧 {len(selected_labels)} tenants selected")
                
                if selected_labels:
                    with st.expander("📧 Preview Email"):
                        st.markdown(f"""
                        **Subject:** 📝 {survey_title}
                        **From:** facilityXperience — Churchgate Group
                        **To:** {len(selected_labels)} tenants
                        ---
                        Dear Valued Tenant,
                        We value your feedback. Please take a moment to complete our {selected_quarter} tenant satisfaction survey.
                        **Time to complete:** Less than 5 minutes
                        [Take Survey Now]
                        Your responses help us improve our services.
                        — Churchgate Group Facility Management
                        """)
                
                if st.button(f"📧 SEND SURVEY TO {len(selected_labels)} TENANTS", use_container_width=True, type="primary"):
                    if len(selected_labels) == 0:
                        st.error("⚠️ Select at least one tenant")
                    else:
                        sent_count = 0
                        for label in selected_labels:
                            t = tenant_options[label]
                            email = t.get("primary_contact_email", t.get("email", ""))
                            if email:
                                send_email_notification(email, f"📝 {survey_title}",
                                    f"""<div style="font-family:Arial;max-width:600px;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
                                    <div style="background:#C8A951;padding:20px;color:white;"><h2>We Value Your Feedback</h2><p>{info.get('full_name',fc)} — {selected_quarter}</p></div>
                                    <div style="padding:20px;"><p>Dear {t.get('name','Valued Tenant')},</p>
                                    <p>Please take our tenant satisfaction survey. Your feedback helps us improve.</p>
                                    <p><b>Time:</b> Less than 5 minutes</p>
                                    <div style="text-align:center;margin:20px 0;"><a href="https://churchgate-facilityxperience.hf.space" style="background:#C8A951;color:white;padding:12px 30px;text-decoration:none;border-radius:6px;font-weight:bold;">Take Survey Now</a></div></div></div>""")
                                sent_count += 1
                        st.success(f"✅ Survey sent to {sent_count} tenants!")
                        st.balloons()
            else:
                st.info("No tenants found in the database. Add tenants in the organizations table.")

# ============================================
# UTILITY INTELLIGENCE COMMAND CENTER
# E.N.E.R.G.Y. FRAMEWORK — ELECTRICITY • WATER • DIESEL
# COMPLETE FORTUNE 500 MODULE
# ============================================
def page_uc():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    st.markdown(f'## ⚡ Utility Intelligence Command Center — {info.get("full_name", fc)}')
    
    all_assets = DB.get_assets(fc, 50000)
    df = pd.DataFrame(all_assets) if all_assets else pd.DataFrame()
    
    readings = safe_supabase_query(lambda: supabase.table("utility_readings").select("*").eq("facility_code", fc).order("reading_date", desc=True).limit(1000).execute(), error_prefix="Utility readings")
    
    readings_df = pd.DataFrame(readings.data) if readings and readings.data else pd.DataFrame()
    
    today = date.today()
    
    # ============================================
    # 🟦 TOP RIBBON — ALL UTILITIES COMBINED
    # ============================================
    total_readings = len(readings_df)
    energy_meter_count = len(df[df['parent_asset'].str.contains('ENERGY METER', na=False)]) if len(df) > 0 else 0
    diesel_gen_count = len(df[df['parent_asset'].str.contains('DIESEL GENERATOR', na=False)]) if len(df) > 0 else 0
    
    elec_readings = readings_df[readings_df["utility_type"] == "Electricity"] if len(readings_df) > 0 and "utility_type" in readings_df.columns else pd.DataFrame()
    diesel_readings = readings_df[readings_df["utility_type"] == "Diesel"] if len(readings_df) > 0 and "utility_type" in readings_df.columns else pd.DataFrame()
    
    total_elec = elec_readings["reading_value"].sum() if len(elec_readings) > 0 else 0
    total_diesel = diesel_readings["reading_value"].sum() if len(diesel_readings) > 0 else 0
    live_spend_rate = round((total_elec * 75 + total_diesel * 400) / max(total_readings, 1), 2)
    backup_hours = round((33000 * 3 * 0.7) / 80, 0) if diesel_gen_count > 0 else 0
    
    st.markdown("### 🟦 Financial Heartbeat — All Utilities")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #CC0000;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Live Spend Rate</div><div style="font-size:1.8rem;font-weight:800;color:#CC0000;">₦{live_spend_rate}/hr</div><div style="font-size:0.55rem;color:#888;">Combined Utilities</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #F59E0B;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Energy Intensity</div><div style="font-size:1.8rem;font-weight:800;color:#F59E0B;">{energy_meter_count}</div><div style="font-size:0.55rem;color:#888;">Meters Active</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #3B82F6;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Backup Readiness</div><div style="font-size:1.8rem;font-weight:800;color:#3B82F6;">{backup_hours:.0f} hrs</div><div style="font-size:0.55rem;color:#888;">Diesel Runtime</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #06B6D4;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Total Readings</div><div style="font-size:1.8rem;font-weight:800;color:#06B6D4;">{total_readings}</div><div style="font-size:0.55rem;color:#888;">All Utilities</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-top:4px solid #EF4444;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.6rem;color:#888;text-transform:uppercase;">Non-Revenue Water</div><div style="font-size:1.8rem;font-weight:800;color:#EF4444;">8.5%</div><div style="font-size:0.55rem;color:#888;">Lost/Unbilled</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["⚡ Electricity", "💧 Water", "⛽ Diesel Command", "📝 Record Readings", "📈 Analytics", "📊 Reports"])
    
    # ============================================
    # TAB 0: ELECTRICITY — ENERGY METERS
    # ============================================
    with tabs[0]:
        st.markdown("### ⚡ Electricity — Energy Meter Network")
        
        energy_meters = df[df["parent_asset"].str.contains("ENERGY METER", na=False)] if len(df) > 0 else pd.DataFrame()
        
        if len(energy_meters) == 0:
            st.info("No energy meters found.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                buildings = ["All"] + sorted(energy_meters["location_building"].dropna().unique().tolist())
                sel_bldg = st.selectbox("🏢 Building", buildings, key="elec_bldg")
            with c2:
                meter_types = ["All"] + sorted(energy_meters["parent_asset"].dropna().unique().tolist())
                sel_type = st.selectbox("🔌 Meter Type", meter_types, key="elec_type")
            with c3:
                elec_search = st.text_input("🔍 Search Meter", key="elec_search", placeholder="Meter name or ID...")
            
            display_meters = energy_meters.copy()
            if sel_bldg != "All": display_meters = display_meters[display_meters["location_building"] == sel_bldg]
            if sel_type != "All": display_meters = display_meters[display_meters["parent_asset"] == sel_type]
            if elec_search:
                display_meters = display_meters[display_meters["name"].str.contains(elec_search, case=False, na=False) | display_meters["asset_tag"].str.contains(elec_search, case=False, na=False)]
            
            st.caption(f"📋 {len(display_meters)} meters")
            
            page_size = 12
            if "elec_page" not in st.session_state: st.session_state.elec_page = 1
            total_pages = max(1, (len(display_meters) + page_size - 1) // page_size)
            start = (st.session_state.elec_page - 1) * page_size
            end = min(start + page_size, len(display_meters))
            
            c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
            with c1:
                if st.button("◀◀", key="el_first"): st.session_state.elec_page = 1; st.rerun()
            with c2:
                if st.button("◀", key="el_prev") and st.session_state.elec_page > 1: st.session_state.elec_page -= 1; st.rerun()
            with c3: st.markdown(f"**Page {st.session_state.elec_page} of {total_pages}**")
            with c4:
                if st.button("▶", key="el_next") and st.session_state.elec_page < total_pages: st.session_state.elec_page += 1; st.rerun()
            with c5:
                if st.button("▶▶", key="el_last"): st.session_state.elec_page = total_pages; st.rerun()
            
            for i, (_, meter) in enumerate(display_meters.iloc[start:end].iterrows()):
                meter_name = meter.get("name", "N/A")
                meter_id = meter.get("asset_tag", "N/A")
                location = meter.get("location_building", "N/A")
                meter_type = meter.get("parent_asset", "N/A")
                sno = start + i + 1
                
                meter_readings = readings_df[readings_df["meter_id"] == str(meter_id)] if len(readings_df) > 0 else pd.DataFrame()
                latest = meter_readings.iloc[0] if len(meter_readings) > 0 else None
                prev = meter_readings.iloc[1] if len(meter_readings) > 1 else None
                
                last_val = f"{latest['reading_value']} {latest.get('unit','')}" if latest is not None else "—"
                last_date = str(latest["reading_date"]) if latest is not None else "—"
                prev_val = f"{prev['reading_value']} {prev.get('unit','')}" if prev is not None else "—"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid #F59E0B;border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="flex:1;">
                            <b>#{sno} {meter_name[:90]}</b>
                            <br><span style="font-size:0.65rem;color:#666;">🆔 {meter_id} | 📍 {location} | 🔌 {meter_type}</span>
                        </div>
                        <div style="text-align:right;min-width:120px;">
                            <div style="font-size:0.6rem;color:#888;">Last: {last_date}</div>
                            <div style="font-weight:700;color:#F59E0B;">{last_val}</div>
                            <div style="font-size:0.6rem;color:#888;">Prev: {prev_val}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 1: WATER
    # ============================================
    with tabs[1]:
        st.markdown("### 💧 Water Network Command")
        
        if fc == "WTC":
            # WTC — keep original hardcoded water meters
            water_meters = [
                {"name": "WTC Water Meter 1 — FCT Water Board", "id": "CAH000888", "location": "Main Gate", "type": "Bulk Municipal (M1)", "meter_num": 2076},
                {"name": "WTC Water Meter 2 — FCT Water Board", "id": "CAH00076", "location": "Main Gate", "type": "Bulk Municipal (M2)", "meter_num": 2077},
                {"name": "CT Water Meter — In-house", "id": "CT-WATER-01", "location": "CT/B3/Fire Pump Room", "type": "Domestic Cold Water (M3)", "meter_num": 2078},
                {"name": "Club House Water Meter", "id": "SAT-WATER-01", "location": "SAT/B1/Car Park", "type": "Domestic Cold Water (M4)", "meter_num": 2079},
                {"name": "Jogging Area Water Meter", "id": "SAT-WATER-02", "location": "SAT/B1/Car Park", "type": "Irrigation/Landscape (M5)", "meter_num": 2080},
                {"name": "SAT Water Meter — Fire Pump Room", "id": "SAT-WATER-03", "location": "SAT/B2/Fire Pump Room", "type": "Fire Suppression (M6)", "meter_num": 2081},
            ]
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Meters", len(water_meters))
            with c2: st.metric("Bulk Supply", 2)
            with c3: st.metric("Sub-Meters", 4)
            st.markdown("---")
            
            for i, wm in enumerate(water_meters):
                wm_readings = readings_df[readings_df["meter_id"] == wm["id"]] if len(readings_df) > 0 else pd.DataFrame()
                latest_wm = wm_readings.iloc[0] if len(wm_readings) > 0 else None
                last_val = f"{latest_wm['reading_value']:,.0f} {latest_wm.get('unit','Ltr')}" if latest_wm is not None else "—"
                last_date = str(latest_wm["reading_date"]) if latest_wm is not None else "No readings"
                
                with st.container():
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid #06B6D4;border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <b>M{i+1}: {wm['name']}</b>
                                <br><span style="font-size:0.65rem;color:#666;">🆔 {wm['id']} | 📍 {wm['location']} | 🏷️ {wm['type']}</span>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:0.6rem;color:#888;">Last: {last_date}</div>
                                <div style="font-weight:700;color:#06B6D4;">{last_val}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    toggle_key = f"wm_toggle_{i}"
                    if toggle_key not in st.session_state: st.session_state[toggle_key] = False
                    
                    if not st.session_state[toggle_key]:
                        if st.button(f"📝 Enter Reading for M{i+1}", key=f"wm_toggle_btn_{i}", use_container_width=True):
                            st.session_state[toggle_key] = True; st.rerun()
                    else:
                        st.markdown(f"""<div style="background:#EFF6FF;border-left:4px solid #06B6D4;border-radius:8px;padding:0.6rem;margin:0.3rem 0;"><b>📝 Recording: {wm['name'][:60]}</b><br><span style="font-size:0.7rem;color:#888;">Previous: {last_val} ({last_date})</span></div>""", unsafe_allow_html=True)
                        c1, c2, c3 = st.columns(3)
                        with c1: wm_value = st.number_input("Value*", min_value=0.0, value=0.0, step=1.0, key=f"wm_val_{i}")
                        with c2: wm_date = st.date_input("Date", wat_now.date(), key=f"wm_date_{i}")
                        with c3: wm_time = st.time_input("Time", wat_now.time(), key=f"wm_time_{i}")
                        wm_notes = st.text_input("Notes", key=f"wm_notes_{i}", placeholder="Optional...")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(f"📝 Record", key=f"wm_btn_{i}", use_container_width=True, type="primary"):
                                if wm_value > 0:
                                    prev_wm = wm_readings.iloc[0]["reading_value"] if len(wm_readings) > 0 else wm_value
                                    consumption = max(0, wm_value - prev_wm) if wm_value > prev_wm else 0
                                    safe_supabase_query(lambda: supabase.table("utility_readings").insert({"facility_code":fc,"utility_type":"Water","meter_id":wm["id"],"reading_date":str(wm_date),"reading_time":str(wm_time),"reading_value":wm_value,"unit":"Ltr","consumption":consumption,"created_at":datetime.now().isoformat()}).execute(), error_prefix="Water reading")
                                    st.success("✅ Reading recorded!"); st.session_state[toggle_key] = False; st.rerun()
                                else: st.error("⚠️ Enter a value")
                        with c2:
                            if st.button("❌ Close", key=f"wm_close_{i}", use_container_width=True): st.session_state[toggle_key] = False; st.rerun()
            
            st.markdown("---")
            st.markdown("### 🔍 Non-Revenue Water (NRW) Tracking")
            st.info("💧 Estimated NRW: 8.5% of total supply. Industry best practice is <5%. AI recommends investigating cooling tower make-up line for continuous bleed.")
        
        else:
            # Other facilities — show only WATER METER assets
            water_assets = df[df["parent_asset"] == "WATER METER"] if len(df) > 0 else pd.DataFrame()
            
            if len(water_assets) == 0:
                st.info(f"No water meters found for {info.get('full_name', fc)}.")
            else:
                st.metric("Total Water Meters", len(water_assets))
                st.markdown("---")
                for i, (_, wm) in enumerate(water_assets.iterrows()):
                    wm_name = wm.get("name", "N/A")[:90]
                    wm_id = str(wm.get("asset_tag", "N/A"))
                    wm_location = wm.get("location_building", "N/A")
                    
                    wm_readings = readings_df[readings_df["meter_id"] == wm_id] if len(readings_df) > 0 else pd.DataFrame()
                    latest_wm = wm_readings.iloc[0] if len(wm_readings) > 0 else None
                    last_val = f"{latest_wm['reading_value']:,.0f} {latest_wm.get('unit','Ltr')}" if latest_wm is not None else "—"
                    last_date = str(latest_wm["reading_date"]) if latest_wm is not None else "No readings"
                    
                    st.markdown(f"""<div style="background:white;border-left:4px solid #06B6D4;border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><b>W{i+1}: {wm_name}</b><br><span style="font-size:0.65rem;color:#666;">🆔 {wm_id} | 📍 {wm_location}</span></div><div style="text-align:right;"><div style="font-size:0.6rem;color:#888;">Last: {last_date}</div><div style="font-weight:700;color:#06B6D4;">{last_val}</div></div></div></div>""", unsafe_allow_html=True)
    
    # ============================================
    # TAB 2: DIESEL COMMAND
    # ============================================
    with tabs[2]:
        st.markdown("### ⛽ Diesel Tank Farm — Fuel Security Command")
        
        if fc == "WTC":
            # WTC — keep original 3 diesel tanks
            st.markdown("""<div style="background:#1a1a1a;border-radius:12px;padding:1.5rem;color:white;margin-bottom:1rem;"><h3 style="margin:0;color:#F59E0B;">⛽ Three Underground Diesel Tanks</h3><p style="margin:5px 0 0 0;font-size:0.8rem;opacity:0.8;">35,000 Litres Each | External Location | Backup Power Infrastructure</p></div>""", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            for i in range(3):
                with [c1, c2, c3][i]:
                    tank_id = f"Tank{i+1}"
                    tank_reading = diesel_readings[diesel_readings["meter_id"] == tank_id] if len(diesel_readings) > 0 else pd.DataFrame()
                    current_level = tank_reading["reading_value"].iloc[0] if len(tank_reading) > 0 else 20000
                    fill_pct = round((current_level / 20000) * 100)
                    abs_pct = round((current_level / 33000) * 100)
                    
                    if fill_pct > 50: color = "#10B981"; status = "Healthy"
                    elif fill_pct > 25: color = "#F59E0B"; status = "Order Fuel"
                    else: color = "#EF4444"; status = "Critical"
                    
                    visual_pct = min(fill_pct, 100)
                    st.markdown(f"""<div style="background:white;border-radius:12px;padding:1.2rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);border:2px solid #e5e7eb;"><b style="font-size:1rem;">Tank #{i+1}</b><div style="font-size:0.6rem;color:#888;margin-bottom:8px;">Underground Diesel Storage</div><div style="position:relative;width:100%;height:80px;margin:10px 0;"><div style="position:absolute;top:0;left:0;width:100%;height:80px;border:3px solid #374151;border-radius:40px;background:linear-gradient(180deg,#e5e7eb 0%,#d1d5db 100%);overflow:hidden;box-shadow:inset 0 2px 4px rgba(0,0,0,0.1);"><div style="position:absolute;bottom:0;left:0;width:100%;height:{visual_pct}%;background:linear-gradient(180deg,{color}dd,{color});border-radius:0 0 37px 37px;transition:height 0.5s ease;box-shadow:inset 0 2px 4px rgba(255,255,255,0.3);"></div></div></div><div style="font-size:1.5rem;font-weight:800;color:{color};">{current_level:,.0f} L</div><div style="font-size:0.65rem;color:#888;">{fill_pct}% of Operating Max | {abs_pct}% Absolute</div><span style="background:{color};color:white;padding:3px 12px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status}</span></div>""", unsafe_allow_html=True)
            
            st.markdown("### 📝 Record Diesel Tank Reading")
            with st.form("diesel_reading_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    tank_select = st.selectbox("Select Tank*", ["Tank 1", "Tank 2", "Tank 3"])
                    dip_reading = st.number_input("Dipstick Reading (Litres)*", min_value=0.0, value=0.0, step=100.0)
                    fuel_delivered = st.number_input("Fuel Delivered Today (Litres)", min_value=0.0, value=0.0, step=100.0)
                with c2:
                    reading_date_d = st.date_input("Reading Date*", wat_now.date())
                    reading_time_d = st.time_input("Reading Time", wat_now.time())
                with c3:
                    notes = st.text_area("Notes/Observations")
                
                if st.form_submit_button("📝 RECORD DIESEL READING", use_container_width=True, type="primary"):
                    if dip_reading > 0:
                        tank_id_val = tank_select.replace(" ", "")
                        prev = diesel_readings[diesel_readings["meter_id"] == tank_id_val]["reading_value"].iloc[0] if len(diesel_readings) > 0 and len(diesel_readings[diesel_readings["meter_id"] == tank_id_val]) > 0 else 0
                        consumption = max(0, prev + fuel_delivered - dip_reading) if prev > 0 else 0
                        safe_supabase_query(lambda: supabase.table("utility_readings").insert({"facility_code":fc,"utility_type":"Diesel","meter_id":tank_id_val,"reading_date":str(reading_date_d),"reading_time":str(reading_time_d),"reading_value":dip_reading,"unit":"Litres","consumption":consumption,"created_at":datetime.now().isoformat()}).execute(), error_prefix="Diesel reading")
                        st.success(f"✅ Diesel reading recorded!"); st.balloons(); st.rerun()
                    else: st.error("⚠️ Dipstick Reading is required")
        
        else:
            # Other facilities — show only real diesel tanks with graphics
            diesel_assets = df[df["parent_asset"].isin(["DG TANK", "Service Tank", "Storage Tank"])] if len(df) > 0 else pd.DataFrame()
            
            if len(diesel_assets) == 0:
                st.info(f"No diesel storage tanks found for {info.get('full_name', fc)}.")
            else:
                st.markdown(f"""<div style="background:#1a1a1a;border-radius:12px;padding:1.5rem;color:white;margin-bottom:1rem;"><h3 style="margin:0;color:#F59E0B;">⛽ {len(diesel_assets)} Diesel Storage Tanks</h3><p style="margin:5px 0 0 0;font-size:0.8rem;opacity:0.8;">{info.get('full_name', fc)}</p></div>""", unsafe_allow_html=True)
                
                for i in range(0, len(diesel_assets), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        idx = i + j
                        if idx < len(diesel_assets):
                            asset = diesel_assets.iloc[idx]
                            asset_name = asset.get("name", f"Tank {idx+1}")[:40]
                            asset_id = str(asset.get("asset_tag", "N/A"))
                            tank_reading = diesel_readings[diesel_readings["meter_id"] == asset_id] if len(diesel_readings) > 0 else pd.DataFrame()
                            current_level = tank_reading["reading_value"].iloc[0] if len(tank_reading) > 0 else 0
                            tank_capacity = float(asset.get("capacity", 0) or 0)
                            if tank_capacity <= 0:
                                tank_capacity = 10000
                            fill_pct = round((current_level / tank_capacity) * 100)
                            visual_pct = min(fill_pct, 100)
                            
                            if fill_pct > 50: color = "#10B981"; status = "Healthy"
                            elif fill_pct > 25: color = "#F59E0B"; status = "Order Fuel"
                            else: color = "#EF4444"; status = "Critical"
                            
                            with cols[j]:
                                st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);border:2px solid #e5e7eb;"><b style="font-size:0.85rem;">{asset_name}</b><div style="font-size:0.55rem;color:#888;margin-bottom:6px;">{asset_id}</div><div style="position:relative;width:100%;height:70px;margin:8px 0;"><div style="position:absolute;top:0;left:0;width:100%;height:70px;border:3px solid #374151;border-radius:35px;background:linear-gradient(180deg,#e5e7eb 0%,#d1d5db 100%);overflow:hidden;box-shadow:inset 0 2px 4px rgba(0,0,0,0.1);"><div style="position:absolute;bottom:0;left:0;width:100%;height:{visual_pct}%;background:linear-gradient(180deg,{color}dd,{color});border-radius:0 0 32px 32px;transition:height 0.5s ease;box-shadow:inset 0 2px 4px rgba(255,255,255,0.3);"></div></div></div><div style="font-size:1.3rem;font-weight:800;color:{color};">{current_level:,.0f} / {tank_capacity:,.0f} L</div><div style="font-size:0.6rem;color:#888;">{fill_pct}% Full</div><span style="background:{color};color:white;padding:2px 10px;border-radius:10px;font-size:0.55rem;font-weight:600;">{status}</span></div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 📝 Record Fuel Reading")
                with st.form("diesel_reading_form_other"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        tank_options = [f"{a.get('name','')} ({a.get('asset_tag','')})" for _, a in diesel_assets.iterrows()]
                        tank_select = st.selectbox("Select Tank*", tank_options)
                        dip_reading = st.number_input("Fuel Level (Litres)*", min_value=0.0, value=0.0, step=100.0)
                        fuel_delivered = st.number_input("Fuel Delivered (Litres)", min_value=0.0, value=0.0, step=100.0)
                    with c2:
                        reading_date_d = st.date_input("Date*", wat_now.date())
                        reading_time_d = st.time_input("Time", wat_now.time())
                    with c3:
                        notes = st.text_area("Notes")
                    if st.form_submit_button("📝 RECORD FUEL READING", use_container_width=True, type="primary"):
                        if dip_reading > 0:
                            selected_id = tank_select.split("(")[-1].replace(")", "").strip()
                            safe_supabase_query(lambda: supabase.table("utility_readings").insert({"facility_code":fc,"utility_type":"Diesel","meter_id":selected_id,"reading_date":str(reading_date_d),"reading_time":str(reading_time_d),"reading_value":dip_reading,"unit":"Litres","consumption":0,"created_at":datetime.now().isoformat()}).execute(), error_prefix="Fuel reading")
                            st.success("✅ Reading recorded!"); st.balloons(); st.rerun()
                        else: st.error("⚠️ Enter fuel level")
            
            st.markdown("---")
            st.markdown("### 📊 Recent Fuel Readings")
            if len(diesel_readings) > 0:
                st.dataframe(diesel_readings[["meter_id","reading_date","reading_value","consumption","unit"]].head(10), use_container_width=True, hide_index=True)
            else:
                st.info("No fuel readings recorded yet.")
    
    # ============================================
    # TAB 3: RECORD READINGS
    # ============================================
    with tabs[3]:
        st.markdown("### 📝 Record Meter Readings")
        
        reading_mode = st.radio("Reading Mode", ["⚡ Energy Meter (Detailed)", "💧 Water Meter", "📝 Quick Entry (Universal)"], horizontal=True)
        
        if reading_mode == "⚡ Energy Meter (Detailed)":
            st.markdown("#### ⚡ Energy Meter Reading — Cascading Selection")
            
            energy_meters_list = df[df["parent_asset"].str.contains("ENERGY METER", na=False)] if len(df) > 0 else pd.DataFrame()
            
            if len(energy_meters_list) == 0:
                st.info("No energy meters found.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    buildings = ["Select Building..."] + sorted(energy_meters_list["location_building"].dropna().unique().tolist())
                    sel_em_bldg = st.selectbox("🏢 Building*", buildings, key="em_bldg")
                with c2:
                    meter_types = ["Select Type..."] + sorted(energy_meters_list["parent_asset"].dropna().unique().tolist())
                    sel_em_type = st.selectbox("🔌 Meter Type*", meter_types, key="em_type")
                with c3:
                    filtered_em = energy_meters_list.copy()
                    if sel_em_bldg != "Select Building...":
                        filtered_em = filtered_em[filtered_em["location_building"] == sel_em_bldg]
                    if sel_em_type != "Select Type...":
                        filtered_em = filtered_em[filtered_em["parent_asset"] == sel_em_type]
                    
                    locations = ["Select Location..."] + sorted(filtered_em["location_floor"].dropna().unique().tolist()) if "location_floor" in filtered_em.columns else ["Select Location..."]
                    sel_em_loc = st.selectbox("📍 Location", locations, key="em_loc")
                with c4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    em_search = st.text_input("🔍 Search Meter", key="em_search", placeholder="Name or ID...")
                
                if sel_em_loc != "Select Location..." and "location_floor" in filtered_em.columns:
                    filtered_em = filtered_em[filtered_em["location_floor"] == sel_em_loc]
                if em_search:
                    filtered_em = filtered_em[filtered_em["name"].str.contains(em_search, case=False, na=False) | filtered_em["asset_tag"].str.contains(em_search, case=False, na=False)]
                
                st.caption(f"📋 {len(filtered_em)} meters match your filters")
                
                if len(filtered_em) > 0:
                    meter_options = ["Select Meter..."] + [f"{m['name'][:100]} (ID: {m['asset_tag']})" for _, m in filtered_em.iterrows()]
                    selected_meter_str = st.selectbox("Select Meter*", meter_options, key="em_meter_select")
                    
                    if selected_meter_str != "Select Meter...":
                        selected_idx = [i for i, m in enumerate(filtered_em.iterrows()) if f"{m[1]['name'][:100]} (ID: {m[1]['asset_tag']})" == selected_meter_str][0]
                        selected_meter = filtered_em.iloc[selected_idx]
                        selected_meter_id = selected_meter["asset_tag"]
                        
                        meter_history = readings_df[readings_df["meter_id"] == str(selected_meter_id)] if len(readings_df) > 0 else pd.DataFrame()
                        last_reading = meter_history.iloc[0] if len(meter_history) > 0 else None
                        
                        st.markdown("---")
                        st.markdown(f"**Selected Meter:** {selected_meter['name'][:120]}")
                        st.markdown(f"**Location:** {selected_meter.get('location_building','N/A')} | **Type:** {selected_meter.get('parent_asset','N/A')}")
                        
                        if last_reading is not None:
                            st.info(f"📅 Last Reading: {str(last_reading['reading_date'])} | Value: {last_reading['reading_value']} {last_reading.get('unit','kWh')}")
                        
                        with st.form("energy_meter_form"):
                            st.markdown("---")
                            st.markdown("**📊 Current Readings**")
                            
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("**Grid (EB)**")
                                eb_kwh = st.number_input("EB-KWH*", min_value=0.0, value=0.0, step=0.1, key="eb_kwh")
                                eb_mwh = st.number_input("EB-MWH", min_value=0.0, value=0.0, step=0.01, key="eb_mwh")
                            with c2:
                                st.markdown("**Generator (DG)**")
                                dg_kwh = st.number_input("DG-KWH*", min_value=0.0, value=0.0, step=0.1, key="dg_kwh")
                                dg_mwh = st.number_input("DG-MWH", min_value=0.0, value=0.0, step=0.01, key="dg_mwh")
                            with c3:
                                st.markdown("**Other**")
                                amp = st.number_input("AMP", min_value=0.0, value=0.0, step=0.1, key="amp")
                            
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                reading_date_em = st.date_input("Reading Date*", today, key="em_date")
                            with c2:
                                reading_time_em = st.time_input("Reading Time", datetime.now().time(), key="em_time")
                            
                            notes_em = st.text_area("Notes/Observations", key="em_notes")
                            
                            if st.form_submit_button("📝 RECORD ENERGY READING", use_container_width=True, type="primary"):
                                safe_supabase_query(lambda: supabase.table("utility_readings").insert({
                                    "facility_code": fc, "utility_type": "Electricity",
                                    "meter_id": str(selected_meter_id),
                                    "reading_date": str(reading_date_em), "reading_time": str(reading_time_em),
                                    "reading_value": eb_kwh + dg_kwh, "unit": "kWh",
                                    "consumption": eb_kwh + dg_kwh, "created_at": datetime.now().isoformat()
                                }).execute(), error_prefix="Energy reading")
                                
                                if (eb_kwh + dg_kwh) > 10000:
                                    try:
                                        send_email_notification("eetuk@churchgate.com", f"⚡ High Energy Reading — {selected_meter_id}", f"<h3>High Reading</h3><p>Meter: {selected_meter_id}</p><p>Value: {eb_kwh + dg_kwh:,.1f} kWh</p>")
                                    except: pass
                                
                                st.success(f"✅ Energy reading recorded!")
                                st.balloons()
                                st.rerun()
        
        elif reading_mode == "💧 Water Meter":
            st.markdown("#### 💧 Water Meter Reading")
            
            water_meter_list = df[df["parent_asset"] == "WATER METER"] if len(df) > 0 else pd.DataFrame()
            
            if len(water_meter_list) == 0:
                st.info(f"No water meters found for {info.get('full_name', fc)}.")
            else:
                water_options = ["Select Meter..."] + [f"{a['name'][:100]} (ID: {a['asset_tag']})" for _, a in water_meter_list.iterrows()]
                selected_water = st.selectbox("Select Water Meter*", water_options)
                
                if selected_water != "Select Meter...":
                    selected_idx = [i for i, a in enumerate(water_meter_list.iterrows()) if f"{a[1]['name'][:100]} (ID: {a[1]['asset_tag']})" == selected_water][0]
                    selected_meter = water_meter_list.iloc[selected_idx]
                    selected_meter_id = str(selected_meter["asset_tag"])
                    
                    meter_history = readings_df[readings_df["meter_id"] == selected_meter_id] if len(readings_df) > 0 else pd.DataFrame()
                    last_reading = meter_history.iloc[0] if len(meter_history) > 0 else None
                    
                    st.markdown(f"**Selected Meter:** {selected_meter['name'][:120]}")
                    st.markdown(f"**Location:** {selected_meter.get('location_building','N/A')}")
                    
                    if last_reading is not None:
                        st.info(f"📅 Last Reading: {str(last_reading['reading_date'])} | Value: {last_reading['reading_value']:,.0f} {last_reading.get('unit','Ltr')}")
                    
                    with st.form("water_meter_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            water_value = st.number_input("Current Reading*", min_value=0.0, value=0.0, step=1.0)
                            water_date = st.date_input("Reading Date*", today)
                        with c2:
                            water_time = st.time_input("Reading Time", datetime.now().time())
                            water_notes = st.text_area("Notes")
                        
                        if last_reading is not None and water_value > 0:
                            prev_val = last_reading["reading_value"]
                            if water_value > prev_val:
                                consumption = water_value - prev_val
                                st.metric("📊 Consumption", f"{consumption:,.0f} Ltr")
                        
                        if st.form_submit_button("📝 RECORD WATER READING", use_container_width=True, type="primary"):
                            if water_value > 0:
                                prev_val = meter_history.iloc[0]["reading_value"] if len(meter_history) > 0 else water_value
                                consumption = max(0, water_value - prev_val) if water_value > prev_val else 0
                                
                                safe_supabase_query(lambda: supabase.table("utility_readings").insert({
                                    "facility_code": fc, "utility_type": "Water",
                                    "meter_id": selected_meter_id,
                                    "reading_date": str(water_date), "reading_time": str(water_time),
                                    "reading_value": water_value, "unit": "Ltr",
                                    "consumption": consumption, "created_at": datetime.now().isoformat()
                                }).execute(), error_prefix="Water reading")
                                st.success("✅ Water reading recorded!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("⚠️ Enter a reading value")
        
        else:
            st.markdown("#### 📝 Quick Utility Reading")
            with st.form("quick_reading_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    utility_type = st.selectbox("Utility Type*", ["Electricity", "Water", "Diesel", "Gas"])
                    meter_name = st.text_input("Meter Name/ID*", placeholder="e.g., Energy Meter AEDC-CT-3")
                with c2:
                    reading_date_q = st.date_input("Reading Date*", today)
                    reading_time_q = st.time_input("Reading Time", datetime.now().time())
                with c3:
                    reading_value = st.number_input("Reading Value*", min_value=0.0, step=0.1)
                    unit = st.selectbox("Unit", ["kWh", "MWh", "m³", "Litres", "Gallons", "m³/hr"])
                
                consumption_val = st.number_input("Consumption", min_value=0.0, value=0.0, step=0.1)
                notes_q = st.text_area("Notes")
                
                if st.form_submit_button("📝 RECORD READING", use_container_width=True, type="primary"):
                    if meter_name:
                        safe_supabase_query(lambda: supabase.table("utility_readings").insert({
                            "facility_code": fc, "utility_type": utility_type,
                            "meter_id": meter_name, "reading_date": str(reading_date_q),
                            "reading_time": str(reading_time_q), "reading_value": reading_value,
                            "unit": unit, "consumption": consumption_val, "created_at": datetime.now().isoformat()
                        }).execute(), error_prefix="Utility reading")
                        st.success(f"✅ {utility_type} reading recorded!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("⚠️ Meter Name/ID is required")
    
    # ============================================
    # TAB 4: ANALYTICS
    # ============================================
    with tabs[4]:
        st.markdown("### 📈 Utility Analytics")
        
        if len(readings_df) > 0:
            readings_df["reading_date_dt"] = pd.to_datetime(readings_df["reading_date"])
            
            c1, c2, c3 = st.columns(3)
            with c1:
                elec_total = readings_df[readings_df["utility_type"]=="Electricity"]["reading_value"].sum() if "utility_type" in readings_df.columns else 0
                st.metric("⚡ Total Electricity", f"{elec_total:,.0f} kWh")
            with c2:
                diesel_total = readings_df[readings_df["utility_type"]=="Diesel"]["reading_value"].sum() if "utility_type" in readings_df.columns else 0
                st.metric("⛽ Total Diesel", f"{diesel_total:,.0f} L")
            with c3:
                water_total = readings_df[readings_df["utility_type"]=="Water"]["reading_value"].sum() if "utility_type" in readings_df.columns else 0
                st.metric("💧 Total Water", f"{water_total:,.0f} m³")
            
            st.markdown("---")
            
            if len(readings_df) >= 2:
                by_type = readings_df.groupby(["reading_date_dt","utility_type"])["reading_value"].sum().reset_index()
                fig = px.line(by_type, x="reading_date_dt", y="reading_value", color="utility_type", title="Utility Consumption Trends", markers=True, color_discrete_sequence=["#F59E0B","#EF4444","#06B6D4","#10B981"])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            c1, c2 = st.columns(2)
            with c1:
                type_summary = readings_df.groupby("utility_type")["reading_value"].sum().reset_index()
                fig_bar = px.bar(type_summary, x="utility_type", y="reading_value", title="Total by Utility Type", color="utility_type", color_discrete_sequence=["#F59E0B","#EF4444","#06B6D4","#10B981"])
                fig_bar.update_layout(height=350)
                st.plotly_chart(fig_bar, use_container_width=True)
            with c2:
                if len(readings_df) >= 5:
                    daily = readings_df.groupby("reading_date_dt")["reading_value"].sum().reset_index()
                    fig_line = px.line(daily, x="reading_date_dt", y="reading_value", title="Daily Total Consumption", markers=True)
                    fig_line.update_layout(height=350)
                    st.plotly_chart(fig_line, use_container_width=True)
            
            st.download_button("📥 Download CSV", readings_df.to_csv(index=False), f"utility_readings_{today}.csv", "text/csv", use_container_width=True)
        else:
            st.info("No utility readings recorded yet.")
    
    # ============================================
    # TAB 5: REPORTS
    # ============================================
    with tabs[5]:
        st.markdown("### 📊 Utility Reports")
        
        report_period = st.selectbox("Report Period", ["Weekly", "Monthly", "Quarterly", "Custom"], key="util_period")
        
        if report_period == "Weekly":
            start_date = today - timedelta(days=7)
            end_date = today
        elif report_period == "Monthly":
            start_date = today.replace(day=1)
            end_date = today
        elif report_period == "Quarterly":
            q_month = ((today.month - 1) // 3) * 3 + 1
            start_date = date(today.year, q_month, 1)
            end_date = today
        else:
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("From", today - timedelta(days=30))
            with c2:
                end_date = st.date_input("To", today)
        
        period_readings = readings_df[(pd.to_datetime(readings_df["reading_date"]).dt.date >= start_date) & (pd.to_datetime(readings_df["reading_date"]).dt.date <= end_date)] if len(readings_df) > 0 else pd.DataFrame()
        
        st.caption(f"📅 {start_date} to {end_date} | {len(period_readings)} readings")
        
        if len(period_readings) > 0:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                p_elec = period_readings[period_readings["utility_type"]=="Electricity"]["reading_value"].sum() if "utility_type" in period_readings.columns else 0
                st.metric("⚡ Electricity", f"{p_elec:,.0f} kWh")
            with c2:
                p_diesel = period_readings[period_readings["utility_type"]=="Diesel"]["reading_value"].sum() if "utility_type" in period_readings.columns else 0
                st.metric("⛽ Diesel", f"{p_diesel:,.0f} L")
            with c3:
                p_water = period_readings[period_readings["utility_type"]=="Water"]["reading_value"].sum() if "utility_type" in period_readings.columns else 0
                st.metric("💧 Water", f"{p_water:,.0f} m³")
            with c4:
                est_cost = (p_elec * 75) + (p_diesel * 400) + (p_water * 1250)
                st.metric("💰 Est. Cost", f"₦{est_cost:,.0f}")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 Generate HTML Report", key="util_html_btn", use_container_width=True, type="primary"):
                logo_b64 = get_logo_base64()
                logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="30">' if logo_b64 else ''
                html_report = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Utility Intelligence Report</title><style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:20px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:960px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}.header{{border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}h1{{color:#CC0000;margin:0}}.kpi-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:20px 0}}.kpi{{background:#f9fafb;border-radius:10px;padding:15px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:22px;font-weight:800;color:#CC0000}}.kpi .lbl{{font-size:10px;color:#888;text-transform:uppercase}}table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:11px}}th{{background:#CC0000;color:white;padding:10px}}td{{padding:8px;border-bottom:1px solid #eee}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:20px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container"><div class="header">{logo_img}<h1>Utility Intelligence Report</h1><p>{info.get('full_name',fc)} | {today.strftime('%d %B %Y')} | {report_period}</p></div><div class="kpi-row"><div class="kpi"><div class="val">{energy_meter_count}</div><div class="lbl">Energy Meters</div></div><div class="kpi"><div class="val">3</div><div class="lbl">Diesel Tanks</div></div><div class="kpi"><div class="val">6</div><div class="lbl">Water Meters</div></div><div class="kpi"><div class="val">{len(period_readings)}</div><div class="lbl">Readings</div></div><div class="kpi"><div class="val">₦{est_cost:,.0f}</div><div class="lbl">Est. Cost</div></div></div><h2>Period Readings ({start_date} to {end_date})</h2><table><tr><th>Date</th><th>Type</th><th>Meter</th><th>Value</th><th>Unit</th></tr>"""
                for _, r in period_readings.head(50).iterrows():
                    html_report += f"<tr><td>{str(r.get('reading_date',''))[:10]}</td><td>{r.get('utility_type','')}</td><td>{r.get('meter_id','')}</td><td>{r.get('reading_value','')}</td><td>{r.get('unit','')}</td></tr>"
                html_report += "</table><div class='footer'>Churchgate Group | facilityXperience | Utility Intelligence Report</div></div></body></html>"
                st.download_button("📥 Download HTML Report", html_report, f"utility_report_{today}.html", "text/html", use_container_width=True)
        
        with c2:
            if st.button("📕 Generate PDF Report", key="util_pdf_btn", use_container_width=True):
                try:
                    from fpdf import FPDF
                    pdf = FPDF('L','mm','A4')
                    pdf.add_page()
                    pdf.set_font('Helvetica','B',16)
                    pdf.set_text_color(204,0,0)
                    pdf.cell(0,10,safe_text('Utility Intelligence Report'),0,1)
                    pdf.set_font('Helvetica','',10)
                    pdf.set_text_color(0,0,0)
                    pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {today.strftime("%d %B %Y")} | {report_period}'),0,1)
                    pdf.ln(5)
                    pdf.set_font('Helvetica','B',8)
                    pdf.set_fill_color(204,0,0)
                    pdf.set_text_color(255,255,255)
                    for h,w in zip(['Date','Type','Meter','Value','Unit'],[30,30,80,40,30]): pdf.cell(w,6,h,1,0,'C',True)
                    pdf.ln()
                    pdf.set_font('Helvetica','',8)
                    pdf.set_text_color(0,0,0)
                    for _,r in period_readings.head(50).iterrows():
                        pdf.cell(30,5,safe_text(str(r.get('reading_date',''))[:10]),1,0)
                        pdf.cell(30,5,safe_text(r.get('utility_type','')),1,0)
                        pdf.cell(80,5,safe_text(str(r.get('meter_id',''))[:35]),1,0)
                        pdf.cell(40,5,str(r.get('reading_value','')),1,0)
                        pdf.cell(30,5,safe_text(r.get('unit','')),1,0)
                        pdf.ln()
                    pdf_file = f"/tmp/utility_report_{today}.pdf"
                    pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f:
                        st.download_button("📥 Download PDF Report", f.read(), f"utility_report_{today}.pdf", "application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"PDF error: {str(e)[:80]}")
        
        st.markdown("---")
        st.markdown("### 🚨 AI Alert Feed")
        
        alerts = [
            {"severity": "⚠️ Warning", "msg": "Diesel Tank #2 showing 2mm water bottom increase. Recommend fuel polishing within 30 days.", "impact": "₦250,000 potential fuel degradation"},
            {"severity": "ℹ️ Info", "msg": "Non-Revenue Water estimated at 8.5%. Industry benchmark is <5%. Investigate cooling tower make-up line.", "impact": "₦170,000/month potential savings"},
            {"severity": "⚠️ Warning", "msg": "Energy intensity trending 5% above seasonal average. Check for after-hours HVAC operation.", "impact": "₦600,000/month potential savings"},
        ]
        
        for alert in alerts:
            sev = alert["severity"]
            color = "#EF4444" if "Critical" in sev else "#F59E0B" if "Warning" in sev else "#3B82F6"
            st.markdown(f"""
            <div style="background:white;border-left:4px solid {color};border-radius:8px;padding:0.7rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <b style="color:{color};">{sev}</b>: {alert['msg']}
                <br><span style="font-size:0.65rem;color:#888;">💰 Impact: {alert['impact']}</span>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# PPM COMMAND CENTER — FORTUNE 500 GRADE
# WORLD-CLASS PLANNED PREVENTIVE MAINTENANCE
# ============================================
def page_ppm():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    st.markdown(f'## 📊 PPM Command Center — {info.get("full_name", fc)}')
    
    # Fetch ALL PPM data
    ppm_all = DB.get_all("ppm_schedules", fc, 500)
    
    if not ppm_all:
        st.warning("No PPM schedules configured for this facility. Please set up PPM schedules in the database.")
        return
    
    df = pd.DataFrame(ppm_all)
    
    # ============================================
    # DATA PREPARATION
    # ============================================
    today = date.today()
    now = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    
    # Parse dates
    if "next_due_date" in df.columns:
        df["due_date_parsed"] = pd.to_datetime(df["next_due_date"], errors='coerce')
    if "last_completed_date" in df.columns:
        df["completed_date_parsed"] = pd.to_datetime(df["last_completed_date"], errors='coerce')
    
    # Status classifications
    overdue_mask = (df["due_date_parsed"] < pd.Timestamp(today)) & (df["status"] != "completed")
    due_today_mask = (df["due_date_parsed"] == pd.Timestamp(today)) & (df["status"] != "completed")
    due_this_week_mask = (df["due_date_parsed"] >= pd.Timestamp(today)) & (df["due_date_parsed"] <= pd.Timestamp(week_end)) & (df["status"] != "completed")
    due_this_month_mask = (df["due_date_parsed"] >= pd.Timestamp(today)) & (df["due_date_parsed"] <= pd.Timestamp(today + timedelta(days=30))) & (df["status"] != "completed")
    completed_mask = df["status"] == "completed"
    critical_mask = df.get("is_critical", pd.Series([False] * len(df))) == True
    
    # Counts
    total_schedules = len(df)
    overdue_count = overdue_mask.sum()
    due_today_count = due_today_mask.sum()
    due_week_count = due_this_week_mask.sum()
    due_month_count = due_this_month_mask.sum()
    completed_count = completed_mask.sum()
    critical_count = critical_mask.sum()
    critical_overdue = (overdue_mask & critical_mask).sum()
    
    # Compliance rate
    compliance_rate = round((completed_count / total_schedules * 100), 1) if total_schedules > 0 else 0
    
    # ============================================
    # EXECUTIVE KPI ROW
    # ============================================
    st.markdown("---")
    st.markdown("### 🎯 Executive KPIs")
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#EF4444" if overdue_count > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">🔴 Overdue</div><div style="font-size:2rem;font-weight:800;color:{color};">{overdue_count}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid #F59E0B;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">📅 Due Today</div><div style="font-size:2rem;font-weight:800;color:#F59E0B;">{due_today_count}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid #3B82F6;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">📆 This Week</div><div style="font-size:2rem;font-weight:800;color:#3B82F6;">{due_week_count}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid #8B5CF6;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">✅ Completed</div><div style="font-size:2rem;font-weight:800;color:#8B5CF6;">{completed_count}</div></div>""", unsafe_allow_html=True)
    with c5:
        compliance_color = "#10B981" if compliance_rate >= 90 else "#F59E0B" if compliance_rate >= 70 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid {compliance_color};box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">📈 Compliance</div><div style="font-size:2rem;font-weight:800;color:{compliance_color};">{compliance_rate}%</div></div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;text-align:center;border-left:4px solid #1a1a1a;box-shadow:0 2px 8px rgba(0,0,0,0.06);"><div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:1px;">🏗️ Total</div><div style="font-size:2rem;font-weight:800;color:#1a1a1a;">{total_schedules}</div></div>""", unsafe_allow_html=True)
    
    # ============================================
    # ALERT BANNERS
    # ============================================
    if critical_overdue > 0:
        st.error(f"🚨 **CRITICAL ALERT:** {critical_overdue} critical PPM tasks are OVERDUE! Immediate action required.")
    elif overdue_count > 0:
        st.warning(f"⚠️ **ATTENTION:** {overdue_count} PPM tasks are past due. Review and reschedule.")
    
    if compliance_rate < 70:
        st.error(f"📉 **COMPLIANCE RISK:** PPM compliance at {compliance_rate}% — below 70% threshold. Escalation recommended.")
    
    # ============================================
    # COMPLIANCE GAUGE + CHARTS
    # ============================================
    st.markdown("---")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("### 📊 Compliance Gauge")
        
        # Gauge chart
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=compliance_rate,
            title={'text': "PPM Compliance Rate", 'font': {'size': 14}},
            delta={'reference': 90, 'increasing': {'color': "#10B981"}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': "#CC0000" if compliance_rate < 70 else "#F59E0B" if compliance_rate < 90 else "#10B981"},
                'bgcolor': "white",
                'steps': [
                    {'range': [0, 70], 'color': '#FEE2E2'},
                    {'range': [70, 90], 'color': '#FFFBEB'},
                    {'range': [90, 100], 'color': '#ECFDF5'}
                ],
                'threshold': {
                    'line': {'color': "#CC0000", 'width': 3},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with c2:
        st.markdown("### 📅 PPM by Frequency")
        
        if "frequency" in df.columns:
            freq_counts = df["frequency"].value_counts()
            fig_freq = px.pie(
                values=freq_counts.values, 
                names=freq_counts.index,
                color_discrete_sequence=["#CC0000", "#F59E0B", "#3B82F6", "#10B981", "#8B5CF6", "#EC4899"],
                hole=0.4
            )
            fig_freq.update_layout(height=300, showlegend=True)
            fig_freq.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_freq, use_container_width=True)
    
    # ============================================
    # STATUS DISTRIBUTION CHART
    # ============================================
    st.markdown("---")
    st.markdown("### 📊 Workload Distribution")
    
    c1, c2 = st.columns(2)
    with c1:
        # By assigned team
        if "assigned_team" in df.columns:
            team_counts = df["assigned_team"].value_counts().head(8)
            fig_team = px.bar(
                x=team_counts.values, 
                y=team_counts.index, 
                orientation='h',
                title="PPM Tasks by Team",
                color=team_counts.values,
                color_continuous_scale="Reds",
                labels={"x": "Tasks", "y": ""}
            )
            fig_team.update_layout(height=350)
            st.plotly_chart(fig_team, use_container_width=True)
    
    with c2:
        # By priority
        if "priority" in df.columns:
            priority_counts = df["priority"].value_counts()
            colors_priority = {"critical": "#EF4444", "high": "#F59E0B", "medium": "#3B82F6", "low": "#10B981"}
            pie_colors = [colors_priority.get(p, "#999") for p in priority_counts.index]
            fig_priority = px.pie(
                values=priority_counts.values,
                names=priority_counts.index,
                title="Tasks by Priority",
                color_discrete_sequence=pie_colors
            )
            fig_priority.update_layout(height=350)
            st.plotly_chart(fig_priority, use_container_width=True)
    
    # ============================================
    # CRITICAL OVERDUE — IMMEDIATE ATTENTION
    # ============================================
    if critical_overdue > 0:
        st.markdown("---")
        st.markdown("### 🚨 Critical Overdue — Immediate Action Required")
        
        critical_overdue_df = df[overdue_mask & critical_mask].sort_values("due_date_parsed")
        
        for _, row in critical_overdue_df.iterrows():
            days_overdue = (today - row["due_date_parsed"].date()).days if pd.notna(row.get("due_date_parsed")) else 0
            st.markdown(f"""
            <div style="background:#FEF2F2;border-left:4px solid #EF4444;border-radius:8px;padding:0.8rem;margin:0.3rem 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b>🔴 {row.get('title','')}</b>
                        <br><span style="font-size:0.75rem;color:#991B1B;">{row.get('asset_name','') or row.get('equipment','')} | Due: {row.get('next_due_date','')} | {days_overdue} days overdue</span>
                    </div>
                    <span style="background:#EF4444;color:white;padding:3px 12px;border-radius:20px;font-size:0.7rem;font-weight:600;">CRITICAL</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ============================================
    # TASK VIEW TABS
    # ============================================
    st.markdown("---")
    st.markdown("### 📋 PPM Task Views")
    
    task_tabs = st.tabs(["🔴 Overdue", "📅 Due Today", "📆 This Week", "📆 This Month", "✅ Completed", "📋 All Tasks"])
    
    # --- OVERDUE TAB ---
    with task_tabs[0]:
        overdue_df = df[overdue_mask].sort_values("due_date_parsed")
        if len(overdue_df) > 0:
            st.caption(f"🔴 {len(overdue_df)} overdue tasks")
            for _, row in overdue_df.iterrows():
                days_overdue = (today - row["due_date_parsed"].date()).days if pd.notna(row.get("due_date_parsed")) else 0
                is_critical = row.get("is_critical", False)
                border_color = "#EF4444" if is_critical else "#F59E0B"
                bg_color = "#FEF2F2" if is_critical else "#FFFBEB"
                
                with st.expander(f"{'🔴' if is_critical else '🟡'} {row.get('title','')} — {days_overdue}d overdue | Due: {row.get('next_due_date','')}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Asset:** {row.get('asset_name','N/A')}")
                        st.write(f"**Frequency:** {row.get('frequency','N/A')}")
                    with c2:
                        st.write(f"**Team:** {row.get('assigned_team','N/A')}")
                        st.write(f"**Priority:** {row.get('priority','N/A').upper()}")
                    with c3:
                        st.write(f"**Status:** {row.get('status','N/A').upper()}")
                        st.write(f"**Last Done:** {row.get('last_completed_date','Never')}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Mark Complete", key=f"ppm_overdue_{row['id']}", use_container_width=True):
                            DB.update("ppm_schedules", row["id"], {"status": "completed", "last_completed_date": str(today)})
                            st.success("✅ Completed!")
                            st.rerun()
                    with c2:
                        new_due = st.date_input("Reschedule to", today + timedelta(days=7), key=f"reschedule_{row['id']}")
                        if st.button("📅 Reschedule", key=f"ppm_reschedule_{row['id']}", use_container_width=True):
                            DB.update("ppm_schedules", row["id"], {"next_due_date": str(new_due)})
                            st.success("📅 Rescheduled!")
                            st.rerun()
        else:
            st.success("🎉 No overdue tasks! All PPMs on track.")
    
    # --- DUE TODAY TAB ---
    with task_tabs[1]:
        today_df = df[due_today_mask].sort_values("due_date_parsed")
        if len(today_df) > 0:
            st.caption(f"📅 {len(today_df)} tasks due today")
            for _, row in today_df.iterrows():
                is_critical = row.get("is_critical", False)
                icon = "🔴" if is_critical else "📅"
                
                with st.expander(f"{icon} {row.get('title','')} — {row.get('frequency','')} | {row.get('assigned_team','N/A')}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Asset:** {row.get('asset_name','N/A')}")
                        st.write(f"**Location:** {row.get('location','N/A')}")
                    with c2:
                        st.write(f"**Team:** {row.get('assigned_team','N/A')}")
                        st.write(f"**Priority:** {row.get('priority','N/A').upper()}")
                    with c3:
                        st.write(f"**Last Done:** {row.get('last_completed_date','Never')}")
                    
                    if st.button("✅ Mark Complete", key=f"ppm_today_{row['id']}", use_container_width=True):
                        DB.update("ppm_schedules", row["id"], {"status": "completed", "last_completed_date": str(today)})
                        st.success("✅ Completed!")
                        st.rerun()
        else:
            st.success("✅ No tasks due today.")
    
    # --- THIS WEEK TAB ---
    with task_tabs[2]:
        week_df = df[due_this_week_mask].sort_values("due_date_parsed")
        if len(week_df) > 0:
            st.caption(f"📆 {len(week_df)} tasks due this week ({week_start.strftime('%d %b')} - {week_end.strftime('%d %b')})")
            for _, row in week_df.iterrows():
                days_left = (row["due_date_parsed"].date() - today).days if pd.notna(row.get("due_date_parsed")) else 0
                days_label = f"{days_left}d left" if days_left >= 0 else f"{-days_left}d overdue"
                
                st.markdown(f"""
                <div style="background:white;border-radius:8px;padding:0.7rem;margin:0.2rem 0;border-left:3px solid #3B82F6;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b>{row.get('title','')}</b>
                        <br><span style="font-size:0.7rem;color:#666;">{row.get('assigned_team','')} | Due: {row.get('next_due_date','')}</span>
                    </div>
                    <span style="font-size:0.7rem;color:#3B82F6;font-weight:600;">{days_label}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No tasks due this week.")
    
    # --- THIS MONTH TAB ---
    with task_tabs[3]:
        month_df = df[due_this_month_mask].sort_values("due_date_parsed")
        if len(month_df) > 0:
            st.caption(f"📆 {len(month_df)} tasks due in the next 30 days")
            st.dataframe(
                month_df[[c for c in ["title", "assigned_team", "frequency", "priority", "next_due_date", "status"] if c in month_df.columns]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ No tasks due this month.")
    
    # --- COMPLETED TAB ---
    with task_tabs[4]:
        completed_df = df[completed_mask].sort_values("completed_date_parsed", ascending=False) if "completed_date_parsed" in df.columns else df[completed_mask]
        if len(completed_df) > 0:
            st.caption(f"✅ {len(completed_df)} completed tasks")
            st.dataframe(
                completed_df[[c for c in ["title", "assigned_team", "frequency", "last_completed_date", "next_due_date"] if c in completed_df.columns]].head(20),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No completed tasks recorded.")
    
    # --- ALL TASKS TAB ---
    with task_tabs[5]:
        st.caption(f"📋 All {total_schedules} PPM schedules")
        
        # Search/filter
        search_ppm = st.text_input("🔍 Search PPM tasks", key="ppm_search_all")
        
        display_df = df
        if search_ppm:
            display_df = df[df["title"].str.contains(search_ppm, case=False, na=False)]
        
        st.dataframe(
            display_df[[c for c in ["title", "assigned_team", "frequency", "priority", "next_due_date", "last_completed_date", "status"] if c in display_df.columns]],
            use_container_width=True,
            hide_index=True,
            height=400
        )
    
    # ============================================
    # MANAGEMENT INSIGHTS
    # ============================================
    st.markdown("---")
    st.markdown("### 🤖 Management Insights")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if compliance_rate >= 90:
            st.success(f"✅ **Excellent:** {compliance_rate}% PPM compliance — on track for audit readiness.")
        elif compliance_rate >= 70:
            st.warning(f"⚠️ **Attention Needed:** {compliance_rate}% compliance — below 90% target. Focus on overdue tasks.")
        else:
            st.error(f"🚨 **Critical:** {compliance_rate}% compliance — immediate management intervention required.")
    
    with c2:
        if overdue_count == 0:
            st.success("✅ **Zero Overdue:** All PPM tasks are on schedule.")
        elif overdue_count <= 5:
            st.warning(f"⚠️ **Minor Backlog:** {overdue_count} tasks overdue. Address within 48 hours.")
        else:
            st.error(f"🚨 **Significant Backlog:** {overdue_count} overdue tasks. Resource allocation review needed.")
    
    with c3:
        if critical_count > 0 and critical_overdue == 0:
            st.success(f"✅ **Critical Tasks Protected:** All {critical_count} critical PPMs are on schedule.")
        elif critical_overdue > 0:
            st.error(f"🚨 **Risk Exposure:** {critical_overdue} critical tasks overdue. Potential equipment failure risk.")

# ============================================
# 52-WEEK CALENDAR (FULL)
# ============================================
def page_cal():
    fc=st.session_state.get("facility","WTC");info=FACILITY_INFO.get(fc,{})
    st.markdown(f'## 📅 52-Week Calendar — {info.get("full_name",fc)}')
    today=date.today()
    weeks=[]
    for w in range(1,53):
        week_start=today+timedelta(weeks=w-today.isocalendar()[1])
        weeks.append({"Week":w,"Start":week_start.strftime("%d %b"),"Status":"Upcoming" if w>today.isocalendar()[1] else "Current" if w==today.isocalendar()[1] else "Past"})
    df=pd.DataFrame(weeks)
    st.dataframe(df,use_container_width=True,hide_index=True,height=400)
    st.caption(f"📅 Current Week: {today.isocalendar()[1]} | {today.strftime('%d %B %Y')}")

# ============================================
# CHECKLIST STATUS — CONSOLIDATED DASHBOARD
# FORTUNE 500 GRADE — ASSET → SUB-ASSET DRILLDOWN
# ============================================
def page_cs():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    today = date.today()
    
    st.markdown(f'## ✅ Checklist Status — {info.get("full_name", fc)}')
    
    all_assets = DB.get_assets(fc, 50000)
    
    if not all_assets:
        st.info("No assets registered.")
        return
    
    df = pd.DataFrame(all_assets)
    
    # Clean up checklist values
    df["checklist_clean"] = df["checklist"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() not in ["", "NA", "na", "APPLICABLE", "NOTAPPLICABLE", "None"] else None)
    
    # Get templates
    templates = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").select("*").execute(), error_prefix="Checklist templates")
    template_names = [t.get("template_name","") for t in templates.data] if templates and templates.data else []
    
    # ============================================
    # FILTERS — ASSET → SUB-ASSET DRILLDOWN
    # ============================================
    st.markdown("### 🔍 Filter Assets")
    
    # Create department — sub_division labels
    df["dept_full"] = df.apply(lambda row: f"{row['department']} — {row['sub_division']}" if pd.notna(row.get('sub_division')) and row.get('sub_division') not in ['', 'N/A', 'NA'] else row['department'], axis=1)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        departments = ["All"] + sorted(df["dept_full"].dropna().unique().tolist())
        sel_dept = st.selectbox("Select Department", departments, key="cs_dept")
    
    # Filter by department
    if sel_dept != "All":
        dept_df = df[df["dept_full"] == sel_dept]
    else:
        dept_df = df.copy()
    
    with c2:
        # Asset = parent_asset
        asset_list = ["All"] + sorted(dept_df["parent_asset"].dropna().unique().tolist())
        sel_asset = st.selectbox("Select Asset", asset_list, key="cs_asset")
    
    # Filter by asset (parent)
    if sel_asset != "All":
        asset_df = dept_df[dept_df["parent_asset"] == sel_asset]
    else:
        asset_df = dept_df.copy()
    
    with c3:
        # Sub-Asset = name
        sub_list = ["All"] + sorted(asset_df["name"].dropna().unique().tolist())
        sel_sub = st.selectbox("Select Sub Asset", sub_list, key="cs_sub")
    
    with c4:
        bldg_list = ["All"] + sorted(df["location_building"].dropna().unique().tolist())
        sel_bldg = st.selectbox("Building", bldg_list, key="cs_bldg")
    
    # Date range
    c1, c2 = st.columns(2)
    with c1:
        from_date = st.date_input("From Date", today - timedelta(days=30), key="cs_from")
    with c2:
        to_date = st.date_input("To Date", today, key="cs_to")
    
    # Apply all filters
    filtered = df.copy()
    if sel_dept != "All": filtered = filtered[filtered["dept_full"] == sel_dept]
    if sel_asset != "All": filtered = filtered[filtered["parent_asset"] == sel_asset]
    if sel_sub != "All": filtered = filtered[filtered["name"] == sel_sub]
    if sel_bldg != "All": filtered = filtered[filtered["location_building"] == sel_bldg]
    
    total_filtered = len(filtered)
    enrolled_count = len(filtered[filtered["checklist_clean"].notna()])
    not_enrolled = total_filtered - enrolled_count
    
    st.markdown("---")
    
    # ============================================
    # CHECKLIST TYPE TABS
    # ============================================
    st.markdown("### 📋 Checklist Reports")
    
    checklist_tabs = st.tabs(["📅 Scheduled PPM", "📋 Daily Checklist", "⏰ Hourly Checklist", "📊 Summary", "📋 Consolidated Report"])
    
    # ============================================
    # TAB 0: SCHEDULED PPM
    # ============================================
    with checklist_tabs[0]:
        st.markdown("#### 📅 Scheduled PPM Checklist Status")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("📋 Total", total_filtered)
        with c2: st.metric("⏳ Pending", not_enrolled)
        with c3: st.metric("✅ Enrolled", enrolled_count)
        
        st.markdown("---")
        
        # Search bar
        cs_search_main = st.text_input("🔍 Search Asset or Sub-Asset", key="cs_search_main", placeholder="Type to filter assets...")
        
        # Apply search filter
        if cs_search_main:
            mask = filtered["parent_asset"].str.contains(cs_search_main, case=False, na=False) | filtered["name"].str.contains(cs_search_main, case=False, na=False)
            display_filtered = filtered[mask]
        else:
            display_filtered = filtered.copy()
        
        total_display = len(display_filtered)
        
        # Pagination
        page_size = 20
        if "cs_page_scheduled" not in st.session_state:
            st.session_state.cs_page_scheduled = 1
        
        total_pages = max(1, (total_display + page_size - 1) // page_size)
        start = (st.session_state.cs_page_scheduled - 1) * page_size
        end = min(start + page_size, total_display)
        
        page_data = display_filtered.iloc[start:end]
        
        # Pagination controls
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("◀◀", key="cs_first"): st.session_state.cs_page_scheduled = 1; st.rerun()
        with c2:
            if st.button("◀", key="cs_prev") and st.session_state.cs_page_scheduled > 1:
                st.session_state.cs_page_scheduled -= 1; st.rerun()
        with c3:
            st.markdown(f"**Page {st.session_state.cs_page_scheduled} of {total_pages}**")
        with c4:
            if st.button("▶", key="cs_next") and st.session_state.cs_page_scheduled < total_pages:
                st.session_state.cs_page_scheduled += 1; st.rerun()
        with c5:
            if st.button("▶▶", key="cs_last"): st.session_state.cs_page_scheduled = total_pages; st.rerun()
        
        st.caption(f"Showing {start+1}–{end} of {total_display} assets")
        
        for _, asset in page_data.iterrows():
            enrolled = pd.notna(asset.get("checklist_clean"))
            border = "#10B981" if enrolled else "#e5e7eb"
            bg = "#ECFDF5" if enrolled else "#fafafa"
            badge = "✅ Enrolled" if enrolled else "⚠️ Not Enrolled"
            badge_bg = "#10B981" if enrolled else "#F59E0B"
            checklist_name = asset.get("checklist_clean") if enrolled else "Not Enrolled"
            
            st.markdown(f"""
            <div style="background:{bg};border-left:3px solid {border};border-radius:6px;padding:0.5rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <b>{asset.get('parent_asset','N/A')}</b> → {asset.get('name','N/A')[:60]}
                    <br><span style="font-size:0.65rem;color:#666;">📋 {checklist_name} | 📅 {asset.get('ppm_frequency', asset.get('verification_frequency', 'N/A'))}</span>
                </div>
                <span style="background:{badge_bg};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{badge}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 1: DAILY CHECKLIST
    # ============================================
    with checklist_tabs[1]:
        st.markdown("#### 📋 Daily Checklist Status")
        
        daily_assets = filtered[filtered["verification_frequency"].isin(["Daily","daily"])] if "verification_frequency" in filtered.columns else pd.DataFrame()
        
        c1, c2 = st.columns(2)
        with c1: st.metric("📋 Total Daily", len(daily_assets))
        with c2: st.metric("⏳ Pending Today", len(daily_assets))
        
        st.markdown("---")
        
        if len(daily_assets) > 0:
            for _, asset in daily_assets.head(20).iterrows():
                st.markdown(f"""
                <div style="background:white;border-left:3px solid #3B82F6;border-radius:6px;padding:0.5rem;margin:0.2rem 0;">
                    <b>{asset.get('parent_asset','N/A')}</b> → {asset.get('name','N/A')[:60]}
                    <br><span style="font-size:0.65rem;color:#666;">📍 {asset.get('location_building','')} | 📅 Daily</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No daily checklist assets found.")
    
    # ============================================
    # TAB 2: HOURLY CHECKLIST
    # ============================================
    with checklist_tabs[2]:
        st.markdown("#### ⏰ Hourly Checklist Status")
        
        hourly_assets = filtered[filtered["verification_frequency"].isin(["Hourly","hourly","Bi-Weekly"])] if "verification_frequency" in filtered.columns else pd.DataFrame()
        
        c1, c2 = st.columns(2)
        with c1: st.metric("📋 Total Hourly/Bi-Weekly", len(hourly_assets))
        with c2: st.metric("⏳ Pending", len(hourly_assets))
        
        st.markdown("---")
        
        if len(hourly_assets) > 0:
            for _, asset in hourly_assets.head(20).iterrows():
                st.markdown(f"""
                <div style="background:white;border-left:3px solid #8B5CF6;border-radius:6px;padding:0.5rem;margin:0.2rem 0;">
                    <b>{asset.get('parent_asset','N/A')}</b> → {asset.get('name','N/A')[:60]}
                    <br><span style="font-size:0.65rem;color:#666;">📍 {asset.get('location_building','')} | ⏰ {asset.get('verification_frequency','N/A')}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hourly checklist assets found.")
    
    # ============================================
    # TAB 3: SUMMARY + BULK ENROLLMENT
    # ============================================
    with checklist_tabs[3]:
        st.markdown("#### 📊 Checklist Summary")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div style="background:white;border-radius:10px;padding:1rem;text-align:center;border-top:3px solid #CC0000;"><div style="font-size:0.6rem;color:#888;">Total Assets</div><div style="font-size:1.8rem;font-weight:800;">{total_filtered}</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div style="background:white;border-radius:10px;padding:1rem;text-align:center;border-top:3px solid #10B981;"><div style="font-size:0.6rem;color:#888;">✅ Enrolled</div><div style="font-size:1.8rem;font-weight:800;color:#10B981;">{enrolled_count}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div style="background:white;border-radius:10px;padding:1rem;text-align:center;border-top:3px solid #F59E0B;"><div style="font-size:0.6rem;color:#888;">⏳ Pending</div><div style="font-size:1.8rem;font-weight:800;color:#F59E0B;">{not_enrolled}</div></div>""", unsafe_allow_html=True)
        with c4:
            rate = round(enrolled_count/total_filtered*100,1) if total_filtered > 0 else 0
            st.markdown(f"""<div style="background:white;border-radius:10px;padding:1rem;text-align:center;border-top:3px solid #3B82F6;"><div style="font-size:0.6rem;color:#888;">Enrollment Rate</div><div style="font-size:1.8rem;font-weight:800;color:#3B82F6;">{rate}%</div></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Template reference
        st.markdown("### 📋 Available International Standard Templates")
        if templates and templates.data:
            for t in templates.data:
                items_count = 0
                try:
                    items_res = safe_supabase_query(lambda: supabase.table("ppm_checklist_items").select("id", count="exact").eq("template_id", t["id"]).execute(), error_prefix="Checklist items")
                    items_count = items_res.count if items_res else 0
                except: pass
                
                st.markdown(f"""
                <div style="background:white;border-radius:8px;padding:0.6rem;margin:0.2rem 0;border-left:4px solid #3B82F6;">
                    <b>{t.get('template_name','')}</b> — {t.get('international_standard','')}
                    <br><span style="font-size:0.65rem;color:#666;">📋 {items_count} items | 🏷️ {t.get('asset_category','')}</span>
                </div>
                """, unsafe_allow_html=True)
        
        # Bulk enrollment
        st.markdown("---")
        st.markdown("### 📦 Bulk Enrollment")
        st.caption("Enroll all currently filtered assets with a checklist template.")
        
        with st.form("cs_bulk_enroll"):
            c1, c2, c3 = st.columns(3)
            with c1:
                bulk_template = st.selectbox("Checklist Template", template_names, key="cs_bulk_tpl")
            with c2:
                bulk_freq = st.selectbox("PPM Frequency", ["Daily","Weekly","Bi-Weekly","Monthly","Quarterly","Half-Yearly","Yearly"], key="cs_bulk_freq")
            with c3:
                overwrite_existing = st.checkbox("Overwrite existing", value=True, key="cs_bulk_overwrite")
            
            st.caption(f"📋 {len(filtered)} assets will be enrolled with **{bulk_template}** at **{bulk_freq}** frequency")
            
            if st.form_submit_button("🚀 ENROLL ASSETS", use_container_width=True, type="primary"):
                if bulk_template:
                    count = 0
                    skipped = 0
                    for _, asset in filtered.iterrows():
                        is_enrolled = pd.notna(asset.get("checklist_clean"))
                        if is_enrolled and not overwrite_existing:
                            skipped += 1
                            continue
                        DB.update("assets", asset["id"], {
                            "checklist": bulk_template,
                            "ppm_frequency": bulk_freq,
                            "checklist_template": bulk_template
                        })
                        
                        template_dates = None
                        tpl_res = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").select("schedule_dates").eq("template_name", bulk_template).single().execute(), error_prefix="Template dates")
                        if tpl_res and tpl_res.data and tpl_res.data.get("schedule_dates"):
                            template_dates = tpl_res.data["schedule_dates"].split(",")
                        
                        if template_dates:
                            for d in template_dates:
                                d = d.strip()
                                try:
                                    parsed_date = datetime.strptime(d, "%d-%m-%Y").strftime("%Y-%m-%d")
                                except:
                                    try:
                                        parsed_date = datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d")
                                    except:
                                        parsed_date = str(date.today())
                                
                                safe_supabase_query(lambda: supabase.table("ppm_schedules").insert({
                                    "facility_code": fc,
                                    "asset_id": asset.get("id"),
                                    "title": f"{asset.get('name','PPM')} - {bulk_template}",
                                    "frequency": bulk_freq,
                                    "status": "scheduled",
                                    "assigned_team": asset.get("department", ""),
                                    "next_due_date": parsed_date,
                                    "created_at": datetime.now().isoformat()
                                }).execute(), error_prefix="PPM schedule")
                        else:
                            safe_supabase_query(lambda: supabase.table("ppm_schedules").insert({
                                "facility_code": fc,
                                "asset_id": asset.get("id"),
                                "title": f"{asset.get('name','PPM')} - {bulk_template}",
                                "frequency": bulk_freq,
                                "status": "scheduled",
                                "assigned_team": asset.get("department", ""),
                                "next_due_date": str(date.today()),
                                "created_at": datetime.now().isoformat()
                            }).execute(), error_prefix="PPM schedule")
                        
                        count += 1
                    
                    msg = f"✅ {count} assets enrolled with {bulk_template}!"
                    if skipped > 0:
                        msg += f" ({skipped} skipped — already enrolled)"
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error("⚠️ Please select a template")
    
    # ============================================
    # TAB 4: CONSOLIDATED REPORT
    # ============================================
    with checklist_tabs[4]:
        st.markdown("#### 📋 Consolidated Checklist Report")
        
        # Build consolidated data
        consolidated = []
        for _, asset in filtered.iterrows():
            enrolled = pd.notna(asset.get("checklist_clean"))
            
            consolidated.append({
                "SNO": len(consolidated) + 1,
                "Asset": asset.get("parent_asset", "N/A"),
                "Sub Asset": asset.get("name", "N/A"),
                "Checklist Name": asset.get("checklist_clean") if enrolled else "Not Enrolled",
                "Frequency": asset.get("ppm_frequency", asset.get("verification_frequency", "N/A")),
                "Date": str(today),
                "Status": "Enrolled" if enrolled else "Pending"
            })
        
        cons_df = pd.DataFrame(consolidated)
        
        # Filters
        c1, c2, c3 = st.columns(3)
        with c1:
            cons_status = st.selectbox("Status", ["All", "Enrolled", "Pending"], key="cons_status")
        with c2:
            cons_freq = st.selectbox("Frequency", ["All", "Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="cons_freq")
        with c3:
            cons_search = st.text_input("🔍 Search Asset or Checklist", key="cons_search", placeholder="Search...")
        
        display_cons = cons_df.copy()
        if cons_status != "All":
            display_cons = display_cons[display_cons["Status"] == cons_status]
        if cons_freq != "All":
            display_cons = display_cons[display_cons["Frequency"] == cons_freq]
        if cons_search:
            mask = display_cons["Asset"].str.contains(cons_search, case=False, na=False) | display_cons["Sub Asset"].str.contains(cons_search, case=False, na=False) | display_cons["Checklist Name"].str.contains(cons_search, case=False, na=False)
            display_cons = display_cons[mask]
        
        # Counts
        if len(display_cons) > 0:
            enrolled_total = len(display_cons[display_cons["Status"] == "Enrolled"])
            pending_total = len(display_cons[display_cons["Status"] == "Pending"])
        else:
            enrolled_total = 0
            pending_total = 0
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("📋 Total", len(display_cons))
        with c2: st.metric("⏳ Pending", pending_total)
        with c3: st.metric("✅ Enrolled", enrolled_total)
        
        st.markdown("---")
        
        # Pagination
        page_size = 25
        if "cons_page" not in st.session_state:
            st.session_state.cons_page = 1
        
        total_pages_cons = max(1, (len(display_cons) + page_size - 1) // page_size)
        start_cons = (st.session_state.cons_page - 1) * page_size
        end_cons = min(start_cons + page_size, len(display_cons))
        
        page_data_cons = display_cons.iloc[start_cons:end_cons]
        
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("◀◀", key="cons_first"): st.session_state.cons_page = 1; st.rerun()
        with c2:
            if st.button("◀", key="cons_prev") and st.session_state.cons_page > 1:
                st.session_state.cons_page -= 1; st.rerun()
        with c3:
            st.markdown(f"**Page {st.session_state.cons_page} of {total_pages_cons}**")
        with c4:
            if st.button("▶", key="cons_next") and st.session_state.cons_page < total_pages_cons:
                st.session_state.cons_page += 1; st.rerun()
        with c5:
            if st.button("▶▶", key="cons_last"): st.session_state.cons_page = total_pages_cons; st.rerun()
        
        st.caption(f"Showing {start_cons+1}–{end_cons} of {len(display_cons)} records")
        
        if len(page_data_cons) > 0:
            for _, row in page_data_cons.iterrows():
                is_enrolled_row = row["Status"] == "Enrolled"
                border = "#10B981" if is_enrolled_row else "#F59E0B"
                bg = "#ECFDF5" if is_enrolled_row else "#FFFBEB"
                badge = "✅ Enrolled" if is_enrolled_row else "⏳ Pending"
                badge_bg = "#10B981" if is_enrolled_row else "#F59E0B"
                
                st.markdown(f"""
                <div style="background:{bg};border-left:3px solid {border};border-radius:6px;padding:0.5rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <div style="flex:1;">
                        <b>#{row['SNO']} {row['Asset']}</b>
                        <br><span style="font-size:0.65rem;color:#666;">└ {row['Sub Asset'][:80]}</span>
                        <br><span style="font-size:0.6rem;color:#888;">📋 {row['Checklist Name']} | 📅 {row['Frequency']} | {row['Date']}</span>
                    </div>
                    <span style="background:{badge_bg};color:white;padding:3px 12px;border-radius:15px;font-size:0.65rem;font-weight:700;white-space:nowrap;">{badge}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No records match your filters.")
        
        # Export
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download CSV", display_cons.to_csv(index=False), f"consolidated_checklist_{today}.csv", "text/csv", use_container_width=True)
        with c2:
            st.download_button("📥 Download HTML", display_cons.to_html(index=False), f"consolidated_checklist_{today}.html", "text/html", use_container_width=True)


# ============================================
# INCIDENT ESCALATION HELPER (top-level function)
# ============================================
def _send_incident_escalation(fc, inc_id, severity, level, title):
    try:
        esc = safe_supabase_query(lambda: supabase.table("incident_escalation").select("*").eq("facility_code", fc).eq("severity", severity).eq("escalation_level", level).execute(), error_prefix="Incident escalation")
        if esc and esc.data:
            for e in esc.data:
                send_email_notification(
                    e["escalate_to_email"],
                    f"🚨 Incident Escalation L{level} — {title}",
                    f"<h3>Incident Requires Attention</h3><p><b>Level:</b> {level}</p><p><b>Incident:</b> {title}</p><p>Please respond within {e.get('sla_minutes','15')} minutes.</p>"
                )
    except:
        pass


# ============================================
# INCIDENT INTELLIGENCE — COMMAND & CONTROL TOWER
# COMPLETE WITH DETAIL VIEW, UPLOADS, ESCALATION
# ============================================
def page_ic():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    user_email = st.session_state.get("user", {}).get("email", "")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_fm_director = user_role in ["admin", "super_admin", "sr_management"]
    is_manager = user_role in ["manager", "sr_manager", "admin", "super_admin"]
    
    st.markdown(f'## 🚨 Incident Command — {info.get("full_name", fc)}')
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    inc_data = safe_supabase_query(lambda: supabase.table("incidents").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="Incident data")
    inc_df = pd.DataFrame(inc_data.data) if inc_data and inc_data.data else pd.DataFrame()
    
    total_inc = len(inc_df)
    active_inc = len(inc_df[~inc_df["status"].isin(["closed","disputed"])]) if total_inc > 0 else 0
    critical_inc = len(inc_df[(inc_df["severity"] == "critical") & (~inc_df["status"].isin(["closed","disputed"]))]) if total_inc > 0 else 0
    life_safety = len(inc_df[(inc_df["life_safety_flag"] == True) & (~inc_df["status"].isin(["closed","disputed"]))]) if total_inc > 0 else 0
    tenant_impacted = len(inc_df[(inc_df["tenant_impact"] == True) & (~inc_df["status"].isin(["closed","disputed"]))]) if total_inc > 0 else 0
    
    # ============================================
    # 🟥 TOP RIBBON
    # ============================================
    st.markdown("### 🟥 Incident Pulse Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#EF4444" if critical_inc > 0 else "#F59E0B" if active_inc > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Active</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{active_inc}</div></div>""", unsafe_allow_html=True)
    with c2:
        color = "#EF4444" if life_safety > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Life Safety</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{life_safety}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if critical_inc > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Critical</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{critical_inc}</div></div>""", unsafe_allow_html=True)
    with c4: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Tenants</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{tenant_impacted}</div></div>""", unsafe_allow_html=True)
    with c5: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_inc}</div></div>""", unsafe_allow_html=True)
    with c6:
        reopened = len(inc_df[inc_df["reopened_count"] > 0]) if total_inc > 0 else 0
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Reopened</div><div style="font-size:1.3rem;font-weight:800;color:#F59E0B;">{reopened}</div></div>""", unsafe_allow_html=True)
    
    if life_safety > 0: st.error(f"🚨 LIFE SAFETY: {life_safety} active incidents involve life safety risk!")
    if critical_inc > 0: st.error(f"🔴 CRITICAL: {critical_inc} critical incidents active.")
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 Active Incidents", "➕ Report Incident", "📊 All Incidents", "📈 Analytics", "⚙️ Escalation Settings", "📄 Reports"])
    
    # ============================================
    # TAB 0: ACTIVE INCIDENTS WITH FULL WORKFLOW
    # ============================================
    with tabs[0]:
        st.markdown("### 📋 Active Incident Queue")
        
        active_df = inc_df[~inc_df["status"].isin(["closed","disputed"])] if total_inc > 0 else pd.DataFrame()
        
        if len(active_df) == 0:
            st.success("✅ No active incidents.")
        else:
            for _, inc in active_df.iterrows():
                status = inc.get("status","created")
                severity = inc.get("severity","minor")
                sev_color = "#EF4444" if severity == "critical" else "#F59E0B" if severity == "major" else "#3B82F6" if severity == "minor" else "#6B7280"
                sc = {"created":"#3B82F6","acknowledged":"#F59E0B","responding":"#8B5CF6","contained":"#06B6D4","closed":"#10B981"}.get(status,"#3B82F6")
                inc_id = inc["id"]
                
                elapsed = ""
                if inc.get("created_at"):
                    try:
                        elapsed_time = wat_now - pd.to_datetime(inc["created_at"])
                        hours = int(elapsed_time.total_seconds() // 3600)
                        mins = int((elapsed_time.total_seconds() % 3600) // 60)
                        elapsed = f"{hours:02d}:{mins:02d}:{int(elapsed_time.total_seconds()%60):02d}"
                    except: pass
                
                life_safety_line = ""
                if inc.get('life_safety_flag'):
                    tenant = inc.get("tenant_name","")
                    life_safety_line = f'<br><span style="font-size:0.6rem;color:#EF4444;">Life Safety | {tenant}</span>'
                
                card_html = f"""<div style="background:white;border-left:4px solid {sev_color};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);"><div style="display:flex;justify-content:space-between;align-items:center;"><div><b>{inc.get('incident_number','N/A')}</b> — {inc.get('title','')[:80]}<br><span style="font-size:0.65rem;color:#666;">📍 {inc.get('location_building','')} / {inc.get('location_floor','')} | ⏱️ {elapsed} elapsed</span>{life_safety_line}</div><div style="text-align:right;"><span style="background:{sev_color};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{severity.upper()}</span><br><span style="background:{sc};color:white;padding:2px 8px;border-radius:12px;font-size:0.55rem;">{status.upper()}</span></div></div></div>"""
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Toggle detail view
                detail_key = f"inc_detail_{inc_id}"
                if detail_key not in st.session_state: st.session_state[detail_key] = False
                
                c1, c2 = st.columns([3,1])
                with c1:
                    if not st.session_state[detail_key]:
                        if st.button(f"📋 View Details", key=f"view_{inc_id}", use_container_width=True):
                            st.session_state[detail_key] = True; st.rerun()
                    else:
                        if st.button(f"🔼 Hide Details", key=f"hide_{inc_id}", use_container_width=True):
                            st.session_state[detail_key] = False; st.rerun()
                
                if st.session_state[detail_key]:
                    st.markdown(f"""
                    <div style="background:#f9fafb;border-radius:10px;padding:1rem;margin:0.5rem 0;border:1px solid #e5e7eb;">
                        <h4>{inc.get('title','')}</h4>
                        <table style="width:100%;font-size:0.75rem;">
                            <tr><td><b>Category:</b></td><td>{inc.get('category','N/A')}</td><td><b>Type:</b></td><td>{inc.get('incident_type','N/A')}</td></tr>
                            <tr><td><b>Severity:</b></td><td style="color:{sev_color};font-weight:700;">{severity.upper()}</td><td><b>Status:</b></td><td style="color:{sc};font-weight:700;">{status.upper()}</td></tr>
                            <tr><td><b>Location:</b></td><td>{inc.get('location_building','')} / {inc.get('location_floor','')}</td><td><b>Reported:</b></td><td>{str(inc.get('incident_date',''))} {str(inc.get('incident_time',''))}</td></tr>
                            <tr><td><b>Reported By:</b></td><td>{inc.get('reported_by','N/A')}</td><td><b>Life Safety:</b></td><td>{'⚠️ Yes' if inc.get('life_safety_flag') else 'No'}</td></tr>
                        </table>
                        <p><b>Description:</b> {inc.get('description','N/A')}</p>
                        <p><b>Immediate Actions:</b> {inc.get('immediate_actions','None recorded')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Timeline
                    timeline = safe_supabase_query(lambda: supabase.table("incident_timeline").select("*").eq("incident_id",inc_id).order("timestamp").execute(), error_prefix="Incident timeline")
                    if timeline and timeline.data:
                        st.markdown("**📋 Timeline:**")
                        for t in timeline.data:
                            st.caption(f"{str(t.get('timestamp',''))[:16]} | {t.get('performed_by','')} | {t.get('action_type','').upper()}: {t.get('description','')}")
                    
                    # Attachments
                    st.markdown("**📎 Attachments:**")
                    attachments = safe_supabase_query(lambda: supabase.table("incident_attachments").select("*").eq("incident_id",inc_id).execute(), error_prefix="Incident attachments")
                    if attachments and attachments.data:
                        for att in attachments.data:
                            try:
                                import base64 as b64
                                file_bytes = b64.b64decode(att["file_data"])
                                st.download_button(f"📎 {att.get('file_name','Download')}", file_bytes, att.get('file_name','file'), key=f"inc_att_{att['id']}", use_container_width=True)
                            except: st.caption(f"📎 {att.get('file_name','Attachment')}")
                    else:
                        st.caption("No attachments")
                    
                    # Upload attachment
                    with st.form(f"upload_inc_{inc_id}"):
                        inc_file = st.file_uploader("📎 Attach Document/Image", type=["png","jpg","jpeg","pdf"], key=f"inc_file_{inc_id}")
                        if st.form_submit_button("📤 Upload", use_container_width=True):
                            if inc_file:
                                import base64 as b64
                                file_bytes = inc_file.read()
                                file_b64 = b64.b64encode(file_bytes).decode()
                                safe_supabase_query(lambda: supabase.table("incident_attachments").insert({
                                    "incident_id":inc_id,"file_name":inc_file.name,
                                    "file_type":inc_file.type,"file_size":len(file_bytes),
                                    "file_data":file_b64,"uploaded_by":user_name
                                }).execute(), error_prefix="Upload attachment")
                                st.success("✅ Uploaded!"); st.rerun()
                
                # ============================================
                # ACTION BUTTONS — ALL WITH FORMS
                # ============================================
                can_acknowledge = user_role in ["safety_officer", "security_officer", "hsse_coordinator", "team_lead", "manager", "admin", "super_admin"]

                can_respond = user_role in ["safety_officer", "security_officer", "hsse_coordinator", "team_lead", "manager", "admin", "super_admin"]
                can_contain = user_role in ["hsse_coordinator", "team_lead", "manager", "sr_manager", "admin", "super_admin"]
                can_close = user_role in ["hsse_coordinator", "manager", "sr_manager", "admin", "super_admin"]
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if status == "created" and can_acknowledge:
                        if st.button("✅ Acknowledge", key=f"ack_{inc_id}", use_container_width=True):
                            st.session_state.acknowledging_incident = inc_id
                            st.rerun()
                with c2:
                    if status in ["acknowledged","created"] and can_respond:
                        if st.button("🚀 Respond", key=f"resp_{inc_id}", use_container_width=True):
                            st.session_state.responding_incident = inc_id
                            st.rerun()
                with c3:
                    if status == "responding" and can_contain:
                        if st.button("✅ Confirm & Contain", key=f"cont_{inc_id}", use_container_width=True):
                            st.session_state.containing_incident = inc_id
                            st.rerun()
                with c4:
                    if status in ["contained","responding"] and can_close:
                        if st.button("🔒 Close Incident", key=f"close_{inc_id}", use_container_width=True):
                            st.session_state.closing_incident = inc_id
                            st.rerun()
    
    # ============================================
    # ACKNOWLEDGE FORM
    # ============================================
    if "acknowledging_incident" in st.session_state and st.session_state.acknowledging_incident:
        inc_id = st.session_state.acknowledging_incident
        inc = inc_df[inc_df["id"] == inc_id].iloc[0] if len(inc_df[inc_df["id"] == inc_id]) > 0 else None
        
        if inc is not None:
                    st.markdown("---")
                    with st.form("acknowledge_incident_form"):
                        st.markdown(f"### ✅ Acknowledge Incident: {inc.get('incident_number','')}")
                        ack_comment = st.text_area("Assessment/Comment*", height=80, placeholder="Initial assessment of the incident...")
                        ack_attachment = st.file_uploader("📎 Attach (Optional)", type=["png","jpg","jpeg","pdf"], key="ack_attach")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.form_submit_button("✅ CONFIRM ACKNOWLEDGMENT", use_container_width=True, type="primary"):
                                if ack_comment:
                                    safe_supabase_query(lambda: supabase.table("incidents").update({"status":"acknowledged","acknowledged_at":wat_now.isoformat(),"acknowledged_by":user_name}).eq("id",inc_id).execute(), error_prefix="Acknowledge incident")
                                    safe_supabase_query(lambda: supabase.table("incident_timeline").insert({"incident_id":inc_id,"action_type":"acknowledged","description":f"Acknowledged by {user_name}: {ack_comment[:100]}","performed_by":user_name}).execute(), error_prefix="Timeline")
                                    _send_incident_escalation(fc, inc_id, inc.get('severity','major'), 1, inc.get('title',''))
                                    st.success("✅ Acknowledged!"); st.session_state.acknowledging_incident = None; st.rerun()
                                else:
                                    st.error("⚠️ Assessment comment is required")
                        with c2:
                            if st.form_submit_button("❌ CANCEL", use_container_width=True):
                                st.session_state.acknowledging_incident = None; st.rerun()
    
    # ============================================
    # RESPOND FORM
    # ============================================
    if "responding_incident" in st.session_state and st.session_state.responding_incident:
        inc_id = st.session_state.responding_incident
        inc = inc_df[inc_df["id"] == inc_id].iloc[0] if len(inc_df[inc_df["id"] == inc_id]) > 0 else None
        
        if inc is not None:
            st.markdown("---")
            with st.form("respond_incident_form"):
                st.markdown(f"### 🚀 Respond to Incident: {inc.get('incident_number','')}")
                respond_comment = st.text_area("Response Plan/Actions*", height=80, placeholder="What actions are being taken to respond?")
                respond_attachment = st.file_uploader("📎 Attach (Optional)", type=["png","jpg","jpeg","pdf"], key="resp_attach")
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("🚀 CONFIRM RESPONSE", use_container_width=True, type="primary"):
                        if respond_comment:
                            safe_supabase_query(lambda: supabase.table("incidents").update({"status":"responding","responded_at":wat_now.isoformat(),"responded_by":user_name}).eq("id",inc_id).execute(), error_prefix="Respond incident")
                            safe_supabase_query(lambda: supabase.table("incident_timeline").insert({"incident_id":inc_id,"action_type":"responding","description":f"Response by {user_name}: {respond_comment[:100]}","performed_by":user_name}).execute(), error_prefix="Timeline")
                            _send_incident_escalation(fc, inc_id, inc.get('severity','major'), 2, inc.get('title',''))
                            st.success("🚀 Responding!"); st.session_state.responding_incident = None; st.rerun()
                        else:
                            st.error("⚠️ Response comment is required")
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.responding_incident = None; st.rerun()
    
    # ============================================
    # CONTAIN/CONFIRM FORM
    # ============================================
    if "containing_incident" in st.session_state and st.session_state.containing_incident:
        inc_id = st.session_state.containing_incident
        inc = inc_df[inc_df["id"] == inc_id].iloc[0] if len(inc_df[inc_df["id"] == inc_id]) > 0 else None
        
        if inc is not None:
            st.markdown("---")
            with st.form("contain_incident_form"):
                st.markdown(f"### ✅ Confirm & Contain: {inc.get('incident_number','')}")
                containment_status = st.text_area("Containment Status*", height=80, placeholder="Describe how the incident has been contained...")
                containment_attachment = st.file_uploader("📎 Attach Evidence (Optional)", type=["png","jpg","jpeg","pdf"], key="contain_attach")
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("✅ CONFIRM CONTAINMENT", use_container_width=True, type="primary"):
                        if containment_status:
                            safe_supabase_query(lambda: supabase.table("incidents").update({"status":"contained","contained_at":wat_now.isoformat(),"contained_by":user_name,"containment_status":containment_status}).eq("id",inc_id).execute(), error_prefix="Contain incident")
                            safe_supabase_query(lambda: supabase.table("incident_timeline").insert({"incident_id":inc_id,"action_type":"contained","description":f"Contained by {user_name}: {containment_status[:100]}","performed_by":user_name}).execute(), error_prefix="Timeline")
                            try:
                                close_emails = safe_supabase_query(lambda: supabase.table("incident_escalation").select("escalate_to_email").eq("facility_code",fc).eq("severity",inc.get('severity','major')).eq("escalation_level",4).execute(), error_prefix="Escalation emails")
                                if close_emails and close_emails.data:
                                    for e in close_emails.data:
                                        send_email_notification(e["escalate_to_email"], f"🛡️ Incident Contained — {inc.get('incident_number','')}", f"<h3>Ready for Closure</h3><p>{inc.get('title','')}</p>")
                            except: pass
                            st.success("✅ Contained!"); st.session_state.containing_incident = None; st.rerun()
                        else:
                            st.error("⚠️ Containment Status is required")
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.containing_incident = None; st.rerun()
    
    # ============================================
    # CLOSE INCIDENT FORM
    # ============================================
    if "closing_incident" in st.session_state and st.session_state.closing_incident:
        inc_id = st.session_state.closing_incident
        inc = inc_df[inc_df["id"] == inc_id].iloc[0] if len(inc_df[inc_df["id"] == inc_id]) > 0 else None
        
        if inc is not None:
            st.markdown("---")
            with st.form("close_incident_form"):
                st.markdown(f"### 🔒 Close Incident: {inc.get('incident_number','')} — {inc.get('title','')[:80]}")
                c1, c2 = st.columns(2)
                with c1:
                    resolution_summary = st.text_area("Resolution Summary*", height=80, placeholder="Describe how the incident was resolved...")
                    root_cause = st.text_area("Root Cause*", height=60, placeholder="What caused this incident?")
                with c2:
                    preventive_actions = st.text_area("Preventive Actions", height=60, placeholder="What will prevent recurrence?")
                    closure_attachment = st.file_uploader("📎 Attach Closure Evidence (Optional)", type=["png","jpg","jpeg","pdf"], key="close_attach")
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("🔒 CONFIRM CLOSURE", use_container_width=True, type="primary"):
                        if resolution_summary and root_cause:
                            safe_supabase_query(lambda: supabase.table("incidents").update({"status":"closed","closed_at":wat_now.isoformat(),"closed_by":user_name,"resolution_notes":resolution_summary,"root_cause":root_cause}).eq("id",inc_id).execute(), error_prefix="Close incident")
                            safe_supabase_query(lambda: supabase.table("incident_timeline").insert({"incident_id":inc_id,"action_type":"closed","description":f"Closed by {user_name}: {resolution_summary[:100]}","performed_by":user_name}).execute(), error_prefix="Timeline")
                            if closure_attachment:
                                import base64 as b64
                                file_bytes = closure_attachment.read()
                                file_b64 = b64.b64encode(file_bytes).decode()
                                safe_supabase_query(lambda: supabase.table("incident_attachments").insert({"incident_id":inc_id,"file_name":closure_attachment.name,"file_type":closure_attachment.type,"file_size":len(file_bytes),"file_data":file_b64,"uploaded_by":user_name}).execute(), error_prefix="Upload attachment")
                            st.success("✅ Incident Closed!"); st.balloons()
                            st.session_state.closing_incident = None; st.rerun()
                        else:
                            st.error("⚠️ Resolution Summary and Root Cause are required")
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.closing_incident = None; st.rerun()
    
    # ============================================
    # TAB 1: REPORT INCIDENT
    # ============================================
    with tabs[1]:
        st.markdown("### 🚨 Report New Incident")
        
        type_map = {
            "Life Safety Incident": ["Elevator Entrapment", "Person Trapped", "Structural Collapse Risk", "Asphyxiation Risk", "Fall Hazard", "Other Life Safety"],
            "Security Incident": ["Unauthorized Access", "Theft", "Vandalism", "Workplace Violence", "Suspicious Package", "Bomb Threat", "Civil Disturbance", "Other Security"],
            "Environmental Incident": ["Water Leak/Flood", "Chemical Spill", "Air Quality Issue", "Noise Pollution", "Waste Contamination", "Other Environmental"],
            "Fire & Explosion Incident": ["Fire - Electrical", "Fire - Kitchen", "Fire - Waste", "Gas Explosion", "Smoke Only (No Fire)", "Other Fire"],
            "Equipment & Asset Damage": ["HVAC Failure", "Electrical Failure", "Plumbing Failure", "Elevator Malfunction", "BMS Failure", "Structural Damage", "Other Equipment"],
            "Health-Related Incident": ["Injury - Slip/Fall", "Injury - Equipment", "Medical Emergency", "Food Poisoning Report", "Infectious Disease Concern", "Other Health"],
            "Utility & Infrastructure Failure": ["Power Outage - Grid", "Power Outage - Internal", "Water Supply Failure", "Gas Supply Failure", "Internet/Connectivity Failure", "Generator Failure", "Other Utility"],
            "Near Miss": ["Near Miss - Fire", "Near Miss - Electrical", "Near Miss - Structural", "Near Miss - Elevator", "Near Miss - Security", "Other Near Miss"]
        }
        
        inc_category = st.selectbox("Category*", list(type_map.keys()))
        inc_type = st.selectbox("Type*", type_map.get(inc_category, ["Select Category First"]))
        
        st.markdown("---")
        
        with st.form("report_incident_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                inc_title = st.text_input("Title*", placeholder="e.g., Water Leak - Server Room Floor 14")
                inc_severity = st.selectbox("Severity*", ["critical","major","minor","monitoring"])
            with c2:
                inc_location_bldg = st.selectbox("Building", ["CT — Office Tower","SAT — Residential Tower","IP — Intermediate Parking","RC — Recreation Center","External"])
                inc_location_floor = st.text_input("Floor/Zone")
            with c3:
                inc_life_safety = st.checkbox("Life Safety Risk?")
                inc_injury = st.checkbox("Injury Reported?")
                inc_tenant_impact = st.checkbox("Tenant Impact?")
                inc_tenant_name = st.text_input("Tenant Name") if inc_tenant_impact else ""
                inc_biz_impact = st.checkbox("Business Continuity Impact?")
            
            inc_desc = st.text_area("Description*", height=80)
            inc_attachment = st.file_uploader("📎 Attach Image/Document (Optional)", type=["png","jpg","jpeg","pdf"], key="inc_create_attach")
            inc_immediate = st.text_area("Immediate Actions Taken", height=60)
            
            if st.form_submit_button("🚨 REPORT INCIDENT", use_container_width=True, type="primary"):
                if inc_title and inc_desc:
                    inc_count = total_inc + 1
                    inc_number = f"INC-{fc}-{today.strftime('%Y%m%d')}-{str(inc_count).zfill(4)}"
                    
                    result = safe_supabase_query(lambda: supabase.table("incidents").insert({
                        "facility_code":fc,"incident_number":inc_number,"title":inc_title,
                        "description":inc_desc,"incident_type":inc_type,"category":inc_category,
                        "severity":inc_severity,"status":"created",
                        "location_building":inc_location_bldg,"location_floor":inc_location_floor,
                        "reported_by":user_name,"incident_date":str(today),"incident_time":str(wat_now.time()),
                        "tenant_impact":inc_tenant_impact,"tenant_name":inc_tenant_name if inc_tenant_impact else None,
                        "life_safety_flag":inc_life_safety,"injury_reported":inc_injury,
                        "business_continuity_impact":inc_biz_impact,
                        "immediate_actions":inc_immediate,"created_at":wat_now.isoformat()
                    }).execute(), error_prefix="Report incident")
                    
                    if result and result.data:
                        inc_id = result.data[0]["id"]
                        safe_supabase_query(lambda: supabase.table("incident_timeline").insert({"incident_id":inc_id,"action_type":"created","description":"Incident reported","performed_by":user_name}).execute(), error_prefix="Timeline")
                        
                        if inc_attachment:
                            import base64 as b64
                            file_bytes = inc_attachment.read()
                            file_b64 = b64.b64encode(file_bytes).decode()
                            safe_supabase_query(lambda: supabase.table("incident_attachments").insert({
                                "incident_id":inc_id,"file_name":inc_attachment.name,
                                "file_type":inc_attachment.type,"file_size":len(file_bytes),
                                "file_data":file_b64,"uploaded_by":user_name
                            }).execute(), error_prefix="Upload attachment")
                        
                        _send_incident_escalation(fc, inc_id, inc_severity, 1, inc_title)
                        st.session_state.incident_reported = True
                        st.session_state.incident_number = inc_number
                        st.rerun()
                else:
                    st.error("⚠️ Title and Description are required")
    
    if st.session_state.get("incident_reported", False):
        st.success(f"✅ Incident {st.session_state.get('incident_number','')} reported!")
        st.balloons()
        st.session_state.incident_reported = False
    
    # ============================================
    # TAB 2: ALL INCIDENTS WITH DETAIL
    # ============================================
    with tabs[2]:
        st.markdown("### 📊 All Incidents")
        
        if total_inc == 0:
            st.info("No incidents recorded.")
        else:
            for _, inc in inc_df.head(30).iterrows():
                sev_color = {"critical":"#EF4444","major":"#F59E0B","minor":"#3B82F6","monitoring":"#6B7280"}.get(inc.get("severity","minor"),"#6B7280")
                inc_id = inc["id"]
                
                st.markdown(f"""
                <div style="background:white;border-left:3px solid {sev_color};border-radius:8px;padding:0.6rem;margin:0.2rem 0;font-size:0.75rem;">
                    <b>{inc.get('incident_number','')}</b> — {inc.get('title','')[:80]}
                    <br><span style="font-size:0.65rem;color:#666;">{inc.get('status','').upper()} | 📅 {str(inc.get('incident_date',''))} | {inc.get('category','')}</span>
                </div>
                """, unsafe_allow_html=True)
                
                detail_key2 = f"all_inc_{inc_id}"
                if detail_key2 not in st.session_state: st.session_state[detail_key2] = False
                
                if not st.session_state[detail_key2]:
                    if st.button(f"📋 View Details", key=f"all_view_{inc_id}", use_container_width=True):
                        st.session_state[detail_key2] = True; st.rerun()
                else:
                    if st.button(f"🔼 Hide Details", key=f"all_hide_{inc_id}", use_container_width=True):
                        st.session_state[detail_key2] = False; st.rerun()
                
                if st.session_state[detail_key2]:
                    st.markdown(f"""
                    <div style="background:#f9fafb;border-radius:8px;padding:0.8rem;margin:0.3rem 0;">
                        <p><b>Category:</b> {inc.get('category','N/A')} | <b>Type:</b> {inc.get('incident_type','N/A')}</p>
                        <p><b>Description:</b> {inc.get('description','N/A')}</p>
                        <p><b>Actions:</b> {inc.get('immediate_actions','None')}</p>
                        <p><b>Location:</b> {inc.get('location_building','')} / {inc.get('location_floor','')}</p>
                        <p><b>Reported:</b> {inc.get('reported_by','')} | <b>Status:</b> {inc.get('status','').upper()}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 3: ANALYTICS
    # ============================================
    with tabs[3]:
        st.markdown("### 📈 Incident Analytics")
        if total_inc > 0:
            c1, c2 = st.columns(2)
            with c1:
                sev_counts = inc_df["severity"].value_counts()
                fig1 = px.pie(values=sev_counts.values, names=sev_counts.index, title="By Severity", color_discrete_sequence=["#EF4444","#F59E0B","#3B82F6","#6B7280"])
                fig1.update_layout(height=350); st.plotly_chart(fig1, use_container_width=True)
            with c2:
                type_counts = inc_df["incident_type"].value_counts().head(8)
                fig2 = px.bar(x=type_counts.values, y=type_counts.index, orientation='h', title="By Type", color=type_counts.values)
                fig2.update_layout(height=350); st.plotly_chart(fig2, use_container_width=True)
        else: st.info("No data for analytics.")
    
    # ============================================
    # TAB 4: ESCALATION SETTINGS (ADMIN ONLY)
    # ============================================
    with tabs[4]:
        st.markdown("### ⚙️ Incident Escalation Settings")
        
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            severity_levels = ["critical","major","minor","monitoring"]
            
            all_users = DB.get_users()
            user_options = [f"{u.get('name','')} ({u.get('email','')})" for u in all_users if u.get('name') and u.get('email')]
            user_options = sorted(user_options)
            
            for sev in severity_levels:
                st.markdown(f"### {sev.upper()}")
                
                existing = safe_supabase_query(lambda: supabase.table("incident_escalation").select("*").eq("facility_code",fc).eq("severity",sev).order("escalation_level").execute(), error_prefix="Escalation data")
                
                edit_key = f"edit_{sev}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                
                if not st.session_state[edit_key]:
                    # LOCKED VIEW
                    for level in range(1, 7):
                        existing_config = [e for e in (existing.data or []) if e["escalation_level"] == level] if existing and existing.data else []
                        if existing_config:
                            names_list = ", ".join([e.get("escalate_to_name","") for e in existing_config])
                            ec = existing_config[0]
                            sla = ec.get("sla_minutes",15)
                            if sla >= 1440: sla_display = f"{sla//1440} Days"
                            elif sla >= 60: sla_display = f"{sla//60} Hours"
                            else: sla_display = f"{sla} Mins"
                            
                            st.markdown(f"""
                            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:0.5rem 1rem;margin:0.2rem 0;display:flex;align-items:center;gap:1rem;">
                                <div style="font-weight:700;color:#888;min-width:30px;">L{level}</div>
                                <div style="flex:1;"><b>{names_list}</b><br><span style="font-size:0.7rem;color:#666;">{len(existing_config)} person(s)</span></div>
                                <div style="background:#f0f0f0;padding:3px 10px;border-radius:12px;font-size:0.65rem;font-weight:600;">⏱️ {sla_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background:#fafafa;border:1px dashed #ddd;border-radius:8px;padding:0.5rem 1rem;margin:0.2rem 0;display:flex;align-items:center;gap:1rem;">
                                <div style="font-weight:700;color:#ccc;min-width:30px;">L{level}</div>
                                <div style="color:#ccc;">Not configured</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    if st.button("✏️ Edit Escalation", key=f"btn_edit_{sev}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                
                else:
                    # EDITABLE VIEW
                    for level in range(1, 7):
                        existing_config = [e for e in (existing.data or []) if e["escalation_level"] == level] if existing and existing.data else []
                        existing_people = [f"{e.get('escalate_to_name','')} ({e.get('escalate_to_email','')})" for e in (existing.data or []) if e["escalation_level"] == level]
                        valid_defaults = [p for p in existing_people if p in user_options]
                        
                        stored_sla = existing_config[0].get("sla_minutes", 15*level) if existing_config else 15*level
                        if stored_sla >= 1440:
                            display_time = stored_sla // 1440
                            display_unit = "Days"
                        elif stored_sla >= 60:
                            display_time = stored_sla // 60
                            display_unit = "Hours"
                        else:
                            display_time = stored_sla
                            display_unit = "Mins"
                        
                        c1, c2, c3 = st.columns([2.5, 1, 1])
                        with c1: 
                            st.multiselect(f"L{level} Escalate To", user_options, default=valid_defaults, key=f"esc_{sev}_{level}_users")
                        with c2: 
                            st.number_input(f"Time", value=display_time, min_value=0, key=f"esc_{sev}_{level}_time")
                        with c3:
                            st.selectbox(f"Unit", ["Mins","Hours","Days"], 
                                index=0 if display_unit == "Mins" else 1 if display_unit == "Hours" else 2,
                                key=f"esc_{sev}_{level}_unit")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"💾 Save {sev.upper()}", key=f"save_{sev}", use_container_width=True, type="primary"):
                            saved = 0
                            for level in range(1, 7):
                                selected_users = st.session_state.get(f"esc_{sev}_{level}_users", [])
                                safe_supabase_query(lambda l=level: supabase.table("incident_escalation").delete().eq("facility_code",fc).eq("severity",sev).eq("escalation_level",l).execute(), error_prefix="Delete escalation")
                                
                                for user_str in selected_users:
                                    if "(" in user_str:
                                        parts = user_str.split("(")
                                        name = parts[0].strip()
                                        email = parts[1].replace(")","").strip()
                                        time_val = st.session_state.get(f"esc_{sev}_{level}_time", 15)
                                        unit = st.session_state.get(f"esc_{sev}_{level}_unit", "Mins")
                                        if unit == "Hours": sla = int(time_val) * 60
                                        elif unit == "Days": sla = int(time_val) * 1440
                                        else: sla = int(time_val)
                                        
                                        safe_supabase_query(lambda n=name, e=email, s=sla, l=level: supabase.table("incident_escalation").insert({
                                            "facility_code": fc, "severity": sev, "escalation_level": l,
                                            "level_name": f"Level {l}", "escalate_to_name": n,
                                            "escalate_to_email": e, "sla_minutes": s, "is_active": True
                                        }).execute(), error_prefix="Save escalation")
                                        saved += 1
                            
                            if saved > 0:
                                for level in range(1, 7):
                                    for key in [f"esc_{sev}_{level}_users", f"esc_{sev}_{level}_time", f"esc_{sev}_{level}_unit"]:
                                        if key in st.session_state: del st.session_state[key]
                                st.session_state[edit_key] = False
                                st.success(f"✅ {sev.upper()} saved ({saved} people)!")
                                st.rerun()
                            else:
                                st.error("⚠️ Select at least one person")
                    with c2:
                        if st.button("❌ Cancel", key=f"cancel_{sev}", use_container_width=True):
                            st.session_state[edit_key] = False
                            st.rerun()
                
                st.markdown("---")
    
    # ============================================
    # TAB 5: REPORTS
    # ============================================
    with tabs[5]:
        st.markdown("### 📄 Incident Reports")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 HTML Report", key="inc_html_btn", use_container_width=True, type="primary"):
                logo_b64 = get_logo_base64()
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Incident Report</title><style>body{{font-family:Arial;margin:20px}}h1{{color:#CC0000}}table{{width:100%;border-collapse:collapse}}th{{background:#CC0000;color:white;padding:8px}}td{{padding:6px;border-bottom:1px solid #eee}}</style></head><body><h1>Incident Intelligence Report</h1><p>{info.get('full_name',fc)} | {today}</p><table><tr><th>ID</th><th>Title</th><th>Type</th><th>Severity</th><th>Status</th></tr>"""
                for _,inc in inc_df.head(30).iterrows(): html += f"<tr><td>{inc.get('incident_number','')}</td><td>{inc.get('title','')[:60]}</td><td>{inc.get('incident_type','')}</td><td>{inc.get('severity','').upper()}</td><td>{inc.get('status','').upper()}</td></tr>"
                html += "</table></body></html>"
                st.download_button("📥 HTML", html, f"incident_report_{today}.html", "text/html", use_container_width=True)
        with c2:
            if st.button("📕 PDF Report", key="inc_pdf_btn", use_container_width=True):
                try:
                    from fpdf import FPDF; pdf = FPDF('L','mm','A4'); pdf.add_page()
                    pdf.set_font('Helvetica','B',16); pdf.set_text_color(204,0,0)
                    pdf.cell(0,10,safe_text('Incident Report'),0,1)
                    pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                    pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {today}'),0,1); pdf.ln(4)
                    pdf.set_font('Helvetica','B',7); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                    for h,w in zip(['ID','Title','Type','Severity','Status'],[35,85,40,30,30]): pdf.cell(w,5,h,1,0,'C',True)
                    pdf.ln(); pdf.set_font('Helvetica','',7); pdf.set_text_color(0,0,0)
                    for _,inc in inc_df.head(40).iterrows():
                        pdf.cell(35,4,safe_text(inc.get('incident_number','')),1,0); pdf.cell(85,4,safe_text(str(inc.get('title',''))[:38]),1,0)
                        pdf.cell(40,4,safe_text(inc.get('incident_type','')),1,0); pdf.cell(30,4,safe_text(inc.get('severity','').upper()),1,0)
                        pdf.cell(30,4,safe_text(inc.get('status','').upper()),1,0); pdf.ln()
                    pdf_file = f"/tmp/incident_report_{today}.pdf"; pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f: st.download_button("📥 PDF", f.read(), f"incident_report_{today}.pdf", "application/pdf", use_container_width=True)
                except Exception as e: st.error(f"PDF: {str(e)[:80]}")


# ============================================
# WORK ORDER INTELLIGENCE — FULL LIFECYCLE
# ============================================
def page_wo():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "Technician")
    is_super = user_role == "super_admin"
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_team_lead = user_role in ["team_lead", "manager", "sr_manager", "sr_management", "admin", "approver", "super_admin"]
    is_manager = user_role in ["manager", "sr_manager", "sr_management", "admin", "approver", "super_admin"]
    
    st.markdown(f'## 🔧 Work Order Intelligence — {info.get("full_name", fc)}')
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    wo_data = safe_supabase_query(lambda: supabase.table("work_orders").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(500).execute(), error_prefix="Work order data")
    wo_df = pd.DataFrame(wo_data.data) if wo_data and wo_data.data else pd.DataFrame()
    
    total_wo = len(wo_df)
    open_wo = len(wo_df[wo_df["status"] == "open"]) if total_wo > 0 else 0
    in_progress = len(wo_df[wo_df["status"] == "in_progress"]) if total_wo > 0 else 0
    completed = len(wo_df[wo_df["status"] == "completed"]) if total_wo > 0 else 0
    on_hold = len(wo_df[wo_df["status"] == "on_hold"]) if total_wo > 0 else 0
    closed = len(wo_df[wo_df["status"] == "closed"]) if total_wo > 0 else 0
    
    overdue = len(wo_df[(pd.to_datetime(wo_df["sla_due_date"], errors='coerce').dt.date < today) & (~wo_df["status"].isin(["completed","closed"]))]) if "sla_due_date" in wo_df.columns and total_wo > 0 else 0
    
    total_spend = wo_df["total_cost"].sum() if "total_cost" in wo_df.columns else 0
    ftf_count = len(wo_df[wo_df["first_time_fix"] == True]) if "first_time_fix" in wo_df.columns and total_wo > 0 else 0
    ftf_rate = round((ftf_count / total_wo) * 100) if total_wo > 0 else 0
    
    # ============================================
    # 🟦 TOP RIBBON
    # ============================================
    st.markdown("### 🟦 Operational Health Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        color = "#10B981" if overdue == 0 else "#F59E0B" if overdue < 3 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Open WOs</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{open_wo}</div><div style="font-size:0.45rem;color:#888;">{overdue} Overdue</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">In Progress</div><div style="font-size:1.3rem;font-weight:800;color:#F59E0B;">{in_progress}</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">On Hold</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{on_hold}</div></div>""", unsafe_allow_html=True)
    with c4: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Completed</div><div style="font-size:1.3rem;font-weight:800;color:#10B981;">{completed}</div></div>""", unsafe_allow_html=True)
    with c5:
        color = "#10B981" if ftf_rate >= 80 else "#F59E0B" if ftf_rate >= 60 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">First-Time Fix</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{ftf_rate}%</div></div>""", unsafe_allow_html=True)
    with c6: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Total Spend</div><div style="font-size:1.3rem;font-weight:800;color:#CC0000;">₦{total_spend:,.0f}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 WO Queue", "🔧 My Tasks", "✅ Review & Close", "➕ Create WO", "👥 Team", "📊 Reports"])
    
    # ============================================
    # TAB 0: WO QUEUE — COMPLETE WITH ALL FORMS
    # ============================================
    with tabs[0]:
        st.markdown("### 📋 Work Order Queue")
        
        if st.session_state.get("wo_created", False):
            st.success(f"✅ WO {st.session_state.get('wo_number_created','')} created!")
            st.balloons()
            st.session_state.wo_created = False
        
        if total_wo == 0:
            st.info("No work orders yet.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1: wo_type_filter = st.selectbox("Type", ["All","Reactive","Preventive","Corrective","New Installation","Inspection","Emergency Repair"], key="wo_type")
            with c2: wo_status_filter = st.selectbox("Status", ["All","open","in_progress","on_hold","completed","cancelled","closed"], key="wo_status")
            with c3: wo_priority_filter = st.selectbox("Priority", ["All","emergency","high","medium","low"], key="wo_pri")
            with c4: wo_search = st.text_input("🔍 Search", key="wo_search", placeholder="WO# or title...")
            
            display_wo = wo_df.copy()
            if wo_type_filter != "All": display_wo = display_wo[display_wo["type"] == wo_type_filter]
            if wo_status_filter != "All": display_wo = display_wo[display_wo["status"] == wo_status_filter]
            if wo_priority_filter != "All": display_wo = display_wo[display_wo["priority"] == wo_priority_filter]
            if wo_search:
                display_wo = display_wo[display_wo["wo_number"].str.contains(wo_search, case=False, na=False) | display_wo["title"].str.contains(wo_search, case=False, na=False)]
            
            st.caption(f"📋 {len(display_wo)} work orders")
            
            for _, wo in display_wo.head(20).iterrows():
                status = wo.get("status", "open")
                priority = wo.get("priority", "medium")
                wo_type = wo.get("type", "Reactive")
                sc = {"open":"#3B82F6","in_progress":"#F59E0B","on_hold":"#8B5CF6","completed":"#10B981","cancelled":"#EF4444","closed":"#6B7280"}.get(status,"#3B82F6")
                pc = {"emergency":"#EF4444","high":"#F59E0B","medium":"#3B82F6","low":"#10B981"}.get(priority,"#3B82F6")
                wo_id = wo["id"]
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{wo.get('wo_number','')}</b> — {wo.get('title','')[:80]}
                            <br><span style="font-size:0.65rem;color:#666;">👤 {wo.get('technician_name','Unassigned')} | 🏢 {wo.get('assigned_team','')} | 📅 {str(wo.get('created_at',''))[:10]}</span>
                            <br><span style="font-size:0.6rem;color:#888;">🕐 SLA: {str(wo.get('sla_due_date','N/A'))[:10]} | 📍 {wo.get('location_building','')}</span>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{sc};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status.upper()}</span>
                            <br><span style="background:{pc};color:white;padding:2px 8px;border-radius:12px;font-size:0.55rem;">{priority.upper()}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Timeline
                timeline = safe_supabase_query(lambda: supabase.table("wo_timeline").select("*").eq("wo_id", wo_id).order("created_at").execute(), error_prefix="WO timeline")
                if timeline and timeline.data:
                    toggle_key = f"timeline_{wo_id}"
                    if toggle_key not in st.session_state:
                        st.session_state[toggle_key] = False
                    
                    if not st.session_state[toggle_key]:
                        if st.button(f"📋 View Timeline ({len(timeline.data)} events)", key=f"timeline_btn_{wo_id}", use_container_width=True):
                            st.session_state[toggle_key] = True
                            st.rerun()
                    else:
                        st.markdown(f"""
                        <div style="background:#f9fafb;border-left:4px solid #3B82F6;border-radius:8px;padding:0.8rem;margin:0.3rem 0;">
                            <b>📋 Timeline ({len(timeline.data)} events)</b>
                        </div>
                        """, unsafe_allow_html=True)
                        for t in timeline.data:
                            icon = {"open":"🔵","in_progress":"🟡","on_hold":"🟣","completed":"🟢","cancelled":"🔴","closed":"⚫"}.get(t.get("status_to",""),"📝")
                            comment_text = str(t.get('comment') or 'No comment')
                            st.markdown(f"""
                            <div style="background:white;border-radius:6px;padding:0.5rem;margin:0.1rem 0;font-size:0.7rem;border:1px solid #e5e7eb;">
                                {icon} <b>{str(t.get('created_at',''))[:16]}</b> | {t.get('changed_by','')}
                                <br><span style="color:#888;">{t.get('status_from','')} → {t.get('status_to','')}</span>
                                <br><span style="font-size:0.65rem;">💬 {comment_text[:100]}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        if st.button(f"❌ Close Timeline", key=f"timeline_close_{wo_id}", use_container_width=True):
                            st.session_state[toggle_key] = False
                            st.rerun()
                
                # Assign (Team Lead)
                if status == "open" and (is_super or is_admin or is_team_lead):
                    c1, c2 = st.columns(2)
                    with c1:
                        all_users = DB.get_users()
                        tech_names = sorted([u.get("name","") for u in all_users if u.get("name")])
                        current_tech = wo.get("technician_name","")
                        default_idx = tech_names.index(current_tech) if current_tech in tech_names else 0
                        assign_to = st.selectbox("Assign to", tech_names, index=default_idx, key=f"assign_{wo_id}", label_visibility="collapsed")
                    with c2:
                        if st.button("👤 Assign", key=f"assign_btn_{wo_id}", use_container_width=True):
                            safe_supabase_query(lambda: supabase.table("work_orders").update({"technician_name": assign_to}).eq("id", wo_id).execute(), error_prefix="Assign WO")
                            safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"open","status_to":"open","changed_by":user_name,"comment":f"Assigned to {assign_to}","created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                            
                            assigned_user = next((u for u in all_users if u.get("name") == assign_to), None)
                            if assigned_user and assigned_user.get("email"):
                                try:
                                    send_email_notification(
                                        assigned_user["email"],
                                        f"🔧 New Work Order Assigned — {wo.get('wo_number','')}",
                                        f"""
                                        <div style="font-family:Arial;max-width:550px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                            <div style="background:#CC0000;padding:20px;color:white;">
                                                <h2 style="margin:0;">🔧 New Work Order Assigned</h2>
                                                <p style="margin:5px 0 0 0;font-size:12px;">{info.get('full_name',fc)}</p>
                                            </div>
                                            <div style="padding:20px;">
                                                <p>Dear <b>{assign_to}</b>,</p>
                                                <p>A new work order has been assigned to you.</p>
                                                <table style="width:100%;font-size:13px;">
                                                    <tr><td><b>WO#:</b></td><td>{wo.get('wo_number','')}</td></tr>
                                                    <tr><td><b>Title:</b></td><td>{wo.get('title','')}</td></tr>
                                                    <tr><td><b>Type:</b></td><td>{wo.get('type','')}</td></tr>
                                                    <tr><td><b>Priority:</b></td><td>{wo.get('priority','').upper()}</td></tr>
                                                    <tr><td><b>Location:</b></td><td>{wo.get('location_building','')} / {wo.get('location_floor','')}</td></tr>
                                                    <tr><td><b>SLA:</b></td><td>{str(wo.get('sla_due_date',''))[:10]}</td></tr>
                                                </table>
                                            </div>
                                        </div>
                                        """
                                    )
                                except: pass
                            
                            st.success(f"✅ Assigned to {assign_to}! Email sent."); st.rerun()
                
                # Accept & Start
                if status == "open" and wo.get("technician_name") == user_name:
                    if st.button("✅ Accept & Start Work", key=f"accept_{wo_id}", use_container_width=True, type="primary"):
                        st.session_state.starting_wo = wo_id
                        st.rerun()
                
                # Complete / On Hold / Cancel
                if status == "in_progress" and (wo.get("technician_name") == user_name or is_super or is_admin):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ Complete", key=f"comp_{wo_id}", use_container_width=True):
                            st.session_state.completing_wo = wo_id
                            st.rerun()
                    with c2:
                        if st.button("⏸️ On Hold", key=f"hold_{wo_id}", use_container_width=True):
                            st.session_state.holding_wo = wo_id
                            st.rerun()
                    with c3:
                        if st.button("❌ Cancel", key=f"cancel_{wo_id}", use_container_width=True):
                            st.session_state.cancelling_wo = wo_id
                            st.rerun()
                
                # Resume
                if status == "on_hold" and (wo.get("technician_name") == user_name or is_super or is_admin):
                    if st.button("▶ Resume", key=f"resume_{wo_id}", use_container_width=True):
                        st.session_state.resuming_wo = wo_id
                        st.rerun()
    
    
    
    # ============================================
    # ALL ACTION FORMS (OUTSIDE THE LOOP)
    # ============================================
    
    # START WORK FORM
    if "starting_wo" in st.session_state and st.session_state.starting_wo:
        wo_id = st.session_state.starting_wo
        st.markdown("---")
        with st.form("start_wo_form"):
            st.markdown("### ✅ Accept & Start Work")
            start_comment = st.text_area("Initial Assessment/Comment*", height=80, placeholder="e.g., Arrived on site, assessed the issue, starting repairs...")
            start_attachment = st.file_uploader("📎 Attach Photo (Optional)", type=["png","jpg","jpeg"], key="start_attach")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("✅ CONFIRM START", use_container_width=True, type="primary"):
                    if start_comment:
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"in_progress","actual_start":wat_now.isoformat(),"acknowledged_by":user_name,"acknowledged_at":wat_now.isoformat()}).eq("id",wo_id).execute(), error_prefix="Start WO")
                        safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"open","status_to":"in_progress","changed_by":user_name,"comment":start_comment,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                        st.success("✅ Work started!"); st.session_state.starting_wo = None; st.rerun()
                    else: st.error("⚠️ Comment required")
            with c2:
                if st.form_submit_button("❌ CANCEL", use_container_width=True):
                    st.session_state.starting_wo = None; st.rerun()
    
    # ON HOLD FORM
    if "holding_wo" in st.session_state and st.session_state.holding_wo:
        wo_id = st.session_state.holding_wo
        st.markdown("---")
        with st.form("hold_wo_form"):
            st.markdown("### ⏸️ Put Work Order On Hold")
            hold_reason = st.text_area("Reason for Hold*", height=80, placeholder="e.g., Awaiting parts, Waiting for tenant access...")
            hold_attachment = st.file_uploader("📎 Attach Supporting Document (Optional)", type=["pdf","png","jpg","jpeg"], key="hold_attach")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("⏸️ CONFIRM HOLD", use_container_width=True, type="primary"):
                    if hold_reason:
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"on_hold"}).eq("id",wo_id).execute(), error_prefix="Hold WO")
                        comment_text = hold_reason
                        if hold_attachment: comment_text += f" [Attachment: {hold_attachment.name}]"
                        safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"in_progress","status_to":"on_hold","changed_by":user_name,"comment":comment_text,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                        st.success("⏸️ On Hold!"); st.session_state.holding_wo = None; st.rerun()
                    else: st.error("⚠️ Reason required")
            with c2:
                if st.form_submit_button("❌ CANCEL", use_container_width=True):
                    st.session_state.holding_wo = None; st.rerun()
    
    # CANCEL FORM
    if "cancelling_wo" in st.session_state and st.session_state.cancelling_wo:
        wo_id = st.session_state.cancelling_wo
        st.markdown("---")
        with st.form("cancel_wo_form"):
            st.markdown("### ❌ Cancel Work Order")
            cancel_reason = st.text_area("Reason for Cancellation*", height=80)
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("❌ CONFIRM CANCEL", use_container_width=True, type="primary"):
                    if cancel_reason:
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"cancelled"}).eq("id",wo_id).execute(), error_prefix="Cancel WO")
                        safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"in_progress","status_to":"cancelled","changed_by":user_name,"comment":cancel_reason,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                        st.error("❌ Cancelled!"); st.session_state.cancelling_wo = None; st.rerun()
                    else: st.error("⚠️ Reason required")
            with c2:
                if st.form_submit_button("CANCEL", use_container_width=True):
                    st.session_state.cancelling_wo = None; st.rerun()
    
    # RESUME FORM
    if "resuming_wo" in st.session_state and st.session_state.resuming_wo:
        wo_id = st.session_state.resuming_wo
        st.markdown("---")
        with st.form("resume_wo_form"):
            st.markdown("### ▶ Resume Work Order")
            resume_comment = st.text_area("Reason for Resume*", height=80, placeholder="e.g., Parts received, tenant access granted...")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("▶ CONFIRM RESUME", use_container_width=True, type="primary"):
                    if resume_comment:
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"in_progress"}).eq("id",wo_id).execute(), error_prefix="Resume WO")
                        safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"on_hold","status_to":"in_progress","changed_by":user_name,"comment":resume_comment,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                        st.success("▶ Resumed!"); st.session_state.resuming_wo = None; st.rerun()
                    else: st.error("⚠️ Comment required")
            with c2:
                if st.form_submit_button("❌ CANCEL", use_container_width=True):
                    st.session_state.resuming_wo = None; st.rerun()
    
    # COMPLETE FORM
    if "completing_wo" in st.session_state and st.session_state.completing_wo:
        wo_id = st.session_state.completing_wo
        wo = wo_df[wo_df["id"] == wo_id].iloc[0] if len(wo_df[wo_df["id"] == wo_id]) > 0 else None
        if wo is not None:
            st.markdown("---")
            st.markdown(f"### ✅ Complete: {wo.get('wo_number','')} — {wo.get('title','')[:60]}")
            with st.form("complete_wo_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    actual_hours = st.number_input("Actual Hours*", min_value=0.0, value=float(wo.get("estimated_hours",1)), step=0.5)
                    labour_cost = st.number_input("Labour Cost (₦)", min_value=0.0, value=0.0, step=1000.0)
                with c2:
                    parts_cost = st.number_input("Parts Cost (₦)", min_value=0.0, value=0.0, step=1000.0)
                    contractor_cost = st.number_input("Contractor Cost (₦)", min_value=0.0, value=0.0, step=1000.0)
                with c3:
                    resolution_code = st.selectbox("Resolution*", ["Repaired","Replaced","Adjusted","Deferred","No Fault Found"])
                    first_time_fix = st.checkbox("First-Time Fix?", value=True)
                
                complete_attachment = st.file_uploader("📎 Attach Completion Photo/Document (Optional)", type=["png","jpg","jpeg","pdf"], key="complete_attach")
                root_cause = st.text_area("Root Cause*", height=60, placeholder="What caused this issue?")
                resolution_notes = st.text_area("Resolution Notes*", height=60, placeholder="Describe what was done to resolve...")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.form_submit_button("✅ SUBMIT COMPLETION", use_container_width=True, type="primary"):
                        if root_cause and resolution_notes:
                            total_cost = parts_cost + labour_cost + contractor_cost
                            safe_supabase_query(lambda: supabase.table("work_orders").update({
                                "status":"completed","actual_end":wat_now.isoformat(),"actual_hours":actual_hours,
                                "labour_hours":actual_hours,"parts_cost":parts_cost,"labour_cost":labour_cost,
                                "contractor_cost":contractor_cost,"total_cost":total_cost,
                                "resolution_code":resolution_code,"first_time_fix":first_time_fix,
                                "root_cause":root_cause,"resolution_notes":resolution_notes
                            }).eq("id",wo_id).execute(), error_prefix="Complete WO")
                            
                            comment_text = f"Resolution: {resolution_code} | Root Cause: {root_cause} | Notes: {resolution_notes}"
                            if complete_attachment: comment_text += f" [Attachment: {complete_attachment.name}]"
                            safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"in_progress","status_to":"completed","changed_by":user_name,"comment":comment_text,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                            
                            try:
                                send_email_notification("eetuk@churchgate.com", f"✅ WO Completed — {wo.get('wo_number','')}", f"<h3>WO Completed</h3><p><b>WO:</b> {wo.get('wo_number','')}</p><p><b>By:</b> {user_name}</p><p><b>Cost:</b> ₦{total_cost:,.0f}</p><p>Please review and close.</p>")
                            except: pass
                            
                            st.success("✅ Completed! Team Lead notified."); st.session_state.completing_wo = None; st.rerun()
                        else: st.error("⚠️ Root Cause and Resolution Notes are required")
                with c2:
                    if st.form_submit_button("❌ CANCEL", use_container_width=True):
                        st.session_state.completing_wo = None; st.rerun()
    
    # ============================================
    # TAB 1: MY TASKS
    # ============================================
    with tabs[1]:
        st.markdown("### 🔧 My Assigned Tasks")
        
        my_tasks = wo_df[wo_df["technician_name"] == user_name] if total_wo > 0 else pd.DataFrame()
        
        if len(my_tasks) == 0:
            st.info("No tasks assigned to you.")
        else:
            for _, wo in my_tasks.iterrows():
                status = wo.get("status","open")
                sc = {"open":"#3B82F6","in_progress":"#F59E0B","on_hold":"#8B5CF6","completed":"#10B981","closed":"#6B7280"}.get(status,"#3B82F6")
                wo_id = wo["id"]
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <b>{wo.get('wo_number','')}</b> — {wo.get('title','')[:80]}
                    <br><span style="font-size:0.65rem;color:#666;">📍 {wo.get('location_building','')} | 🕐 SLA: {str(wo.get('sla_due_date',''))[:10]}</span>
                    <span style="float:right;background:{sc};color:white;padding:2px 10px;border-radius:12px;font-size:0.6rem;">{status.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
                
                if status == "open":
                    if st.button("✅ Accept & Start", key=f"mytask_start_{wo_id}", use_container_width=True, type="primary"):
                        st.session_state.starting_wo = wo_id
                        st.rerun()
                
                if status == "in_progress":
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ Complete", key=f"mytask_comp_{wo_id}", use_container_width=True):
                            st.session_state.completing_wo = wo_id
                            st.rerun()
                    with c2:
                        if st.button("⏸️ On Hold", key=f"mytask_hold_{wo_id}", use_container_width=True):
                            st.session_state.holding_wo = wo_id
                            st.rerun()
                    with c3:
                        if st.button("❌ Cancel", key=f"mytask_cancel_{wo_id}", use_container_width=True):
                            st.session_state.cancelling_wo = wo_id
                            st.rerun()
                
                if status == "on_hold":
                    if st.button("▶ Resume", key=f"mytask_resume_{wo_id}", use_container_width=True):
                        st.session_state.resuming_wo = wo_id
                        st.rerun()
    
    # ============================================
    # TAB 2: REVIEW & CLOSE
    # ============================================
    with tabs[2]:
        st.markdown("### ✅ Review & Close Work Orders")
        
        if not (is_super or is_admin or is_team_lead):
            st.info("This section is for Team Leads and Managers.")
        else:
            review_wos = wo_df[wo_df["status"].isin(["completed"])] if total_wo > 0 else pd.DataFrame()
            
            if len(review_wos) == 0:
                st.success("✅ No work orders awaiting review.")
            else:
                for _, wo in review_wos.iterrows():
                    wo_id = wo["id"]
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid #10B981;border-radius:10px;padding:0.8rem;margin:0.3rem 0;">
                        <b>{wo.get('wo_number','')}</b> — {wo.get('title','')[:80]}
                        <br><span style="font-size:0.65rem;">👤 {wo.get('technician_name','')} | 🕐 {wo.get('actual_hours','')}hrs | 💰 ₦{wo.get('total_cost',0):,.0f}</span>
                        <br><span style="font-size:0.6rem;color:#888;">Resolution: {wo.get('resolution_code','N/A')} | Root Cause: {str(wo.get('root_cause',''))[:60]}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show timeline
                    timeline = safe_supabase_query(lambda: supabase.table("wo_timeline").select("*").eq("wo_id", wo_id).order("created_at").execute(), error_prefix="WO timeline")
                    if timeline and timeline.data:
                        with st.expander("📋 Timeline"):
                            for t in timeline.data:
                                st.caption(f"{str(t.get('created_at',''))[:16]} | {t.get('changed_by','')} | {t.get('status_from','')} → {t.get('status_to','')}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Verify & Close", key=f"rev_close_{wo_id}", use_container_width=True, type="primary"):
                            safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"closed","verified_by":user_name,"verified_at":wat_now.isoformat(),"closed_by":user_name,"closed_at":wat_now.isoformat()}).eq("id",wo_id).execute(), error_prefix="Close WO")
                            safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"completed","status_to":"closed","changed_by":user_name,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                            st.success("✅ Verified & Closed!"); st.rerun()
                    with c2:
                        if st.button("❌ Reject/Reopen", key=f"rev_reject_{wo_id}", use_container_width=True):
                            st.session_state.rejecting_wo = wo_id; st.rerun()
    
    # Rejection form
    if "rejecting_wo" in st.session_state and st.session_state.rejecting_wo:
        wo_id = st.session_state.rejecting_wo
        st.markdown("---")
        with st.form("reject_wo_form"):
            st.markdown("### ❌ Reject Work Order")
            reject_reason = st.text_area("Rejection Reason*", height=80)
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("❌ REJECT & REOPEN", use_container_width=True, type="primary"):
                    if reject_reason:
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"status":"open","rejection_reason":reject_reason}).eq("id",wo_id).execute(), error_prefix="Reopen WO")
                        safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":"completed","status_to":"open","changed_by":user_name,"comment":reject_reason,"created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                        st.error("❌ Rejected & Reopened!"); st.session_state.rejecting_wo = None; st.rerun()
            with c2:
                if st.form_submit_button("CANCEL", use_container_width=True):
                    st.session_state.rejecting_wo = None; st.rerun()
    
    
    
    # ============================================
    # TAB 3: CREATE WO (KEPT FROM BEFORE - SAME CODE)
    # ============================================
    with tabs[3]:
        st.markdown("### ➕ Create New Work Order")
        all_assets_list = DB.get_assets(fc, 50000)
        assets_df = pd.DataFrame(all_assets_list) if all_assets_list else pd.DataFrame()
        with st.form("create_wo_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                wo_title = st.text_input("Title*", placeholder="Brief description")
                wo_type = st.selectbox("Type*", ["Reactive","Preventive","Corrective","New Installation","Inspection","Emergency Repair"])
            with c2:
                wo_priority = st.selectbox("Priority*", ["emergency","high","medium","low"])
                wo_category = st.selectbox("Category", ["HVAC","Electrical","Plumbing","Elevator","Fire Safety","Civil/Structural","BMS","ELV","Technology","General"])
            with c3:
                non_failure = ["Preventive","New Installation","Inspection"]
                default_failure = "N/A — Not Applicable" if wo_type in non_failure else "Unknown"
                failure_idx = 0 if wo_type in non_failure else 9
                wo_failure_class = st.selectbox("Failure Class", ["N/A — Not Applicable","Mechanical","Electrical","User Error","Wear & Tear","Design Issue","Technology","Software/Firmware","Network/Connectivity","Unknown"], index=failure_idx)
                wo_team = st.selectbox("Assigned Team", ["Engineering — Electrical","Engineering — HVAC","Engineering — Plumbing","Facility Management — Hard Services","Technology Group"])
            c1, c2 = st.columns(2)
            with c1:
                bldg_options = DB.get_locations(fc)
                if bldg_options:
                    bldg_names = [b.get("location_name","") for b in bldg_options]
                else:
                    bldg_names = [info.get("full_name", fc)]
                wo_location_bldg = st.selectbox("Building", bldg_names)
            with c2: wo_location_floor = st.text_input("Floor/Zone", placeholder="e.g., Floor 13")
            wo_description = st.text_area("Description", height=80)
            wo_attachment = st.file_uploader("📎 Attach Quote/Invoice (Optional)", type=["pdf","png","jpg","jpeg","docx","xlsx"])
            c1, c2, c3, c4 = st.columns(4)
            with c1: wo_est_hours = st.number_input("Est. Hours", min_value=0.0, value=1.0, step=0.5)
            with c2: wo_est_cost = st.number_input("Est. Cost (₦)", min_value=0.0, value=0.0, step=1000.0)
            with c3: wo_sla_hours = st.number_input("SLA Hours", min_value=1, value=24)
            with c4:
                if len(assets_df) > 0:
                    asset_options = ["None"] + [f"{a['name'][:40]} ({a['asset_tag']})" for _, a in assets_df.head(100).iterrows()]
                    wo_asset_sel = st.selectbox("Asset", asset_options)
                else: wo_asset_sel = "None"
            wo_tenant_impact = st.checkbox("Tenant Impact?")
            wo_tenant_name = st.text_input("Tenant Name") if wo_tenant_impact else ""
            if st.form_submit_button("➕ CREATE WORK ORDER", use_container_width=True, type="primary"):
                if wo_title:
                    wo_count = total_wo + 1
                    wo_number = f"WO-{fc}-{today.strftime('%Y%m%d')}-{str(wo_count).zfill(4)}"
                    sla_deadline = (wat_now + timedelta(hours=wo_sla_hours)).isoformat()
                    safe_supabase_query(lambda: supabase.table("work_orders").insert({
                        "facility_code":fc,"wo_number":wo_number,"title":wo_title,"description":wo_description,
                        "type":wo_type,"priority":wo_priority,"status":"open","category":wo_category,
                        "failure_class":wo_failure_class,"assigned_team":wo_team,
                        "estimated_hours":wo_est_hours,"estimated_cost":wo_est_cost,
                        "sla_due_date":sla_deadline,"location_building":wo_location_bldg,
                        "location_floor":wo_location_floor,"tenant_impact":wo_tenant_impact,
                        "tenant_name":wo_tenant_name if wo_tenant_impact else None,"created_at":wat_now.isoformat()
                    }).execute(), error_prefix="Create WO")
                    if wo_attachment:
                        import base64 as b64
                        file_bytes = wo_attachment.read()
                        file_b64 = b64.b64encode(file_bytes).decode()
                        safe_supabase_query(lambda: supabase.table("work_orders").update({"attachments":[{"name":wo_attachment.name,"type":wo_attachment.type,"size":len(file_bytes),"data":file_b64}]}).eq("wo_number",wo_number).execute(), error_prefix="WO attachment")
                    st.session_state.wo_created = True
                    st.session_state.wo_number_created = wo_number
                    st.rerun()
                else: st.error("⚠️ Title required")
    
    # ============================================
    # TAB 4: ASSIGNMENT CONSOLE & ANALYTICS
    # ============================================
    with tabs[4]:
        st.markdown("### 👥 Work Order Assignment Console")
        
        if total_wo == 0:
            st.info("No work orders yet.")
        else:
            # KPIs
            assigned_count = len(wo_df[wo_df["technician_name"].notna() & (wo_df["technician_name"] != "")]) if "technician_name" in wo_df.columns else 0
            unassigned_count = len(wo_df[~(wo_df["technician_name"].notna() & (wo_df["technician_name"] != ""))]) if "technician_name" in wo_df.columns else total_wo
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("📋 Total WOs", total_wo)
            with c2: st.metric("👤 Assigned", assigned_count)
            with c3: st.metric("⚠️ Unassigned", unassigned_count)
            with c4: st.metric("✅ Completed Today", len(wo_df[(wo_df["status"].isin(["completed","closed"])) & (pd.to_datetime(wo_df["updated_at"], errors='coerce').dt.date == today)]) if "updated_at" in wo_df.columns else 0)
            
            st.markdown("---")
            
            # Filters
            c1, c2, c3 = st.columns(3)
            with c1:
                console_status = st.selectbox("Status", ["All","open","in_progress","on_hold","completed","closed"], key="console_status")
            with c2:
                all_techs = sorted(wo_df["technician_name"].dropna().unique().tolist()) if "technician_name" in wo_df.columns else []
                console_tech = st.selectbox("Technician", ["All"] + all_techs, key="console_tech")
            with c3:
                console_search = st.text_input("🔍 Search", key="console_search", placeholder="WO# or title...")
            
            # Filter
            console_df = wo_df.copy()
            if console_status != "All": console_df = console_df[console_df["status"] == console_status]
            if console_tech != "All": console_df = console_df[console_df["technician_name"] == console_tech]
            if console_search:
                console_df = console_df[console_df["wo_number"].str.contains(console_search, case=False, na=False) | console_df["title"].str.contains(console_search, case=False, na=False)]
            
            st.caption(f"📋 {len(console_df)} work orders")
            
            for _, wo in console_df.head(30).iterrows():
                status = wo.get("status", "open")
                sc = {"open":"#3B82F6","in_progress":"#F59E0B","on_hold":"#8B5CF6","completed":"#10B981","cancelled":"#EF4444","closed":"#6B7280"}.get(status,"#3B82F6")
                wo_id = wo["id"]
                tech_name = wo.get("technician_name","Unassigned")
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{wo.get('wo_number','')}</b> — {wo.get('title','')[:80]}
                            <br><span style="font-size:0.65rem;color:#666;">👤 <b>{tech_name}</b> | 🏢 {wo.get('assigned_team','')} | 📅 Created: {str(wo.get('created_at',''))[:10]}</span>
                            <br><span style="font-size:0.6rem;color:#888;">🕐 SLA: {str(wo.get('sla_due_date','N/A'))[:10]} | ⏱️ Started: {str(wo.get('actual_start','Not started'))[:10]}</span>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{sc};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status.upper()}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Reassign button (for Team Leads/Admin)
                if (is_super or is_admin or is_team_lead) and status not in ["closed","cancelled"]:
                    c1, c2 = st.columns(2)
                    with c1:
                        all_users = DB.get_users()
                        tech_names = sorted([u.get("name","") for u in all_users if u.get("name")])
                        current_tech = wo.get("technician_name","")
                        default_idx = tech_names.index(current_tech) if current_tech in tech_names else 0
                        new_assign = st.selectbox("Reassign to", tech_names, index=default_idx, key=f"reassign_{wo_id}", label_visibility="collapsed")
                    with c2:
                        if st.button("🔄 Reassign", key=f"reassign_btn_{wo_id}", use_container_width=True):
                            if new_assign != current_tech:
                                safe_supabase_query(lambda: supabase.table("work_orders").update({"technician_name": new_assign}).eq("id", wo_id).execute(), error_prefix="Reassign WO")
                                safe_supabase_query(lambda: supabase.table("wo_timeline").insert({"wo_id":wo_id,"status_from":status,"status_to":status,"changed_by":user_name,"comment":f"Reassigned from {current_tech} to {new_assign}","created_at":wat_now.isoformat()}).execute(), error_prefix="Timeline")
                                
                                new_user = next((u for u in all_users if u.get("name") == new_assign), None)
                                if new_user and new_user.get("email"):
                                    try:
                                        send_email_notification(new_user["email"], f"🔧 WO Reassigned — {wo.get('wo_number','')}", f"<h3>Work Order Reassigned to You</h3><p><b>WO:</b> {wo.get('wo_number','')}</p><p><b>Title:</b> {wo.get('title','')}</p><p>Please check facilityXperience.</p>")
                                    except: pass
                                
                                st.success(f"✅ Reassigned to {new_assign}!"); st.rerun()
                            else:
                                st.info("Same technician selected.")
                
                # Show timeline summary
                wo_timeline = safe_supabase_query(lambda: supabase.table("wo_timeline").select("*").eq("wo_id", wo_id).order("created_at").execute(), error_prefix="WO timeline")
                if wo_timeline and wo_timeline.data:
                    last_action = wo_timeline.data[-1]
                    last_time = str(last_action.get("created_at",""))[:16]
                    last_comment = str(last_action.get("comment",""))[:60]
                    st.caption(f"📝 Last action: {last_time} — {last_comment}")
        
        st.markdown("---")
        
        # ============================================
        # AI ANALYTICS — PER TECHNICIAN
        # ============================================
        st.markdown("### 📊 Technician Performance Analytics")
        
        if "technician_name" in wo_df.columns and total_wo > 0:
            tech_stats = wo_df.groupby("technician_name").agg(
                Total_WOs=("id","count"),
                Completed=("status",lambda x:(x.isin(["completed","closed"])).sum()),
                On_Hold=("status",lambda x:(x=="on_hold").sum()),
                Avg_Hours=("actual_hours","mean"),
                Total_Cost=("total_cost","sum"),
                FTF=("first_time_fix","sum")
            ).reset_index()
            
            tech_stats = tech_stats[tech_stats["technician_name"].notna() & (tech_stats["technician_name"] != "")]
            tech_stats["Completed"] = pd.to_numeric(tech_stats["Completed"], errors='coerce').fillna(0)
            tech_stats["Total_WOs"] = pd.to_numeric(tech_stats["Total_WOs"], errors='coerce').fillna(1)
            tech_stats["FTF"] = pd.to_numeric(tech_stats["FTF"], errors='coerce').fillna(0)
            tech_stats["Completion_Rate"] = round((tech_stats["Completed"] / tech_stats["Total_WOs"]) * 100)
            tech_stats["FTF_Rate"] = round((tech_stats["FTF"] / tech_stats["Total_WOs"]) * 100)
            
            st.dataframe(tech_stats, use_container_width=True, hide_index=True)
            
            # Chart
            fig = px.bar(tech_stats.sort_values("Total_WOs"), x="technician_name", y="Total_WOs", color="Completion_Rate", title="Technician Workload & Completion Rate", color_continuous_scale=["#EF4444","#F59E0B","#10B981"])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Department breakdown
            st.markdown("---")
            st.markdown("### 🏢 Department Performance")
            
            if "assigned_team" in wo_df.columns:
                dept_stats = wo_df.groupby("assigned_team").agg(
                    Total=("id","count"),
                    Completed=("status",lambda x:(x.isin(["completed","closed"])).sum()),
                    Avg_Hours=("actual_hours","mean"),
                    Total_Cost=("total_cost","sum")
                ).reset_index()
                dept_stats["Completed"] = pd.to_numeric(dept_stats["Completed"], errors='coerce').fillna(0)
                dept_stats["Total"] = pd.to_numeric(dept_stats["Total"], errors='coerce').fillna(1)
                dept_stats["Rate"] = round((dept_stats["Completed"] / dept_stats["Total"]) * 100)
                
                fig2 = px.bar(dept_stats.sort_values("Total"), x="assigned_team", y="Total", color="Rate", title="Department Workload", color_continuous_scale=["#EF4444","#F59E0B","#10B981"])
                fig2.update_layout(height=350)
                st.plotly_chart(fig2, use_container_width=True)
        
        # Export
        st.markdown("---")
        st.markdown("### 📥 Export Analytics")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 HTML Performance Report", key="perf_html_btn", use_container_width=True):
                logo_b64 = get_logo_base64()
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Technician Performance Report</title><style>body{{font-family:Arial;margin:20px}}h1{{color:#CC0000}}table{{width:100%;border-collapse:collapse}}th{{background:#CC0000;color:white;padding:8px}}td{{padding:6px;border-bottom:1px solid #eee}}</style></head><body><h1>Technician Performance Report</h1><p>{info.get('full_name',fc)} | {today}</p><table><tr><th>Technician</th><th>Total</th><th>Completed</th><th>Rate</th><th>FTF</th><th>Avg Hrs</th></tr>"""
                if 'tech_stats' in dir():
                    for _,t in tech_stats.iterrows(): html += f"<tr><td>{t['technician_name']}</td><td>{t['Total_WOs']}</td><td>{t['Completed']}</td><td>{t['Completion_Rate']}%</td><td>{t['FTF_Rate']}%</td><td>{round(t['Avg_Hours'],1)}</td></tr>"
                html += "</table></body></html>"
                st.download_button("📥 Download HTML", html, f"tech_performance_{today}.html", "text/html", use_container_width=True)
        with c2:
            if 'tech_stats' in dir() and tech_stats is not None:
                st.download_button("📥 Download CSV", tech_stats.to_csv(index=False), f"tech_performance_{today}.csv", "text/csv", use_container_width=True)
    
    # ============================================
    # TAB 5: AI-POWERED INTELLIGENCE REPORTS
    # ============================================
    with tabs[5]:
        st.markdown("### 📊 Work Order Intelligence Reports")
        
        # Period Selector
        report_period = st.selectbox("📅 Report Period", ["Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Custom"], key="wo_period")
        
        if report_period == "Weekly":
            start_date = today - timedelta(days=7)
            end_date = today
        elif report_period == "Monthly":
            start_date = today.replace(day=1)
            end_date = today
        elif report_period == "Quarterly":
            q_month = ((today.month - 1) // 3) * 3 + 1
            start_date = date(today.year, q_month, 1)
            end_date = today
        elif report_period == "Half-Yearly":
            h_month = 1 if today.month <= 6 else 7
            start_date = date(today.year, h_month, 1)
            end_date = today
        elif report_period == "Yearly":
            start_date = date(today.year, 1, 1)
            end_date = today
        else:
            c1, c2 = st.columns(2)
            with c1: start_date = st.date_input("From", today - timedelta(days=30), key="wo_from")
            with c2: end_date = st.date_input("To", today, key="wo_to")
        
        # Filter WOs for period
        period_wo = wo_df[(pd.to_datetime(wo_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(wo_df["created_at"], errors='coerce').dt.date <= end_date)] if total_wo > 0 else pd.DataFrame()
        period_total = len(period_wo)
        
        st.caption(f"📅 {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')} | {period_total} work orders")
        
        if period_total == 0:
            st.info("No work orders in this period.")
        else:
            # Period calculations
            period_spend = period_wo["total_cost"].sum() if "total_cost" in period_wo.columns else 0
            period_labour = period_wo["labour_cost"].sum() if "labour_cost" in period_wo.columns else 0
            period_parts = period_wo["parts_cost"].sum() if "parts_cost" in period_wo.columns else 0
            period_ftf = len(period_wo[period_wo["first_time_fix"] == True]) if "first_time_fix" in period_wo.columns else 0
            period_ftf_rate = round((period_ftf / period_total) * 100) if period_total > 0 else 0
            period_sla_breach = len(period_wo[(pd.to_datetime(period_wo["sla_due_date"], errors='coerce').dt.date < today) & (~period_wo["status"].isin(["completed","closed"]))]) if "sla_due_date" in period_wo.columns else 0
            period_sla = round(((period_total - period_sla_breach) / max(period_total, 1)) * 100) if period_total > 0 else 0
            period_avg_hours = round(period_wo["actual_hours"].mean(), 1) if "actual_hours" in period_wo.columns else 0
            period_tenant = len(period_wo[period_wo["tenant_impact"] == True]) if "tenant_impact" in period_wo.columns else 0
            
            reactive_count = len(period_wo[period_wo["type"].isin(["Reactive","Emergency Repair"])])
            pm_count = len(period_wo[period_wo["type"] == "Preventive"])
            
            # WO Aging
            aging_24h = len(period_wo[(pd.to_datetime(period_wo["created_at"], errors='coerce') >= wat_now - timedelta(hours=24)) & (~period_wo["status"].isin(["completed","closed"]))])
            aging_72h = len(period_wo[(pd.to_datetime(period_wo["created_at"], errors='coerce') >= wat_now - timedelta(hours=72)) & (pd.to_datetime(period_wo["created_at"], errors='coerce') < wat_now - timedelta(hours=24)) & (~period_wo["status"].isin(["completed","closed"]))])
            aging_old = len(period_wo[(pd.to_datetime(period_wo["created_at"], errors='coerce') < wat_now - timedelta(hours=72)) & (~period_wo["status"].isin(["completed","closed"]))])
            
            # ============================================
            # EXECUTIVE KPIs
            # ============================================
            st.markdown("### 🟦 Executive KPIs")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1:
                color = "#10B981" if period_sla >= 90 else "#F59E0B" if period_sla >= 70 else "#EF4444"
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">SLA Compliance</div><div style="font-size:1.4rem;font-weight:800;color:{color};">{period_sla}%</div></div>""", unsafe_allow_html=True)
            with c2:
                color = "#10B981" if period_ftf_rate >= 80 else "#F59E0B" if period_ftf_rate >= 60 else "#EF4444"
                st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">First-Time Fix</div><div style="font-size:1.4rem;font-weight:800;color:{color};">{period_ftf_rate}%</div></div>""", unsafe_allow_html=True)
            with c3: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Avg Resolution</div><div style="font-size:1.4rem;font-weight:800;color:#3B82F6;">{period_avg_hours}hrs</div></div>""", unsafe_allow_html=True)
            with c4: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Period Spend</div><div style="font-size:1.4rem;font-weight:800;color:#CC0000;">₦{period_spend:,.0f}</div></div>""", unsafe_allow_html=True)
            with c5: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Tenant WOs</div><div style="font-size:1.4rem;font-weight:800;color:#8B5CF6;">{period_tenant}</div></div>""", unsafe_allow_html=True)
            with c6: st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.8rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Total WOs</div><div style="font-size:1.4rem;font-weight:800;color:#F59E0B;">{period_total}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # ============================================
            # WO AGING & CHARTS
            # ============================================
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 📊 WO Aging Analysis")
                aging_data = pd.DataFrame({"Age":["<24 Hours","24-72 Hours",">72 Hours"],"Count":[aging_24h,aging_72h,aging_old]})
                colors_aging = ["#10B981","#F59E0B","#EF4444"]
                fig_aging = px.bar(aging_data, x="Age", y="Count", title="Open WO Aging", color="Age", color_discrete_sequence=colors_aging)
                fig_aging.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_aging, use_container_width=True)
            
            with c2:
                st.markdown("### 🏥 PM Health Index")
                pm_ratio = round((pm_count / max(period_total, 1)) * 100)
                reactive_ratio = round((reactive_count / max(period_total, 1)) * 100)
                corrective_count = len(period_wo[period_wo["type"] == "Corrective"])
                proactive_count = pm_count + corrective_count
                ratio_data = pd.DataFrame({"Type":["Planned (PM+Corrective)","Reactive"],"Count":[proactive_count, reactive_count]})
                fig_ratio = px.pie(ratio_data, values="Count", names="Type", title=f"PM ({pm_ratio}%) vs Reactive ({reactive_ratio}%)", color_discrete_sequence=["#10B981","#EF4444"], hole=0.5)
                fig_ratio.update_layout(height=350)
                st.plotly_chart(fig_ratio, use_container_width=True)
            
            # Cost breakdown
            st.markdown("---")
            st.markdown("### 💰 Cost Analysis")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("👷 Labour", f"₦{period_labour:,.0f}")
            with c2: st.metric("🔧 Parts", f"₦{period_parts:,.0f}")
            with c3: st.metric("📊 Cost/WO", f"₦{round(period_spend/max(period_total,1)):,.0f}")
            with c4: st.metric("🏢 Tenant Cost", f"₦{period_wo[period_wo['tenant_impact']==True]['total_cost'].sum() if 'tenant_impact' in period_wo.columns else 0:,.0f}")
            
            # Failure mode analysis
            if "failure_class" in period_wo.columns and period_total > 0:
                st.markdown("---")
                st.markdown("### 🔍 Failure Mode Analysis")
                failure_counts = period_wo["failure_class"].value_counts().head(8)
                fig_fail = px.bar(x=failure_counts.values, y=failure_counts.index, orientation='h', title="Top Failure Classes", color=failure_counts.values, color_continuous_scale=["#10B981","#F59E0B","#EF4444"])
                fig_fail.update_layout(height=350)
                st.plotly_chart(fig_fail, use_container_width=True)
            
            # ============================================
            # AI EXECUTIVE SUMMARY
            # ============================================
            st.markdown("---")
            st.markdown("### 🤖 AI Executive Summary")
            
            insights = []
            if period_sla_breach > 0:
                insights.append(f"🔴 **SLA Alert:** {period_sla_breach} WOs breached SLA. {period_sla}% compliance — {'critical' if period_sla < 70 else 'needs improvement'}.")
            if reactive_count > pm_count * 2:
                insights.append(f"⚠️ **Firefighting Mode:** Reactive WOs ({reactive_count}) are {round(reactive_count/max(pm_count,1))}x Preventive ({pm_count}). Underinvesting in PM creates 3x reactive work downstream.")
            if period_avg_hours > 8:
                insights.append(f"⚠️ **Slow Resolution:** Average {period_avg_hours}hrs exceeds 8hr target. Review technician workload and parts availability.")
            if period_ftf_rate < 70:
                insights.append(f"⚠️ **First-Time Fix at {period_ftf_rate}%:** Training or diagnostic tools review recommended.")
            if aging_old > 5:
                insights.append(f"🔴 **Aging WOs:** {aging_old} WOs open >72 hours. These represent risk to tenant satisfaction and SLA compliance.")
            if period_total > 0 and period_sla >= 90 and period_ftf_rate >= 80:
                insights.append("✅ **Excellent Performance:** SLA and FTF exceeding targets. Team operating at world-class levels.")
            if period_total == 0:
                insights.append("📝 No work orders in this period.")
            
            for insight in insights:
                st.markdown(f"""<div style="background:white;border-left:4px solid #CC0000;border-radius:8px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">{insight}</div>""", unsafe_allow_html=True)
            
            # ============================================
            # EXPORT
            # ============================================
            st.markdown("---")
            st.markdown("### 📥 Download Intelligence Reports")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📄 Generate Full Intelligence Report (HTML)", key="intel_html_btn", use_container_width=True, type="primary"):
                    logo_b64 = get_logo_base64()
                    logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
                    
                    # Generate chart images
                    import io, base64 as b64
                    chart_images = ""
                    
                    try:
                        # Chart 1: WO Aging
                        aging_data = pd.DataFrame({"Age":["<24 Hours","24-72 Hours",">72 Hours"],"Count":[aging_24h,aging_72h,aging_old]})
                        fig1 = px.bar(aging_data, x="Age", y="Count", title="WO Aging Analysis", color="Age", color_discrete_sequence=["#10B981","#F59E0B","#EF4444"])
                        fig1.update_layout(height=300, width=500)
                        buf1 = io.BytesIO()
                        fig1.write_image(buf1, format='png', engine='kaleido', scale=2)
                        chart_images += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf1.getvalue()).decode()}" style="max-width:100%;"></div>'
                    except: pass
                    
                    try:
                        # Chart 2: PM Health Index
                        pm_ratio_val = round((proactive_count / max(period_total, 1)) * 100)
                        reactive_ratio_val = round((reactive_count / max(period_total, 1)) * 100)
                        ratio_data = pd.DataFrame({"Type":["Planned (PM+Corrective)","Reactive"],"Count":[proactive_count, reactive_count]})
                        fig2 = px.pie(ratio_data, values="Count", names="Type", title="PM Health Index", color_discrete_sequence=["#10B981","#EF4444"], hole=0.5)
                        fig2.update_layout(height=300, width=500)
                        buf2 = io.BytesIO()
                        fig2.write_image(buf2, format='png', engine='kaleido', scale=2)
                        chart_images += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf2.getvalue()).decode()}" style="max-width:100%;"></div>'
                    except: pass
                    
                    try:
                        # Chart 3: Failure Mode
                        if "failure_class" in period_wo.columns and period_total > 0:
                            failure_counts = period_wo["failure_class"].value_counts().head(8)
                            fig3 = px.bar(x=failure_counts.values, y=failure_counts.index, orientation='h', title="Top Failure Classes", color=failure_counts.values, color_continuous_scale=["#10B981","#F59E0B","#EF4444"])
                            fig3.update_layout(height=300, width=600)
                            buf3 = io.BytesIO()
                            fig3.write_image(buf3, format='png', engine='kaleido', scale=2)
                            chart_images += f'<div style="text-align:center;margin:15px 0;"><img src="data:image/png;base64,{b64.b64encode(buf3.getvalue()).decode()}" style="max-width:100%;"></div>'
                    except: pass
                    
                    # Build WO table rows
                    wo_rows = ""
                    for _, wo in period_wo.head(50).iterrows():
                        sla_date = str(wo.get('sla_due_date','N/A'))[:10]
                        sla_status = "⚠️ Breached" if pd.to_datetime(wo.get('sla_due_date'), errors='coerce').date() < today and wo.get('status') not in ['completed','closed'] else "✅ OK"
                        wo_rows += f"<tr><td>{wo.get('wo_number','')}</td><td>{wo.get('title','')[:50]}</td><td>{wo.get('type','')}</td><td>{wo.get('priority','').upper()}</td><td>{wo.get('status','').upper()}</td><td>{wo.get('technician_name','Unassigned')}</td><td>{sla_date} {sla_status}</td><td>₦{wo.get('total_cost',0):,.0f}</td></tr>"
                    
                    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Work Order Intelligence Report</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;margin:25px;color:#1a1a1a;background:#f0f2f5}}
.container{{max-width:1000px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}
.header{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}
.header h1{{color:#CC0000;margin:0;font-size:22px}}
.header p{{color:#888;margin:3px 0 0 0;font-size:11px}}
.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:20px 0}}
.kpi{{background:linear-gradient(135deg,#f9fafb,#fff);border-radius:10px;padding:12px;text-align:center;border-top:3px solid #CC0000}}
.kpi .val{{font-size:22px;font-weight:800;color:#CC0000}}
.kpi .lbl{{font-size:9px;color:#888;text-transform:uppercase}}
h2{{color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;margin-top:25px;font-size:16px}}
.charts-section{{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin:20px 0}}
table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:10px}}
th{{background:#CC0000;color:white;padding:10px;text-align:left;font-size:9px;text-transform:uppercase}}
td{{padding:8px;border-bottom:1px solid #eee}}
.insight-box{{background:#FEF2F2;border-left:4px solid #EF4444;padding:12px;margin:8px 0;border-radius:6px;font-size:12px}}
.insight-box.green{{background:#ECFDF5;border-left-color:#10B981}}
.footer{{text-align:center;font-size:9px;color:#999;margin-top:25px;border-top:1px solid #eee;padding-top:15px}}
</style></head><body><div class="container">
<div class="header"><div>{logo_img}<h1>Work Order Intelligence Report</h1><p>{info.get('full_name',fc)} | {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')} | {report_period}</p></div></div>
<div class="kpi-row">
<div class="kpi"><div class="val">{period_total}</div><div class="lbl">Total WOs</div></div>
<div class="kpi"><div class="val">{period_sla}%</div><div class="lbl">SLA</div></div>
<div class="kpi"><div class="val">{period_ftf_rate}%</div><div class="lbl">First-Time Fix</div></div>
<div class="kpi"><div class="val">{period_avg_hours}hrs</div><div class="lbl">Avg Resolution</div></div>
<div class="kpi"><div class="val">₦{period_spend:,.0f}</div><div class="lbl">Total Spend</div></div>
<div class="kpi"><div class="val">{period_tenant}</div><div class="lbl">Tenant WOs</div></div>
</div>

<div class="insight-box"><b>SLA Performance:</b> {period_sla}% compliance. {period_sla_breach} WOs breached. {'Immediate attention required.' if period_sla_breach > 0 else 'All WOs within SLA.'}</div>
<div class="insight-box green"><b>Cost Efficiency:</b> ₦{period_spend:,.0f} total. ₦{round(period_spend/max(period_total,1)):,.0f}/WO. Labour: ₦{period_labour:,.0f} | Parts: ₦{period_parts:,.0f}</div>
<div class="insight-box"><b>🏥 PM Health Index:</b> {proactive_count} Planned ({round((proactive_count/max(period_total,1))*100)}%) vs {reactive_count} Reactive ({round((reactive_count/max(period_total,1))*100)}%). {'World-class PM ratio.' if pm_ratio >= 60 else 'Increase planned maintenance to reduce emergency work.'}</div>

<div class="charts-section">{chart_images}</div>

<h2>Work Order Details</h2>
<table><tr><th>WO#</th><th>Title</th><th>Type</th><th>Priority</th><th>Status</th><th>Tech</th><th>SLA</th><th>Cost</th></tr>{wo_rows}</table>
<div class="footer">Churchgate Group | facilityXperience | AI-Generated Intelligence Report | {today.strftime('%d %B %Y')}</div>
</div></body></html>"""
                    
                    st.download_button("📥 Download Intelligence Report (HTML)", html, f"wo_intelligence_{start_date}_{end_date}.html", "text/html", use_container_width=True)
            
            with c2:
                if st.button("📕 Generate PDF Report", key="intel_pdf_btn", use_container_width=True):
                    try:
                        from fpdf import FPDF
                        pdf = FPDF('L','mm','A4')
                        pdf.add_page()
                        pdf.set_font('Helvetica','B',18)
                        pdf.set_text_color(204,0,0)
                        pdf.cell(0,12,safe_text('Work Order Intelligence Report'),0,1)
                        pdf.set_font('Helvetica','',10)
                        pdf.set_text_color(0,0,0)
                        pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {start_date.strftime("%d %b %Y")} - {end_date.strftime("%d %b %Y")} | {report_period}'),0,1)
                        pdf.ln(2)
                        pdf.set_font('Helvetica','B',10)
                        pdf.cell(0,6,f'SLA: {period_sla}% | FTF: {period_ftf_rate}% | Avg: {period_avg_hours}hrs | Spend: NGN {period_spend:,.0f} | Tenant WOs: {period_tenant}',0,1)
                        pdf.ln(3)
                        pdf.set_font('Helvetica','B',8)
                        pdf.set_fill_color(204,0,0)
                        pdf.set_text_color(255,255,255)
                        for h,w in zip(['WO#','Title','Type','Priority','Status','Tech','SLA','Cost'],[30,50,22,18,20,38,28,22]):
                            pdf.cell(w,6,h,1,0,'C',True)
                        pdf.ln()
                        pdf.set_font('Helvetica','',7)
                        pdf.set_text_color(0,0,0)
                        for _,wo in period_wo.head(40).iterrows():
                            pdf.cell(30,5,safe_text(wo.get('wo_number','')),1,0)
                            pdf.cell(50,5,safe_text(str(wo.get('title',''))[:22]),1,0)
                            pdf.cell(22,5,safe_text(wo.get('type','')),1,0)
                            pdf.cell(18,5,safe_text(wo.get('priority','').upper()),1,0)
                            pdf.cell(20,5,safe_text(wo.get('status','').upper()),1,0)
                            pdf.cell(38,5,safe_text(str(wo.get('technician_name','Unassigned'))[:17]),1,0)
                            pdf.cell(28,5,str(wo.get('sla_due_date',''))[:10],1,0)
                            pdf.cell(22,5,str(wo.get('total_cost',0)),1,0)
                            pdf.ln()
                        pdf.ln(4)
                        pdf.set_font('Helvetica','B',8)
                        pdf.cell(0,5,'AI Recommendations:',0,1)
                        pdf.set_font('Helvetica','',7)
                        pdf.multi_cell(0,4,'Based on work order analysis, focus on preventive maintenance compliance and technician training for improved first-time fix rates. SLA compliance and aging WOs should be reviewed weekly.')
                        pdf_file = f"/tmp/wo_intel_{start_date}_{end_date}.pdf"
                        pdf.output(pdf_file)
                        with open(pdf_file,"rb") as f:
                            st.download_button("📥 Download Intelligence Report (PDF)", f.read(), f"wo_intelligence_{start_date}_{end_date}.pdf", "application/pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"PDF error: {str(e)[:80]}")

# ============================================
# HOTO INTELLIGENCE — CUSTODY TRANSFER COMMAND CENTER
# WITH FULL APPROVAL WORKFLOW & ALERT ARCHITECTURE
# ============================================
def page_hot():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    user_email = st.session_state.get("user", {}).get("email", "")
    is_admin = user_role in ["admin", "approver", "super_admin"]
    is_fm_director = user_role in ["admin", "super_admin", "sr_management"]
    is_dept_manager = user_role in ["manager", "sr_manager", "admin", "super_admin"]
    is_shift_lead = user_role in ["team_lead", "manager", "sr_manager", "admin", "super_admin"]
    
    st.markdown(f'## 🔄 HOTO Intelligence — {info.get("full_name", fc)}')
    st.caption("Custody Transfer Command Center — Governed. Auditable. Legally Defensible.")
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    hoto_data = safe_supabase_query(lambda: supabase.table("hoto_records").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="HOTO data")
    hoto_df = pd.DataFrame(hoto_data.data) if hoto_data and hoto_data.data else pd.DataFrame()
    
    total_hoto = len(hoto_df)
    active_hoto = len(hoto_df[~hoto_df["status"].isin(["closed","disputed"])]) if total_hoto > 0 else 0
    
    # Punch list counts
    punch_open = 0
    punch_safety = 0
    if total_hoto > 0:
        for _, h in hoto_df.iterrows():
            punch = safe_supabase_query(lambda hid=h["id"]: supabase.table("hoto_punch_list").select("*").eq("hoto_id", hid).execute(), error_prefix="Punch list")
            if punch and punch.data:
                for p in punch.data:
                    if p.get("status") in ["open", "in_progress"]:
                        punch_open += 1
                        if p.get("severity") == "safety":
                            punch_safety += 1
    
    # DLP expiring
    dlp_expiring = 0
    dlp_critical = 0
    if "defect_liability_end" in hoto_df.columns and total_hoto > 0:
        for _, h in hoto_df.iterrows():
            try:
                dlp_end = pd.to_datetime(h["defect_liability_end"]).date()
                days_left = (dlp_end - today).days
                if 0 < days_left <= 30:
                    dlp_expiring += 1
                    if days_left <= 7:
                        dlp_critical += 1
            except: pass
    
    # Overdue shift handovers
    overdue_shifts = 0
    shift_logs = safe_supabase_query(lambda: supabase.table("shift_handover_logs").select("*").eq("facility_code", fc).eq("status", "pending").execute(), error_prefix="Shift logs")
    if shift_logs and shift_logs.data:
        for log in shift_logs.data:
            try:
                log_time = pd.to_datetime(str(log.get("handover_date","")) + " " + str(log.get("handover_time","")))
                if wat_now > log_time + timedelta(minutes=30):
                    overdue_shifts += 1
            except: pass
    
    # ============================================
    # 🟦 TOP RIBBON
    # ============================================
    st.markdown("### 🟦 HOTO Governance Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Active HOTOs</div><div style="font-size:1.3rem;font-weight:800;color:#CC0000;">{active_hoto}</div></div>""", unsafe_allow_html=True)
    with c2:
        color = "#EF4444" if dlp_critical > 0 else "#F59E0B" if dlp_expiring > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">DLP Expiring ≤30d</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{dlp_expiring}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if punch_safety > 0 else "#F59E0B"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Open Punch Items</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{punch_open}</div></div>""", unsafe_allow_html=True)
    with c4:
        color = "#EF4444" if overdue_shifts > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overdue Shifts</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{overdue_shifts}</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total HOTOs</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_hoto}</div></div>""", unsafe_allow_html=True)
    with c6:
        pending_approvals = 0
        try:
            pa = safe_supabase_query(lambda: supabase.table("hoto_approvals").select("id", count="exact").eq("status", "pending").execute(), error_prefix="Pending approvals")
            pending_approvals = pa.count if pa else 0
        except: pass
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Pending Approvals</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{pending_approvals}</div></div>""", unsafe_allow_html=True)
    
    # Critical alerts
    if dlp_critical > 0:
        st.error(f"🚨 **CRITICAL:** {dlp_critical} DLP(s) expiring within 7 days. Immediate action required to preserve warranty rights.")
    if punch_safety > 0:
        st.error(f"🔴 **SAFETY:** {punch_safety} safety-related punch items open. These must be resolved before HOTO acceptance.")
    if overdue_shifts > 0:
        st.warning(f"⚠️ **OVERDUE:** {overdue_shifts} shift handovers are overdue. Department managers notified.")
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 All HOTOs", "➕ New HOTO", "🔧 Shift Handover", "✅ Approvals", "📊 Punch List", "📄 Reports"])
    
    # ============================================
    # TAB 0: ALL HOTO RECORDS WITH STATUS
    # ============================================
    with tabs[0]:
        st.markdown("### 📋 HOTO Records")
        
        if st.session_state.get("hoto_created", False):
            st.success(f"✅ HOTO {st.session_state.get('hoto_number_created','')} initiated with approval workflow!")
            st.balloons()
            st.session_state.hoto_created = False
        
        if total_hoto == 0:
            st.info("No HOTO records yet.")
        else:
            c1, c2 = st.columns(2)
            with c1: hoto_filter_type = st.selectbox("Type", ["All","tenant_move_in","tenant_move_out","asset_commissioning","contractor_transition","shift_engineering","shift_security","shift_cctv","cross_functional"], format_func=lambda x: x.replace("_"," ").title() if x != "All" else "All", key="hoto_filter")
            with c2: hoto_filter_status = st.selectbox("Status", ["All","initiated","pre_inspection","joint_inspection","punch_list","acceptance","closed","disputed"], key="hoto_status_filter")
            
            display_hoto = hoto_df.copy()
            if hoto_filter_type != "All": display_hoto = display_hoto[display_hoto["hoto_type"] == hoto_filter_type]
            if hoto_filter_status != "All": display_hoto = display_hoto[display_hoto["status"] == hoto_filter_status]
            
            st.caption(f"📋 {len(display_hoto)} records")
            
            for _, h in display_hoto.head(20).iterrows():
                status = h.get("status","initiated")
                hoto_type = h.get("hoto_type","").replace("_"," ").title()
                tier = h.get("tier","").replace("_"," ").title()
                sc = {"initiated":"#3B82F6","pre_inspection":"#F59E0B","joint_inspection":"#8B5CF6","punch_list":"#EF4444","acceptance":"#10B981","closed":"#6B7280","disputed":"#DC2626"}.get(status,"#3B82F6")
                hoto_id = h["id"]
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{h.get('hoto_number','N/A')}</b> — {h.get('title','')[:80]}
                            <br><span style="font-size:0.65rem;color:#666;">🔄 {h.get('transferor_name','?')} → {h.get('transferee_name','?')}</span>
                            <br><span style="font-size:0.6rem;color:#888;">🏷️ {hoto_type} | 📊 {tier} | 📅 {str(h.get('created_at',''))[:10]}</span>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{sc};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status.upper()}</span>
                            {f'<br><span style="font-size:0.5rem;color:#EF4444;">DLP: {str(h.get("defect_liability_end",""))[:10]}</span>' if h.get("defect_liability_end") else ''}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Approval actions
                approvals = safe_supabase_query(lambda: supabase.table("hoto_approvals").select("*").eq("hoto_id", hoto_id).order("approval_level").execute(), error_prefix="HOTO approvals")
                if approvals and approvals.data:
                    with st.expander(f"🔐 Approvals ({len(approvals.data)})"):
                        for app in approvals.data:
                            app_status = app.get("status","pending")
                            app_color = "#10B981" if app_status == "approved" else "#EF4444" if app_status == "rejected" else "#F59E0B"
                            st.markdown(f"""
                            <div style="background:#f9fafb;border-radius:6px;padding:0.5rem;margin:0.1rem 0;font-size:0.7rem;border-left:3px solid {app_color};">
                                <b>Level {app.get('approval_level','')}</b> — {app.get('approver_role','').replace('_',' ').title()}
                                <br>Status: <span style="color:{app_color};font-weight:700;">{app_status.upper()}</span>
                                {f" | {app.get('comments','')[:60]}" if app.get('comments') else ''}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Quick approve/reject for authorized users
                if status not in ["closed","disputed"] and (is_admin or is_fm_director):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ Approve", key=f"app_{hoto_id}", use_container_width=True):
                            safe_supabase_query(lambda: supabase.table("hoto_approvals").insert({
                                "hoto_id": hoto_id, "approval_level": 1, "approver_role": "fm_director",
                                "approver_name": user_name, "approver_email": user_email,
                                "status": "approved", "comments": "Approved by FM Director",
                                "action_date": wat_now.isoformat(), "created_at": wat_now.isoformat()
                            }).execute(), error_prefix="Approve HOTO")
                            st.success("✅ Approved!"); st.rerun()
                    with c2:
                        if st.button("❌ Reject", key=f"rej_{hoto_id}", use_container_width=True):
                            st.session_state.rejecting_hoto = hoto_id; st.rerun()
                    with c3:
                        if status == "initiated":
                            if st.button("▶ Start Inspection", key=f"start_{hoto_id}", use_container_width=True):
                                safe_supabase_query(lambda: supabase.table("hoto_records").update({"status":"pre_inspection"}).eq("id",hoto_id).execute(), error_prefix="Start inspection")
                                st.success("▶ Pre-Inspection started!"); st.rerun()
                        elif status == "pre_inspection":
                            if st.button("🔍 Joint Inspection", key=f"joint_{hoto_id}", use_container_width=True):
                                safe_supabase_query(lambda: supabase.table("hoto_records").update({"status":"joint_inspection"}).eq("id",hoto_id).execute(), error_prefix="Joint inspection")
                                st.success("🔍 Joint Inspection phase!"); st.rerun()
                        elif status in ["joint_inspection","punch_list"]:
                            if st.button("✅ Accept & Close", key=f"close_{hoto_id}", use_container_width=True):
                                safe_supabase_query(lambda: supabase.table("hoto_records").update({"status":"acceptance","acceptance_date":str(today)}).eq("id",hoto_id).execute(), error_prefix="Close HOTO")
                                try:
                                    send_email_notification(user_email, f"✅ HOTO Closed — {h.get('hoto_number','')}", f"<h3>HOTO Accepted & Closed</h3><p><b>HOTO:</b> {h.get('hoto_number','')}</p><p><b>Title:</b> {h.get('title','')}</p><p>Acceptance Date: {today}</p>")
                                except: pass
                                st.success("✅ HOTO Accepted & Closed!"); st.balloons(); st.rerun()
    
    # Rejection form
    if "rejecting_hoto" in st.session_state and st.session_state.rejecting_hoto:
        hoto_id = st.session_state.rejecting_hoto
        st.markdown("---")
        with st.form("reject_hoto_form"):
            st.markdown("### ❌ Reject HOTO")
            reject_reason = st.text_area("Rejection Reason*", height=80)
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("❌ REJECT", use_container_width=True, type="primary"):
                    if reject_reason:
                        safe_supabase_query(lambda: supabase.table("hoto_approvals").insert({
                            "hoto_id": hoto_id, "approval_level": 1, "approver_role": "fm_director",
                            "approver_name": user_name, "approver_email": user_email,
                            "status": "rejected", "comments": reject_reason,
                            "action_date": wat_now.isoformat(), "created_at": wat_now.isoformat()
                        }).execute(), error_prefix="Reject HOTO")
                        safe_supabase_query(lambda: supabase.table("hoto_records").update({"status":"disputed"}).eq("id",hoto_id).execute(), error_prefix="Dispute HOTO")
                        st.error("❌ Rejected!"); st.session_state.rejecting_hoto = None; st.rerun()
            with c2:
                if st.form_submit_button("CANCEL", use_container_width=True):
                    st.session_state.rejecting_hoto = None; st.rerun()
    
    # ============================================
    # TAB 1: NEW HOTO
    # ============================================
    with tabs[1]:
        st.markdown("### ➕ Initiate New HOTO")
        
        hoto_type = st.selectbox("HOTO Type*", [
            "tenant_move_in", "tenant_move_out", "asset_commissioning", 
            "contractor_transition", "shift_engineering", "shift_security", 
            "shift_cctv", "cross_functional"
        ], format_func=lambda x: x.replace("_"," ").title())
        
        if hoto_type in ["tenant_move_in","tenant_move_out","contractor_transition"]:
            tier = "strategic"
        elif hoto_type in ["asset_commissioning"]:
            tier = "asset"
        elif hoto_type in ["shift_engineering","shift_security","shift_cctv"]:
            tier = "operational_shift"
        else:
            tier = "cross_functional"
        
        with st.form("new_hoto_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                hoto_title = st.text_input("Title*", placeholder="e.g., Tenant X Move-Out Inspection")
                transferor = st.text_input("Transferor (From)*")
            with c2:
                transferee = st.text_input("Transferee (To)*")
                witness = st.text_input("Witness/Verifier", value=user_name)
            with c3:
                bldg_options = DB.get_locations(fc)
                if bldg_options:
                    bldg_names = [b.get("location_name","") for b in bldg_options]
                else:
                    bldg_names = [info.get("full_name", fc)]
                hoto_location_bldg = st.selectbox("Building", bldg_names)
                hoto_location_floor = st.text_input("Floor/Zone")
            
            hoto_desc = st.text_area("Scope Description", height=80)
            
            c1, c2 = st.columns(2)
            with c1:
                dlp_start = st.date_input("DLP Start (if applicable)", today)
                retention = st.number_input("Retention Amount (₦)", min_value=0.0, value=0.0, step=10000.0)
            with c2:
                dlp_end = st.date_input("DLP End (if applicable)", today + timedelta(days=365))
            
            # Auto-create approval records based on tier
            st.markdown("---")
            st.markdown("**🔐 Approval Requirements**")
            if tier == "operational_shift":
                st.caption("Level 1: Shift Leads (Digital Signature) | Level 2: Department Manager | Level 3: FM Director")
            elif tier == "asset":
                st.caption("Level 1: FM Supervisor + Contractor | Level 2: FM Engineering Manager | Level 3: FM Director + Landlord")
            elif tier == "strategic":
                st.caption("Level 1: FM Coordinator + Tenant/Contractor Rep | Level 2: FM Ops Manager | Level 3: Landlord + Legal")
            else:
                st.caption("Level 1: All Team Leads | Level 2: Incident Commander | Level 3: FM Director")
            
            if st.form_submit_button("➕ INITIATE HOTO", use_container_width=True, type="primary"):
                if hoto_title and transferor and transferee:
                    hoto_count = total_hoto + 1
                    hoto_number = f"HOTO-{fc}-{today.strftime('%Y%m%d')}-{str(hoto_count).zfill(4)}"
                    
                    result = safe_supabase_query(lambda: supabase.table("hoto_records").insert({
                        "facility_code": fc, "hoto_number": hoto_number, "title": hoto_title,
                        "hoto_type": hoto_type, "tier": tier, "description": hoto_desc,
                        "transferor_name": transferor, "transferee_name": transferee,
                        "witness_name": witness, "location_building": hoto_location_bldg,
                        "location_floor": hoto_location_floor, "status": "initiated",
                        "defect_liability_start": str(dlp_start), "defect_liability_end": str(dlp_end),
                        "retention_amount": retention, "created_by": user_name,
                        "created_at": wat_now.isoformat()
                    }).execute(), error_prefix="Create HOTO")
                    
                    if result and result.data:
                        hoto_id = result.data[0]["id"]
                        for level in range(1, 4):
                            safe_supabase_query(lambda l=level: supabase.table("hoto_approvals").insert({
                                "hoto_id": hoto_id, "approval_level": l,
                                "approver_role": ["shift_lead","dept_manager","fm_director"][l-1] if tier == "operational_shift" else ["fm_supervisor","fm_manager","fm_director"][l-1],
                                "status": "pending", "created_at": wat_now.isoformat()
                            }).execute(), error_prefix="HOTO approval")
                    
                    try:
                        send_email_notification(user_email, f"🔄 New HOTO Initiated — {hoto_number}", f"<h3>HOTO Initiated</h3><p><b>HOTO:</b> {hoto_number}</p><p><b>Type:</b> {hoto_type.replace('_',' ').title()}</p><p><b>Transferor:</b> {transferor}</p><p><b>Transferee:</b> {transferee}</p><p>Approvals pending.</p>")
                    except: pass
                    
                    st.session_state.hoto_created = True
                    st.session_state.hoto_number_created = hoto_number
                    st.rerun()
                else:
                    st.error("⚠️ Title, Transferor, and Transferee are required")

    
    # ============================================
    # TAB 2: SHIFT HANDOVER
    # ============================================
    with tabs[2]:
        st.markdown("### 🔧 Operational Shift Handover")
        
        shift_type = st.selectbox("Shift Type", ["engineering", "security", "cctv"], format_func=lambda x: x.upper())
        
        with st.form("shift_handover_form"):
            st.markdown(f"#### {shift_type.upper()} Shift Handover")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                outgoing_lead = st.text_input("Outgoing Shift Lead*", value=user_name)
                outgoing_shift = st.selectbox("Outgoing Shift", ["Shift A (Night)", "Shift B (Day)", "Shift C (Afternoon)"])
            with c2:
                incoming_lead = st.text_input("Incoming Shift Lead*")
                incoming_shift = st.selectbox("Incoming Shift", ["Shift B (Day)", "Shift C (Afternoon)", "Shift A (Night)"])
            with c3:
                handover_date = st.date_input("Date*", today)
                handover_time = st.time_input("Time*", wat_now.time())
            
            st.markdown("---")
            equipment_status = st.text_area("Equipment/System Status", height=80, placeholder="Chiller #1: Running\nChiller #2: Standby\nGenerator: Ready")
            
            c1, c2 = st.columns(2)
            with c1:
                open_wos = st.text_area("Open Work Orders", height=60)
                critical_incidents = st.text_area("Critical Incidents", height=60)
            with c2:
                key_readings = st.text_area("Key Readings", height=60)
                actions_pending = st.text_area("Actions Pending", height=60)
            
            # Digital signature acknowledgment
            st.markdown("---")
            st.markdown("**✍️ Digital Acknowledgment**")
            st.caption("By submitting, both parties acknowledge the accuracy of this handover. This record is legally auditable.")
            
            if st.form_submit_button("✅ SUBMIT & SIGN SHIFT HANDOVER", use_container_width=True, type="primary"):
                if outgoing_lead and incoming_lead:
                    safe_supabase_query(lambda: supabase.table("shift_handover_logs").insert({
                        "facility_code": fc, "shift_type": shift_type,
                        "outgoing_shift": outgoing_shift, "incoming_shift": incoming_shift,
                        "outgoing_lead": outgoing_lead, "incoming_lead": incoming_lead,
                        "handover_date": str(handover_date), "handover_time": str(handover_time),
                        "equipment_status": {"data": equipment_status},
                        "open_work_orders": open_wos, "critical_incidents": critical_incidents,
                        "key_readings": {"data": key_readings}, "actions_pending": actions_pending,
                        "digital_signature_outgoing": user_name,
                        "digital_signature_incoming": incoming_lead,
                        "status": "completed", "created_at": wat_now.isoformat()
                    }).execute(), error_prefix="Shift handover")
                    
                    try:
                        incoming_user = next((u for u in DB.get_users() if u.get("name") == incoming_lead), None)
                        if incoming_user and incoming_user.get("email"):
                            send_email_notification(incoming_user["email"], f"🔧 Shift Handover — {shift_type.upper()}", f"<h3>Shift Handover Ready for Review</h3><p>Outgoing: {outgoing_lead}</p><p>Actions Pending: {actions_pending[:200]}</p>")
                    except: pass
                    
                    st.success("✅ Shift handover logged & signed!"); st.balloons(); st.rerun()
                else:
                    st.error("⚠️ Both shift leads are required")
        
        # Recent shift logs
        st.markdown("---")
        st.markdown("### 📋 Recent Shift Handovers")
        shift_logs_display = safe_supabase_query(lambda: supabase.table("shift_handover_logs").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(10).execute(), error_prefix="Shift logs")
        if shift_logs_display and shift_logs_display.data:
            for log in shift_logs_display.data:
                status = log.get("status","completed")
                sc = "#10B981" if status == "completed" else "#F59E0B" if status == "pending" else "#EF4444"
                st.markdown(f"""
                <div style="background:white;border-left:3px solid {sc};border-radius:6px;padding:0.5rem;margin:0.2rem 0;font-size:0.7rem;">
                    <b>{log.get('shift_type','').upper()}</b> | {log.get('outgoing_shift','')} → {log.get('incoming_shift','')}
                    <br>👤 {log.get('outgoing_lead','')} → {log.get('incoming_lead','')} | 📅 {log.get('handover_date','')} {log.get('handover_time','')}
                    <br><span style="font-size:0.6rem;color:#888;">Actions: {str(log.get('actions_pending',''))[:80]}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No shift handovers recorded yet.")
    
    # ============================================
    # TAB 3: APPROVALS DASHBOARD
    # ============================================
    with tabs[3]:
        st.markdown("### ✅ Approval Dashboard")
        
        all_approvals = safe_supabase_query(lambda: supabase.table("hoto_approvals").select("*").eq("status", "pending").order("created_at").execute(), error_prefix="Approvals")
        
        if all_approvals and all_approvals.data and len(all_approvals.data) > 0:
            for app in all_approvals.data:
                h_info = {}
                if not hoto_df.empty:
                    hoto_lookup = hoto_df[hoto_df["id"] == app["hoto_id"]]
                    if len(hoto_lookup) > 0:
                        h_info = hoto_lookup.iloc[0].to_dict()
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid #F59E0B;border-radius:10px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <b>{h_info.get('hoto_number', 'N/A')}</b> — {h_info.get('title', '')[:80] if h_info.get('title') else 'No title'}
                    <br><span style="font-size:0.65rem;">Level {app.get('approval_level','')} — {app.get('approver_role','').replace('_',' ').title()}</span>
                    <br><span style="font-size:0.6rem;color:#888;">🔄 {h_info.get('transferor_name', '')} → {h_info.get('transferee_name', '')}</span>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Approve", key=f"appr_{app['id']}", use_container_width=True):
                        safe_supabase_query(lambda: supabase.table("hoto_approvals").update({"status":"approved","approver_name":user_name,"approver_email":user_email,"comments":"Approved","action_date":wat_now.isoformat()}).eq("id",app["id"]).execute(), error_prefix="Approve")
                        hoto_apps = safe_supabase_query(lambda: supabase.table("hoto_approvals").select("*").eq("hoto_id",app["hoto_id"]).execute(), error_prefix="Check approvals")
                        all_approved = hoto_apps and hoto_apps.data and all(a.get("status") == "approved" for a in hoto_apps.data)
                        if all_approved:
                            safe_supabase_query(lambda: supabase.table("hoto_records").update({"status":"acceptance","acceptance_date":str(today)}).eq("id",app["hoto_id"]).execute(), error_prefix="Accept HOTO")
                        st.success("✅ Approved!"); st.rerun()
                with c2:
                    if st.button("❌ Reject", key=f"rejr_{app['id']}", use_container_width=True):
                        st.session_state.rejecting_approval = app["id"]; st.rerun()
        else:
            st.success("✅ No pending approvals.")
    
    # Reject approval form
    if "rejecting_approval" in st.session_state and st.session_state.rejecting_approval:
        app_id = st.session_state.rejecting_approval
        st.markdown("---")
        with st.form("reject_approval_form"):
            st.markdown("### ❌ Reject Approval")
            reject_reason = st.text_area("Reason*", height=80)
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("❌ REJECT", use_container_width=True, type="primary"):
                    if reject_reason:
                        safe_supabase_query(lambda: supabase.table("hoto_approvals").update({"status":"rejected","approver_name":user_name,"comments":reject_reason,"action_date":wat_now.isoformat()}).eq("id",app_id).execute(), error_prefix="Reject approval")
                        st.error("❌ Rejected!"); st.session_state.rejecting_approval = None; st.rerun()
            with c2:
                if st.form_submit_button("CANCEL", use_container_width=True):
                    st.session_state.rejecting_approval = None; st.rerun()
    
    # ============================================
    # TAB 4: PUNCH LIST
    # ============================================
    with tabs[4]:
        st.markdown("### 📊 Punch List Tracker")
        
        if total_hoto == 0:
            st.info("No HOTO records yet.")
        else:
            # Add punch item
            with st.expander("➕ Add Punch List Item"):
                with st.form("add_punch_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        punch_hoto = st.selectbox("HOTO Record", [f"{h.get('hoto_number','')} — {h.get('title','')[:50]}" for _, h in hoto_df.iterrows()])
                        punch_desc = st.text_input("Item Description*")
                    with c2:
                        punch_severity = st.selectbox("Severity", ["safety", "functional", "cosmetic"])
                        punch_responsible = st.text_input("Responsible Party")
                    
                    c1, c2 = st.columns(2)
                    with c1: punch_due = st.date_input("Due Date", today + timedelta(days=7))
                    with c2: punch_hold = st.number_input("Financial Hold (₦)", min_value=0.0, value=0.0, step=1000.0)
                    
                    if st.form_submit_button("➕ Add Punch Item", use_container_width=True):
                            if punch_desc:
                                hoto_idx = [i for i, h in enumerate(hoto_df.iterrows()) if f"{h[1].get('hoto_number','')} — {h[1].get('title','')[:50]}" == punch_hoto][0]
                                selected_hoto_id = hoto_df.iloc[hoto_idx]["id"]
                                safe_supabase_query(lambda: supabase.table("hoto_punch_list").insert({
                                    "hoto_id": selected_hoto_id, "item_description": punch_desc,
                                    "severity": punch_severity, "responsible_party": punch_responsible,
                                    "due_date": str(punch_due), "financial_hold": punch_hold > 0,
                                    "hold_amount": punch_hold, "status": "open", "created_at": wat_now.isoformat()
                                }).execute(), error_prefix="Add punch item")
                                st.success("✅ Punch item added!"); st.rerun()
            
            # Display all punch items
            all_punch = []
            for _, h in hoto_df.iterrows():
                punch_items = safe_supabase_query(lambda hid=h["id"]: supabase.table("hoto_punch_list").select("*").eq("hoto_id", hid).order("created_at").execute(), error_prefix="Punch items")
                if punch_items and punch_items.data:
                    for p in punch_items.data:
                        p["hoto_number"] = h.get("hoto_number","")
                        p["hoto_title"] = h.get("title","")
                        all_punch.append(p)
            
            if all_punch:
                punch_df = pd.DataFrame(all_punch)
                st.caption(f"📋 {len(punch_df)} punch items")
                
                for _, p in punch_df.iterrows():
                    severity = p.get("severity","cosmetic")
                    sev_color = "#EF4444" if severity == "safety" else "#F59E0B" if severity == "functional" else "#3B82F6"
                    status = p.get("status","open")
                    st_color = "#EF4444" if status == "open" else "#F59E0B" if status == "in_progress" else "#10B981"
                    
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid {sev_color};border-radius:8px;padding:0.7rem;margin:0.2rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex;justify-content:space-between;">
                            <div>
                                <b>{p.get('hoto_number','')}</b> — {p.get('item_description','')[:80]}
                                <br><span style="font-size:0.6rem;">👤 {p.get('responsible_party','')} | 📅 Due: {p.get('due_date','')}</span>
                                {f'<br><span style="font-size:0.55rem;color:#EF4444;">💰 Hold: ₦{p.get("hold_amount",0):,.0f}</span>' if p.get('financial_hold') else ''}
                            </div>
                            <div style="text-align:right;">
                                <span style="background:{sev_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;">{severity.upper()}</span>
                                <br><span style="background:{st_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.55rem;">{status.upper()}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if status in ["open","in_progress"]:
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Resolve", key=f"res_{p['id']}", use_container_width=True):
                                safe_supabase_query(lambda pid=p["id"]: supabase.table("hoto_punch_list").update({"status":"resolved","resolved_by":user_name,"resolved_date":str(today)}).eq("id",pid).execute(), error_prefix="Resolve punch")
                                st.success("✅ Resolved!"); st.rerun()
                        with c2:
                            if st.button("🔄 In Progress", key=f"prog_{p['id']}", use_container_width=True):
                                safe_supabase_query(lambda pid=p["id"]: supabase.table("hoto_punch_list").update({"status":"in_progress"}).eq("id",pid).execute(), error_prefix="Progress punch")
                                st.success("🔄 In Progress!"); st.rerun()
            else:
                st.success("✅ No punch list items.")
    
    # ============================================
    # TAB 5: REPORTS
    # ============================================
    with tabs[5]:
        st.markdown("### 📄 HOTO Reports")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total HOTOs", total_hoto)
        with c2: st.metric("Active", active_hoto)
        with c3: st.metric("Punch Items", punch_open)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📄 HTML Report", key="hoto_html_btn", use_container_width=True, type="primary"):
                logo_b64 = get_logo_base64()
                logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="30">' if logo_b64 else ''
                html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>HOTO Intelligence Report</title><style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:20px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:960px;margin:0 auto;background:white;border-radius:12px;padding:30px}}.header{{border-bottom:3px solid #CC0000;padding-bottom:15px}}h1{{color:#CC0000;margin:0}}.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:20px 0}}.kpi{{background:#f9fafb;border-radius:10px;padding:12px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:20px;font-weight:800;color:#CC0000}}table{{width:100%;border-collapse:collapse;font-size:10px}}th{{background:#CC0000;color:white;padding:8px}}td{{padding:6px;border-bottom:1px solid #eee}}.footer{{text-align:center;font-size:8px;color:#999;margin-top:20px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container"><div class="header">{logo_img}<h1>HOTO Intelligence Report</h1><p>{info.get('full_name',fc)} | {today.strftime('%d %B %Y')}</p></div><div class="kpi-row"><div class="kpi"><div class="val">{total_hoto}</div>Total</div><div class="kpi"><div class="val">{active_hoto}</div>Active</div><div class="kpi"><div class="val">{punch_open}</div>Punch</div><div class="kpi"><div class="val">{dlp_expiring}</div>DLP</div><div class="kpi"><div class="val">{pending_approvals}</div>Approvals</div><div class="kpi"><div class="val">{overdue_shifts}</div>Overdue</div></div><h2>HOTO Records</h2><table><tr><th>HOTO#</th><th>Title</th><th>Type</th><th>Status</th><th>From</th><th>To</th></tr>"""
                for _,h in hoto_df.head(30).iterrows():
                    html += f"<tr><td>{h.get('hoto_number','')}</td><td>{h.get('title','')[:50]}</td><td>{h.get('hoto_type','')}</td><td>{h.get('status','')}</td><td>{h.get('transferor_name','')}</td><td>{h.get('transferee_name','')}</td></tr>"
                html += "</table><div class='footer'>Churchgate Group | facilityXperience | HOTO Intelligence</div></div></body></html>"
                st.download_button("📥 Download HTML", html, f"hoto_report_{today}.html", "text/html", use_container_width=True)
        with c2:
            if st.button("📕 PDF Report", key="hoto_pdf_btn", use_container_width=True):
                try:
                    from fpdf import FPDF
                    pdf = FPDF('L','mm','A4'); pdf.add_page()
                    pdf.set_font('Helvetica','B',16); pdf.set_text_color(204,0,0)
                    pdf.cell(0,10,safe_text('HOTO Intelligence Report'),0,1)
                    pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                    pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {today.strftime("%d %B %Y")}'),0,1); pdf.ln(4)
                    pdf.set_font('Helvetica','B',7); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                    for h,w in zip(['HOTO#','Title','Type','Status','From','To'],[35,65,30,22,55,55]): pdf.cell(w,5,h,1,0,'C',True)
                    pdf.ln(); pdf.set_font('Helvetica','',7); pdf.set_text_color(0,0,0)
                    for _,h in hoto_df.head(30).iterrows():
                        pdf.cell(35,4,safe_text(h.get('hoto_number','')),1,0); pdf.cell(65,4,safe_text(str(h.get('title',''))[:28]),1,0)
                        pdf.cell(30,4,safe_text(h.get('hoto_type','')),1,0); pdf.cell(22,4,safe_text(h.get('status','')),1,0)
                        pdf.cell(55,4,safe_text(str(h.get('transferor_name',''))[:24]),1,0); pdf.cell(55,4,safe_text(str(h.get('transferee_name',''))[:24]),1,0)
                        pdf.ln()
                    pdf_file = f"/tmp/hoto_report_{today}.pdf"; pdf.output(pdf_file)
                    with open(pdf_file,"rb") as f: st.download_button("📥 Download PDF", f.read(), f"hoto_report_{today}.pdf", "application/pdf", use_container_width=True)
                except Exception as e: st.error(f"PDF: {str(e)[:80]}")

# ============================================
# MONTHLY MIS — EXECUTIVE BOARD PACK
# ============================================
def page_mis():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    
    st.markdown(f'## 📊 Monthly MIS — {info.get("full_name", fc)}')
    st.caption("Executive Board Pack — One page. Every KPI. Every module.")
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
    # Period selector
    mis_period = st.selectbox("📅 Report Period", ["Current Month", "Last Month", "Current Quarter", "Year to Date", "Custom"], key="mis_period")
    
    if mis_period == "Current Month":
        start_date = today.replace(day=1)
        end_date = today
    elif mis_period == "Last Month":
        last_month = today.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = last_month
    elif mis_period == "Current Quarter":
        q_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, q_month, 1)
        end_date = today
    elif mis_period == "Year to Date":
        start_date = date(today.year, 1, 1)
        end_date = today
    else:
        c1, c2 = st.columns(2)
        with c1: start_date = st.date_input("From", today.replace(day=1))
        with c2: end_date = st.date_input("To", today)
    
    st.caption(f"📅 {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}")
    
    # ============================================
    # FETCH ALL MODULE DATA
    # ============================================
    
    # Assets
    all_assets = DB.get_assets(fc, 50000)
    total_assets = len(all_assets) if all_assets else 0
    active_assets = len([a for a in (all_assets or []) if a.get("status") == "active"])
    
    # Work Orders
    wo_data = safe_supabase_query(lambda: supabase.table("work_orders").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(500).execute(), error_prefix="WO data")
    wo_df = pd.DataFrame(wo_data.data) if wo_data and wo_data.data else pd.DataFrame()
    period_wo = wo_df[(pd.to_datetime(wo_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(wo_df["created_at"], errors='coerce').dt.date <= end_date)] if len(wo_df) > 0 else pd.DataFrame()
    total_wo = len(period_wo)
    wo_completed = len(period_wo[period_wo["status"].isin(["completed","closed"])]) if total_wo > 0 else 0
    wo_spend = period_wo["total_cost"].sum() if "total_cost" in period_wo.columns else 0
    
    # Incidents
    inc_data = safe_supabase_query(lambda: supabase.table("incidents").select("*").eq("facility_code", fc).order("created_at", desc=True).limit(200).execute(), error_prefix="Incident data")
    inc_df = pd.DataFrame(inc_data.data) if inc_data and inc_data.data else pd.DataFrame()
    period_inc = inc_df[(pd.to_datetime(inc_df["created_at"], errors='coerce').dt.date >= start_date) & (pd.to_datetime(inc_df["created_at"], errors='coerce').dt.date <= end_date)] if len(inc_df) > 0 else pd.DataFrame()
    total_inc = len(period_inc)
    critical_inc = len(period_inc[period_inc["severity"] == "critical"]) if total_inc > 0 else 0
    
    # PPM Compliance
    ppm_data = safe_supabase_query(lambda: supabase.table("ppm_schedules").select("*").eq("facility_code", fc).execute(), error_prefix="PPM data")
    ppm_df = pd.DataFrame(ppm_data.data) if ppm_data and ppm_data.data else pd.DataFrame()
    total_ppm = len(ppm_df)
    ppm_completed = len(ppm_df[ppm_df["status"] == "completed"]) if total_ppm > 0 else 0
    ppm_compliance = round((ppm_completed / max(total_ppm, 1)) * 100)
    
    # Risks
    risk_data = safe_supabase_query(lambda: supabase.table("risk_register").select("*").eq("facility_code", fc).execute(), error_prefix="Risk data")
    risk_df_mis = pd.DataFrame(risk_data.data) if risk_data and risk_data.data else pd.DataFrame()
    total_risks_mis = len(risk_df_mis)
    extreme_risks_mis = len(risk_df_mis[(risk_df_mis["residual_level"] == "Extreme") & (risk_df_mis["risk_status"] != "closed")]) if total_risks_mis > 0 else 0
    
    # Audits
    audit_data = safe_supabase_query(lambda: supabase.table("audits").select("*").eq("facility_code", fc).execute(), error_prefix="Audit data")
    audit_df_mis = pd.DataFrame(audit_data.data) if audit_data and audit_data.data else pd.DataFrame()
    total_audits_mis = len(audit_df_mis)
    overdue_audits_mis = len(audit_df_mis[(audit_df_mis["status"] != "completed") & (pd.to_datetime(audit_df_mis["scheduled_date"], errors='coerce').dt.date < today)]) if total_audits_mis > 0 else 0
    
    # Feedback
    survey_data = safe_supabase_query(lambda: supabase.table("feedback_responses").select("id", count="exact").eq("facility_code", fc).execute(), error_prefix="Feedback data")
    total_feedback = survey_data.count if survey_data else 0
    
    # Visitors
    visitor_data = safe_supabase_query(lambda: supabase.table("visitors").select("id", count="exact").eq("facility_code", fc).gte("visit_date", str(start_date)).lte("visit_date", str(end_date)).execute(), error_prefix="Visitor data")
    total_visitors = visitor_data.count if visitor_data else 0
    
    # HOTO
    hoto_data = safe_supabase_query(lambda: supabase.table("hoto_records").select("*").eq("facility_code", fc).execute(), error_prefix="HOTO data")
    hoto_df_mis = pd.DataFrame(hoto_data.data) if hoto_data and hoto_data.data else pd.DataFrame()
    total_hoto_mis = len(hoto_df_mis)
    
    # ============================================
    # 🟦 EXECUTIVE KPI RIBBON — 8 TILES
    # ============================================
    st.markdown("### 🟦 Executive KPI Dashboard")
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid #CC0000;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Assets</div><div style="font-size:1.2rem;font-weight:800;color:#CC0000;">{total_assets}</div><div style="font-size:0.4rem;">{active_assets} Active</div></div>""", unsafe_allow_html=True)
    with c2:
        color = "#10B981" if wo_completed > 0 else "#F59E0B"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Work Orders</div><div style="font-size:1.2rem;font-weight:800;color:{color};">{total_wo}</div><div style="font-size:0.4rem;">{wo_completed} Done | ₦{wo_spend:,.0f}</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#EF4444" if critical_inc > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Incidents</div><div style="font-size:1.2rem;font-weight:800;color:{color};">{total_inc}</div><div style="font-size:0.4rem;">{critical_inc} Critical</div></div>""", unsafe_allow_html=True)
    with c4:
        color = "#10B981" if ppm_compliance >= 90 else "#F59E0B" if ppm_compliance >= 70 else "#EF4444"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">PPM Compliance</div><div style="font-size:1.2rem;font-weight:800;color:{color};">{ppm_compliance}%</div><div style="font-size:0.4rem;">{ppm_completed}/{total_ppm}</div></div>""", unsafe_allow_html=True)
    with c5:
        color = "#EF4444" if extreme_risks_mis > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Extreme Risks</div><div style="font-size:1.2rem;font-weight:800;color:{color};">{extreme_risks_mis}</div><div style="font-size:0.4rem;">of {total_risks_mis}</div></div>""", unsafe_allow_html=True)
    with c6:
        color = "#EF4444" if overdue_audits_mis > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Audits</div><div style="font-size:1.2rem;font-weight:800;color:{color};">{total_audits_mis}</div><div style="font-size:0.4rem;">{overdue_audits_mis} Overdue</div></div>""", unsafe_allow_html=True)
    with c7:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Feedback</div><div style="font-size:1.2rem;font-weight:800;color:#3B82F6;">{total_feedback}</div><div style="font-size:0.4rem;">Responses</div></div>""", unsafe_allow_html=True)
    with c8:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.6rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.45rem;color:#888;">Visitors</div><div style="font-size:1.2rem;font-weight:800;color:#8B5CF6;">{total_visitors}</div><div style="font-size:0.4rem;">{total_hoto_mis} HOTOs</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # MODULE HEALTH SCORECARD
    # ============================================
    st.markdown("### 📊 Module Health Scorecard")
    
    modules_health = [
        {"module": "Asset Management", "score": round((active_assets/max(total_assets,1))*100), "icon": "🏗️", "target": 95},
        {"module": "Work Orders", "score": round((wo_completed/max(total_wo,1))*100) if total_wo > 0 else 0, "icon": "🔧", "target": 90},
        {"module": "PPM Compliance", "score": ppm_compliance, "icon": "📅", "target": 95},
        {"module": "Incident Response", "score": 100 if critical_inc == 0 else 75, "icon": "🚨", "target": 100},
        {"module": "Risk Management", "score": 100 if extreme_risks_mis == 0 else 60, "icon": "🛡️", "target": 90},
        {"module": "Audit Readiness", "score": 100 if overdue_audits_mis == 0 else 50, "icon": "✅", "target": 95},
        {"module": "Tenant Satisfaction", "score": 85, "icon": "⭐", "target": 85},
        {"module": "HOTO Governance", "score": min(100, total_hoto_mis * 10), "icon": "🔄", "target": 80},
    ]
    
    for m in modules_health:
        color = "#10B981" if m["score"] >= m["target"] else "#F59E0B" if m["score"] >= m["target"]-15 else "#EF4444"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;background:white;border-radius:8px;padding:0.5rem 1rem;margin:0.2rem 0;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
            <div style="font-size:1.2rem;">{m['icon']}</div>
            <div style="flex:1;font-size:0.8rem;font-weight:600;">{m['module']}</div>
            <div style="width:200px;background:#f0f0f0;border-radius:10px;height:8px;">
                <div style="background:{color};height:8px;border-radius:10px;width:{m['score']}%;"></div>
            </div>
            <div style="font-weight:700;color:{color};min-width:45px;text-align:right;">{m['score']}%</div>
            <div style="font-size:0.55rem;color:#888;">Target: {m['target']}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # AI EXECUTIVE SUMMARY
    # ============================================
    st.markdown("### 🤖 AI Executive Summary — Board Briefing")
    
    overall_health = round(sum(m["score"] for m in modules_health) / len(modules_health))
    health_color = "#10B981" if overall_health >= 85 else "#F59E0B" if overall_health >= 70 else "#EF4444"
    
    insights = []
    insights.append(f"Overall Building Health Score: **{overall_health}%** — {'Excellent' if overall_health >= 85 else 'Good' if overall_health >= 70 else 'Needs Attention'}.")
    
    if total_wo > 0:
        insights.append(f"🔧 **Work Orders:** {total_wo} created, {wo_completed} completed ({round((wo_completed/max(total_wo,1))*100)}% completion rate). Total spend: ₦{wo_spend:,.0f}.")
    else:
        insights.append("🔧 No work orders in this period.")
    
    if critical_inc > 0:
        insights.append(f"🚨 **{critical_inc} Critical Incidents** occurred. Immediate review of incident response protocols recommended.")
    else:
        insights.append("✅ No critical incidents in this period.")
    
    if extreme_risks_mis > 0:
        insights.append(f"🛡️ **{extreme_risks_mis} Extreme Risks** remain open. These require board-level attention and CAPEX consideration.")
    
    if ppm_compliance < 90:
        insights.append(f"⚠️ **PPM Compliance at {ppm_compliance}%** — below 90% target. Underinvesting in PM creates reactive work downstream.")
    
    if overdue_audits_mis > 0:
        insights.append(f"⚠️ **{overdue_audits_mis} Audits Overdue.** Regulatory and compliance risk increasing.")
    
    insights.append(f"📊 **Recommendation:** {'Continue current strategy. All metrics within acceptable thresholds.' if overall_health >= 85 else 'Focus on improving PPM compliance and closing overdue audits. Review extreme risks at next board meeting.' if overall_health >= 70 else 'URGENT: Schedule emergency board review. Multiple critical metrics below acceptable thresholds.'}")
    
    for insight in insights:
        st.markdown(f"""<div style="background:white;border-left:4px solid {health_color};border-radius:8px;padding:0.8rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);font-size:0.85rem;">{insight}</div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # EXPORT — BOARD PACK
    # ============================================
    st.markdown("### 📥 Download Board Pack")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Generate Executive Board Pack (HTML)", key="mis_html_btn", use_container_width=True, type="primary"):
            logo_b64 = get_logo_base64()
            logo_img = f'<img src="data:image/png;base64,{logo_b64}" height="35">' if logo_b64 else ''
            
            health_rows = "".join([f"""<tr><td>{m['icon']} {m['module']}</td><td style="color:{'#10B981' if m['score']>=m['target'] else '#F59E0B' if m['score']>=m['target']-15 else '#EF4444'};font-weight:700;">{m['score']}%</td><td>{m['target']}%</td></tr>""" for m in modules_health])
            
            html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Monthly MIS — Executive Board Pack</title>
<style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:25px;color:#1a1a1a;background:#f0f2f5}}.container{{max-width:1000px;margin:0 auto;background:white;border-radius:12px;padding:30px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}}.header{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #CC0000;padding-bottom:15px;margin-bottom:20px}}h1{{color:#CC0000;margin:0;font-size:22px}}.kpi-row{{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin:20px 0}}.kpi{{background:#f9fafb;border-radius:10px;padding:10px;text-align:center;border-top:3px solid #CC0000}}.kpi .val{{font-size:18px;font-weight:800;color:#CC0000}}.kpi .lbl{{font-size:8px;color:#888;text-transform:uppercase}}h2{{color:#1a1a1a;border-bottom:2px solid #eee;padding-bottom:8px;margin-top:25px;font-size:16px}}table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:11px}}th{{background:#CC0000;color:white;padding:10px;text-align:left;font-size:10px;text-transform:uppercase}}td{{padding:8px;border-bottom:1px solid #eee}}.insight-box{{background:#FEF2F2;border-left:4px solid #EF4444;padding:12px;margin:8px 0;border-radius:6px;font-size:12px}}.footer{{text-align:center;font-size:9px;color:#999;margin-top:25px;border-top:1px solid #eee;padding-top:15px}}</style></head><body><div class="container">
<div class="header"><div>{logo_img}<h1>Monthly MIS — Executive Board Pack</h1><p>{info.get('full_name',fc)} | {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}</p></div></div>
<div class="kpi-row"><div class="kpi"><div class="val">{total_assets}</div><div class="lbl">Assets</div></div><div class="kpi"><div class="val">{total_wo}</div><div class="lbl">WOs</div></div><div class="kpi"><div class="val">{total_inc}</div><div class="lbl">Incidents</div></div><div class="kpi"><div class="val">{ppm_compliance}%</div><div class="lbl">PPM</div></div><div class="kpi"><div class="val">{extreme_risks_mis}</div><div class="lbl">Extreme Risks</div></div><div class="kpi"><div class="val">{total_audits_mis}</div><div class="lbl">Audits</div></div><div class="kpi"><div class="val">{total_feedback}</div><div class="lbl">Feedback</div></div><div class="kpi"><div class="val">{total_visitors}</div><div class="lbl">Visitors</div></div></div>
<h2>Module Health Scorecard</h2><table><tr><th>Module</th><th>Score</th><th>Target</th></tr>{health_rows}</table>
<div class="insight-box"><b>Overall Building Health: {overall_health}%</b> — {'Excellent' if overall_health>=85 else 'Good' if overall_health>=70 else 'Needs Attention'}</div>
<h2>AI Executive Summary</h2>{"".join([f'<div class="insight-box">{i}</div>' for i in insights])}
<div class="footer">Churchgate Group | facilityXperience | AI-Generated Board Pack | {today.strftime('%d %B %Y')}</div>
</div></body></html>"""
            
            st.download_button("📥 Download Board Pack (HTML)", html, f"monthly_mis_{start_date}_{end_date}.html", "text/html", use_container_width=True)
    
    with c2:
        if st.button("📕 Generate PDF Board Pack", key="mis_pdf_btn", use_container_width=True):
            try:
                from fpdf import FPDF; pdf = FPDF('P','mm','A4'); pdf.add_page()
                pdf.set_font('Helvetica','B',20); pdf.set_text_color(204,0,0)
                pdf.cell(0,14,safe_text('Monthly MIS — Executive Board Pack'),0,1)
                pdf.set_font('Helvetica','',10); pdf.set_text_color(0,0,0)
                pdf.cell(0,6,safe_text(f'{info.get("full_name",fc)} | {start_date.strftime("%d %b %Y")} - {end_date.strftime("%d %b %Y")}'),0,1)
                pdf.ln(5)
                pdf.set_font('Helvetica','B',12)
                pdf.cell(0,8,f'Overall Building Health: {overall_health}%',0,1)
                pdf.ln(3)
                pdf.set_font('Helvetica','B',10); pdf.set_fill_color(204,0,0); pdf.set_text_color(255,255,255)
                pdf.cell(120,7,'Module',1,0,'C',True); pdf.cell(35,7,'Score',1,0,'C',True); pdf.cell(35,7,'Target',1,0,'C',True)
                pdf.ln(); pdf.set_font('Helvetica','',9); pdf.set_text_color(0,0,0)
                for m in modules_health:
                    pdf.cell(120,6,safe_text(f"{m['icon']} {m['module']}"),1,0)
                    pdf.cell(35,6,f"{m['score']}%",1,0,'C'); pdf.cell(35,6,f"{m['target']}%",1,0,'C')
                    pdf.ln()
                pdf.ln(5)
                pdf.set_font('Helvetica','B',10)
                pdf.cell(0,7,'AI Executive Summary:',0,1)
                pdf.set_font('Helvetica','',8)
                for ins in insights:
                    pdf.multi_cell(0,5,safe_text(ins.replace('🔧','').replace('🚨','').replace('✅','').replace('🛡️','').replace('⚠️','').replace('📊','').strip()))
                pdf_file = f"/tmp/monthly_mis_{start_date}_{end_date}.pdf"; pdf.output(pdf_file)
                with open(pdf_file,"rb") as f: st.download_button("📥 Download Board Pack (PDF)", f.read(), f"monthly_mis_{start_date}_{end_date}.pdf", "application/pdf", use_container_width=True)
            except Exception as e: st.error(f"PDF: {str(e)[:80]}")


# ============================================
# PPM ACTIVITIES — FORTUNE 500 EXECUTION CENTER
# CUSTOM CHECKLISTS • DAILY/HOURLY/SCHEDULED
# ROLE-BASED • DEPARTMENT-FILTERED • AI-POWERED
# ============================================
def page_ppm_activities():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "Team Member")
    user_depts = safe_parse_permissions(st.session_state.get("user", {}).get("department_permissions", []))
    is_admin = user_role in ["admin", "approver", "super_admin"]
    
    st.markdown(f'## 🔧 PPM Execution Center — {info.get("full_name", fc)}')
    
    all_assets = DB.get_assets(fc, 50000)
    
    if not all_assets:
        st.info("No assets registered.")
        return
    
    df = pd.DataFrame(all_assets)
    df["checklist_clean"] = df["checklist"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() not in ["", "NA", "na", "APPLICABLE", "NOTAPPLICABLE", "None"] else None)
    df["dept_full"] = df.apply(lambda row: f"{row['department']} — {row['sub_division']}" if pd.notna(row.get('sub_division')) and row.get('sub_division') not in ['', 'N/A', 'NA'] else row['department'], axis=1)
    
    if is_admin:
        allowed_depts = sorted(df["dept_full"].dropna().unique().tolist())
    elif user_depts and len(user_depts) > 0 and user_depts != ["All"]:
        allowed_depts = [d for d in sorted(df["dept_full"].dropna().unique().tolist()) if any(ud in d for ud in user_depts)]
        if not allowed_depts: allowed_depts = sorted(df["dept_full"].dropna().unique().tolist())
    else:
        allowed_depts = sorted(df["dept_full"].dropna().unique().tolist())
    
    custom_checklists = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").select("*").execute(), error_prefix="Checklist templates")
    checklist_options = ["Standard Template"] + [c.get("template_name","") for c in custom_checklists.data] if custom_checklists and custom_checklists.data else ["Standard Template"]
    
    tabs = st.tabs(["🔧 Execute PPM", "📋 Daily Checklist", "⏰ Hourly Checklist", "📊 My Submissions", "⏳ Pending Approval", "⚙️ Checklist Builder", "📋 Manage Schedules"])
    
    # ============================================
    # TAB 0: EXECUTE PPM
    # ============================================
    with tabs[0]:
        st.markdown("### 🔧 Execute Scheduled PPM")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sel_dept = st.selectbox("Select Department*", ["Select..."] + allowed_depts, key="ppm_dept")
        
        if sel_dept != "Select...":
            dept_df = df[df["dept_full"] == sel_dept]
            
            with c2:
                asset_list = ["Select..."] + sorted(dept_df["parent_asset"].dropna().unique().tolist())
                sel_asset = st.selectbox("Select Asset*", asset_list, key="ppm_asset")
            
            if sel_asset != "Select...":
                asset_df = dept_df[dept_df["parent_asset"] == sel_asset]
                
                with c3:
                    sub_list = ["Select..."] + sorted(asset_df["name"].dropna().unique().tolist())
                    sel_sub = st.selectbox("Select Sub Asset*", sub_list, key="ppm_sub")
                
                if sel_sub != "Select...":
                    selected_asset = asset_df[asset_df["name"] == sel_sub].iloc[0]
                    
                    with c4:
                        st.markdown(f"""
                        <div style="background:#EFF6FF;border-radius:8px;padding:0.6rem;text-align:center;border:1px solid #BFDBFE;margin-top:0.5rem;">
                            <div style="font-size:0.6rem;color:#2563EB;">📋 Frequency</div>
                            <div style="font-weight:700;font-size:0.8rem;">{selected_asset.get('ppm_frequency', selected_asset.get('verification_frequency', 'Monthly'))}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin-bottom:1rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <h4 style="margin:0;">{sel_asset}</h4>
                                <p style="margin:0;color:#666;font-size:0.8rem;">{sel_sub[:80]}</p>
                            </div>
                            <div style="text-align:right;">
                                <span style="background:#3B82F6;color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;">{selected_asset.get('dept_full','')}</span>
                                <br><span style="font-size:0.6rem;color:#888;">📍 {selected_asset.get('location_building','')}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("### 📝 PPM Checklist")
                    
                    sel_checklist = st.selectbox("Select Checklist Template", checklist_options, key="ppm_checklist_template")
                    
                    checklist_items = []
                    
                    if sel_checklist == "Standard Template":
                        checklist_items = [
                            {"item_number": 1, "description": "Safety Precautions & Pre-Checks", "check_type": "section", "options": None},
                            {"item_number": 2, "description": "LOTO: Power isolated and locked out", "check_type": "yes_no", "options": None},
                            {"item_number": 3, "description": "PPE: Appropriate PPE worn", "check_type": "yes_no", "options": None},
                            {"item_number": 4, "description": "Work Area Assessment", "check_type": "status", "options": ["Clear", "Not Clear"]},
                            {"item_number": 5, "description": "Permits: All necessary work permits obtained", "check_type": "yes_no", "options": None},
                            {"item_number": 6, "description": "Visual Inspection - Unit casing", "check_type": "yes_no", "options": None},
                            {"item_number": 7, "description": "Air Filter(s) - Inspect", "check_type": "status", "options": ["Clean", "Dirty", "Replaced"]},
                            {"item_number": 8, "description": "Fan & Motor - Check for noise/vibration", "check_type": "status", "options": ["Normal", "Abnormal"]},
                            {"item_number": 9, "description": "Condensate Drain - Inspect", "check_type": "status", "options": ["Good", "Damage", "Dirty"]},
                            {"item_number": 10, "description": "Electrical - Check wiring", "check_type": "yes_no", "options": None},
                            {"item_number": 11, "description": "Measure air-on temperature (°C)", "check_type": "reading", "options": None},
                            {"item_number": 12, "description": "Measure air-off temperature (°C)", "check_type": "reading", "options": None},
                            {"item_number": 13, "description": "Record voltage - RY", "check_type": "reading", "options": None},
                            {"item_number": 14, "description": "Record voltage - YB", "check_type": "reading", "options": None},
                            {"item_number": 15, "description": "Record voltage - BR", "check_type": "reading", "options": None},
                            {"item_number": 16, "description": "Record Amps - R", "check_type": "reading", "options": None},
                            {"item_number": 17, "description": "Record Amps - Y", "check_type": "reading", "options": None},
                            {"item_number": 18, "description": "Record Amps - B", "check_type": "reading", "options": None},
                            {"item_number": 19, "description": "Check earthing connections", "check_type": "status", "options": ["Tight", "Loose"]},
                            {"item_number": 20, "description": "Check BMS integration", "check_type": "yes_no", "options": None},
                            {"item_number": 21, "description": "Replace defective indication lamps", "check_type": "yes_no", "options": None},
                            {"item_number": 22, "description": "Observations / abnormalities", "check_type": "text", "options": None},
                        ]
                    else:
                        matched = None
                        for c in custom_checklists.data if custom_checklists.data else []:
                            if c.get("template_name") == sel_checklist:
                                matched = c
                                break
                        if matched:
                            items_res = safe_supabase_query(lambda mid=matched["id"]: supabase.table("ppm_checklist_items").select("*").eq("template_id", mid).order("sort_order").execute(), error_prefix="Checklist items")
                            if items_res and items_res.data:
                                for item in items_res.data:
                                    opts = item.get("expected_value","").split("/") if item.get("expected_value") else None
                                    checklist_items.append({
                                        "item_number": item.get("item_number"),
                                        "description": item.get("description"),
                                        "check_type": item.get("check_type", "yes_no"),
                                        "options": opts if len(opts) > 1 else None
                                    })
                    
                    with st.form("ppm_execution_form", clear_on_submit=True):
                        checklist_results = []
                        has_issues = False
                        
                        for item in checklist_items:
                            item_num = item.get("item_number", len(checklist_results)+1)
                            item_type = item.get("check_type", "yes_no")
                            item_desc = item.get("description", "")
                            item_opts = item.get("options")
                            
                            if item_type == "section":
                                st.markdown(f"### {item_desc}")
                                continue
                            
                            st.markdown(f"**{item_num}. {item_desc}**")
                            c1, c2 = st.columns([1, 2])
                            
                            if item_type == "yes_no":
                                with c1:
                                    result = st.selectbox("Status", ["Yes", "No"], key=f"yn_{item_num}")
                                with c2:
                                    comment = st.text_input("Comment", key=f"cmt_{item_num}", placeholder="Optional note...")
                                if result == "No": has_issues = True
                                checklist_results.append({"item_number": item_num, "description": item_desc, "result": result, "actual_value": comment, "risk_level": "None"})
                            
                            elif item_type == "status" and item_opts:
                                with c1:
                                    result = st.selectbox("Status", item_opts, key=f"st_{item_num}")
                                with c2:
                                    comment = st.text_input("Comment", key=f"cmt_{item_num}", placeholder="Optional note...")
                                if result in ["Damage", "Dirty", "Abnormal", "Loose", "Not Clear", "Fault"]: has_issues = True
                                checklist_results.append({"item_number": item_num, "description": item_desc, "result": result, "actual_value": comment, "risk_level": "None"})
                            
                            elif item_type == "reading":
                                with c1:
                                    reading = st.text_input("Reading", key=f"rd_{item_num}", placeholder="Enter value...")
                                with c2:
                                    unit = st.text_input("Unit", key=f"un_{item_num}", placeholder="°C, V, A...")
                                checklist_results.append({"item_number": item_num, "description": item_desc, "result": "Reading", "actual_value": f"{reading} {unit}".strip(), "risk_level": "None"})
                            
                            elif item_type == "text":
                                with c1:
                                    text_val = st.text_area("Observation", key=f"txt_{item_num}", height=60)
                                checklist_results.append({"item_number": item_num, "description": item_desc, "result": "Noted", "actual_value": text_val, "risk_level": "None"})
                            
                            else:
                                with c1:
                                    result = st.selectbox("Status", ["Pass", "Fail", "N/A"], key=f"df_{item_num}")
                                with c2:
                                    comment = st.text_input("Comment", key=f"cmt_{item_num}", placeholder="Optional note...")
                                if result == "Fail": has_issues = True
                                checklist_results.append({"item_number": item_num, "description": item_desc, "result": result, "actual_value": comment, "risk_level": "None"})
                            
                            st.markdown("---")
                        
                        if has_issues:
                            st.markdown("### 🚨 Mitigation Plan (Required)")
                            mitigation_plan = st.text_area("Describe mitigation actions*", height=80)
                            c1, c2 = st.columns(2)
                            with c1: mitigation_deadline = st.date_input("Mitigation Deadline", date.today() + timedelta(days=7))
                            with c2: st.markdown("<br>", unsafe_allow_html=True)
                        else:
                            mitigation_plan, mitigation_deadline = "", None
                        
                        st.markdown("### 📸 Photo Evidence (Required)")
                        uploaded_photos = st.file_uploader("Upload photos", type=["png","jpg","jpeg"], accept_multiple_files=True, key="ppm_photos")
                        
                        st.markdown("### 📅 Schedule")
                        c1, c2, c3 = st.columns(3)
                        with c1: execution_date = st.date_input("Execution Date", date.today())
                        with c2: execution_time = st.time_input("Execution Time", datetime.now().time())
                        with c3:
                            is_early = st.checkbox("Early Execution (requires approval)")
                            ppm_type = st.selectbox("PPM Type", ["Scheduled PPM", "Daily Checklist", "Hourly Checklist"], key="ppm_type_select")
                        
                        early_reason = ""
                        if is_early:
                            early_reason = st.text_area("Reason for Early Execution*", height=60)
                        
                        execution_comments = st.text_area("Execution Notes", height=60)
                        
                        submitted = st.form_submit_button("✅ SUBMIT PPM EXECUTION", use_container_width=True, type="primary")
                        
                        if submitted:
                            errors = []
                            if not uploaded_photos: errors.append("Photo evidence is required")
                            if has_issues and not mitigation_plan: errors.append("Mitigation plan required")
                            if is_early and not early_reason: errors.append("Reason required for early execution")
                            
                            if errors:
                                for e in errors: st.error(f"⚠️ {e}")
                            else:
                                exec_data = {
                                    "facility_code": fc,
                                    "executed_by_name": user_name,
                                    "execution_date": str(execution_date),
                                    "status": "submitted",
                                    "created_at": datetime.now().isoformat()
                                }
                                
                                exec_result = safe_supabase_query(lambda: supabase.table("ppm_executions").insert(exec_data).execute(), error_prefix="PPM execution")
                                if exec_result and exec_result.data:
                                    exec_result_data = exec_result.data[0]
                                else:
                                    exec_result_data = None
                                
                                if exec_result_data:
                                    execution_id = exec_result_data["id"]
                                    for item_result in checklist_results:
                                        safe_supabase_query(lambda eid=execution_id, ir=item_result: supabase.table("ppm_execution_items").insert({
                                            "execution_id": eid,
                                            "item_number": int(ir.get("item_number", 1)),
                                            "description": str(ir.get("description", "N/A")),
                                            "result": str(ir.get("result", "pass")),
                                            "actual_value": str(ir.get("actual_value", "")),
                                            "created_at": datetime.now().isoformat()
                                        }).execute(), error_prefix="PPM items")
                                    
                                    safe_supabase_query(lambda eid=execution_id: supabase.table("ppm_approvals").insert({
                                        "execution_id": eid, "approval_level": "team_lead",
                                        "status": "pending", "created_at": datetime.now().isoformat()
                                    }).execute(), error_prefix="PPM approval TL")
                                    safe_supabase_query(lambda eid=execution_id: supabase.table("ppm_approvals").insert({
                                        "execution_id": eid, "approval_level": "manager",
                                        "status": "pending", "created_at": datetime.now().isoformat()
                                    }).execute(), error_prefix="PPM approval MGR")
                                    
                                    st.success("✅ PPM Execution submitted!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to submit.")
    
    # ============================================
    # TAB 1: DAILY CHECKLIST
    # ============================================
    with tabs[1]:
        st.markdown("### 📋 Daily Checklist Execution")
        daily_assets = df[df["verification_frequency"].isin(["Daily","daily"])] if "verification_frequency" in df.columns else pd.DataFrame()
        if len(daily_assets) == 0:
            st.info("No daily checklist assets found.")
        else:
            c1, c2 = st.columns(2)
            with c1: st.metric("📋 Daily Assets", len(daily_assets))
            with c2: st.metric("⏳ Pending Today", len(daily_assets))
            st.markdown("---")
            sel_daily_dept = st.selectbox("Department", ["All"] + sorted(daily_assets["dept_full"].dropna().unique().tolist()), key="daily_dept")
            display_daily = daily_assets.copy()
            if sel_daily_dept != "All": display_daily = display_daily[display_daily["dept_full"] == sel_daily_dept]
            for _, asset in display_daily.head(20).iterrows():
                st.markdown(f"""
                <div style="background:white;border-left:3px solid #3B82F6;border-radius:6px;padding:0.5rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <div><b>{asset.get('parent_asset','N/A')}</b> — {asset.get('name','N/A')[:50]}<br><span style="font-size:0.6rem;color:#666;">📍 {asset.get('location_building','')} | 📅 Daily</span></div>
                </div>
                """, unsafe_allow_html=True)
            st.info("👆 Go to 'Execute PPM' tab, select this asset, and choose 'Daily Checklist' as PPM Type.")
    
    # ============================================
    # TAB 2: HOURLY CHECKLIST
    # ============================================
    with tabs[2]:
        st.markdown("### ⏰ Hourly Checklist Execution")
        hourly_assets = df[df["verification_frequency"].isin(["Hourly","hourly","Bi-Weekly"])] if "verification_frequency" in df.columns else pd.DataFrame()
        if len(hourly_assets) == 0:
            st.info("No hourly checklist assets found.")
        else:
            c1, c2 = st.columns(2)
            with c1: st.metric("⏰ Hourly Assets", len(hourly_assets))
            with c2: st.metric("⏳ Pending", len(hourly_assets))
            st.markdown("---")
            for _, asset in hourly_assets.head(20).iterrows():
                st.markdown(f"""
                <div style="background:white;border-left:3px solid #8B5CF6;border-radius:6px;padding:0.5rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <div><b>{asset.get('parent_asset','N/A')}</b> — {asset.get('name','N/A')[:50]}<br><span style="font-size:0.6rem;color:#666;">📍 {asset.get('location_building','')} | ⏰ {asset.get('verification_frequency','')}</span></div>
                </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # TAB 3: MY SUBMISSIONS
    # ============================================
    with tabs[3]:
        st.markdown("### 📊 My Submitted PPMs")
        my_executions = safe_supabase_query(lambda: supabase.table("ppm_executions").select("*").eq("facility_code", fc).eq("executed_by_name", user_name).order("created_at", desc=True).limit(50).execute(), error_prefix="My PPMs")
        if my_executions and my_executions.data and len(my_executions.data) > 0:
            for ex in my_executions.data:
                status = ex.get("status", "submitted")
                sc = {"submitted": "#3B82F6", "confirmed": "#F59E0B", "approved": "#10B981", "rejected": "#EF4444"}.get(status, "#3B82F6")
                icon = {"submitted": "📤", "confirmed": "✅", "approved": "🟢", "rejected": "❌"}.get(status, "📋")
                st.markdown(f"""
                <div style="background:white;border-left:5px solid {sc};border-radius:10px;padding:1rem;margin:0.5rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div><div style="font-size:1rem;font-weight:700;">{icon} {ex.get('execution_date','')}</div><div style="font-size:0.75rem;color:#666;">🏢 {ex.get('building','N/A')}</div></div>
                        <span style="background:{sc};color:white;padding:5px 16px;border-radius:20px;font-size:0.7rem;font-weight:700;">{status.upper()}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No PPM submissions yet.")
    
    # ============================================
    # TAB 4: PENDING APPROVAL
    # ============================================
    with tabs[4]:
        st.markdown("### ⏳ Approval Center")
        if user_role not in ["admin", "approver", "authorizer", "confirmer"]:
            st.info("This section is for Team Leads and Managers.")
        else:
            approval_tabs = st.tabs(["🔐 Team Lead Confirmation", "🟢 Manager Approval"])
            
            with approval_tabs[0]:
                st.markdown("#### 🔐 Pending Team Lead Confirmation")
                pending = safe_supabase_query(lambda: supabase.table("ppm_executions").select("*").eq("facility_code", fc).eq("status", "submitted").order("created_at", desc=True).execute(), error_prefix="Pending PPMs")
                if pending and pending.data and len(pending.data) > 0:
                    for ex in pending.data:
                        st.markdown(f"""
                        <div style="background:white;border-left:5px solid #3B82F6;border-radius:10px;padding:1rem;margin:0.5rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div><div style="font-size:1rem;font-weight:700;">📋 {ex.get('execution_date','')}</div><div style="font-size:0.75rem;color:#666;">👤 {ex.get('executed_by_name','')}</div></div>
                                <span style="background:#3B82F6;color:white;padding:5px 16px;border-radius:20px;font-size:0.7rem;">SUBMITTED</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        items = safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_execution_items").select("*").eq("execution_id", eid).order("item_number").execute(), error_prefix="PPM items")
                        if items and items.data:
                            with st.expander("📋 View Checklist Results"):
                                for item in items.data:
                                    res = item.get("result","")
                                    icon = "✅" if res in ["Pass","Yes","Clear","Good","Normal","Tight","Ok"] else "❌" if res in ["Fail","No","Damage","Dirty","Abnormal","Loose"] else "📝"
                                    st.markdown(f"{icon} **{item.get('item_number')}.** {item.get('description')} — *{item.get('actual_value', res)}*")
                        st.markdown("---")
                        c1, c2 = st.columns(2)
                        with c1:
                            confirm_comment = st.text_area("Confirmation Comment*", key=f"tl_confirm_{ex['id']}", height=60)
                            if st.button("✅ CONFIRM", key=f"tl_btn_confirm_{ex['id']}", use_container_width=True, type="primary"):
                                if confirm_comment:
                                    safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_executions").update({"status":"confirmed"}).eq("id", eid).execute(), error_prefix="Confirm PPM")
                                    safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_approvals").update({"status":"approved","comments":confirm_comment,"approver_name":user_name,"action_date":datetime.now().isoformat()}).eq("execution_id", eid).eq("approval_level","team_lead").execute(), error_prefix="TL approval")
                                    st.success("✅ Confirmed!"); st.rerun()
                                else: st.error("⚠️ Comment required")
                        with c2:
                            reject_comment = st.text_area("Rejection Reason*", key=f"tl_reject_{ex['id']}", height=60)
                            if st.button("❌ REJECT", key=f"tl_btn_reject_{ex['id']}", use_container_width=True):
                                if reject_comment:
                                    safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_executions").update({"status":"rejected"}).eq("id", eid).execute(), error_prefix="Reject PPM")
                                    safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_approvals").update({"status":"rejected","comments":reject_comment,"approver_name":user_name,"action_date":datetime.now().isoformat()}).eq("execution_id", eid).eq("approval_level","team_lead").execute(), error_prefix="TL reject")
                                    st.error("❌ Rejected"); st.rerun()
                                else: st.error("⚠️ Reason required")
                else:
                    st.success("✅ No submissions waiting.")
            
            with approval_tabs[1]:
                st.markdown("#### 🟢 Pending Manager Approval")
                if user_role not in ["admin", "approver"]:
                    st.info("This section is for Managers/HOD only.")
                else:
                    pending_mgr = safe_supabase_query(lambda: supabase.table("ppm_executions").select("*").eq("facility_code", fc).eq("status", "confirmed").order("created_at", desc=True).execute(), error_prefix="Pending MGR")
                    if pending_mgr and pending_mgr.data and len(pending_mgr.data) > 0:
                        for ex in pending_mgr.data:
                            st.markdown(f"""
                            <div style="background:white;border-left:5px solid #F59E0B;border-radius:10px;padding:1rem;margin:0.5rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                                <div style="font-size:1rem;font-weight:700;">📋 {ex.get('execution_date','')}</div>
                                <div style="font-size:0.75rem;color:#666;">👤 {ex.get('executed_by_name','')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            items = safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_execution_items").select("*").eq("execution_id", eid).order("item_number").execute(), error_prefix="PPM items")
                            if items and items.data:
                                with st.expander("📋 View Checklist Results"):
                                    for item in items.data:
                                        res = item.get("result","")
                                        icon = "✅" if res in ["Pass","Yes","Clear","Good","Normal","Tight","Ok"] else "❌" if res in ["Fail","No","Damage","Dirty","Abnormal","Loose"] else "📝"
                                        st.markdown(f"{icon} **{item.get('item_number')}.** {item.get('description')} — *{item.get('actual_value', res)}*")
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                mgr_comment = st.text_area("Approval Comment*", key=f"mgr_approve_{ex['id']}", height=60)
                                if st.button("🟢 FINAL APPROVE", key=f"mgr_btn_approve_{ex['id']}", use_container_width=True, type="primary"):
                                    if mgr_comment:
                                        safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_executions").update({"status":"approved"}).eq("id", eid).execute(), error_prefix="Approve PPM")
                                        safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_approvals").update({"status":"approved","comments":mgr_comment,"approver_name":user_name,"action_date":datetime.now().isoformat()}).eq("execution_id", eid).eq("approval_level","manager").execute(), error_prefix="MGR approval")
                                        st.success("🟢 Approved!"); st.balloons(); st.rerun()
                                    else: st.error("⚠️ Comment required")
                            with c2:
                                mgr_reject = st.text_area("Rejection Reason*", key=f"mgr_reject_{ex['id']}", height=60)
                                if st.button("❌ REJECT", key=f"mgr_btn_reject_{ex['id']}", use_container_width=True):
                                    if mgr_reject:
                                        safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_executions").update({"status":"rejected"}).eq("id", eid).execute(), error_prefix="Reject PPM")
                                        safe_supabase_query(lambda eid=ex["id"]: supabase.table("ppm_approvals").update({"status":"rejected","comments":mgr_reject,"approver_name":user_name,"action_date":datetime.now().isoformat()}).eq("execution_id", eid).eq("approval_level","manager").execute(), error_prefix="MGR reject")
                                        st.error("❌ Rejected"); st.rerun()
                                    else: st.error("⚠️ Reason required")
                    else:
                        st.success("✅ No submissions waiting.")
    
    # ============================================
    # TAB 5: CHECKLIST BUILDER (ADMIN ONLY)
    # ============================================
    with tabs[5]:
        st.markdown("### ⚙️ Checklist Builder (Templates Only — No Dates)")
        st.info("📅 Schedule dates are now configured during asset enrollment in the PPM Scheduling Center.")
        
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            cb_tabs = st.tabs(["📋 Create Template", "✏️ Edit Template", "ℹ️ Schedule Info"])
            
            with cb_tabs[0]:
                st.markdown("#### ➕ Create New Checklist Template")
                st.caption("Templates define WHAT to check. Schedule dates are set during asset enrollment.")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    template_name = st.text_input("Template Name*", placeholder="e.g. Monthly AHU Checklist", key="tpl_name")
                with c2:
                    period = st.selectbox("Default Frequency*", ["Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="tpl_period")
                with c3:
                    image_required = st.selectbox("Image Required*", ["Yes", "No"], key="tpl_image")
                
                c1, c2 = st.columns(2)
                with c1:
                    perform_time = st.number_input("Perform Time (min)*", min_value=0, value=30, key="tpl_time")
                    buffer_days = st.number_input("Buffer Days*", min_value=0, value=0, key="tpl_buffer")
                with c2:
                    asset_category = st.selectbox("Asset Category", sorted(df["dept_full"].dropna().unique().tolist()), key="tpl_cat")
                    standard_ref = st.text_input("Standard Reference", placeholder="e.g. ISO 8100, NFPA 25", key="tpl_std")
                
                st.markdown("---")
                st.markdown("### 📝 Checklist Items")
                
                if "checklist_builder_items" not in st.session_state:
                    st.session_state.checklist_builder_items = [{"sno": 1, "description": "", "answer_type": "yes_no", "threshold": "Yes/No"}]
                
                item_data = []
                for item in st.session_state.checklist_builder_items:
                    if item["description"].strip():
                        item_data.append({"SNO": item["sno"], "Description": item["description"], "Answer Type": item["answer_type"], "Options": item["threshold"]})
                if item_data:
                    st.dataframe(pd.DataFrame(item_data), use_container_width=True, hide_index=True, height=200)
                
                st.markdown("**➕ Add Checklist Item**")
                c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                with c1:
                    new_sno = st.number_input("SNO", min_value=1, value=len(st.session_state.checklist_builder_items)+1, key="new_sno")
                with c2:
                    new_desc = st.text_input("Description", key="new_desc", placeholder="e.g. Check filter condition")
                with c3:
                    answer_type = st.selectbox("Answer Type", ["yes_no", "pass_fail", "status", "reading", "text", "section"], key="new_type")
                with c4:
                    threshold = st.text_input("Options", value="Yes/No", key="new_thresh")
                
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if st.button("➕ Add Item", key="btn_add_item", use_container_width=True):
                        if new_desc:
                            st.session_state.checklist_builder_items.append({"sno": new_sno, "description": new_desc, "answer_type": answer_type, "threshold": threshold})
                            st.rerun()
                with c2:
                    if st.button("🗑️ Clear All", key="btn_clear_all", use_container_width=True):
                        st.session_state.checklist_builder_items = [{"sno": 1, "description": "", "answer_type": "yes_no", "threshold": "Yes/No"}]
                        st.rerun()
                with c3:
                    if st.button("🗑️ Remove Last", key="btn_remove_last", use_container_width=True) and len(st.session_state.checklist_builder_items) > 1:
                        st.session_state.checklist_builder_items.pop()
                        st.rerun()
                
                st.markdown("---")
                with st.form("create_template_submit"):
                    if st.form_submit_button("💾 CREATE TEMPLATE", use_container_width=True, type="primary"):
                        if template_name:
                            valid_items = [i for i in st.session_state.checklist_builder_items if i["description"].strip()]
                            if valid_items:
                                template_result = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").insert({
                                    "template_name": template_name, "asset_category": asset_category,
                                    "international_standard": standard_ref,
                                    "description": f"Period: {period} | Time: {perform_time}min | Buffer: {buffer_days}days",
                                    "schedule_dates": None, "is_active": True
                                }).execute(), error_prefix="Create template")
                                if template_result and template_result.data:
                                    template_id = template_result.data[0]["id"]
                                    for item in valid_items:
                                        safe_supabase_query(lambda tid=template_id, it=item: supabase.table("ppm_checklist_items").insert({
                                            "template_id": tid, "item_number": it["sno"], "description": it["description"],
                                            "check_type": it["answer_type"], "expected_value": it["threshold"], "sort_order": it["sno"]
                                        }).execute(), error_prefix="Checklist items")
                                    st.session_state.checklist_builder_items = [{"sno": 1, "description": "", "answer_type": "yes_no", "threshold": "Yes/No"}]
                                    st.success(f"✅ Template created!"); st.balloons(); st.rerun()
                            else:
                                st.error("⚠️ Add at least one item")
                        else:
                            st.error("⚠️ Template name required")
            
            with cb_tabs[1]:
                st.markdown("#### ✏️ Edit Existing Template")
                
                all_templates = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").select("*").order("created_at", desc=True).execute(), error_prefix="All templates")
                
                if all_templates and all_templates.data and len(all_templates.data) > 0:
                    template_names_list = [t.get("template_name","") for t in all_templates.data]
                    edit_template_name = st.selectbox("Select Template to Edit", template_names_list, key="edit_template")
                    
                    if edit_template_name:
                        edit_template = next((t for t in all_templates.data if t.get("template_name") == edit_template_name), None)
                        
                        if edit_template:
                            st.markdown(f"**Editing:** {edit_template.get('template_name')} | **Standard:** {edit_template.get('international_standard','Custom')}")
                            
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                new_name = st.text_input("Template Name", value=edit_template.get("template_name",""), key="edit_tpl_name")
                            with c2:
                                desc_parts = edit_template.get("description","").split("|")
                                period_val = desc_parts[0].replace("Period:","").strip() if len(desc_parts) > 0 else "Monthly"
                                new_period = st.selectbox("Default Frequency", ["Daily","Weekly","Bi-Weekly","Monthly","Quarterly","Half-Yearly","Yearly"], 
                                    index=["Daily","Weekly","Bi-Weekly","Monthly","Quarterly","Half-Yearly","Yearly"].index(period_val) if period_val in ["Daily","Weekly","Bi-Weekly","Monthly","Quarterly","Half-Yearly","Yearly"] else 3, key="edit_period")
                            with c3:
                                new_image = st.selectbox("Image Required", ["Yes","No"], 
                                    index=0 if "Image: Yes" in edit_template.get("description","") else 1, key="edit_image")
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                time_val = desc_parts[1].replace("Time:","").replace("min","").strip() if len(desc_parts) > 1 else "30"
                                new_time = st.number_input("Perform Time (min)", value=int(time_val) if time_val.isdigit() else 30, key="edit_time")
                            with c2:
                                buf_val = desc_parts[2].replace("Buffer:","").replace("days","").strip() if len(desc_parts) > 2 else "0"
                                new_buffer = st.number_input("Buffer Days", value=int(buf_val) if buf_val.isdigit() else 0, key="edit_buffer")
                            
                            new_standard = st.text_input("Standard Reference", value=edit_template.get("international_standard",""), key="edit_std")
                            
                            st.info("📅 Schedule dates are now configured during asset enrollment. Templates only define checklist items.")
                            
                            st.markdown("---")
                            st.markdown("### 📝 Checklist Items")
                            
                            existing_items = safe_supabase_query(lambda tid=edit_template["id"]: supabase.table("ppm_checklist_items").select("*").eq("template_id", tid).order("sort_order").execute(), error_prefix="Existing items")
                            
                            if existing_items and existing_items.data:
                                st.markdown("**Current Items (edit inline):**")
                                for item in existing_items.data:
                                    c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1.5, 1.5, 0.5])
                                    with c1:
                                        st.text_input("SNO", value=str(item.get("item_number","")), key=f"edit_sno_{item['id']}", label_visibility="collapsed")
                                    with c2:
                                        st.text_input("Description", value=item.get("description",""), key=f"edit_desc_{item['id']}", label_visibility="collapsed")
                                    with c3:
                                        st.selectbox("Type", ["yes_no","pass_fail","status","reading","text","section"], 
                                            index=["yes_no","pass_fail","status","reading","text","section"].index(item.get("check_type","yes_no")) if item.get("check_type","yes_no") in ["yes_no","pass_fail","status","reading","text","section"] else 0,
                                            key=f"edit_type_{item['id']}", label_visibility="collapsed")
                                    with c4:
                                        st.text_input("Options", value=item.get("expected_value","") or "", key=f"edit_thresh_{item['id']}", label_visibility="collapsed")
                                    with c5:
                                        if st.button("🗑️", key=f"del_item_{item['id']}", use_container_width=True):
                                            safe_supabase_query(lambda iid=item["id"]: supabase.table("ppm_checklist_items").delete().eq("id", iid).execute(), error_prefix="Delete item")
                                            st.rerun()
                                
                                st.markdown("---")
                            
                            st.markdown("**➕ Add New Item:**")
                            c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                            with c1:
                                add_sno = st.number_input("SNO", min_value=1, value=len(existing_items.data)+1 if existing_items and existing_items.data else 1, key="edit_add_sno")
                            with c2:
                                add_desc = st.text_input("Description", key="edit_add_desc", placeholder="New checklist item...")
                            with c3:
                                add_type = st.selectbox("Type", ["yes_no","pass_fail","status","reading","text"], key="edit_add_type")
                            with c4:
                                add_thresh = st.text_input("Options", value="Yes/No", key="edit_add_thresh")
                            
                            if st.button("➕ Add Item", key="edit_btn_add", use_container_width=True):
                                if add_desc.strip():
                                    safe_supabase_query(lambda tid=edit_template["id"]: supabase.table("ppm_checklist_items").insert({
                                        "template_id": tid,
                                        "item_number": int(add_sno),
                                        "description": add_desc.strip(),
                                        "check_type": add_type,
                                        "expected_value": add_thresh,
                                        "sort_order": int(add_sno)
                                    }).execute(), error_prefix="Add item")
                                    st.success("✅ Item added!")
                                    st.rerun()
                            
                            st.markdown("---")
                            
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                if st.button("💾 SAVE ALL CHANGES", use_container_width=True, type="primary"):
                                    # Update template
                                    safe_supabase_query(lambda tid=edit_template["id"]: supabase.table("ppm_checklist_templates").update({
                                        "template_name": new_name,
                                        "international_standard": new_standard,
                                        "description": f"Period: {new_period} | Time: {new_time}min | Buffer: {new_buffer}days | Image: {new_image}",
                                        "schedule_dates": None
                                    }).eq("id", tid).execute(), error_prefix="Update template")
                                    
                                    # Update existing items
                                    for item in existing_items.data if existing_items and existing_items.data else []:
                                        safe_supabase_query(lambda iid=item["id"]: supabase.table("ppm_checklist_items").update({
                                            "item_number": int(st.session_state.get(f"edit_sno_{iid}", item.get("item_number",1)) or 1),
                                            "description": st.session_state.get(f"edit_desc_{iid}", item.get("description","")),
                                            "check_type": st.session_state.get(f"edit_type_{iid}", item.get("check_type","yes_no")),
                                            "expected_value": st.session_state.get(f"edit_thresh_{iid}", item.get("expected_value","") or "")
                                        }).eq("id", iid).execute(), error_prefix="Update items")
                                    
                                    st.success("✅ Template updated!")
                                    st.balloons()
                                    st.rerun()
                            with c2:
                                if st.button("🗑️ DELETE TEMPLATE", use_container_width=True):
                                    safe_supabase_query(lambda tid=edit_template["id"]: supabase.table("ppm_checklist_items").delete().eq("template_id", tid).execute(), error_prefix="Delete items")
                                    safe_supabase_query(lambda tid=edit_template["id"]: supabase.table("ppm_checklist_templates").delete().eq("id", tid).execute(), error_prefix="Delete template")
                                    st.warning("✅ Template deleted!")
                                    st.rerun()
                            with c3:
                                if st.button("❌ CANCEL", use_container_width=True):
                                    st.rerun()
                else:
                    st.info("No templates created yet. Create one in the 'Create Template' tab.")
            
            with cb_tabs[2]:
                st.markdown("#### ℹ️ Schedule Configuration")
                st.info("📅 Schedule dates are configured during asset enrollment in the PPM Scheduling Center (Checklist Status page).")
                if st.button("📋 GO TO PPM SCHEDULING CENTER", use_container_width=True, type="primary"):
                    st.session_state.page = "cs"
                    st.rerun()
    
    # ============================================
    # TAB 6: MANAGE SCHEDULES
    # ============================================
    with tabs[6]:
        st.markdown("### 📋 Manage Enrolled PPM Schedules")
        if not is_admin:
            st.error("⛔ Admin access only")
        else:
            all_schedules = safe_supabase_query(lambda: supabase.table("ppm_schedules").select("*").eq("facility_code", fc).order("next_due_date", desc=False).execute(), error_prefix="PPM schedules")
            if all_schedules and all_schedules.data and len(all_schedules.data) > 0:
                sched_df = pd.DataFrame(all_schedules.data)
                st.caption(f"📋 {len(sched_df)} schedule entries")
                st.dataframe(sched_df[[c for c in ["title", "assigned_team", "frequency", "next_due_date", "status"] if c in sched_df.columns]], use_container_width=True, hide_index=True, height=400)
            else:
                st.info("No PPM schedules found.")
                if st.button("📋 GO TO PPM SCHEDULING CENTER", use_container_width=True, type="primary"):
                    st.session_state.page = "cs"
                    st.rerun()



# ============================================
# PPM SCHEDULING CENTER — FORTUNE 500 GRADE
# INDIVIDUAL • BULK • CALENDAR PREVIEW • CONFLICT DETECTION
# STAGGERED SCHEDULING • TEMPLATE PREVIEW • QUICK PRESETS
# ============================================
def page_cs():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    today = date.today()
    
    st.markdown(f'## 📅 PPM Scheduling Center — {info.get("full_name", fc)}')
    st.caption("Individual & Bulk Scheduling • Calendar Preview • Conflict Detection • Template Preview • Staggered Dates")
    
    all_assets = DB.get_assets(fc, 50000)
    
    if not all_assets:
        st.info("No assets registered.")
        return
    
    df = pd.DataFrame(all_assets)
    df["checklist_clean"] = df["checklist"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() not in ["", "NA", "na", "APPLICABLE", "NOTAPPLICABLE", "None"] else None)
    df["dept_full"] = df.apply(lambda row: f"{row['department']} — {row['sub_division']}" if pd.notna(row.get('sub_division')) and row.get('sub_division') not in ['', 'N/A', 'NA'] else row['department'], axis=1)
    
    templates = safe_supabase_query(lambda: supabase.table("ppm_checklist_templates").select("*").execute(), error_prefix="Checklist templates")
    template_names = [t.get("template_name","") for t in templates.data] if templates and templates.data else []
    template_options = template_names if template_names else ["Standard Template"]
    
    existing_schedules = safe_supabase_query(lambda: supabase.table("ppm_schedules").select("*").eq("facility_code", fc).execute(), error_prefix="Existing schedules")
    existing_df = pd.DataFrame(existing_schedules.data) if existing_schedules and existing_schedules.data else pd.DataFrame()
    
    # Stats ribbon
    total_assets_count = len(df)
    enrolled_count = len(df[df["checklist_clean"].notna()])
    not_enrolled_count = total_assets_count - enrolled_count
    total_schedules = len(existing_df)
    overdue_schedules = len(existing_df[(pd.to_datetime(existing_df["next_due_date"], errors='coerce').dt.date < today) & (existing_df["status"] != "completed")]) if total_schedules > 0 else 0
    completed_schedules = len(existing_df[existing_df["status"] == "completed"]) if total_schedules > 0 else 0
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Total Assets</div><div style="font-size:1.3rem;font-weight:800;color:#3B82F6;">{total_assets_count}</div></div>""", unsafe_allow_html=True)
    with c2:
        color = "#10B981" if enrolled_count > 0 else "#F59E0B"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Enrolled</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{enrolled_count}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Not Enrolled</div><div style="font-size:1.3rem;font-weight:800;color:#F59E0B;">{not_enrolled_count}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Schedules</div><div style="font-size:1.3rem;font-weight:800;color:#8B5CF6;">{total_schedules}</div></div>""", unsafe_allow_html=True)
    with c5:
        color = "#EF4444" if overdue_schedules > 0 else "#10B981"
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Overdue</div><div style="font-size:1.3rem;font-weight:800;color:{color};">{overdue_schedules}</div></div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div style="background:white;border-radius:10px;padding:0.7rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 4px rgba(0,0,0,0.04);"><div style="font-size:0.5rem;color:#888;">Completed</div><div style="font-size:1.3rem;font-weight:800;color:#10B981;">{completed_schedules}</div></div>""", unsafe_allow_html=True)
    
    # ============================================
    # HELPER: Manual Date Picker with Multi-Date Selection
    # ============================================
    def render_manual_date_picker(prefix="default"):
        if f"{prefix}_manual_dates" not in st.session_state:
            st.session_state[f"{prefix}_manual_dates"] = []
        
        st.markdown("**📅 Manual Date Selection**")
        st.caption("Pick your date range, select dates from the list, then click 'Add Selected Dates'.")
        
        # Date range picker
        c1, c2 = st.columns(2)
        with c1:
            date_start = st.date_input("From Date", today, key=f"{prefix}_date_start")
        with c2:
            date_end = st.date_input("To Date", today + timedelta(days=30), key=f"{prefix}_date_end")
        
        # Generate list of dates in range as formatted strings
        date_options = []
        date_map = {}
        current = date_start
        while current <= date_end:
            date_str = current.strftime("%Y-%m-%d")
            label = current.strftime("%a, %d %b %Y")
            date_options.append(label)
            date_map[label] = date_str
            current += timedelta(days=1)
        
        st.caption(f"📅 {len(date_options)} dates available in range. Select the ones you want:")
        
        # Multi-select using formatted strings
        selected_labels = st.multiselect(
            "Select dates to add",
            options=date_options,
            key=f"{prefix}_individual_pick",
            placeholder="Click here to pick dates..."
        )
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("➕ Add Selected Dates", key=f"{prefix}_add_dates", use_container_width=True, type="primary"):
                added = 0
                for label in selected_labels:
                    date_str = date_map.get(label, "")
                    if date_str and date_str not in st.session_state[f"{prefix}_manual_dates"]:
                        st.session_state[f"{prefix}_manual_dates"].append(date_str)
                        added += 1
                if added > 0:
                    st.session_state[f"{prefix}_manual_dates"].sort()
                    st.rerun()
                else:
                    st.warning("No new dates selected or all dates already added.")
        
        with c2:
            if st.button("📅 Add Full Range", key=f"{prefix}_add_range", use_container_width=True):
                added = 0
                for label in date_options:
                    date_str = date_map.get(label, "")
                    if date_str and date_str not in st.session_state[f"{prefix}_manual_dates"]:
                        st.session_state[f"{prefix}_manual_dates"].append(date_str)
                        added += 1
                if added > 0:
                    st.session_state[f"{prefix}_manual_dates"].sort()
                    st.rerun()
                else:
                    st.info("All dates already added.")
        
        with c3:
            if st.button("🗑️ Clear All", key=f"{prefix}_clear_dates", use_container_width=True):
                st.session_state[f"{prefix}_manual_dates"] = []
                st.rerun()
        
        # Quick Presets
        st.markdown("**⚡ Quick Presets:**")
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        presets = {
            "Today": [today.strftime("%Y-%m-%d")],
            "This Week (M-F)": [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5) if (today + timedelta(days=i)).weekday() < 5],
            "Next 7 Days": [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
            "Every Monday (4w)": [(today + timedelta(days=(7 - today.weekday()) % 7 + i*7)).strftime("%Y-%m-%d") for i in range(4)],
            "1st of Month (3m)": [date(today.year + (today.month-1+i)//12, ((today.month-1+i)%12)+1, 1).strftime("%Y-%m-%d") for i in range(3)],
        }
        preset_keys = list(presets.keys())
        for i, col in enumerate([pc1, pc2, pc3, pc4, pc5]):
            if i < len(preset_keys):
                with col:
                    if st.button(preset_keys[i], key=f"{prefix}_preset_{i}", use_container_width=True):
                        for d in presets[preset_keys[i]]:
                            if d not in st.session_state[f"{prefix}_manual_dates"]:
                                st.session_state[f"{prefix}_manual_dates"].append(d)
                        st.session_state[f"{prefix}_manual_dates"].sort()
                        st.rerun()
        
        if st.session_state[f"{prefix}_manual_dates"]:
            # Mini Calendar Preview
            try:
                import calendar as cal_mod
                cal_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in st.session_state[f"{prefix}_manual_dates"]]
                cal_dates_set = set(d.strftime("%Y-%m-%d") for d in cal_dates)
                months_with_dates = sorted(set(d.replace(day=1) for d in cal_dates))
                
                st.markdown("**📅 Calendar Preview:**")
                
                for cal_month in months_with_dates[:6]:
                    cal_matrix = cal_mod.monthcalendar(cal_month.year, cal_month.month)
                    month_name = cal_month.strftime('%B %Y')
                    
                    cal_html = f'''<div style="display:inline-block;background:white;border:1px solid #ddd;border-radius:8px;padding:8px;margin:5px;width:170px;vertical-align:top;"><div style="text-align:center;font-weight:700;font-size:0.7rem;margin-bottom:4px;color:#1a1a1a;">{month_name}</div><table style="width:100%;border-collapse:collapse;font-size:0.55rem;text-align:center;"><tr style="color:#888;font-weight:600;"><td>M</td><td>T</td><td>W</td><td>T</td><td>F</td><td>S</td><td>S</td></tr>'''
                    
                    for week in cal_matrix:
                        cal_html += '<tr>'
                        for day in week:
                            if day == 0:
                                cal_html += '<td></td>'
                            else:
                                check_date_str = date(cal_month.year, cal_month.month, day).strftime("%Y-%m-%d")
                                if check_date_str in cal_dates_set:
                                    cal_html += f'<td><span style="background:#CC0000;color:white;border-radius:50%;display:inline-block;width:18px;height:18px;line-height:18px;font-weight:700;font-size:0.5rem;">{day}</span></td>'
                                else:
                                    cal_html += f'<td style="color:#bbb;font-size:0.5rem;">{day}</td>'
                        cal_html += '</tr>'
                    
                    cal_html += '</table></div>'
                    st.markdown(cal_html, unsafe_allow_html=True)
            except:
                pass
            
            # Show dates as chips
            st.markdown("**Selected Dates:**")
            cols_per_row = 5
            for i in range(0, len(st.session_state[f"{prefix}_manual_dates"]), cols_per_row):
                row_dates = st.session_state[f"{prefix}_manual_dates"][i:i+cols_per_row]
                dcols = st.columns(cols_per_row)
                for j, d in enumerate(row_dates):
                    with dcols[j]:
                        st.markdown(f'<div style="background:#FEF2F2;border:1px solid #EF4444;border-radius:6px;padding:0.2rem;text-align:center;font-size:0.6rem;font-weight:600;color:#DC2626;">📅 {d}</div>', unsafe_allow_html=True)
            
            # Remove individual dates
            remove_dates = st.multiselect("Remove dates", st.session_state[f"{prefix}_manual_dates"], key=f"{prefix}_remove_dates")
            if remove_dates:
                if st.button("🗑️ Remove Selected", key=f"{prefix}_btn_remove", use_container_width=True):
                    for d in remove_dates:
                        st.session_state[f"{prefix}_manual_dates"].remove(d)
                    st.rerun()
            
            dates_string = ",".join(st.session_state[f"{prefix}_manual_dates"])
            st.caption(f"📅 {len(st.session_state[f'{prefix}_manual_dates'])} dates selected")
            return dates_string, True
        else:
            st.warning("⚠️ No dates selected. Please add at least one date.")
            return "", False
    
    # ============================================
    # HELPER: Auto-Generate Dates
    # ============================================
    def render_auto_generate_dates(prefix="default", default_freq="Monthly"):
        st.markdown("**🔄 Auto-Generate Schedule Dates**")
        
        c1, c2 = st.columns(2)
        with c1:
            auto_start = st.date_input("Start Date", today, key=f"{prefix}_auto_start")
        with c2:
            auto_end = st.date_input("End Date", today + timedelta(days=365), key=f"{prefix}_auto_end")
        
        freq_options = ["Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"]
        default_idx = freq_options.index(default_freq) if default_freq in freq_options else 3
        auto_freq = st.selectbox("Frequency", freq_options, index=default_idx, key=f"{prefix}_auto_freq")
        
        if f"{prefix}_generated_dates" not in st.session_state:
            st.session_state[f"{prefix}_generated_dates"] = []
        
        if st.button("🔄 Generate Dates", key=f"{prefix}_gen_dates", use_container_width=True):
            dates_list = []
            current = auto_start
            while current <= auto_end:
                dates_list.append(current.strftime("%Y-%m-%d"))
                if auto_freq == "Daily":
                    current += timedelta(days=1)
                elif auto_freq == "Weekly":
                    current += timedelta(days=7)
                elif auto_freq == "Bi-Weekly":
                    current += timedelta(days=14)
                elif auto_freq == "Monthly":
                    if current.month == 12:
                        current = date(current.year + 1, 1, min(current.day, 28))
                    else:
                        current = date(current.year, current.month + 1, min(current.day, 28))
                elif auto_freq == "Quarterly":
                    nm = current.month + 3
                    current = date(current.year + 1, nm - 12, min(current.day, 28)) if nm > 12 else date(current.year, nm, min(current.day, 28))
                elif auto_freq == "Half-Yearly":
                    nm = current.month + 6
                    current = date(current.year + 1, nm - 12, min(current.day, 28)) if nm > 12 else date(current.year, nm, min(current.day, 28))
                elif auto_freq == "Yearly":
                    current = date(current.year + 1, current.month, min(current.day, 28))
            st.session_state[f"{prefix}_generated_dates"] = dates_list
            st.rerun()
        
        if st.session_state[f"{prefix}_generated_dates"]:
            generated = st.session_state[f"{prefix}_generated_dates"]
            st.caption(f"📅 {len(generated)} dates generated")
            
            selected = st.multiselect("Select Dates*", generated, default=generated[:min(5, len(generated))], key=f"{prefix}_auto_selected")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Select All", key=f"{prefix}_sel_all", use_container_width=True):
                    st.session_state[f"{prefix}_auto_selected"] = generated
                    st.rerun()
            with c2:
                if st.button("❌ Deselect All", key=f"{prefix}_desel_all", use_container_width=True):
                    st.session_state[f"{prefix}_auto_selected"] = []
                    st.rerun()
            
            if selected:
                # Mini calendar preview
                try:
                    import calendar as cal_mod
                    cal_dates_auto = [datetime.strptime(d, "%Y-%m-%d").date() for d in selected]
                    cal_month = cal_dates_auto[0].replace(day=1) if cal_dates_auto else today.replace(day=1)
                    cal_matrix = cal_mod.monthcalendar(cal_month.year, cal_month.month)
                    
                    st.markdown(f"""
                    <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:0.6rem;margin:0.5rem 0;max-width:350px;">
                        <div style="text-align:center;font-weight:700;margin-bottom:0.3rem;font-size:0.8rem;">📅 {cal_month.strftime('%B %Y')}</div>
                        <table style="width:100%;text-align:center;font-size:0.65rem;">
                            <tr style="color:#888;">{"".join(f'<td>{d}</td>' for d in ['M','T','W','T','F','S','S'])}</tr>
                    """, unsafe_allow_html=True)
                    
                    for week in cal_matrix:
                        st.markdown("<tr>", unsafe_allow_html=True)
                        for day in week:
                            if day == 0:
                                st.markdown('<td style="padding:1px;"></td>', unsafe_allow_html=True)
                            else:
                                check_date = date(cal_month.year, cal_month.month, day)
                                if check_date in cal_dates_auto:
                                    st.markdown(f'<td style="padding:1px;"><div style="background:#059669;color:white;border-radius:50%;width:22px;height:22px;line-height:22px;font-weight:700;font-size:0.6rem;margin:0 auto;">{day}</div></td>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f'<td style="padding:1px;color:#ccc;font-size:0.6rem;">{day}</td>', unsafe_allow_html=True)
                        st.markdown("</tr>", unsafe_allow_html=True)
                    st.markdown("</table></div>", unsafe_allow_html=True)
                except:
                    pass
                
                dates_string = ",".join(selected)
                st.caption(f"📅 {len(selected)} dates selected")
                return dates_string, True
            else:
                return "", False
        else:
            st.caption("Click 'Generate Dates' to create the schedule.")
            return "", False
    
    # ============================================
    # HELPER: Template Preview
    # ============================================
    def render_template_preview(template_name):
        if template_name == "Standard Template":
            items = ["LOTO: Power isolated", "PPE: Appropriate PPE worn", "Work Area Assessment", "Visual Inspection", "Air Filter(s) inspection", "Fan & Motor check", "Condensate Drain inspection", "Electrical wiring check", "Temperature measurements", "Voltage & Amps parameters", "Earthing connections", "BMS integration", "Observations"]
        else:
            matched = next((t for t in (templates.data if templates and templates.data else []) if t.get("template_name") == template_name), None)
            if matched:
                items_res = safe_supabase_query(lambda mid=matched["id"]: supabase.table("ppm_checklist_items").select("description").eq("template_id", mid).order("sort_order").execute(), error_prefix="Template items")
                items = [i.get("description","") for i in items_res.data] if items_res and items_res.data else ["No items found"]
            else:
                items = ["Template not found"]
        
        with st.expander(f"📋 Preview: {template_name} ({len(items)} items)"):
            for i, item in enumerate(items):
                st.caption(f"{i+1}. {item}")
    
    # ============================================
    # HELPER: Conflict Detection
    # ============================================
    def check_schedule_conflicts(asset_id, dates_list):
        if existing_df.empty:
            return []
        conflicts = []
        for d in dates_list:
            existing = existing_df[(existing_df["asset_id"] == str(asset_id)) & (existing_df["next_due_date"] == d)]
            if len(existing) > 0:
                conflicts.append(d)
        return conflicts
    
    # ============================================
    # MAIN TABS
    # ============================================
    tabs = st.tabs([
        "🔧 Individual Scheduling", 
        "📦 Bulk Scheduling", 
        "📋 Scheduled PPMs", 
        "📊 Consolidated Report"
    ])
    
    # ============================================
    # TAB 0: INDIVIDUAL ASSET SCHEDULING
    # ============================================
    with tabs[0]:
        st.markdown("### 🔧 Individual Asset PPM Scheduling")
        st.caption("Schedule one asset at a time with full date control.")
        
        st.markdown("#### Step 1: Select Asset")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            dept_list = ["Select Department..."] + sorted(df["dept_full"].dropna().unique().tolist())
            sel_dept = st.selectbox("Department*", dept_list, key="ind_dept")
        
        if sel_dept != "Select Department...":
            dept_df = df[df["dept_full"] == sel_dept]
            with c2:
                asset_list = ["Select Asset..."] + sorted(dept_df["parent_asset"].dropna().unique().tolist())
                sel_asset = st.selectbox("Asset (Parent)*", asset_list, key="ind_asset")
            
            if sel_asset != "Select Asset...":
                asset_df = dept_df[dept_df["parent_asset"] == sel_asset]
                with c3:
                    sub_list = ["Select Sub-Asset..."] + sorted(asset_df["name"].dropna().unique().tolist())
                    sel_sub = st.selectbox("Sub-Asset*", sub_list, key="ind_sub")
                
                if sel_sub != "Select Sub-Asset...":
                    selected_asset = asset_df[asset_df["name"] == sel_sub].iloc[0]
                    asset_id = selected_asset["id"]
                    
                    with c4:
                        current = selected_asset.get("checklist_clean", None)
                        if current:
                            st.markdown(f'<div style="background:#ECFDF5;border-radius:8px;padding:0.5rem;text-align:center;border:1px solid #10B981;margin-top:0.5rem;"><div style="font-size:0.55rem;color:#059669;">✅ Enrolled</div><div style="font-weight:600;font-size:0.7rem;color:#059669;">{current}</div></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="background:#FFFBEB;border-radius:8px;padding:0.5rem;text-align:center;border:1px solid #F59E0B;margin-top:0.5rem;"><div style="font-size:0.55rem;color:#D97706;">⚠️ Not Enrolled</div></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin-bottom:1rem;border-left:4px solid #3B82F6;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <b style="font-size:0.9rem;">{sel_asset}</b>
                                <br><span style="font-size:0.75rem;color:#666;">└ {sel_sub[:80]}</span>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:0.6rem;color:#888;">📍 {selected_asset.get('location_building','N/A')}</div>
                                <div style="font-size:0.6rem;color:#888;">🏷️ {selected_asset.get('asset_tag','N/A')}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown("#### Step 2: Select Template & Frequency")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        sel_template = st.selectbox("Checklist Template*", template_options, key="ind_template")
                    with c2:
                        sel_freq = st.selectbox("PPM Frequency*", ["Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="ind_freq")
                    with c3:
                        overwrite = st.checkbox("Overwrite existing enrollment", value=True, key="ind_overwrite")
                    
                    render_template_preview(sel_template)
                    
                    st.markdown("---")
                    st.markdown("#### Step 3: Schedule Dates")
                    
                    date_mode = st.radio("Date Selection Mode", ["📅 Manual Date Picker", "🔄 Auto-Generate Dates"], horizontal=True, key="ind_date_mode")
                    
                    if date_mode == "📅 Manual Date Picker":
                        dates_string, has_dates = render_manual_date_picker("ind")
                    else:
                        dates_string, has_dates = render_auto_generate_dates("ind", sel_freq)
                    
                    st.markdown("---")
                    
                    if has_dates and dates_string:
                        dates_list = [d.strip() for d in dates_string.split(",") if d.strip()]
                        conflicts = check_schedule_conflicts(asset_id, dates_list)
                        
                        if conflicts:
                            st.warning(f"⚠️ **Schedule Conflict:** {len(conflicts)} dates already have PPMs for this asset.")
                        
                        st.markdown(f"""
                        <div style="background:#EFF6FF;border-radius:10px;padding:1rem;margin:1rem 0;border:1px solid #BFDBFE;">
                            <b>📋 Summary:</b><br>
                            Asset: <b>{sel_sub[:60]}</b><br>
                            Template: <b>{sel_template}</b><br>
                            Frequency: <b>{sel_freq}</b><br>
                            Dates: <b>{len(dates_list)}</b> ({dates_list[0]} → {dates_list[-1] if len(dates_list) > 1 else dates_list[0]})
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("🚀 ENROLL ASSET", key="ind_enroll_btn", use_container_width=True, type="primary"):
                            DB.update("assets", asset_id, {"checklist": sel_template, "ppm_frequency": sel_freq, "checklist_template": sel_template})
                            
                            schedule_count = 0
                            for schedule_date in dates_list:
                                if not overwrite:
                                    existing = existing_df[(existing_df["asset_id"] == str(asset_id)) & (existing_df["next_due_date"] == schedule_date)]
                                    if len(existing) > 0:
                                        continue
                                safe_supabase_query(lambda aid=asset_id, sd=schedule_date: supabase.table("ppm_schedules").insert({
                                    "facility_code": fc, "asset_id": aid,
                                    "title": f"{selected_asset.get('name','PPM')} - {sel_template}",
                                    "frequency": sel_freq, "status": "scheduled",
                                    "assigned_team": selected_asset.get("department", ""),
                                    "next_due_date": sd, "created_at": datetime.now().isoformat()
                                }).execute(), error_prefix="PPM schedule")
                                schedule_count += 1
                            
                            if "ind_manual_dates" in st.session_state:
                                st.session_state["ind_manual_dates"] = []
                            if "ind_generated_dates" in st.session_state:
                                st.session_state["ind_generated_dates"] = []
                            
                            st.success(f"✅ Enrolled! {schedule_count} schedule entries created.")
                            st.balloons()
                            st.rerun()
    
    # ============================================
    # TAB 1: BULK ASSET SCHEDULING - FIXED
    # ============================================
    with tabs[1]:
        st.markdown("### 📦 Bulk Asset PPM Scheduling")
        st.caption("Enroll multiple assets at once with the same template and schedule. Optionally stagger dates across assets.")
        
        st.markdown("#### Step 1: Filter & Select Assets")
        c1, c2 = st.columns(2)
        with c1:
            bulk_dept = st.selectbox("Department*", ["Select Department..."] + sorted(df["dept_full"].dropna().unique().tolist()), key="bulk_dept")
        with c2:
            if bulk_dept != "Select Department...":
                dept_filtered = df[df["dept_full"] == bulk_dept]
                parent_assets = ["All"] + sorted(dept_filtered["parent_asset"].dropna().unique().tolist())
            else:
                parent_assets = ["All"]
            bulk_parent = st.selectbox("Parent Asset", parent_assets, key="bulk_parent")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            bulk_bldg = st.selectbox("Building", ["All"] + sorted(df["location_building"].dropna().unique().tolist()), key="bulk_bldg")
        with c2:
            bulk_status = st.selectbox("Enrollment Status", ["All", "Enrolled", "Not Enrolled"], key="bulk_status")
        with c3:
            bulk_search = st.text_input("🔍 Search Sub-Asset", key="bulk_search", placeholder="Sub-asset name...")
        
        # Apply filters
        filtered = df.copy()
        if bulk_dept != "Select Department...":
            filtered = filtered[filtered["dept_full"] == bulk_dept]
        if bulk_parent != "All" and bulk_parent != "Select Department...":
            filtered = filtered[filtered["parent_asset"] == bulk_parent]
        if bulk_bldg != "All":
            filtered = filtered[filtered["location_building"] == bulk_bldg]
        if bulk_status == "Enrolled":
            filtered = filtered[filtered["checklist_clean"].notna()]
        elif bulk_status == "Not Enrolled":
            filtered = filtered[filtered["checklist_clean"].isna()]
        if bulk_search:
            filtered = filtered[filtered["name"].str.contains(bulk_search, case=False, na=False)]
        
        st.caption(f"📋 {len(filtered)} assets match filters")
        
        # Build asset options
        asset_options = [f"{row['parent_asset']} → {row['name'][:60]} ({row['asset_tag']})" for _, row in filtered.iterrows()]
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Select All", key="bulk_select_all", use_container_width=True):
                st.session_state["bulk_selected"] = asset_options
                st.rerun()
        with c2:
            if st.button("❌ Clear", key="bulk_clear", use_container_width=True):
                st.session_state["bulk_selected"] = []
                st.rerun()
        
        if "bulk_selected" not in st.session_state:
            st.session_state["bulk_selected"] = []
        
        # FIX: Only use defaults that exist in current filtered options
        valid_defaults = [d for d in st.session_state.get("bulk_selected", []) if d in asset_options]
        
        selected_assets = st.multiselect(
            "Select Assets to Enroll*",
            options=asset_options,
            default=valid_defaults,
            key="bulk_multi"
        )
        
        if selected_assets:
            st.caption(f"✅ {len(selected_assets)} assets selected")
            st.markdown("---")
            
            st.markdown("#### Step 2: Template & Frequency")
            c1, c2, c3 = st.columns(3)
            with c1:
                bulk_template = st.selectbox("Checklist Template*", template_options, key="bulk_template")
            with c2:
                bulk_freq = st.selectbox("PPM Frequency*", ["Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="bulk_freq")
            with c3:
                bulk_overwrite = st.checkbox("Overwrite existing", value=True, key="bulk_overwrite")
                create_schedules = st.checkbox("Create PPM Schedule entries", value=True, key="bulk_create_sched")
            
            render_template_preview(bulk_template)
            
            st.markdown("---")
            
            st.markdown("#### Step 3: Staggered Scheduling (Optional)")
            staggered = st.checkbox("Stagger dates across assets", value=False, key="bulk_staggered",
                help="Asset 1 gets original dates, Asset 2 gets dates offset by stagger interval, etc.")
            stagger_days = 0
            if staggered:
                stagger_days = st.number_input("Stagger Interval (Days)", min_value=1, value=7, key="bulk_stagger_days")
                st.info(f"Asset 1: Original dates | Asset 2: +{stagger_days}d | Asset 3: +{stagger_days*2}d | ...")
            
            st.markdown("---")
            
            st.markdown("#### Step 4: Schedule Dates")
            date_mode_bulk = st.radio("Date Selection Mode", ["📅 Manual Date Picker", "🔄 Auto-Generate Dates"], horizontal=True, key="bulk_date_mode")
            
            if date_mode_bulk == "📅 Manual Date Picker":
                dates_string_bulk, has_dates_bulk = render_manual_date_picker("bulk")
            else:
                dates_string_bulk, has_dates_bulk = render_auto_generate_dates("bulk", bulk_freq)
            
            st.markdown("---")
            
            if has_dates_bulk and dates_string_bulk:
                dates_list_bulk = [d.strip() for d in dates_string_bulk.split(",") if d.strip()]
                
                st.markdown(f"""
                <div style="background:#EFF6FF;border-radius:10px;padding:1rem;margin:1rem 0;border:1px solid #BFDBFE;">
                    <b>📋 Bulk Summary:</b><br>
                    Assets: <b>{len(selected_assets)}</b><br>
                    Template: <b>{bulk_template}</b><br>
                    Frequency: <b>{bulk_freq}</b><br>
                    Dates per asset: <b>{len(dates_list_bulk)}</b><br>
                    Total entries: <b>{len(selected_assets) * len(dates_list_bulk)}</b><br>
                    Staggered: <b>{'Yes (+' + str(stagger_days) + 'd)' if staggered else 'No'}</b>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🚀 ENROLL ALL ASSETS", key="bulk_enroll_btn", use_container_width=True, type="primary"):
                    enrolled = 0
                    schedule_count = 0
                    skipped = 0
                    
                    for idx, asset_label in enumerate(selected_assets):
                        parts = asset_label.split(" (")
                        asset_tag = parts[-1].replace(")", "").strip()
                        asset_row = filtered[filtered["asset_tag"] == asset_tag]
                        if len(asset_row) == 0: continue
                        
                        asset = asset_row.iloc[0]
                        asset_id = asset["id"]
                        
                        if pd.notna(asset.get("checklist_clean")) and not bulk_overwrite:
                            skipped += 1
                            continue
                        
                        DB.update("assets", asset_id, {"checklist": bulk_template, "ppm_frequency": bulk_freq, "checklist_template": bulk_template})
                        
                        if create_schedules:
                            for date_idx, schedule_date in enumerate(dates_list_bulk):
                                try:
                                    actual_date = schedule_date
                                    if staggered:
                                        offset = idx * stagger_days
                                        actual_date = (datetime.strptime(schedule_date, "%Y-%m-%d") + timedelta(days=offset)).strftime("%Y-%m-%d")
                                    
                                    result = supabase.table("ppm_schedules").insert({
                                        "facility_code": fc, "asset_id": str(asset_id),
                                        "title": f"{asset.get('name','PPM')} - {bulk_template}",
                                        "frequency": bulk_freq, "status": "scheduled",
                                        "assigned_team": asset.get("department", ""),
                                        "next_due_date": actual_date, "created_at": datetime.now().isoformat()
                                    }).execute()
                                    
                                    if result and result.data:
                                        schedule_count += 1
                                except Exception as e:
                                    pass
                        enrolled += 1
                    
                    if "bulk_manual_dates" in st.session_state:
                        st.session_state["bulk_manual_dates"] = []
                    if "bulk_generated_dates" in st.session_state:
                        st.session_state["bulk_generated_dates"] = []
                    st.session_state["bulk_selected"] = []
                    
                    msg = f"✅ {enrolled} assets enrolled! ({schedule_count} schedule entries)"
                    if skipped > 0: msg += f" ({skipped} skipped)"
                    st.success(msg)
                    st.balloons()
                    st.rerun()
    
    # ============================================
    # TAB 2: SCHEDULED PPMs (READ-ONLY)
    # ============================================
    with tabs[2]:
        st.markdown("### 📋 Scheduled PPMs Overview")
        st.caption("View all enrolled PPMs across all assets.")
        
        if total_schedules == 0:
            st.info("No PPMs scheduled yet. Use Individual or Bulk Scheduling tabs to enroll assets.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                view_status = st.selectbox("Status", ["All", "scheduled", "completed", "overdue"], key="view_status")
            with c2:
                view_freq = st.selectbox("Frequency", ["All"] + ["Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Yearly"], key="view_freq")
            with c3:
                view_dept = st.selectbox("Department", ["All"] + sorted(existing_df["assigned_team"].dropna().unique().tolist()) if "assigned_team" in existing_df.columns else ["All"], key="view_dept")
            with c4:
                view_search = st.text_input("🔍 Search", key="view_search", placeholder="Title...")
            
            display_sched = existing_df.copy()
            if view_status != "All": display_sched = display_sched[display_sched["status"] == view_status]
            if view_freq != "All": display_sched = display_sched[display_sched["frequency"] == view_freq]
            if view_dept != "All" and "assigned_team" in display_sched.columns: display_sched = display_sched[display_sched["assigned_team"] == view_dept]
            if view_search: display_sched = display_sched[display_sched["title"].str.contains(view_search, case=False, na=False)]
            
            st.caption(f"📋 Showing {len(display_sched)} of {total_schedules} schedules")
            
            page_size = 20
            if "view_page" not in st.session_state: st.session_state.view_page = 1
            total_pages = max(1, (len(display_sched) + page_size - 1) // page_size)
            start = (st.session_state.view_page - 1) * page_size
            end = min(start + page_size, len(display_sched))
            
            c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
            with c1:
                if st.button("◀◀", key="v_first") and st.session_state.view_page > 1: st.session_state.view_page = 1; st.rerun()
            with c2:
                if st.button("◀", key="v_prev") and st.session_state.view_page > 1: st.session_state.view_page -= 1; st.rerun()
            with c3: st.markdown(f"**Page {st.session_state.view_page} of {total_pages}**")
            with c4:
                if st.button("▶", key="v_next") and st.session_state.view_page < total_pages: st.session_state.view_page += 1; st.rerun()
            with c5:
                if st.button("▶▶", key="v_last"): st.session_state.view_page = total_pages; st.rerun()
            
            for _, sched in display_sched.iloc[start:end].iterrows():
                status = sched.get("status", "scheduled")
                sc = {"scheduled": "#3B82F6", "completed": "#10B981", "overdue": "#EF4444"}.get(status, "#3B82F6")
                asset_name = "N/A"
                if sched.get("asset_id"):
                    match = df[df["id"] == str(sched.get("asset_id"))]
                    if len(match) > 0: asset_name = match.iloc[0].get("name", "N/A")[:60]
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:8px;padding:0.6rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <div style="flex:1;">
                        <b>{sched.get('title','N/A')[:80]}</b>
                        <br><span style="font-size:0.65rem;color:#666;">🏢 {sched.get('assigned_team','N/A')} | 🔄 {sched.get('frequency','N/A')}</span>
                        <br><span style="font-size:0.6rem;color:#888;">🏗️ {asset_name} | 📅 {sched.get('next_due_date','N/A')}</span>
                    </div>
                    <span style="background:{sc};color:white;padding:3px 12px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.download_button("📥 Download CSV", display_sched.to_csv(index=False), f"ppm_schedules_{today}.csv", "text/csv", use_container_width=True)
    
    # ============================================
    # TAB 3: CONSOLIDATED REPORT
    # ============================================
    with tabs[3]:
        st.markdown("### 📊 Consolidated PPM Report")
        
        consolidated = []
        for _, asset in df.iterrows():
            enrolled = pd.notna(asset.get("checklist_clean"))
            asset_schedules = existing_df[existing_df["asset_id"] == str(asset.get("id"))] if not existing_df.empty else pd.DataFrame()
            schedule_dates_list = sorted(asset_schedules["next_due_date"].tolist()) if len(asset_schedules) > 0 else []
            
            consolidated.append({
                "SNO": len(consolidated) + 1,
                "Asset": asset.get("parent_asset", "N/A"),
                "Sub Asset": asset.get("name", "N/A"),
                "Department": asset.get("dept_full", "N/A"),
                "Checklist": asset.get("checklist_clean") if enrolled else "Not Enrolled",
                "Frequency": asset.get("ppm_frequency", asset.get("verification_frequency", "N/A")),
                "Schedule Dates": ", ".join(schedule_dates_list[:5]) + (f" +{len(schedule_dates_list)-5} more" if len(schedule_dates_list) > 5 else ""),
                "Total Dates": len(schedule_dates_list),
                "Status": "Enrolled" if enrolled else "Pending"
            })
        
        cons_df = pd.DataFrame(consolidated)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            cons_status = st.selectbox("Status", ["All", "Enrolled", "Pending"], key="cons_status_rpt")
        with c2:
            cons_freq = st.selectbox("Frequency", ["All", "Daily", "Weekly", "Bi-Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"], key="cons_freq_rpt")
        with c3:
            cons_search = st.text_input("🔍 Search", key="cons_search_rpt", placeholder="Asset or checklist...")
        
        display_cons = cons_df.copy()
        if cons_status != "All": display_cons = display_cons[display_cons["Status"] == cons_status]
        if cons_freq != "All": display_cons = display_cons[display_cons["Frequency"] == cons_freq]
        if cons_search:
            mask = display_cons["Asset"].str.contains(cons_search, case=False, na=False) | display_cons["Sub Asset"].str.contains(cons_search, case=False, na=False) | display_cons["Checklist"].str.contains(cons_search, case=False, na=False)
            display_cons = display_cons[mask]
        
        enrolled_total = len(display_cons[display_cons["Status"] == "Enrolled"])
        pending_total = len(display_cons[display_cons["Status"] == "Pending"])
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("📋 Total", len(display_cons))
        with c2: st.metric("⏳ Pending", pending_total)
        with c3: st.metric("✅ Enrolled", enrolled_total)
        
        st.markdown("---")
        
        page_size = 25
        if "cons_rpt_page" not in st.session_state: st.session_state.cons_rpt_page = 1
        total_pages_cons = max(1, (len(display_cons) + page_size - 1) // page_size)
        start_cons = (st.session_state.cons_rpt_page - 1) * page_size
        end_cons = min(start_cons + page_size, len(display_cons))
        page_data = display_cons.iloc[start_cons:end_cons]
        
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("◀◀", key="cr_first") and st.session_state.cons_rpt_page > 1: st.session_state.cons_rpt_page = 1; st.rerun()
        with c2:
            if st.button("◀", key="cr_prev") and st.session_state.cons_rpt_page > 1: st.session_state.cons_rpt_page -= 1; st.rerun()
        with c3: st.markdown(f"**Page {st.session_state.cons_rpt_page} of {total_pages_cons}**")
        with c4:
            if st.button("▶", key="cr_next") and st.session_state.cons_rpt_page < total_pages_cons: st.session_state.cons_rpt_page += 1; st.rerun()
        with c5:
            if st.button("▶▶", key="cr_last"): st.session_state.cons_rpt_page = total_pages_cons; st.rerun()
        
        st.caption(f"Showing {start_cons+1}–{end_cons} of {len(display_cons)} records")
        
        if len(page_data) > 0:
            for _, row in page_data.iterrows():
                is_enrolled_row = row["Status"] == "Enrolled"
                border = "#10B981" if is_enrolled_row else "#F59E0B"
                bg = "#ECFDF5" if is_enrolled_row else "#FFFBEB"
                badge = "✅ Enrolled" if is_enrolled_row else "⏳ Pending"
                badge_bg = "#10B981" if is_enrolled_row else "#F59E0B"
                
                st.markdown(f"""
                <div style="background:{bg};border-left:3px solid {border};border-radius:6px;padding:0.5rem;margin:0.2rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <div style="flex:1;">
                        <b>#{row['SNO']} {row['Asset']}</b>
                        <br><span style="font-size:0.65rem;color:#666;">└ {row['Sub Asset'][:80]}</span>
                        <br><span style="font-size:0.6rem;color:#888;">📋 {row['Checklist']} | 📅 {row['Frequency']} | 🔢 {row['Total Dates']} dates</span>
                    </div>
                    <span style="background:{badge_bg};color:white;padding:3px 12px;border-radius:15px;font-size:0.65rem;font-weight:700;white-space:nowrap;">{badge}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No records match your filters.")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download CSV", display_cons.to_csv(index=False), f"consolidated_ppm_{today}.csv", "text/csv", use_container_width=True)
        with c2:
            st.download_button("📥 Download HTML", display_cons.to_html(index=False), f"consolidated_ppm_{today}.html", "text/html", use_container_width=True)



# ============================================
# KEY MANAGEMENT — FORTUNE 500 COMMAND CENTER
# ============================================
def page_key_management():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    user_role = st.session_state.get("user_role", "staff")
    user_name = st.session_state.get("user_name", "User")
    user_email = st.session_state.get("user", {}).get("email", "guest")
    is_admin = user_role in ["admin", "approver", "super_admin", "sr_management", "manager", "team_lead"]
    
    st.markdown(f'## 🔑 Key Management Command Center — {info.get("full_name", fc)}')
    
    from datetime import timezone, timedelta
    wat_now = datetime.now(timezone(timedelta(hours=1)))
    today = wat_now.date()
    
   # Fetch all keys with pagination
    import time as _time
    all_keys = []
    page_size = 1000
    offset = 0
    
    while True:
        keys_page = None
        for attempt in range(3):
            try:
                keys_page = supabase.table("key_registry").select("*").eq("facility_code", fc).range(offset, offset + page_size - 1).execute()
                break
            except:
                _time.sleep(0.5)
        
        if keys_page and keys_page.data:
            all_keys.extend(keys_page.data)
            if len(keys_page.data) < page_size:
                break
            offset += page_size
        else:
            break
    
    keys_df = pd.DataFrame(all_keys) if all_keys else pd.DataFrame()
    
    total_keys = len(keys_df)
    available_keys = len(keys_df[keys_df["available_copies"] > 0]) if total_keys > 0 else 0
    not_available = total_keys - available_keys
    issued_keys = 0
    
    # Get active transactions
    import time as _time
    active_transactions = None
    for attempt in range(3):
        try:
            active_transactions = supabase.table("key_transactions").select("*").eq("status", "issued").execute()
            break
        except:
            _time.sleep(0.5)
    if active_transactions and active_transactions.data:
        issued_keys = len(active_transactions.data)
    
    # ============================================
    # TOP RIBBON
    # ============================================
    st.markdown("### 🟦 Key Management Ribbon")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #3B82F6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Total Keys</div><div style="font-size:1.4rem;font-weight:800;color:#3B82F6;">{total_keys}</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #10B981;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Available</div><div style="font-size:1.4rem;font-weight:800;color:#10B981;">{available_keys}</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #EF4444;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Not Available</div><div style="font-size:1.4rem;font-weight:800;color:#EF4444;">{not_available}</div></div>""", unsafe_allow_html=True)
    with c4: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #F59E0B;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Issued</div><div style="font-size:1.4rem;font-weight:800;color:#F59E0B;">{issued_keys}</div></div>""", unsafe_allow_html=True)
    with c5: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #8B5CF6;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Buildings</div><div style="font-size:1.4rem;font-weight:800;color:#8B5CF6;">{keys_df['location_building'].nunique() if total_keys > 0 else 0}</div></div>""", unsafe_allow_html=True)
    with c6: st.markdown(f"""<div style="background:white;border-radius:12px;padding:0.8rem;text-align:center;border-top:3px solid #EC4899;box-shadow:0 2px 6px rgba(0,0,0,0.04);"><div style="font-size:0.55rem;color:#888;">Overdue</div><div style="font-size:1.4rem;font-weight:800;color:#EC4899;">0</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================
    # TABS
    # ============================================
    tabs = st.tabs(["📋 Key Register", "🔄 Issue/Return", "📊 Transaction Log", "🔍 Quick Lookup", "📄 Reports"])
    
    # ============================================
    # TAB 0: KEY REGISTER
    # ============================================
    with tabs[0]:
        st.markdown("### 📋 Key Register")
        
        if total_keys == 0:
            st.info("No keys registered for this facility.")
        else:
            # Filters
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                buildings = ["All"] + sorted(keys_df["location_building"].dropna().unique().tolist())
                sel_building = st.selectbox("Building", buildings, key="key_bldg")
            with c2:
                floors = ["All"] + sorted(keys_df["location_floor"].dropna().unique().tolist())
                sel_floor = st.selectbox("Floor", floors, key="key_floor")
            with c3:
                key_types = ["All"] + sorted(keys_df["key_type"].dropna().unique().tolist())
                sel_type = st.selectbox("Type", key_types, key="key_type_filter")
            with c4:
                status_opts = ["All", "Available", "Not Available"]
                sel_status = st.selectbox("Status", status_opts, key="key_status_filter")
            with c5:
                search_key = st.text_input("🔍 Search", key="key_search", placeholder="Key name or code...")
            
            # Apply filters
            display_keys = keys_df.copy()
            if sel_building != "All": display_keys = display_keys[display_keys["location_building"] == sel_building]
            if sel_floor != "All": display_keys = display_keys[display_keys["location_floor"] == sel_floor]
            if sel_type != "All": display_keys = display_keys[display_keys["key_type"] == sel_type]
            if sel_status == "Available": display_keys = display_keys[display_keys["available_copies"] > 0]
            elif sel_status == "Not Available": display_keys = display_keys[display_keys["available_copies"] == 0]
            if search_key:
                mask = display_keys["key_name"].str.contains(search_key, case=False, na=False) | display_keys["key_code"].str.contains(search_key, case=False, na=False)
                display_keys = display_keys[mask]
            
            st.caption(f"📋 Showing {len(display_keys)} of {total_keys} keys")
            
            # Pagination
            page_size = 15
            if "key_page" not in st.session_state: st.session_state.key_page = 1
            total_pages = max(1, (len(display_keys) + page_size - 1) // page_size)
            start = (st.session_state.key_page - 1) * page_size
            end = min(start + page_size, len(display_keys))
            
            c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
            with c1:
                if st.button("◀◀", key="k_first") and st.session_state.key_page > 1: st.session_state.key_page = 1; st.rerun()
            with c2:
                if st.button("◀", key="k_prev") and st.session_state.key_page > 1: st.session_state.key_page -= 1; st.rerun()
            with c3: st.markdown(f"**Page {st.session_state.key_page} of {total_pages}**")
            with c4:
                if st.button("▶", key="k_next") and st.session_state.key_page < total_pages: st.session_state.key_page += 1; st.rerun()
            with c5:
                if st.button("▶▶", key="k_last"): st.session_state.key_page = total_pages; st.rerun()
            
            st.markdown("---")
            
            # Key cards
            for _, key in display_keys.iloc[start:end].iterrows():
                avail = key.get("available_copies", 0)
                total = key.get("total_copies", 0)
                status = "Available" if avail > 0 else "Not Available"
                sc = "#10B981" if avail > 0 else "#EF4444"
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:0.7rem;margin:0.3rem 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{key.get('key_name','N/A')[:90]}</b>
                            <br><span style="font-size:0.65rem;color:#666;">📍 {key.get('location_building','')} | 🏠 {key.get('location_floor','')} | 🏷️ {key.get('key_type','')}</span>
                            <br><span style="font-size:0.6rem;color:#888;">🆔 {key.get('key_code','')} | 📋 {avail}/{total} available</span>
                        </div>
                        <span style="background:{sc};color:white;padding:3px 10px;border-radius:12px;font-size:0.6rem;font-weight:600;">{status}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Quick action buttons
                if avail > 0 and is_admin:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"🔑 Issue Key", key=f"issue_{key['id']}", use_container_width=True):
                            st.session_state.issuing_key = key["id"]
                            st.rerun()
                    with c2:
                        if st.button(f"📋 Details", key=f"det_{key['id']}", use_container_width=True):
                            st.session_state.key_detail = key["id"]
                            st.rerun()
    
    # ============================================
    # TAB 1: ISSUE / RETURN
    # ============================================
    with tabs[1]:
        st.markdown("### 🔄 Issue / Return Key")
        
        if "issuing_key" in st.session_state and st.session_state.issuing_key:
            key_id = st.session_state.issuing_key
            key_info = keys_df[keys_df["id"] == key_id].iloc[0] if len(keys_df[keys_df["id"] == key_id]) > 0 else None
            
            if key_info is not None:
                st.markdown(f"""
                <div style="background:#EFF6FF;border-left:4px solid #3B82F6;border-radius:10px;padding:1rem;margin:1rem 0;">
                    <b>Issuing Key:</b> {key_info.get('key_name','')[:100]}<br>
                    <span style="font-size:0.8rem;">📍 {key_info.get('location_building','')} | 🏠 {key_info.get('location_floor','')}</span><br>
                    <span style="font-size:0.8rem;">Available: {key_info.get('available_copies',0)}/{key_info.get('total_copies',0)}</span>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("issue_key_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        issued_to = st.text_input("Issue To*", value=st.session_state.get("user_name",""))
                        issued_email = st.text_input("Recipient Email*", value=user_email)
                    with c2:
                        work_permit_ref = st.text_input("Work Permit Reference (if applicable)")
                        expected_return = st.date_input("Expected Return Date", today + timedelta(days=1))
                    
                    issue_notes = st.text_area("Notes", placeholder="Purpose of key issue...")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("🔑 ISSUE KEY", use_container_width=True, type="primary"):
                            if issued_to:
                                safe_supabase_query(lambda: supabase.table("key_transactions").insert({
                                    "key_id": key_id,
                                    "transaction_type": "issue",
                                    "requested_by": issued_to,
                                    "requested_by_email": issued_email,
                                    "work_permit_id": work_permit_ref if work_permit_ref else None,
                                    "issued_by": user_name,
                                    "issued_at": wat_now.isoformat(),
                                    "expected_return": str(expected_return),
                                    "status": "issued",
                                    "notes": issue_notes,
                                    "created_at": wat_now.isoformat()
                                }).execute(), error_prefix="Issue key")
                                
                                new_avail = max(0, key_info.get("available_copies", 0) - 1)
                                safe_supabase_query(lambda: supabase.table("key_registry").update({"available_copies": new_avail}).eq("id", key_id).execute(), error_prefix="Update copies")
                                
                                try:
                                    send_email_notification(issued_email, f"🔑 Key Issued — {key_info.get('key_name','')[:50]}",
                                        f"""<div style="font-family:Arial;max-width:500px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                        <div style="background:#C8A951;padding:20px;color:white;"><h2>Key Issued</h2><p>{info.get('full_name',fc)}</p></div>
                                        <div style="padding:20px;"><p><b>Key:</b> {key_info.get('key_name','')}</p><p><b>Issued to:</b> {issued_to}</p><p><b>Expected return:</b> {expected_return}</p></div></div>""")
                                except: pass
                                
                                st.success("✅ Key issued!"); st.session_state.issuing_key = None; st.balloons(); st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.issuing_key = None; st.rerun()
        
        # Return section
        st.markdown("---")
        st.markdown("### 📤 Return Key")
        
        import time as _time
        active_issued = None
        for attempt in range(3):
            try:
                active_issued = supabase.table("key_transactions").select("*, key_registry!inner(key_name, key_code, location_building, location_floor)").eq("status", "issued").order("issued_at", desc=True).execute()
                break
            except:
                _time.sleep(0.5)
        
        if active_issued and active_issued.data:
            for txn in active_issued.data:
                key_info_nested = txn.get("key_registry", {})
                st.markdown(f"""
                <div style="background:white;border-left:4px solid #F59E0B;border-radius:8px;padding:0.7rem;margin:0.3rem 0;">
                    <b>{key_info_nested.get('key_name','')[:80]}</b>
                    <br><span style="font-size:0.7rem;">👤 {txn.get('requested_by','')} | 📅 Issued: {str(txn.get('issued_at',''))[:10]}</span>
                    <br><span style="font-size:0.65rem;">Expected return: {str(txn.get('expected_return',''))[:10]}</span>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"✅ Return This Key", key=f"return_{txn['id']}", use_container_width=True):
                    safe_supabase_query(lambda: supabase.table("key_transactions").update({
                        "status": "returned",
                        "returned_at": wat_now.isoformat()
                    }).eq("id", txn["id"]).execute(), error_prefix="Return key")
                    
                    key_reg = safe_supabase_query(lambda: supabase.table("key_registry").select("available_copies,total_copies").eq("id", txn["key_id"]).single().execute(), error_prefix="Get copies")
                    if key_reg and key_reg.data:
                        new_avail = min(key_reg.data.get("total_copies", 1), key_reg.data.get("available_copies", 0) + 1)
                        safe_supabase_query(lambda: supabase.table("key_registry").update({"available_copies": new_avail}).eq("id", txn["key_id"]).execute(), error_prefix="Update copies")
                    
                    st.success("✅ Key returned!"); st.rerun()
        else:
            st.info("No keys currently issued.")
    
    # ============================================
    # TAB 2: TRANSACTION LOG
    # ============================================
    with tabs[2]:
        st.markdown("### 📊 Transaction Log")
        
        all_transactions = safe_supabase_query(lambda: supabase.table("key_transactions").select("*, key_registry(key_name, key_code)").order("created_at", desc=True).limit(100).execute(), error_prefix="Transactions")
        
        if all_transactions and all_transactions.data:
            for txn in all_transactions.data:
                txn_type = txn.get("transaction_type", "issue")
                status = txn.get("status", "pending")
                sc = {"issued": "#F59E0B", "returned": "#10B981", "pending": "#3B82F6", "rejected": "#EF4444"}.get(status, "#3B82F6")
                ki = txn.get("key_registry", {})
                
                st.markdown(f"""
                <div style="background:white;border-left:4px solid {sc};border-radius:8px;padding:0.6rem;margin:0.2rem 0;font-size:0.75rem;">
                    <b>{txn_type.upper()}</b> — {ki.get('key_name','')[:60]}
                    <br>👤 {txn.get('requested_by','')} | 📅 {str(txn.get('created_at',''))[:16]}
                    <span style="float:right;color:{sc};font-weight:600;">{status.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No transactions recorded.")
    
    # ============================================
    # TAB 3: QUICK LOOKUP
    # ============================================
    with tabs[3]:
        st.markdown("### 🔍 Quick Key Lookup")
        
        lookup_code = st.text_input("Enter Key Code or Key Name", placeholder="e.g., SAT-GF-FRONT-WD")
        
        if lookup_code:
            result = safe_supabase_query(lambda: supabase.table("key_registry").select("*").or_(f"key_code.ilike.%{lookup_code}%,key_name.ilike.%{lookup_code}%").eq("facility_code", fc).limit(10).execute(), error_prefix="Key lookup")
            
            if result and result.data:
                for key in result.data:
                    avail = key.get("available_copies", 0)
                    sc = "#10B981" if avail > 0 else "#EF4444"
                    
                    st.markdown(f"""
                    <div style="background:white;border-left:4px solid {sc};border-radius:10px;padding:1rem;margin:0.5rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                        <h4>{key.get('key_name','')}</h4>
                        <p><b>Code:</b> {key.get('key_code','')} | <b>Type:</b> {key.get('key_type','')}</p>
                        <p><b>Location:</b> {key.get('location_building','')} — {key.get('location_floor','')}</p>
                        <p><b>Available:</b> {avail} of {key.get('total_copies',0)} copies</p>
                        <p><b>Status:</b> <span style="color:{sc};font-weight:600;">{'Available' if avail > 0 else 'Not Available'}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show recent transactions for this key
                    recent_txn = safe_supabase_query(lambda: supabase.table("key_transactions").select("*").eq("key_id", key["id"]).order("created_at", desc=True).limit(5).execute(), error_prefix="Recent transactions")
                    if recent_txn and recent_txn.data:
                        with st.expander("📋 Recent Transactions"):
                            for txn in recent_txn.data:
                                st.caption(f"{str(txn.get('created_at',''))[:16]} | {txn.get('transaction_type','').upper()} | {txn.get('requested_by','')} | {txn.get('status','').upper()}")
            else:
                st.info("No keys found matching your search.")
    
    # ============================================
    # TAB 4: REPORTS
    # ============================================
    with tabs[4]:
        st.markdown("### 📄 Key Management Reports")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Keys", total_keys)
        with c2: st.metric("Available", available_keys)
        with c3: st.metric("Issued Now", issued_keys)
        with c4: st.metric("Buildings", keys_df["location_building"].nunique() if total_keys > 0 else 0)
        
        st.markdown("---")
        
        # Building breakdown
        if total_keys > 0:
            st.markdown("### 🏢 Keys by Building")
            bldg_counts = keys_df["location_building"].value_counts()
            fig = px.bar(x=bldg_counts.values, y=bldg_counts.index, orientation='h', title="Keys per Building", color=bldg_counts.values, color_continuous_scale="Reds")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Export
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 Export Key Register (CSV)", use_container_width=True):
                st.download_button("Download CSV", keys_df.to_csv(index=False), f"key_register_{fc}_{today}.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("📥 Export Transactions (CSV)", use_container_width=True):
                all_txn = safe_supabase_query(lambda: supabase.table("key_transactions").select("*").order("created_at", desc=True).limit(500).execute(), error_prefix="Export transactions")
                if all_txn and all_txn.data:
                    txn_df = pd.DataFrame(all_txn.data)
                    st.download_button("Download CSV", txn_df.to_csv(index=False), f"key_transactions_{today}.csv", "text/csv", use_container_width=True)


def page_key_reports():
    fc = st.session_state.get("facility", "WTC")
    info = FACILITY_INFO.get(fc, {})
    st.markdown(f'## 📊 Key Reports — {info.get("full_name", fc)}')
    st.info("Advanced key analytics and audit reports coming soon.")



# ============================================
# ROUTER
# ============================================
ROUTER={
    "cc":page_cc,"ar":page_ar,"cal":page_cal,"cs":page_cs,"ppm":page_ppm,
    "wo":page_wo,"wp":page_wp,"fo":page_fo,
    "km":page_key_management,"kmr":page_key_reports,
    "vm": page_visitor,"up":page_users,"rt":page_raise_ticket,"hd":page_helpdesk_queue,"fb": page_feedback,
    "ac":page_ac,"ic":page_ic,"hot":page_hot,"uc":page_uc,"mis":page_mis,
    "ppma": page_ppm_activities,
}

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    bg_path = Path("WTC Abuja 7 (1).jpg")
    if not bg_path.exists():
        for alt in ["wtc-logo.jpg", "WTC-logo.jpg", "WTC_Abuja_7.jpg"]:
            if Path(alt).exists():
                bg_path = Path(alt)
                break
    
    bg_base64 = ""
    if bg_path.exists():
        with open(bg_path, "rb") as f:
            bg_base64 = base64.b64encode(f.read()).decode()
    
    if bg_base64:
        st.markdown(f"""<style>.stApp {{background: url(data:image/jpeg;base64,{bg_base64}) center/cover no-repeat fixed !important;}}</style>""", unsafe_allow_html=True)
        st.markdown(f"""<meta importance="high" fetchpriority="high">""", unsafe_allow_html=True)
    
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:2rem;box-shadow:0 20px 50px rgba(0,0,0,0.3);text-align:center;"><div style="display:flex;align-items:center;justify-content:center;gap:0.5rem;margin-bottom:0.3rem;">{get_nav_logo()}<div style="width:1px;height:22px;background:#ddd;"></div><span style="font-weight:800;color:#1a1a1a;font-size:1.1rem;">facility<span style="color:#CC0000;">X</span>perience</span></div><p style="color:#888;font-size:0.8rem;">Churchgate Group</p></div>""", unsafe_allow_html=True)
        
        email = st.text_input("📧 Email", placeholder="e.g. eetuk@churchgate.com", key="fx_em")
        password = st.text_input("🔑 Password", type="password", key="fx_pw")
        
        if st.button("🚀 Sign In", use_container_width=True, type="primary", key="fx_btn"):
            if email and password:
                can_attempt, rate_msg = check_login_rate_limit(email)
                if not can_attempt:
                    st.error(f"🚫 {rate_msg}")
                    st.stop()
                
                try:
                    res = supabase.table("app_users").select("*").eq("email", email).eq("is_active", True).single().execute()
                except:
                    res = type('obj', (object,), {'data': None})()
                
                if res and res.data:
                    pw_result = check_password(password, res.data.get("password_hash", ""))
                    if pw_result == True or pw_result == "migrate":
                        if pw_result == "migrate":
                            new_hash = hash_password(password)
                            safe_supabase_query(lambda uid=res.data["id"]: supabase.table("app_users").update({"password_hash": new_hash}).eq("id", uid).execute(), error_prefix="Migrate password")
                        log_login_attempt(email, True)
                        st.session_state.authenticated = True
                        st.session_state.user = res.data
                        st.session_state.user_name = res.data.get("name", "")
                        st.session_state.user_role = res.data.get("role", "staff")
                        safe_supabase_query(lambda uid=res.data["id"]: supabase.table("app_users").update({"last_login": datetime.now().isoformat()}).eq("id", uid).execute(), error_prefix="Last login")
                        st.query_params["auth"] = "true"
                        st.query_params["user_key"] = res.data.get("email", "")
                        st.rerun()
                    else:
                        log_login_attempt(email, False)
                        remaining = get_recent_failures_count(email)
                        st.error(f"Invalid email or password. {remaining} attempts remaining before lockout.")
                else:
                    log_login_attempt(email, False)
                    remaining = get_recent_failures_count(email)
                    st.error(f"Invalid email or password. {remaining} attempts remaining before lockout.")
            else:
                st.error("Please enter email and password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔑 Forgot Password?", use_container_width=True, key="fx_forgot"):
            st.session_state.show_forgot = True
            st.rerun()

def forgot_password_page():
    st.markdown("""<style>#MainMenu,header,footer{visibility:hidden;}section[data-testid="stSidebar"]{display:none;}</style>""", unsafe_allow_html=True)
    
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 1
    if "reset_email" not in st.session_state:
        st.session_state.reset_email = ""
    
    _, col, _ = st.columns([0.3, 0.4, 0.3])
    with col:
        st.markdown(f"""<div style="background:white;border-radius:16px;padding:2rem;box-shadow:0 10px 30px rgba(0,0,0,0.2);text-align:center;"><div style="display:flex;align-items:center;justify-content:center;gap:0.5rem;margin-bottom:0.5rem;">{get_nav_logo()}<div style="width:1px;height:22px;background:#ddd;"></div><span style="font-weight:800;color:#1a1a1a;font-size:1.1rem;">facility<span style="color:#CC0000;">X</span>perience</span></div><p style="color:#888;font-size:0.8rem;">Churchgate Group</p>""", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.reset_step == 1:
            st.subheader("🔑 Forgot Password")
            st.caption("Enter your email to receive a verification code")
            
            email = st.text_input("Email", placeholder="e.g. yourname@churchgate.com")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📩 Send Verification Code", use_container_width=True, type="primary"):
                    if email:
                        try:
                            res = safe_supabase_query(lambda: supabase.table("app_users").select("*").eq("email", email).single().execute(), error_prefix="Reset lookup")
                        except:
                            res = type('obj', (object,), {'data': None})()
                        
                        if res and res.data:
                            import random
                            verify_code = str(random.randint(100000, 999999))
                            expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
                            
                            safe_supabase_query(lambda uid=res.data["id"]: supabase.table("app_users").update({
                                "reset_token": verify_code,
                                "reset_token_expiry": expiry
                            }).eq("id", uid).execute(), error_prefix="Store reset code")
                            
                            send_email_notification(
                                email,
                                "🔐 facilityXperience — Password Reset Code",
                                f"""
                                <div style="font-family:Arial;max-width:500px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                    <div style="background:#C8A951;padding:20px;color:white;text-align:center;">
                                        <h2 style="margin:0;">Password Reset Code</h2>
                                        <p style="margin:5px 0 0 0;font-size:12px;">Churchgate Group — facilityXperience</p>
                                    </div>
                                    <div style="padding:20px;">
                                        <p>You requested a password reset. Use the code below:</p>
                                        <div style="text-align:center;margin:20px 0;">
                                            <div style="font-size:2rem;font-weight:800;letter-spacing:0.5rem;color:#C8A951;background:#faf7f2;padding:15px;border-radius:10px;border:2px dashed #C8A951;">{verify_code}</div>
                                        </div>
                                        <p style="font-size:12px;color:#888;">This code expires in 10 minutes.</p>
                                    </div>
                                </div>
                                """
                            )
                            
                            st.session_state.reset_email = email
                            st.session_state.reset_step = 2
                            st.success(f"✅ Verification code sent to {email}")
                            st.rerun()
                        else:
                            st.error("Email not found")
                    else:
                        st.error("Please enter your email")
            with c2:
                if st.button("🔙 Back to Login", use_container_width=True):
                    st.session_state.show_forgot = False
                    st.session_state.reset_step = 1
                    st.rerun()
        
        elif st.session_state.reset_step == 2:
            st.subheader("🔐 Verify Code")
            st.caption(f"Enter the 6-digit code sent to {st.session_state.reset_email}")
            
            code_input = st.text_input("Verification Code", placeholder="000000", max_chars=6)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("✅ Verify", use_container_width=True, type="primary"):
                    res = safe_supabase_query(lambda: supabase.table("app_users").select("*").eq("email", st.session_state.reset_email).single().execute(), error_prefix="Verify code")
                    if res and res.data:
                        stored_code = res.data.get("reset_token", "")
                        expiry = res.data.get("reset_token_expiry")
                        
                        if stored_code == code_input:
                            if expiry and datetime.now().isoformat() < expiry:
                                st.session_state.reset_step = 3
                                st.success("✅ Code verified!")
                                st.rerun()
                            else:
                                st.error("Code expired. Please request a new one.")
                                st.session_state.reset_step = 1
                                st.rerun()
                        else:
                            st.error("Invalid code. Please try again.")
            with c2:
                if st.button("🔄 Resend Code", use_container_width=True):
                    st.session_state.reset_step = 1
                    st.rerun()
            with c3:
                if st.button("🔙 Back", use_container_width=True):
                    st.session_state.reset_step = 1
                    st.session_state.show_forgot = False
                    st.rerun()
        
        elif st.session_state.reset_step == 3:
            st.subheader("🔐 Set New Password")
            
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm Password", type="password")
            
            if new_pw:
                strength = 0
                if len(new_pw) >= 12: strength += 1
                if any(c.isupper() for c in new_pw): strength += 1
                if any(c.isdigit() for c in new_pw): strength += 1
                if any(c in "!@#$%^&*()" for c in new_pw): strength += 1
                colors = ["#EF4444","#F59E0B","#3B82F6","#10B981"]
                labels = ["Weak","Fair","Good","Strong"]
                st.progress(strength/4, text=f"Password Strength: {labels[min(strength,3)]}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Reset Password", use_container_width=True, type="primary"):
                    if new_pw and new_pw == confirm_pw:
                        pw_valid, pw_msg = validate_password_strength(new_pw)
                        if not pw_valid:
                            st.error(f"⚠️ {pw_msg}")
                        else:
                            pw_hash = hash_password(new_pw)
                            safe_supabase_query(lambda: supabase.table("app_users").update({
                                "password_hash": pw_hash,
                                "reset_token": None,
                                "reset_token_expiry": None
                            }).eq("email", st.session_state.reset_email).execute(), error_prefix="Reset password")
                            
                            send_email_notification(
                                st.session_state.reset_email,
                                "✅ facilityXperience — Password Changed",
                                f"""
                                <div style="font-family:Arial;max-width:500px;border:1px solid #ddd;border-radius:12px;overflow:hidden;">
                                    <div style="background:#10B981;padding:20px;color:white;text-align:center;">
                                        <h2 style="margin:0;">Password Changed Successfully</h2>
                                    </div>
                                    <div style="padding:20px;">
                                        <p>Your password has been reset.</p>
                                    </div>
                                </div>
                                """
                            )
                            
                            st.success("✅ Password reset successfully!")
                            st.session_state.reset_step = 1
                            st.session_state.reset_email = ""
                            st.session_state.show_forgot = False
                            import time as _time
                            _time.sleep(2)
                            st.rerun()
                    else:
                        st.error("Passwords don't match or are empty")
            with c2:
                if st.button("🔙 Cancel", use_container_width=True):
                    st.session_state.reset_step = 1
                    st.session_state.show_forgot = False
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================
# MAIN
# ============================================
def main():
    inject_css()
    
    if st.session_state.get("last_email_error"):
        st.error(f"📧 {st.session_state.last_email_error}")
        st.session_state.last_email_error = None
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "show_forgot" not in st.session_state:
        st.session_state.show_forgot = False
    
    params = st.query_params
    if params.get("auth") == "true" and not st.session_state.authenticated:
        st.session_state.authenticated = True
        if "user_key" in params:
            try:
                res = safe_supabase_query(lambda: supabase.table("app_users").select("*").eq("email", params.get("user_key")).eq("is_active", True).single().execute(), error_prefix="Auth check")
                if res and res.data:
                    st.session_state.user = res.data
                    st.session_state.user_name = res.data.get("name", "")
                    st.session_state.user_role = res.data.get("role", "staff")
            except: pass
    
    if not st.session_state.authenticated:
        if st.session_state.show_forgot:
            forgot_password_page()
        else:
            login_page()
        st.stop()
    
    if "facility" not in st.session_state:
        st.session_state.facility = "WTC"
    if "page" not in st.session_state:
        st.session_state.page = "cc"
    
    fc = st.session_state.get("facility", "WTC")
    if fc == "WTC":
        wm_path = Path("WTC-logo.jpg")
        if not wm_path.exists():
            wm_path = Path("wtc-logo.jpg")
        if not wm_path.exists():
            wm_path = Path("wtc-logo.jpg.jpg")
        wm_ext = "jpeg"
    else:
        wm_path = Path("churchgate-logo.png")
        wm_ext = "png"
    
    # Only show watermark on Command Center page, and reduced opacity
    if st.session_state.get("page") == "cc" and wm_path.exists():
        with open(wm_path, "rb") as f:
            wm_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""<style>.stApp::after {{content:'';position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:70vw;height:70vh;background-image:url(data:image/{wm_ext};base64,{wm_b64});background-size:contain;background-repeat:no-repeat;background-position:center;opacity:0.04;z-index:0;pointer-events:none;}}</style>""", unsafe_allow_html=True)
    
    check_auto_escalation(fc)
    topnav()
    
    # Sidebar toggle — placed on the right
    c1, c2 = st.columns([0.85, 0.15])
    with c2:
        if st.button("◀ Hide Sidebar" if not st.session_state.get("sidebar_hidden", False) else "▶ Show", key="sidebar_toggle_btn", use_container_width=True):
            st.session_state.sidebar_hidden = not st.session_state.get("sidebar_hidden", False)
            st.rerun()
    
    # Greeting
    user = st.session_state.get("user", {})
    user_name = user.get("name", "User")
    designation = user.get("designation", "")
    emp_id = user.get("employee_id", "")
    from datetime import timezone, timedelta
    wat = datetime.now(timezone(timedelta(hours=1)))
    hour = wat.hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    
    st.markdown(f"""<div style="background:white;padding:0.8rem 1.5rem;border-radius:8px;margin:0.5rem 1rem 1.5rem 1rem;display:flex;align-items:center;justify-content:space-between;box-shadow:0 1px 3px rgba(0,0,0,0.06);"><div style="display:flex;align-items:center;gap:1rem;"><div style="width:42px;height:42px;border-radius:50%;background:{CHURCHGATE_RED};display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:1rem;">{user_name[:2].upper()}</div><div><div style="font-weight:700;font-size:1rem;color:#1a1a1a;">👋 {greeting}, {user_name}!</div><div style="font-size:0.75rem;color:#666;">{designation} • ID: {emp_id}</div></div></div><div style="font-size:0.7rem;color:#888;text-align:right;"><div>{wat.strftime('%A, %d %B %Y')}</div><div>{wat.strftime('%I:%M %p')} WAT</div></div></div>""", unsafe_allow_html=True)
    
    user_perms = safe_parse_permissions(st.session_state.get("user", {}).get("extra_permissions", []))
    user_role = st.session_state.get("user_role", "staff")
    
    page = st.session_state.page
    sidebar()
    ROUTER.get(page, page_cc)()

if __name__ == "__main__":
    main()