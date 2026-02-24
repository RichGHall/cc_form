import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONNECTIONS & DATA FETCHING ---
@st.cache_resource
def get_google_sheets_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # Uses st.secrets for service account info
    creds = Credentials.from_service_account_info(st.secrets, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def get_registered_users():
    """Fetches Name and PIN, filtering for current year registration."""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        sheet = sh.worksheet("rEntrants")
        data = sheet.get_all_values()
        current_year = str(datetime.datetime.now().year)
        valid_users = {}
        for row in data[1:]:
            if len(row) >= 4:
                name, pin, timestamp = row[0], str(row[2]), row[3]
                if current_year in timestamp:
                    valid_users[name] = pin
        return valid_users
    except:
        return {}

@st.cache_data(ttl=60)
def load_runners_from_sheet():
    """Pulls current horse lists for each race from rRunners."""
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
    except:
        return {}

@st.cache_data(ttl=300)
def load_race_config():
    """Pulls Race Names and Start Times from config_Races sheet."""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        data = sh.worksheet("config_Races").get_all_values()
        return pd.DataFrame(data[1:], columns=data[0])
    except:
        return pd.DataFrame(columns=['Race_ID', 'Race_Name', 'Start_Time'])

# --- 2. VALIDATION HELPER ---
def is_race_open(race_id, config_df):
    try:
        # Find the row where your 'ID' column matches the race (e.g., d1r1)
        race_info = config_df[config_df['ID'] == race_id]
        if race_info.empty:
            return True # Open by default if not found
        
        # Get the 'Start Time' string from your sheet (e.g., "13:30")
        start_str = str(race_info.iloc[0]['Start_Time']).strip()
        
        # Current time
        now = datetime.datetime.now()
        
        # Convert "13:30" string to a datetime object for TODAY
        # This assumes your sheet uses 24-hour format
        start_time = datetime.datetime.strptime(start_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        # LOGIC: Open if Now is BEFORE Start Time
        return now < start_time
    except Exception as e:
        # If there's an error parsing the time, keep it open so users can tip
        return True

# --- 3. PAGE CONFIG & STYLING ---
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
        color: #333;
    }
    div.stButton > button { 
        background-color: #e71312; color: white; border-radius: 8px; font-weight: bold; width: 100%; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. INITIALIZE DATA ---
user_db = get_registered_users()
runners_dict = load_runners_from_sheet()
config_df = load_race_config()
day_code_map = {"Tuesday": "d1", "Wednesday": "d2", "Thursday": "d3", "Friday": "d4"}

st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026 TIPPING</h1></div>', unsafe_allow_html=True)

# --- 5. TABS ---
tab_list = ["New Registration", "Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(tab_list)

# --- TAB 0: REGISTRATION ---
with tabs[0]:
    st.subheader("📝 Registration")
    with st.form("reg_form"):
        n_name = st.text_input("Full Name")
        n_email = st.text_input("Email")
        n_pin = st.number_input("4-Digit PIN", min_value=1000, max_value=9999, step=1, value=None)
        if st.form_submit_button("REGISTER"):
            if n_name and n_email and n_pin:
                client = get_google_sheets_connection()
                sh = client.open("Cheltenham_v2")
                sh.worksheet("rEntrants").append_row([n_name, n_email, str(n_pin), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                st.success("Registered! Refresh the page to tip.")
                st.cache_data.clear()

# --- TABS 1-4: RACE DAYS ---
for i, day in enumerate(tab_list[1:], start=1):
    with tabs[i]:
        st.subheader(f"📅 {day} Tips")
        
        col_id1, col_id2 = st.columns(2)
        with col_id1:
            auth_name = st.selectbox("Name", ["-- Select --"] + sorted(list(user_db.keys())), key=f"auth_n_{day}")
        with col_id2:
            auth_pin = st.text_input("PIN", type="password", key=f"auth_p_{day}")

        st.divider()
        d_code = day_code_map[day]
        
        # Display Races in 2-column grid
        for r_num in range(1, 8, 2):
            cols = st.columns(2)
            for k, offset in enumerate([0, 1]):
                curr_r = r_num + offset
                if curr_r <= 7:
                    rid = f"{d_code}r{curr_r}"
                    race_info = config_df[config_df['Race_ID'] == rid]
                    r_name = race_info.iloc[0]['Race_Name'] if not race_info.empty else "Race Name"
                    start_t = race_info.iloc[0]['Start_Time'] if not race_info.empty else "N/A"
                    
                    is_open = is_race_open(rid, config_df)
                    
                    with cols[k]:
                        st.markdown(f'<div class="race-card"><b>Race {curr_r}</b>: {r_name}<br><small>Starts: {start_t}</small></div>', unsafe_allow_html=True)
                        st.selectbox(f"Pick {rid}", options=runners_dict.get(rid, ["-- No Runners --"]), 
                                     key=f"pick_{rid}", disabled=not is_open, label_visibility="collapsed")

        # EW Bonus (NAP) - Linked to start of Race 1
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312;"><b>🌟 {day.upper()} EW Bonus</b></div>', unsafe_allow_html=True)
        all_runners = []
        for r_num in range(1, 8):
            rid_key = f"{day_code_map[day]}r{r_num}"
            if rid_key in runners_dict: all_runners.extend(runners_dict[rid_key][1:])
        
        nap_open = is_race_open(f"{d_code}r1", config_df)
        st.selectbox(f"NAP {day}", options=["-- Select EW Bonus --"] + sorted(list(set(all_runners))), 
                     key=f"nap_{day}", disabled=not nap_open, label_visibility="collapsed")

        # --- SUBMISSION LOGIC ---
        if st.button(f"SUBMIT {day.upper()} TIPS", key=f"btn_{day}"):
            if auth_name == "-- Select --" or not auth_pin:
                st.error("Select your name and enter your PIN.")
            elif user_db.get(auth_name) != auth_pin:
                st.error("Validation Failed: Incorrect PIN.")
            else:
                try:
                    now_dt = datetime.datetime.now()
                    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                    yr = now_dt.year
                    vertical_data = []

                    # 1. Standard Races (Silent filtering)
                    for r_idx in range(1, 8):
                        rid = f"{d_code}r{r_idx}"
                        selection = st.session_state.get(f"pick_{rid}", "-- Select Runner --")
                        
                        if selection != "-- Select Runner --":
                            if is_race_open(rid, config_df):
                                vertical_data.append([now_str, auth_name, auth_pin, rid, selection, yr])
                            else:
                                st.error(f"Failed: {rid} has already started.")

                    # 2. NAP Submission
                    nap_selection = st.session_state.get(f"nap_{day}", "-- Select EW Bonus --")
                    if nap_selection != "-- Select EW Bonus --":
                        if is_race_open(f"{d_code}r1", config_df):
                            vertical_data.append([now_str, auth_name, auth_pin, f"{d_code}_NAP", nap_selection, yr])
                        else:
                            st.error("Failed: The EW Bonus locks after the first race starts.")

                    # 3. Final Upload
                    if vertical_data:
                        with st.spinner("Uploading..."):
                            client = get_google_sheets_connection()
                            sh = client.open("Cheltenham_v2")
                            sh.worksheet("rPicks").append_rows(vertical_data)
                            st.balloons()
                            st.success(f"Success! {len(vertical_data)} picks recorded.")
                    else:
                        st.info("No new selections made or races are closed.")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 6. VIEW PREVIOUS SUBMISSIONS ---
st.divider()
with st.expander("👁️ View My Submitted Picks"):
    if auth_name != "-- Select --":
        try:
            client = get_google_sheets_connection()
            sh = client.open("Cheltenham_v2")
            raw_data = sh.worksheet("rPicks").get_all_values()
            
            # Create DataFrame and Clean Headers
            df_hist = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df_hist.columns = df_hist.columns.str.strip() # Remove hidden spaces
            
            # 1. Filter by Name (Case-insensitive check)
            user_view = df_hist[df_hist['Name'].str.lower() == auth_name.lower()]
            
            # 2. Filter by Year (Forcing both to string to avoid 2026 vs "2026" errors)
            current_yr_str = str(datetime.datetime.now().year)
            # Find the year column regardless of casing (Year vs year)
            year_col = [c for c in df_hist.columns if c.lower() == 'year'][0]
            user_view = user_view[user_view[year_col].astype(str) == current_yr_str]
            
            if not user_view.empty:
                # Convert Timestamp to actual date objects for sorting
                user_view['Timestamp'] = pd.to_datetime(user_view['Timestamp'])
                
                # Deduplicate: Get the latest entry for each Race_ID
                # Ensure we use the exact column name for 'Race_ID' from your sheet
                rid_col = 'Race_ID' if 'Race_ID' in user_view.columns else 'ID'
                
                latest_picks = user_view.sort_values('Timestamp').groupby(rid_col).tail(1)
                
                # Display a clean table
                st.table(latest_picks[[rid_col, 'Pick', 'Timestamp']].sort_values(rid_col))
            else:
                st.info(f"No picks found in rPicks for {auth_name} in {current_yr_str}.")
        except Exception as e:
            st.error(f"Could not load history: {e}")
                        
