import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS CONNECTION ---

@st.cache_resource
def get_google_sheets_connection():
    """Connect to Google Sheets using service account"""
    # Explicitly include both Sheets and Drive scopes
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
        
        race_ids = data[0] # e.g., d1r1, d1r2
        runners_map = {}

        for col_idx, rid in enumerate(race_ids):
            if rid.strip():
                # Extract from row 5 (index 4) downwards
                runners = [row[col_idx] for row in data[4:] if len(row) > col_idx and row[col_idx].strip()]
                runners_map[rid.lower().strip()] = ["-- Select Runner --"] + runners
        return runners_map
    except Exception as e:
        st.error(f"Error loading runners from Google Sheets: {e}")
        return {}

@st.cache_data
def load_race_schedule():
    """Loads the official race names and order from CSV"""
    try:
        df = pd.read_csv('races.csv')
        return df
    except Exception as e:
        st.error(f"Error loading races.csv: {e}")
        # Fallback empty dataframe with correct columns
        return pd.DataFrame(columns=['DAY', 'RACE_NUMBER', 'RACE_NAME'])

# --- PAGE CONFIG & CSS ---
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
        border-left: 5px solid #00277c; margin-bottom: 5px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #00277c; padding: 8px 8px 0px 8px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f5 !important; color: #00277c !important; }
    div.stButton > button:first-child {
        background-color: #e71312; color: white; width: 100%; font-weight: bold; height: 3em; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE DATA ---
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
        # Filter CSV data for the current tab's day
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        
        if day_races.empty:
            st.warning(f"No races found in CSV for {day}")
            continue

        col1, col2 = st.columns(2)
        
        for index, row in day_races.iterrows():
            # Determine column (Left for odd, Right for even)
            target_col = col1 if row['RACE_NUMBER'] % 2 != 0 else col2
            
            # Map CSV row to GSheet ID (e.g., d1r1)
            race_id = f"{day_code_map[day]}r{row['RACE_NUMBER']}"
            options = runners_dict.get(race_id, ["-- Runners Not Found --"])
            
            with target_col:
                st.markdown(f"""
                    <div class="race-card">
                        <span style="color: #e71312; font-weight: bold;">Race {row['RACE_NUMBER']}</span><br>
                        <b style="font-size: 1.1em;">{row['RACE_NAME']}</b>
                    </div>
                """, unsafe_allow_html=True)
                
                st.selectbox(
                    f"Pick for {row['RACE_NAME']}",
                    options=options,
                    label_visibility="collapsed",
                    key=f"pick_{race_id}"
                )

        # Daily Bonus Pick Section
        st.markdown(f'<div class="race-card" style="border-left: 5px solid #e71312; margin-top:30px;"><b>🌟 {day.upper()} BONUS NAP</b></div>', unsafe_allow_html=True)
        
        # Aggregate all runners for that day into one list for the NAP selection
        all_day_runners = []
        for r_num in range(1, 8):
            rid = f"{day_code_map[day]}r{r_num}"
            if rid in runners_dict:
                all_day_runners.extend(runners_dict[rid][1:]) # Skip the placeholder
        
        st.selectbox(f"Select your NAP for {day}", 
                     options=["-- Select Runner --"] + sorted(list(set(all_day_runners))),
                     label_visibility="collapsed", key=f"nap_{day}")

# --- SUBMISSION LOGIC ---
st.write("---")
user_name = st.text_input("Player Name", placeholder="Enter your name to submit...")

if st.button("SUBMIT ALL TIPS"):
    if not user_name:
        st.error("Please enter your name.")
    else:
        try:
            client = get_google_sheets_connection()
            sheet = client.open("Cheltenham_v2").worksheet("Submissions")
            
            # Prepare row: [Name, d1r1, d1r2... d4r7, NAP1, NAP2, NAP3, NAP4]
            submission_row = [user_name]
            
            # 1. Add individual race picks
            for d_code in ["d1", "d2", "d3", "d4"]:
                for r_num in range(1, 8):
                    val = st.session_state.get(f"pick_{d_code}r{r_num}", "--")
                    submission_row.append(val)
            
            # 2. Add the 4 NAPs
            for day in days:
                submission_row.append(st.session_state.get(f"nap_{day}", "--"))

            sheet.append_row(submission_row)
            st.balloons()
            st.success(f"Tips locked in for {user_name}! Good luck!")
        except Exception as e:
            st.error(f"Error saving to spreadsheet: {e}")