import streamlit as st

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
        padding: 15px;
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

# --- HEADER SECTION ---
st.markdown('<div class="main-header"><h1>🏇 CHELTENHAM FESTIVAL 2026</h1><p>The Official Tipping Competition</p></div>', unsafe_allow_html=True)

# Placeholder image (Replace with your local path or a valid URL)
st.image("https://images.live.dazn.com/www/Sport/24b6139c-720c-4318-80f2-51978280f555.jpg", use_container_width=True)

# --- MOCK DATA ---
dummy_horses = ["Constitution Hill", "State Man", "Galopin Des Champs", "El Fabiolo", "Lossiemouth", "Ballyburn"]

# --- APP LAYOUT ---
tabs = st.tabs(["TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])

# Store selections in a dict
final_selections = {}

for i, day in enumerate(["Tuesday", "Wednesday", "Thursday", "Friday"]):
    with tabs[i]:
        st.subheader(f"📅 {day} Selections")
        
        # Grid Layout for Races
        col1, col2 = st.columns(2)
        
        for race_num in range(1, 8):
            target_col = col1 if race_num % 2 != 0 else col2
            
            with target_col:
                st.markdown(f'<div class="race-card"><b>Race {race_num}</b></div>', unsafe_allow_html=True)
                pick = st.selectbox(
                    f"Select Horse - Race {race_num}", 
                    options=["-- Select Runner --"] + dummy_horses,
                    label_visibility="collapsed",
                    key=f"{day}_r{race_num}"
                )
        
        st.markdown("---")
        # Bonus Selection (Golden Ticket Style)
        st.markdown('<div class="race-card" style="border-left: 5px solid #e71312;"><b>🌟 DAILY BONUS PICK (2x Points)</b></div>', unsafe_allow_html=True)
        st.selectbox(
            "Bonus Pick", 
            options=["-- Select Runner --"] + dummy_horses,
            label_visibility="collapsed",
            key=f"{day}_bonus"
        )

# --- FOOTER & SUBMIT ---
st.write("##")
with st.container():
    st.markdown('<div class="race-card">', unsafe_allow_html=True)
    user_name = st.text_input("Competitor Name", placeholder="e.g. JohnSmith_99")
    st.markdown('</div>', unsafe_allow_html=True)

if st.button("LOCK IN TIPS"):
    if user_name:
        st.success(f"Entries received for {user_name}! Good luck at the Festival.")
        st.balloons()
    else:
        st.error("Please enter a name before locking in your tips.")