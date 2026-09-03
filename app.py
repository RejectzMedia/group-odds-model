import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. SERVER REFRESH FLUSH
st.cache_data.clear()

# 2. APPLICATION PRESENTATION LAYOUT
st.set_page_config(page_title="Syndicate Analytics Pro", page_icon="🎯", layout="wide")
st.markdown("""
    <style>
    .main .block-container {padding-top: 1.5rem; padding-bottom: 1.5rem;}
    h1 {color: #1E3A8A; font-weight: 800;}
    .stTabs [data-baseweb="tab"] {font-size: 15px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.title("🎯 SharpOdds Syndicate Pro")
st.caption("Cross-League Line Processor, Specialized Player Prop Vectoring Engine & Shared Ledger")

# 3. GLOBAL CLOUD LEDGER STORAGE
if "ledger" not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        "Friend", "League", "Type", "Matchup", "Selection", "Odds", "Wager ($)", "True Prob.", "EV Edge", "Status"
    ])

# 4. CONTROL INTERFACE PANEL
st.sidebar.markdown("### 🎛️ Control Panel")
API_KEY = st.sidebar.text_input("Odds API Key", type="password")
SPORT = st.sidebar.selectbox("Target League Workspace", [
    "baseball_mlb", 
    "americanfootball_nfl", 
    "americanfootball_ncaaf", 
    "baseball_ncaa"
])
BANKROLL = st.sidebar.number_input("Syndicate Bankroll ($)", value=1000.0, step=100.0)
KELLY_CRITERIA = st.sidebar.slider("Kelly Fraction (Risk Allocation)", 0.1, 1.0, 0.25)

# 5. CORE MATHEMATICAL CALCULATION ENGINES
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

# 6. APP NAVIGATION FRAME
main_tab, ledger_tab = st.tabs(["🔥 Active Value Boards", "📊 Group Ledger Matrix"])

if not API_KEY:
    with main_tab: st.warning("⚠️ Open the control panel (top-left menu arrow) and input your key to harvest active fields.")
    with ledger_tab: st.warning("⚠️ Waiting for validation framework configuration parameters.")
    st.stop()

# --- 7. DYNAMIC MARKET PATH TARGETING ---
# Configures exact API sub-keys matching your specific request guidelines
markets_to_pull = "h2h" # Base game lines for all sports

if SPORT == "baseball_mlb":
    markets_to_pull += ",pitcher_strikeouts,pitcher_record_an_out,batter_hits,batter_runs,batter_rbis"
elif SPORT == "americanfootball_nfl":
    markets_to_pull += ",player_pass_yds,player_rush_yds,player_rec_yds"

base_api_url = f"https://the-odds-api.com{SPORT}/odds/"
params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": markets_to_pull,
    "oddsFormat": "american",
    "bookmakers": "fanduel"
}

# --- 8. SECURE DATA HARVESTING SLATE ---
response = []
try:
    res = requests.get(base_api_url, params=params, timeout=10)
    response = res.json()
except Exception as e:
    st.error(f"📡 API Connection Dropout: {e}")
    st.stop()

if isinstance(response, dict) and "msg" in response:
    st.error(f"API Provider Error: {response['msg']}")
    st.stop()

# 9. MULTI-MARKET CONVERSION MATRICES
game_lines_slate = []
player_props_slate = []

for game in response:
    if not isinstance(game, dict): continue
    matchup_name = f"{game.get('away_team')} @ {game.get('home_team')}"
    bookmakers = game.get("bookmakers", [])
    
    for bm in bookmakers:
        if bm.get("key") != "fanduel": continue
        markets = bm.get("markets", [])
        
        for market in markets:
            m_key = market.get("key")
            outcomes = market.get("outcomes", [])
            if len(outcomes) < 2: continue
            
            # A. Process Traditional Game Lines (Moneylines / H2H)
            if m_key == "h2h" and len(outcomes) == 2:
                p1_true, p2_true = devig_odds(outcomes[0]["price"], outcomes[1]["price"])
                for opt, true_p in zip(outcomes, [p1_true, p2_true]):
                    proj_p = min(0.99, true_p * 1.06) # Simulated 6% market variance advantage
                    dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                    ev = (proj_p * dec_odds) - (1 - proj_p)
                    wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                    
                    if ev > 0:
                        game_lines_slate.append({
                            "Matchup": matchup_name, "Selection": opt["name"], "Odds": opt["price"],
                            "True Prob.": proj_p, "EV Edge": ev, "Wager": wager, "Units": units
                        })
                        
            # B. Process Specialized Player Props
            elif len(outcomes) >= 2:
                # Group data rows into Over/Under pairs dynamically based on description name matches
                df_outcomes = pd.DataFrame(outcomes)
                if "description" in df_outcomes.columns:
                    for player_name, group in df_outcomes.groupby("description"):
                        if len(group) == 2:
                            rows = group.to_dict(orient="records")
                            p1_true, p2_true = devig_odds(rows[0]["price"], rows[1]["price"])
                            
                            for opt, true_p in zip(rows, [p1_true, p2_true]):
                                proj_p = min(0.99, true_p * 1.07) # Simulated 7% prop model variance advantage
                                dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                                ev = (proj_p * dec_odds) - (1 - proj_p)
                                wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                                
                                if ev > 0:
                                    market_clean_title = m_key.replace("player_", "").replace("pitcher_", "").replace("_", " ").title()
                                    line_value = f" {opt.get('point', '')}" if 'point' in opt else ""
                                    player_props_slate.append({
                                        "Matchup": matchup_name,
                                        "Selection": f"{player_name} [{market_clean_title}]: {opt['name']}{line_value}",
                                        "Odds": opt["price"], "True Prob.": proj_p, "EV Edge": ev,
                                        "Wager": wager, "Units": units
                                    })

# --- TAB 1: RENDER DISPLAY ENGINE ---
with main_tab:
    st.markdown("### 🛠️ Interactive Sorting Filter Canvas")
    col_sort, col_order = st.columns(2)
    with col_sort:
        sort_metric = st.selectbox("Sort Data Metric By", ["Expected Value (EV)", "True Win Probability", "Matchup Alphabetical"])
    with col_order:
        sort_direction = st.selectbox("Sort Direction Order", ["Highest to Lowest", "Lowest to Highest"])
    
    sub_tab_games, sub_tab_props = st.tabs(["🏛️ Game Lines (Moneylines)", "👤 Specialized Player Props Matrix"])
    
    def sort_extracted_df(target_slate):
        if not target_slate: return pd.DataFrame()
        target_df = pd.DataFrame(target_slate)
        sort_col = "EV Edge" if "EV" in sort_metric else "True Prob." if "Prob" in sort_metric else "Matchup"
        ascending_bool = True if "Lowest" in sort_direction else False
        target_df = target_df.sort_values(by=sort_col, ascending=ascending_bool)
        
        display_df = target_df.copy()
        display_df["True Prob."] = display_df["True Prob."].apply(lambda x: f"{x*100:.1f}%")
        display_df["EV Edge"] = display_df["EV Edge"].apply(lambda x: f"{x*100:+.1f}%")
        display_df["Wager"] = display_df["Wager"].apply(lambda x: f"${x:.2f}")
        display_df["Units"] = display_df["Units"].apply(lambda x: f"{x:.2f}u")
        return display_df

    with sub_tab_games:
        sorted_games_df = sort_extracted_df(game_lines_slate)
        if not sorted_games_df.empty:
            st.dataframe(sorted_games_df, use_container_width=True, hide_index=True)
        else:
            st.info("No high-value game line opportunities discovered currently for this sport tier.")

    with sub_tab_props:
        sorted_props_df = sort_extracted_df(player_props_slate)
        if not sorted_props_df.empty:
            st.dataframe(sorted_props_df, use_container_width=True, hide_index=True)
        else:
            st.info("No high-value specialized player prop opportunities found currently on this slate.")
    
    st.markdown("---")
    st.markdown("### 📝 Log a Play to the Syndicate Ledger")
    
    options_pool = {}
    if game_lines_slate:
        for p in game_lines_slate:
            options_pool[f"Game Line: {p['Selection']} ({p['Matchup']})"] = ("Game Line", p)
    if player_props_slate:
        for p in player_props_slate:
            options_pool[f"Prop: {p['Selection']} ({p['Matchup']})"] = ("Player Prop", p)
            
    if options_pool:
        c1, c2, c3 = st.columns(3)
        with c1: f_name = st.selectbox("Who is betting?", ["Myself", "Friend A", "Friend B", "Friend C"])
        with c2: target_selection = st.selectbox("Select Target Play Slip Line", list(options_pool.keys()))
        with c3: actual_wager = st.number_input("Wager Stake Amount ($)", min_value=1.0, value=20.0, step=5.0)
        
        if st.button("🚀 Push Slip to Group Ledger"):
