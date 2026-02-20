import streamlit as st
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cheltenham 2026 Tipping", layout="wide")

# --- CUSTOM CSS (THE "SKY BET" LOOK) ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #f0f2f5;
    }
    
    /* Header Styling */
    .main-header {
        background-color: #00277c;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        border-bottom: 5px solid #e71312;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #00277c;
        padding: 8px 8px 0px 8px;
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        color: white !important;
        font-weight: bold;
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f5 !important;
        color: #00277c !important;
        border-bottom: 4px solid #e71312 !important;
    }

    /* Race Card Styling */
    .race-card {
        background-color: white;
        color: white;
        padding: 5px;
        border-radius: 8px;
        border-left: 5px solid #00277c;
        margin-bottom: 10px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
    }

    /* Submit Button */
    div.stButton > button:first-child {
        background-color: #e71312;
        color: white;
        border: none;
        padding: 15px 30px;
        font-size: 20px;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #c41010;
        border: none;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOAD DATA ---
@st.cache_data
def load_race_data():
    # Replace 'races.csv' with your actual filename
    # Structure: ID, DAY, RACE_NUMBER, RACE_NAME
    df = pd.read_csv('races.csv')
    return df

try:
    df_races = load_race_data()
except:
    # Fallback dummy data so you can run the code immediately
    data = {
        'DAY': ['Tuesday']*3 + ['Wednesday']*3,
        'RACE_NUMBER': [1, 2, 3, 1, 2, 3],
        'RACE_NAME': ['Supreme Novices', 'Arkle Chase', 'Ultima Handicap', 'Ballymore Novices', 'Brown Advisory', 'Coral Cup']
    }
    df_races = pd.DataFrame(data)

# --- HEADER ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM 2026</h1></div>', unsafe_allow_html=True)

# --- DYNAMIC FORM GENERATION ---
days = ["Tuesday", "Wednesday", "Thursday", "Friday"]
tabs = st.tabs(days)

for i, day in enumerate(days):
    with tabs[i]:
        # Filter the CSV for just this day
        day_races = df_races[df_races['DAY'] == day].sort_values('RACE_NUMBER')
        
        if day_races.empty:
            st.info(f"No race data found for {day} in the CSV.")
            continue

        # Split into two columns for the "Betting Card" look
        col1, col2 = st.columns(2)
        
        for index, row in day_races.iterrows():
            # Alternate columns
            target_col = col1 if row['RACE_NUMBER'] % 2 != 0 else col2
            
            with target_col:
                st.markdown(f"""
                    <div class="race-card">
                        <span style="color: #e71312; font-weight: bold;">Race {row['RACE_NUMBER']}</span><br>
                        <b>{row['RACE_NAME']}</b>
                    </div>
                """, unsafe_allow_html=True)
                
                # The dropdown for this specific race
                st.selectbox(
                    f"Select for {row['RACE_NAME']}",
                    options=["-- Select Runner --", "Horse A", "Horse B", "Horse C"],
                    label_visibility="collapsed",
                    key=f"pick_{day}_{row['RACE_NUMBER']}"
                )

        # Add the Bonus Pick at the bottom of each tab
        st.markdown('<div class="race-card" style="border-left: 5px solid #e71312;"><b>🌟 DAILY BONUS PICK</b></div>', unsafe_allow_html=True)
        st.selectbox("Bonus", ["-- Select Runner --", "Horse A", "Horse B"], label_visibility="collapsed", key=f"bonus_{day}")

# --- SUBMIT ---
st.write("##")
user_name = st.text_input("Enter Name to Lock In Tips")
if st.button("SUBMIT ENTRIES"):
    st.success("Taps saved locally!")