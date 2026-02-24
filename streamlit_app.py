import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_google_sheets_connection():
    """Connect to Google Sheets using service account"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(st.secrets, scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600)
def load_runners_from_sheet():
    """Fetches runners from rRunners tab (Row 1 = IDs, Row 5+ = Names)"""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        worksheet = sh.worksheet("rRunners")
        data = worksheet.get_all_values()
        
        race_ids = data[0] # d1r1, d1r2, etc.
        runners_map = {}

        for col_idx, rid in enumerate(race_ids):
            if rid.strip():
                # Extract runners from row 5 (index 4) downwards
                runners = [row[col_idx] for row in data[4:] if len(row) > col_idx and row[col_idx].strip()]
                runners_map[rid.lower().strip()] = ["-- Select Runner --"] + runners
        return runners_map
    except Exception as e:
        st.error(f"Error loading runners: {e}")
        return {}

@st.cache_data
def load_race_schedule():
    """Loads official race names from CSV"""
    try:
        return pd.read_csv('races.csv')
    except Exception as e:
        st.error(f"Error loading races.csv: {e}")
        return pd.DataFrame(columns=['DAY', 'RACE_NUMBER', 'RACE_NAME'])

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cheltenham 2026 Tipping", layout="wide")

# --- CUSTOM CSS (SKY BET STYLE + MOBILE FIXES) ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .main-header {
        background-color: #00277c; padding: 20px; border-radius: 10px;
        color: white; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #e71312;
    }
    .race-card {
        background-color: white; padding: 12px; border-radius: 8px;
        border-left: 5px solid #00277c; margin-bottom: 5px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; border-radius: 5px 5px 0px 0px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; border-bottom: 4px solid #e71312 !important; }
    
    /* Mobile-friendly selectboxes */
    div[data-baseweb="select"] > div { min-height: 45px; }

    /* Red Submit Button */
    div.stButton > button:first-child {
        background-color: #e71312; color: white; border: none;
        padding: 15px 30px; font-size: 20px; font-weight: bold;
        width: 100%; border-radius: 8px; transition: 0.3s;
    }
    div.stButton > button:first-child:hover { background-color: #c41010; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA ---
df_races = load_race_schedule()
runners_dict = load_runners_from_sheet()

# --- HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- FORM GENERATION ---
days = ["Tuesday", "Wednesday", "Thursday", "Friday"]
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}
tabs = st.tabs(days)

for i, day in enumerate(days):
    with tabs[i]: