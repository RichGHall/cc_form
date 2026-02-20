import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cheltenham Tipping 2026", layout="wide")

# --- CUSTOM CSS FOR SKY BET LOOK ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #f2f2f2;
    }
    /* Style the tabs to look more like a betting app */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #00277c;
        padding: 10px;
        border-radius: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        color: white !important;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 4px solid #e71312 !important;
    }
    /* Buttons */
    div.stButton > button:first-child {
        background-color: #e71312;
        color: white;
        border: none;
        width: 100%;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER IMAGE ---
# Replace the URL below with your Cheltenham banner image
st.image("https://images.live.dazn.com/www/Sport/24b6139c-720c-4318-80f2-51978280f555.jpg", use_container_width=True)

st.title("🏇 Cheltenham Festival Tipping")

# --- DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
# Assuming your sheet has columns 'Race' and 'Horse'
df_horses = conn.read(worksheet="HorseList") 

# --- FORM SETUP ---
days = ["Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(days)

all_picks = {}

for i, day in enumerate(days):
    with tabs[i]:
        st.header(f"{day} Runners")
        day_picks = {}
        
        # Create 7 Race Dropdowns + 1 Bonus
        col1, col2 = st.columns(2)
        
        for race_num in range(1, 8):
            # Select column based on odd/even for a clean 2-column layout
            target_col = col1 if race_num % 2 != 0 else col2
            
            # Filter horses for specific race (Assumes sheet has a 'RaceNumber' or 'Day' column)
            horse_options = df_horses[df_horses['Day'] == day]['Horse'].tolist()
            
            day_picks[f"Race {race_num}"] = target_col.selectbox(
                f"Race {race_num} Selection", 
                options=["Select a Horse..."] + horse_options,
                key=f"{day}_r{race_num}"
            )
        
        # Bonus Pick
        st.divider()
        day_picks["Bonus Pick"] = st.selectbox(
            "🌟 Daily Bonus Pick (Double Points)", 
            options=["Select a Horse..."] + horse_options,
            key=f"{day}_bonus"
        )
        
        all_picks[day] = day_picks

# --- SUBMISSION ---
st.divider()
with st.expander("Confirm User Details"):
    user_name = st.text_input("Enter Your Name / Alias")

if st.button("Submit My Tips"):
    if not user_name:
        st.error("Please enter your name before submitting.")
    else:
        # Structure data for Google Sheets
        # We flatten the dictionary to a single row
        submission_data = {"User": user_name}
        for day, picks in all_picks.items():
            for race, horse in picks.items():
                submission_data[f"{day}_{race}"] = horse
        
        # Append to your Results sheet
        existing_results = conn.read(worksheet="Results")
        new_row = pd.DataFrame([submission_data])
        updated_results = pd.concat([existing_results, new_row], ignore_index=True)
        
        conn.update(worksheet="Results", data=updated_results)
        st.success(f"Good luck, {user_name}! Your tips have been logged.")
        st.balloons()