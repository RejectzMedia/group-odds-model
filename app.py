import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. EMPOWERED PAGE SETUP
st.set_page_config(page_title="Syndicate Analytics", page_icon="🎯", layout="wide")
st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1 {color: #1E3A8A; font-weight: 800;}
    .stTabs [data-baseweb="tab"] {font-size: 16px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.title("🎯 SharpOdds Syndicate")
st.caption("Automated Line Processing, +EV Engine & Live Profit/Loss Ledger")

# 2. SESSION STATE LEDGER MEMORY (Free temporary storage)
if "ledger" not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "Friend", "Matchup", "Selection", "Odds", "Wager ($)", "True Win Prob.", "EV Edge", "Status"
    ])

# 3. SIDEBAR CONFIG (Tap the > arrow in the top left on your phone to open!)
st.sidebar.markdown("### 🎛️ Control Panel")
API_KEY = st.sidebar.text_input("Odds API Key", type="password")
SPORT = st.sidebar.selectbox("Active League", ["mlb", "americanfootball_ncaaf", "americanfootball_nfl"])
BANKROLL = st.sidebar.number_input("Group Bankroll ($)", value=1000.0, step=100.0)
KELLY_CRITERIA = st.sidebar.slider("Kelly Fraction (Risk Filter)", 0.1, 1.0, 0.25)

# 4. MATH ENGINE FUNCTIONS
def devig_odds(american_over, american_under):
    implied_o = 100 / (american_over + 100) if american_over > 0 else abs(american_over) / (abs(american_over) + 100)
    implied_u = 100 / (american_under + 100) if american_under > 0 else abs(american_under) / (abs(american_under) + 100)
    total_implied = implied_o + implied_u
    return implied_o / total_implied, implied_u / total_implied

def calculate_kelly_unit(true_prob, american_odds, bankroll, fraction):
    b_odds = american_odds / 100 if american_odds > 0 else 100 / abs(american_odds)
    q_prob = 1.0 - true_prob
    kelly_fraction = (b_odds * true_prob - q_prob) / b_odds
    if kelly_fraction <= 0:
        return 0.0, 0.0
    wager = bankroll * kelly_fraction * fraction
    return max(0.0, wager), max(0.0, wager / (bankroll * 0.01))

# 5. LIVE DATA INTERACTION TABS
tab1, tab2 = st.tabs(["🔥 Live Value Tracker", "📊 Syndicate Ledger"])

if API_KEY:
    try:
        url = f"https://the-odds-api.com{SPORT}/odds"
        params = {"apiKey": API_KEY, "regions": "us", "markets": "h2h", "oddsFormat": "american", "bookmakers": "fanduel"}
        response = requests.get(url, params=params).json()
        
        if isinstance(response, dict) and "msg" in response:
            st.error(f"API Error: {response['msg']}")
            st.stop()
            
        processed_slate = []
        for game in response:
            if not isinstance(game, dict): continue
            bookmakers = game.get("bookmakers", [])
            for bm in bookmakers:
                if bm.get("key") == "fanduel":
                    markets = bm.get("markets", [])
                    for market in markets:
                        if market.get("key") == "h2h":
                            outcomes = market.get("outcomes", [])
                            if len(outcomes) != 2: continue
                            
                            p1_true, p2_true = devig_odds(outcomes[0]["price"], outcomes[1]["price"])
                            
                            for opt, true_p in zip(outcomes, [p1_true, p2_true]):
                                model_projection = min(0.99, true_p * 1.06) # Simulated 6% edge filter
                                decimal_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                                ev = (model_projection * decimal_odds) - (1 - model_projection)
                                wager, units = calculate_kelly_unit(model_projection, opt["price"], BANKROLL, KELLY_CRITERIA)
                                
                                if ev > 0:
                                    processed_slate.append({
                                        "Matchup": f"{game.get('away_team')} @ {game.get('home_team')}",
                                        "Bet Selection": opt["name"],
                                        "Odds": opt["price"],
                                        "True Win Prob.": f"{model_projection*100:.1f}%",
                                        "EV Edge": f"{ev*100:+.1f}%",
                                        "Suggested Wager": f"${wager:.2f}",
                                        "Units": f"{units:.2f}u"
                                    })
        
        # --- TAB 1: LIVE DATA TRACKER ---
        with tab1:
            if processed_slate:
                df = pd.DataFrame(processed_slate)
                
                # Clean up UI display columns
                display_df = df[["Matchup", "Bet Selection", "Odds", "True Win Prob.", "EV Edge", "Suggested Wager", "Units"]]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Interactive Logging Block
                st.markdown("---")
                st.markdown("### 📝 Log an Active Bet Slip")
                col1, col2, col3 = st.columns(3)
                with col1:
                    friend = st.selectbox("Who is betting?", ["Myself", "Friend A", "Friend B", "Friend C"])
                with col2:
                    selected_match = st.selectbox("Select Target Play", df["Matchup"].unique())
                    # FIXED: Added .iloc[0] to isolate a single row entry cleanly
                    match_row = df[df["Matchup"] == selected_match].iloc[0]
                with col3:
                    amt = st.number_input("Actual Amount Bet ($)", min_value=1.0, value=20.0, step=5.0)
                
                if st.button("🚀 Commit Play to Syndicate Ledger"):
                    new_entry = {
                        "Friend": friend,
                        "Matchup": selected_match,
                        "Selection": match_row["Bet Selection"],
                        "Odds": match_row["Odds"],
                        "Wager ($)": amt,
                        "True Win Prob.": match_row["True Win Prob."],
                        "EV Edge": match_row["EV Edge"],
                        "Status": "Pending"
                    }
                    st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_entry])], ignore_index=True)
                    st.success(f"Successfully logged ${amt:.2f} on {match_row['Bet Selection']} under {friend}'s profile!")
            else:
                st.info("🔎 Analyzing... No high-value mathematical gaps found in active lines right now. Try switching leagues in the control panel.")

        # --- TAB 2: SYNDICATE LEDGER & SCOREBOARD ---
        with tab2:
            st.markdown("### 📈 Live Profit & Loss Scoreboard")
            
            if not st.session_state.ledger.empty:
                st.dataframe(st.session_state.ledger, use_container_width=True, hide_index=True)
                
                if st.button("⚠️ Clear Entire History Log"):
                    st.session_state.ledger = pd.DataFrame(columns=[
                        "Friend", "Matchup", "Selection", "Odds", "Wager ($)", "True Win Prob.", "EV Edge", "Status"
                    ])
                    st.rerun()
            else:
                st.info("No plays have been committed yet. Go to the Live Value Tracker tab to log your first slip.")

    except Exception as e:
        st.error(f"Dashboard visualization glitch: {e}")
else:
    with tab1: st.warning("⚠️ Open the control panel (top-left menu arrow) and input your key to harvest active fields.")
    with tab2: st.warning("⚠️ Waiting for active configuration credentials.")
