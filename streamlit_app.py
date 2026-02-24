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

@st.cache_data(ttl=60) # Short TTL so new registrations show up quickly
def get_registered_users():
    """Fetches Name and PIN from rEntrants for validation"""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        sheet = sh.worksheet("rEntrants")
        data = sheet.get_all_values()
        # Create dict: { "Name": "PIN" } - skipping header row
        return {row[0]: str(row[2]) for row in data[1:] if len(row) >= 3}
    except:
        return {}

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
    except:
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
        color: navy;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; border-radius: 5px 5px 0px 0px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; border-bottom: 4px solid #e71312 !important; }
    div.stButton > button { background-color: #e71312; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INITIALIZE DATA ---
df_races = load_race_schedule()
runners_dict = load_runners_from_sheet()
user_db = get_registered_users() # Loaded from rEntrants
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}

# --- 4. HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- 5. TABS ---
tab_list = ["New Registration", "Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(tab_list)

# --- TAB 0: NEW REGISTRATION ---
with tabs[0]:
    st.subheader("📝 Registration (One-time Only)")
    with st.form("registration_form"):
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        new_pin = st.number_input("Set 4-Digit PIN (No leading 0)", min_value=1000, max_value=9999, step=1, value=None)
        reg_submit = st.form_submit_button("REGISTER")
        
        if reg_submit:
            if new_name and new_email and new_pin:
                try:
                    client = get_google_sheets_connection()
                    sh = client.open("Cheltenham_v2")
                    sh.worksheet("rEntrants").append_row([new_name, new_email, str(new_pin)])
                    st.success("Registration Successful! You can now go to the race tabs to tip.")
                    st.cache_data.clear() # Force refresh user list
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("All fields are mandatory.")

# --- TABS 1-4: RACE DAYS ---
for i, day in enumerate(tab_list[1:], start=1):
    with tabs[i]:
        st.subheader(f"📅 {day} Tips")
        
        # Identity Verification for this day
        col_id1, col_id2 = st.columns(2)
        with col_id1:
            auth_name = st.selectbox("Select Your Name", options=["-- Select --"] + sorted(list(user_db.keys())), key=f"auth_name_{day}")
        with col_id2:
            auth_pin = st.text_input("Enter your PIN", type="password", key=f"auth_pin_{day}")

        st.divider()
        
        # Display Races
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        r_list = day_races.to_dict('records')
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

        # Day Submission
        if st.button(f"SUBMIT {day.upper()} TIPS", key=f"btn_{day}"):
            # VALIDATION: Check Name and PIN against user_db
            if auth_name == "-- Select --" or not auth_pin:
                st.error("Please select your name and enter your PIN.")
            elif user_db.get(auth_name) != auth_pin:
                st.error("Validation Failed: Incorrect PIN for this user.")
            else:
                try:
                    client = get_google_sheets_connection()
                    sh = client.open("Cheltenham_v2")
                    tips_sheet = sh.worksheet("Submissions")
                    
                    d_code = day_code_map[day]
                    daily_row = [auth_name, day]
                    for r_idx in range(1, 8):
                        daily_row.append(st.session_state.get(f"pick_{d_code}r{r_idx}", "No Pick"))
                    daily_row.append(st.session_state.get(f"nap_{day}", "No NAP"))
                    
                    tips_sheet.append_row(daily_row)
                    st.balloons()
                    st.success(f"Success! {day} picks saved for {auth_name}.")
                except Exception as e:
                    st.error(f"Error saving: {e}")