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

@st.cache_data(ttl=60)
def load_leaders():
    """Loads leaderboard data from Leaders sheet, Range T3:X100."""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        worksheet = sh.worksheet("Leaders")
        # Get range T3:X100 (columns T-X are indices 19-23)
        data = worksheet.range('T3:X100')
        
        # Convert to list format
        rows_data = []
        current_row = []
        for idx, cell in enumerate(data):
            current_row.append(cell.value if cell.value else "")
            if (idx + 1) % 5 == 0:  # 5 columns (T-X)
                rows_data.append(current_row)
                current_row = []
        
        # Filter out rows where column U (index 1) is empty
        filtered_rows = [row for row in rows_data if len(row) > 1 and row[1]]
        
        # Create DataFrame with proper column names
        df = pd.DataFrame(filtered_rows, columns=['Position', 'Name', 'Wins', 'Placed', 'Total_Winnings'])
        return df
    except Exception as e:
        st.warning(f"Could not load leaders: {e}")
        return pd.DataFrame(columns=['Position', 'Name', 'Wins', 'Placed', 'Total_Winnings'])

@st.cache_data(ttl=30)
def get_next_race_id():
    """Loads next race ID from Next_Race sheet, Cell D1."""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        worksheet = sh.worksheet("Next_Race")
        next_race = worksheet.cell(1, 4).value  # Row 1, Column D (4)
        return next_race.lower().strip() if next_race else None
    except:
        return None

@st.cache_data(ttl=30)
def load_current_picks():
    """Loads current picks from CurrentPicks sheet, Range C2:N5000."""
    try:
        client = get_google_sheets_connection()
        sh = client.open("Cheltenham_v2")
        worksheet = sh.worksheet("CurrentPicks")
        # Get range C2:N5000
        data = worksheet.range('C2:N5000')
        
        # Parse into rows (12 columns: C-N)
        rows_data = []
        current_row = []
        for idx, cell in enumerate(data):
            current_row.append(cell.value if cell.value else "")
            if (idx + 1) % 12 == 0:  # 12 columns (C-N)
                rows_data.append(current_row)
                current_row = []
        
        # Filter out completely empty rows
        filtered_rows = [row for row in rows_data if any(row)]
        
        return filtered_rows
    except:
        return []

def parse_current_picks(picks_data):
    """
    Parse picks data assuming:
    Column D (index 1) = Name
    Column F (index 3) = Race ID
    Column G (index 4) = Horse picked
    """
    picks_list = []
    for row in picks_data:
        if len(row) > 4:  # Need at least up to column G (index 4)
            name = row[1] if row[1] else ""
            race_id = row[3] if row[3] else ""
            horse = row[4] if row[4] else ""
            
            if name and race_id and horse:
                picks_list.append({
                    'name': name,
                    'race_id': race_id.lower().strip(),
                    'horse': horse
                })
    
    return picks_list

# --- 2. VALIDATION HELPER ---
def is_race_open(race_id, config_df):
    try:
        # Find the row where your 'ID' column matches the race (e.g., d1r1)
        race_info = config_df[config_df['Race_ID'] == race_id]
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

def get_race_start_time(race_id, config_df):
    """Get the start time string for a specific race."""
    try:
        race_info = config_df[config_df['Race_ID'] == race_id]
        if race_info.empty:
            return None
        return str(race_info.iloc[0]['Start_Time']).strip()
    except:
        return None

