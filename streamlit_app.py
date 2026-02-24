import streamlit as st
import pandas as pd
import gspread
import re  # For email validation
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
    div.stButton > button:first-child { background-color: #e71312; color: white; border: none; padding: 15px 30px; font-size: 20px; font-weight: bold; width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INITIALIZE DATA ---
df_races = load_race_schedule()
runners_dict = load_runners_from_sheet()
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}

# --- 4. HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- 5. TABS ---
# Adding the new 'Entry Form' tab as the first tab
tab_list = ["Entry Form", "Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(tab_list)

# --- TAB 0: ENTRY FORM ---
with tabs[0]:
    st.subheader("📋 Player Details")
    st.info("All fields below are mandatory to enter the competition.")
    
    player_name = st.text_input("Full Name *", placeholder="e.g., John Smith", key="user_name")
    player_email = st.text_input("Email Address *", placeholder="e.g., john@example.com", key="user_email")
    
    # PIN Validation: Number input between 1000 and 9999 forces 4 digits and no leading zero
    player_pin = st.number_input("4-Digit PIN (Cannot start with 0) *", 
                                 min_value=1000, max_value=9999, step=1, value=None, 
                                 placeholder="Enter PIN", key="user_pin")

# --- TABS 1-4: RACE DAYS ---
for i, day in enumerate(tab_list[1:], start=1):
    with tabs[i]:
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        r_list = day_races.to_dict('records')

        for j in range(0, len(r_list), 2):
            cols = st.columns(2)
            for k in range(2):
                if j + k < len(r_list):
                    race = r_list[j + k]
                    rid = f"{day_code_map[day]}r{race['RACE_NUMBER']}"
                    with cols[k]:
                        st.markdown(f'<div class="race-card"><span style="color: #e71312; font-weight: bold;">Race {race["RACE_NUMBER"]}</span><br><b>{race["RACE_NAME"]}</b></div>', unsafe_allow_html=True)
                        st.selectbox(f"Pick {rid}", options=runners_dict.get(rid, ["-- No Runners --"]), label_visibility="collapsed", key=f"pick_{rid}")

        # Daily NAP
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312; margin-top: 25px;"><b>🌟 {day.upper()} DAILY NAP</b></div>', unsafe_allow_html=True)
        all_runners = []
        for r_num in range(1, 8):
            rid_key = f"{day_code_map[day]}r{r_num}"
            if rid_key in runners_dict:
                all_runners.extend(runners_dict[rid_key][1:])
        st.selectbox(f"NAP {day}", options=["-- Select Daily NAP --"] + sorted(list(set(all_runners))), label_visibility="collapsed", key=f"nap_{day}")

# --- 6. SUBMISSION ---
st.divider()
if st.button("SUBMIT ENTRIES"):
    # Mandatory Field Logic
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    if not player_name or not player_email or player_pin is None:
        st.error("Submission failed: Please complete all fields in the 'Entry Form' tab.")
    elif not re.match(email_regex, player_email):
        st.error("Submission failed: Please enter a valid email address.")
    else:
        try:
            client = get_google_sheets_connection()
            sheet = client.open("Cheltenham_v2").worksheet("Submissions")
            
            # Row data: [Name, Email, PIN, d1r1...d4r7, NAP1, NAP2, NAP3, NAP4]
            submission_row = [player_name, player_email, player_pin]
            
            for d_code in ["d1", "d2", "d3", "d4"]:
                for r_idx in range(1, 8):
                    submission_row.append(st.session_state.get(f"pick_{d_code}r{r_idx}", ""))
            
            for d_name in ["Tuesday", "Wednesday", "Thursday", "Friday"]:
                submission_row.append(st.session_state.get(f"nap_{d_name}", ""))

            sheet.append_row(submission_row)
            st.balloons()
            st.success(f"Success! Good luck, {player_name}!")
        except Exception as e:
            st.error(f"Error: {e}")