import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_google_sheets_connection():
    """Connect to Google Sheets using service account secrets"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(st.secrets, scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600)
def load_runners_from_sheet():
    """Fetches runners: Row 1 = IDs (d1r1...), Row 5+ = Horse Names"""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        worksheet = sh.worksheet("rRunners")
        data = worksheet.get_all_values()
        
        race_ids = data[0] 
        runners_map = {}

        for col_idx, rid in enumerate(race_ids):
            clean_id = rid.lower().strip()
            if clean_id:
                # Row 5 is index 4
                runners = [row[col_idx] for row in data[4:] if len(row) > col_idx and row[col_idx].strip()]
                runners_map[clean_id] = ["-- Select Runner --"] + runners
        return runners_map
    except Exception as e:
        st.error(f"Error loading runners from Sheet: {e}")
        return {}

@st.cache_data
def load_race_schedule():
    """Loads race names from the local CSV file"""
    try:
        return pd.read_csv('races.csv')
    except Exception as e:
        st.error(f"Error loading races.csv: {e}")
        return pd.DataFrame(columns=['DAY', 'RACE_NUMBER', 'RACE_NAME'])

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Cheltenham 2026 Tipping", layout="wide")

# --- 3. CUSTOM CSS (SKY BET THEME) ---
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
        color: #333;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; border-radius: 5px 5px 0px 0px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; border-bottom: 4px solid #e71312 !important; }
    
    div[data-baseweb="select"] > div { min-height: 45px; }

    div.stButton > button:first-child {
        background-color: #e71312; color: white; border: none;
        padding: 15px 30px; font-size: 20px; font-weight: bold;
        width: 100%; border-radius: 8px;
    }
    div.stButton > button:first-child:hover { background-color: #c41010; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. INITIALIZE DATA ---
df_races = load_race_schedule()
runners_dict = load_runners_from_sheet()

# --- 5. HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- 6. FORM GENERATION ---
days = ["Tuesday", "Wednesday", "Thursday", "Friday"]
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}
tabs = st.tabs(days)

for i, day in enumerate(days):
    with tabs[i]:
        # Filter and sort races for the current day
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        
        if day_races.empty:
            st.info(f"No race data found for {day} in races.csv.")
            continue

        # Convert to list to process in pairs (for grid view)
        r_list = day_races.to_dict('records')

        # Row-based grid: ensures order 1, 2, 3... on mobile
        for j in range(0, len(r_list), 2):
            cols = st.columns(2)
            
            # Left Column / First in Stack
            r1 = r_list[j]
            rid1 = f"{day_code_map[day]}r{r1['RACE_NUMBER']}"
            with cols[0]:
                st.markdown(f'<div class="race-card"><span style="color: #e71312; font-weight: bold;">Race {r1["RACE_NUMBER"]}</span><br><b>{r1["RACE_NAME"]}</b></div>', unsafe_allow_html=True)
                st.selectbox(
                    f"Pick {rid1}", 
                    options=runners_dict.get(rid1, ["-- No Runners --"]), 
                    label_visibility="collapsed", 
                    key=f"pick_{rid1}"
                )

            # Right Column / Second in Stack
            if j + 1 < len(r_list):
                r2 = r_list[j+1]
                rid2 = f"{day_code_map[day]}r{r2['RACE_NUMBER']}"
                with cols[1]:
                    st.markdown(f'<div class="race-card"><span style="color: #e71312; font-weight: bold;">Race {r2["RACE_NUMBER"]}</span><br><b>{r2["RACE_NAME"]}</b></div>', unsafe_allow_html=True)
                    st.selectbox(
                        f"Pick {rid2}", 
                        options=runners_dict.get(rid2, ["-- No Runners --"]), 
                        label_visibility="collapsed", 
                        key=f"pick_{rid2}"
                    )

        # Daily Bonus Pick (NAP)
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312; margin-top: 25px;"><b>🌟 {day.upper()} DAILY NAP (BONUS)</b></div>', unsafe_allow_html=True)
        
        # Collect all unique runners for that day for the NAP dropdown
        all_day_runners = []
        for r_num in range(1, 8):
            rid_key = f"{day_code_map[day]}r{r_num}"
            if rid_key in runners_dict:
                all_day_runners.extend(runners_dict[rid_key][1:]) # Skip the placeholder
        
        st.selectbox(
            f"NAP {day}", 
            options=["-- Select Daily NAP --"] + sorted(list(set(all_day_runners))), 
            label_visibility="collapsed", 
            key=f"nap_{day}"
        )

# --- 7. SUBMISSION ---
st.write("---")
user_name = st.text_input("Player Name", placeholder="Enter your full name...")

if st.button("LOCK IN ALL TIPS"):
    if not user_name:
        st.error("Submission failed: Please enter your name.")
    else:
        try:
            client = get_google_sheets_connection()
            sheet = client.open("Cheltenham_v2").worksheet("Submissions")
            
            # Construct row: [Name, d1r1, d1r2... d4r7, NAP_Tue, NAP_Wed, NAP_Thu, NAP_Fri]
            submission_row = [user_name]
            
            # Race Picks
            for d_code in ["d1", "d2", "d3", "d4"]:
                for r_idx in range(1, 8):
                    val = st.session_state.get(f"pick_{d_code}r{r_idx}", "")
                    submission_row.append(val)
            
            # NAP Picks
            for d_name in days:
                submission_row.append(st.session_state.get(f"nap_{d_name}", ""))

            sheet.append_row(submission_row)
            st.balloons()
            st.success(f"Good luck, {user_name}! Your entries have been saved.")
        except Exception as e:
            st.error(f"Critical Error: Could not save to Google Sheets. {e}")