import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. PAGE CONFIG
st.set_page_config(page_title="Syndicate Model", layout="wide")
st.title("🎯 SharpOdds Syndicate Model")
st.subheader("Automated FanDuel Line Engine")

# 2. SIDEBAR CONFIG (Tap the > arrow in the top left on your phone to open!)
st.sidebar.markdown("### 🎛️ Model Settings")
API_KEY = st.sidebar.text_input("Enter Odds API Key", type="password")
SPORT = st.sidebar.selectbox("Select League", ["mlb", "americanfootball_ncaaf", "americanfootball_nfl"])
BANKROLL = st.sidebar.number_input("Total Group Bankroll ($)", value=1000.0, step=100.0)
KELLY_CRITERIA = st.sidebar.slider("Kelly Fraction (Risk)", 0.1, 1.0, 0.25)

# 3. MATH ENGINE
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

# 4. LIVE DATA HARVESTER
if API_KEY:
    try:
        url = f"https://the-odds-api.com{SPORT}/odds/"
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
                    for mk in markets:
                        if mk.get("key") == "h2h":
                            outcomes = mk.get("outcomes", [])
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
                                        "Bet": opt["name"],
                                        "Odds": opt["price"],
                                        "True Prob.": f"{model_projection*100:.1f}%",
                                        "EV Edge": f"{ev*100:+.1f}%",
                                        "Wager": f"${wager:.2f}",
                                        "Units": f"{units:.2f}u"
                                    })
        if processed_slate:
            st.markdown("### 📊 Today's Live Value Grid")
            st.dataframe(pd.DataFrame(processed_slate))
            
            st.markdown("---")
            st.markdown("### 📝 Log a Bet Slip")
            col1, col2, col3 = st.columns(3)
            with col1: friend = st.selectbox("Who is betting?", ["Myself", "Friend A", "Friend B"])
            with col2: bet_target = st.selectbox("Target Play", [p["Matchup"] for p in processed_slate])
            with col3: amt = st.number_input("Amount ($)", min_value=1.0, value=20.0)
            if st.button("Lock Bet"): st.success(f"Tracked ${amt:.2f} for {friend}!")
        else:
            st.info("No value gaps found in active lines. Try another league.")
    except Exception as e:
        st.error(f"Data stream error: {e}")
else:
    st.warning("⚠️ Open the sidebar (top-left arrow) and input your Odds API Key.")
