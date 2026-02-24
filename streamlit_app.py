import streamlit as st
import pandas as pd
import gspread
import re
from google.oauth2.service_account import Credentials

# --- 1. GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_google_sheets_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_runners_from_sheet():
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
                runners = [row[col_idx] for row in data[4:] if len(row) > col_idx and row[col_idx].strip()]
                runners_map[clean_id] = ["-- Select Runner --"] + runners
        return runners_map
    except Exception as e:
        st.error(f"Error loading runners: {e}")
        return {}

@st.cache_data
def load_race_schedule():
    try:
        return pd.read_csv('races.csv')
    except Exception as e:
        st.error(f"Error loading races.csv: {e}")
        return pd.DataFrame(columns=['DAY', 'RACE_NUMBER', 'RACE_NAME'])

# --- 2. PAGE CONFIG & CSS ---
st.set_page_config(page_title="Cheltenham 2026 Tipping", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .main-header {
        background-color: #00277c; padding: 20px; border-radius: 10px;
        color: white; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #e71312;
    }
    .race-card {
        background-color: white; padding: 12px; border-radius: 8px;
        border-left: 5px solid #00277c; margin-bottom: 5px; box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; border-radius: 5px 5px 0px 0px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; border-bottom: 4px solid #e71312 !important; }
    
    /* Submit Button Styling */
    div.stButton > button {
        background-color: #e71312; color: white; border: none; padding: 12px;
        font-size: 18px; font-weight: bold; width: 100%; border-radius: 8px; margin-top: 10px;
    }
    div.stButton > button:hover { background-color: #c41010; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INITIALIZE DATA ---
df_races = load_race_schedule()
runners_dict = load_runners_from_sheet()
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}

# --- 4. HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- 5. TABS ---
tab_list = ["Entry Form", "Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(tab_list)

# GLOBAL FORM DATA (Available across all tabs)
with tabs[0]:
    st.subheader("📋 Step 1: Your Details")
    st.info("Fill this out first, then head to the day's tab to submit your picks.")
    p_name = st.text_input("Full Name *", key="global_name")
    p_email = st.text_input("Email Address *", key="global_email")
    p_pin = st.number_input("4-Digit PIN *", min_value=1000, max_value=9999, step=1, value=None, key="global_pin")

# --- DAY TABS ---
for i, day in enumerate(tab_list[1:], start=1):
    with tabs[i]:
        st.subheader(f"📅 {day} Picks")
        
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        r_list = day_races.to_dict('records')

        # Race Grid
        for j in range(0, len(r_list), 2):
            cols = st.columns(2)
            for k in range(2):
                if j + k < len(r_list):
                    race = r_list[j + k]
                    rid = f"{day_code_map[day]}r{race['RACE_NUMBER']}"
                    with cols[k]:
                        st.markdown(f'<div class="race-card"><b>Race {race["RACE_NUMBER"]}</b><br>{race["RACE_NAME"]}</div>', unsafe_allow_html=True)
                        st.selectbox(f"Pick {rid}", options=runners_dict.get(rid, ["-- No Runners --"]), label_visibility="collapsed", key=f"pick_{rid}")

        # Daily NAP
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312; margin-top: 15px;"><b>🌟 {day.upper()} DAILY NAP</b></div>', unsafe_allow_html=True)
        all_runners = []
        for r_num in range(1, 8):
            rid_key = f"{day_code_map[day]}r{r_num}"
            if rid_key in runners_dict:
                all_runners.extend(runners_dict[rid_key][1:])
        st.selectbox(f"NAP {day}", options=["-- Select Daily NAP --"] + sorted(list(set(all_runners))), label_visibility="collapsed", key=f"nap_{day}")

        # --- INDIVIDUAL SUBMIT BUTTON PER DAY ---
        st.write("---")
        if st.button(f"SUBMIT {day.upper()} ENTRIES", key=f"btn_{day}"):
            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            
            # Validation
            if not p_name or not p_email or p_pin is None:
                st.error("Error: Please complete your details in the 'Entry Form' tab first.")
            elif not re.match(email_regex, p_email):
                st.error("Error: Invalid email format.")
            else:
                try:
                    client = get_google_sheets_connection()
                    sh = client.open("Cheltenham_v2")
                    
                    # 1. Update rEntrants
                    entrants_sheet = sh.worksheet("rEntrants")
                    entrants_sheet.append_row([p_name, p_email, str(p_pin)])
                    
                    # 2. Update Submissions (Specific to this Day)
                    tips_sheet = sh.worksheet("Submissions")
                    
                    # Row Format: [Name, Date/Day, Race1, Race2, Race3, Race4, Race5, Race6, Race7, NAP]
                    d_code = day_code_map[day]
                    daily_picks = [p_name, day] # Identity
                    
                    for r_idx in range(1, 8):
                        val = st.session_state.get(f"pick_{d_code}r{r_idx}", "No Pick")
                        daily_picks.append(val)
                    
                    daily_picks.append(st.session_state.get(f"nap_{day}", "No NAP"))
                    
                    tips_sheet.append_row(daily_picks)
                    
                    st.balloons()
                    st.success(f"Success! {day} picks locked in for {p_name}.")
                except Exception as e:
                    st.error(f"Submission Error: {e}")