def is_after_1320():
    """Check if current time is after 13:20."""
    now = datetime.datetime.now()
    cutoff = datetime.datetime.strptime("13:20", "%H:%M").replace(
        year=now.year, month=now.month, day=now.day
    )
    return now >= cutoff

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
    .leaderboard-table {
        background-color: white; border-radius: 8px; padding: 15px; box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .next-race-header {
        background-color: #e71312; padding: 15px; border-radius: 8px; color: white; margin-bottom: 15px; text-align: center;
    }
    .horse-pick-item {
        background-color: white; padding: 12px; margin-bottom: 8px; border-radius: 8px; 
        border-left: 4px solid #00277c; box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .picker-name {
        background-color: #f0f2f5; padding: 8px; border-radius: 4px; margin-top: 6px; font-size: 0.9em; color: #555;
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
tab_list = ["New Registration", "Tuesday", "Wednesday", "Thursday", "Friday", "Current Leaders"]

# Add "Next Race" tab only if after 13:20
if is_after_1320():
    tab_list.insert(6, "Next Race")

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
for i, day in enumerate(tab_list[1:6], start=1):  # Only first 5 racing tabs
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
                        start_time = get_race_start_time(rid, config_df)
                        
                        if selection != "-- Select Runner --":
                            if is_race_open(rid, config_df):
                                # Include start time in the data
                                vertical_data.append([now_str, auth_name, auth_pin, rid, selection, yr, start_time])
                            else:
                                st.error(f"Failed: {rid} has already started.")

                    # 2. NAP Submission
                    nap_selection = st.session_state.get(f"nap_{day}", "-- Select EW Bonus --")
                    nap_start_time = get_race_start_time(f"{d_code}r1", config_df)
                    if nap_selection != "-- Select EW Bonus --":
                        if is_race_open(f"{d_code}r1", config_df):
                            # Include start time for NAP (uses Race 1 start time)
                            vertical_data.append([now_str, auth_name, auth_pin, f"{d_code}_NAP", nap_selection, yr, nap_start_time])
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

# --- TAB 5: CURRENT LEADERS ---
leaders_tab_idx = 5
with tabs[leaders_tab_idx]:
    st.subheader("🏆 Current Leaders")
    st.divider()
    
    leaders_df = load_leaders()
    
    if leaders_df.empty:
        st.info("No leaderboard data available yet.")
    else:
        st.markdown('<div class="leaderboard-table">', unsafe_allow_html=True)
        # Display as a formatted table
        st.dataframe(
            leaders_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Position": st.column_config.TextColumn("Position", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Wins": st.column_config.TextColumn("Wins", width="small"),
                "Placed": st.column_config.TextColumn("Placed", width="small"),
                "Total_Winnings": st.column_config.TextColumn("Total Winnings", width="medium"),
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 6: NEXT RACE (Only if after 13:20) ---
if is_after_1320():
    next_race_tab_idx = 6
    with tabs[next_race_tab_idx]:
        st.subheader("🏁 Next Race Overview")
        st.divider()
        
        next_race_id = get_next_race_id()
        
        if not next_race_id:
            st.error("Could not determine the next race.")
        else:
            # Get race info
            race_info = config_df[config_df['Race_ID'] == next_race_id]
            if race_info.empty:
                st.error(f"Race {next_race_id} not found in configuration.")
            else:
                race_name = race_info.iloc[0]['Race_Name']
                race_time = race_info.iloc[0]['Start_Time']
                
                st.markdown(f'<div class="next-race-header"><h2>{next_race_id.upper()}: {race_name}</h2><p>Starts at {race_time}</p></div>', unsafe_allow_html=True)
                
                # Load picks
                picks_data = load_current_picks()
                picks_list = parse_current_picks(picks_data)
                
                # Filter picks for next race
                next_race_picks = [p for p in picks_list if p['race_id'] == next_race_id.lower().strip()]
                
                if not next_race_picks:
                    st.info(f"No picks yet for {next_race_id}.")
                else:
                    # Aggregate picks by horse
                    horse_picks = {}
                    for pick in next_race_picks:
                        horse = pick['horse']
                        name = pick['name']
                        if horse not in horse_picks:
                            horse_picks[horse] = []
                        horse_picks[horse].append(name)
                    
                    # Sort by number of picks (descending)
                    sorted_horses = sorted(horse_picks.items(), key=lambda x: len(x[1]), reverse=True)
                    
                    st.write(f"**Total picks for this race: {len(next_race_picks)}**")
                    st.divider()
                    
                    # Display each horse with expander
                    for horse, pickers in sorted_horses:
                        pick_count = len(pickers)
                        with st.expander(f"🐎 {horse} ({pick_count} pick{'s' if pick_count != 1 else ''})"):
                            st.markdown('<div class="picker-name">', unsafe_allow_html=True)
                            for picker in sorted(pickers):
                                st.write(f"• {picker}")
                            st.markdown('</div>', unsafe_allow_html=True)