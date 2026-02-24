import streamlit as st
import pandas as pd
import gspread
import datetime
import re
from google.oauth2.service_account import Credentials


# --- 1. GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_google_sheets_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets, scopes=scope)
    return gspread.authorize(creds)

   
@st.cache_data(ttl=60)
def get_registered_users():
    """Fetches Name and PIN, filtering for current year timestamps"""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        sheet = sh.worksheet("rEntrants")
        data = sheet.get_all_values()
        
        current_year = str(datetime.datetime.now().year) # "2026"
        valid_users = {}
        
        # Start from row 1 to skip header
        for row in data[1:]:
            if len(row) >= 4: # Ensure the row has a timestamp
                name = row[0]
                pin = str(row[2])
                timestamp = row[3]
                
                # Check if the year string (e.g., "2026") is in the timestamp string
                if current_year in timestamp:
                    valid_users[name] = pin
                    
        return valid_users
    except Exception as e:
        # Fallback to empty if sheet is missing or malformed
        return {}    





@st.cache_data(ttl=60)
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
    /* Main App Background */
    .stApp { background-color: #f0f2f5; }
    
    /* Header Styling */
    .main-header {
        background-color: #00277c; padding: 20px; border-radius: 10px;
        color: Red; text-align: center; margin-bottom: 20px; border-bottom: 5px solid #e71312;
    }

    /* Target all Input Labels (Name, PIN, etc) */
    .stWidgetLabel p {
        color: #00277c !important;
        font-weight: bold !important;
    }

    /* Race Card Styling */
    .race-card {
        background-color: white; padding: 12px; border-radius: 8px;
        border-left: 5px solid #00277c; margin-bottom: 5px; box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
        color: #333;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; border-radius: 5px 5px 0px 0px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; border-bottom: 4px solid #e71312 !important; }
    
    /* Button Styling */
    div.stButton > button { 
        background-color: #e71312; color: white; border-radius: 8px; font-weight: bold; width: 100%; height: 3em;
    }
    div.stButton > button:hover { background-color: #c41010; color: white; border: none; }
    
    /* Input field borders to make them more visible */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border: 1px solid #ced4da;
    }
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
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        reg_submit = st.form_submit_button("REGISTER")
        
        if reg_submit:
            if new_name and new_email and new_pin:
                try:
                    client = get_google_sheets_connection()
                    sh = client.open("Cheltenham_v2")
                    
                    sh.worksheet("rEntrants").append_row([new_name, new_email, str(new_pin), now])
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
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312; margin-top: 15px;"><b>🌟 {day.upper()} EW Bonus</b></div>', unsafe_allow_html=True)
        all_runners = []
        for r_num in range(1, 8):
            rid_key = f"{day_code_map[day]}r{r_num}"
            if rid_key in runners_dict:
                all_runners.extend(runners_dict[rid_key][1:])
        st.selectbox(f"NAP {day}", options=["-- Select EW Bonus --"] + sorted(list(set(all_runners))), label_visibility="collapsed", key=f"nap_{day}")

        # Day Submission

        if st.button(f"SUBMIT {day.upper()} TIPS", key=f"btn_{day}"):
            # 1. Identity Validation
            if auth_name == "-- Select --" or not auth_pin:
                st.error("Please select your name and enter your PIN.")
            elif user_db.get(auth_name) != auth_pin:
                st.error("Validation Failed: Incorrect PIN.")
            else:
                # 2. Check for incomplete races
                d_code = day_code_map[day]
                incomplete_races = []
                
                # Check standard races
                for r_idx in range(1, 8):
                    rid = f"{d_code}r{r_idx}"
                    pick = st.session_state.get(f"pick_{rid}", "-- Select Runner --")
                    if pick == "-- Select Runner --" or not pick:
                        incomplete_races.append(f"Race {r_idx}")
                
                # Check NAP
                nap_val = st.session_state.get(f"nap_{day}", "-- Select Daily NAP --")
                if nap_val == "-- Select Daily NAP --":
                    incomplete_races.append("Daily NAP")

                # 3. Execution Logic
                # We check if we need a bypass, otherwise we proceed
                should_upload = False
                if incomplete_races:
                    st.warning(f"⚠️ You have not selected runners for: {', '.join(incomplete_races)}.")
                    # Note: In some Streamlit versions, nested interactions inside buttons 
                    # can be tricky. If this checkbox feels "laggy", we can move it outside the button.
                    if st.checkbox("I want to submit anyway (e.g. for Non-Runners)", key=f"bypass_{day}"):
                        should_upload = True
                else:
                    should_upload = True

                if should_upload:
                    try:
                        with st.spinner(f"Uploading to rPicks..."):
                            client = get_google_sheets_connection()
                            sh = client.open("Cheltenham_v2")
                            # UPDATED TAB NAME HERE
                            picks_sheet = sh.worksheet("rPicks")
                            
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            yr = datetime.datetime.now().year
                            vertical_data = []
                            
                            # 7 Standard Races
                            for r_idx in range(1, 8):
                                rid = f"{d_code}r{r_idx}"
                                # Grab the actual horse name using the 'pick_' prefix
                                horse_selection = st.session_state.get(f"pick_{rid}", "No Pick")
                                vertical_data.append([now, auth_name, auth_pin, rid, horse_selection,yr])
                            
                            # NAP Row
                            final_nap = st.session_state.get(f"nap_{day}", "No NAP")
                            vertical_data.append([now, auth_name, auth_pin, f"{d_code}_NAP", final_nap,yr])
                            
                            picks_sheet.append_rows(vertical_data)
                            
                            st.balloons()
                            st.success(f"Success! 8 rows added to rPicks for {auth_name}.")
                    except Exception as e:
                        st.error(f"Submission Error: {e}")