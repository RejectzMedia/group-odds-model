import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. SERVER WORKSPACE REFRESH FLUSH
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

VIEW_MODE = st.sidebar.radio("Display Filter Matrix", ["Show +EV Edges Only", "Show Raw Board (Debug Stream)"])

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

def extract_player_name(df):
    possible_keys = ["description", "player", "name", "participant"]
    for key in possible_keys:
        if key in df.columns:
            return key
    return None

# 6. APP NAVIGATION FRAME
main_tab, ledger_tab = st.tabs(["🔥 Active Value Boards", "📊 Group Ledger Matrix"])

if not API_KEY:
    with main_tab:
        st.warning("⚠️ Open the control panel (top-left menu arrow) and input your key to harvest active fields.")
    with ledger_tab:
        st.warning("⚠️ Waiting for validation framework configuration parameters.")
    st.stop()

# --- 7. PASS 1: FETCH BASE BULK GAME ML, SPREADS, AND TOTALS ---
clean_sport = str(SPORT).strip()
base_api_url = f"https://api.the-odds-api.com/v4/sports/{clean_sport}/odds"

game_params = {
    "apiKey": str(API_KEY).strip(),
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "bookmakers": "fanduel,draftkings"
}

try:
    game_response = requests.get(base_api_url, params=game_params, timeout=10).json()
except Exception as e:
    st.error("📡 API Game Line Connection Dropout: " + str(e))
    st.stop()

if isinstance(game_response, dict) and "msg" in game_response:
    st.error("API Provider Error: " + str(game_response['msg']))
    st.stop()

game_lines_slate = []
player_props_slate = []

if isinstance(game_response, list):
    for game in game_response:
        if not isinstance(game, dict):
            continue
        matchup_name = game.get('away_team', 'Away') + " @ " + game.get('home_team', 'Home')
        game_id = game.get("id")
        bookmakers = game.get("bookmakers", [])
        
        for bm in bookmakers:
            bm_key = bm.get("key")
            if bm_key not in ["fanduel", "draftkings"]:
                continue
            
            markets = bm.get("markets", [])
            for market in markets:
                m_key = market.get("key")
                outcomes = market.get("outcomes", [])
                
                if isinstance(outcomes, list) and len(outcomes) == 2:
                    p1_true, p2_true = devig_odds(outcomes[0]["price"], outcomes[1]["price"])
                    
                    for opt, true_p in zip(outcomes, [p1_true, p2_true]):
                        mult = 1.06 if m_key == "h2h" else 1.05
                        proj_p = min(0.99, true_p * mult)
                        
                        dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                        ev = (proj_p * dec_odds) - (1 - proj_p)
                        wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                        
                        if VIEW_MODE == "Show Raw Board (Debug Stream)" or ev > 0:
                            pt_suffix = " (" + str(opt['point']) + ")" if "point" in opt else ""
                            if m_key == "h2h":
                                market_label = "Moneyline"
                            elif m_key == "spreads":
                                market_label = "Spread"
                            else:
                                market_label = "Over/Under"
                                
                            game_lines_slate.append({
                                "Bookmaker": bm_key.upper(),
                                "Matchup": matchup_name,
                                "Market": market_label,
                                "Selection": str(opt['name']) + pt_suffix,
                                "Odds": opt["price"], 
                                "True Prob.": proj_p, 
                                "EV Edge": ev, 
                                "Wager": wager, 
                                "Units": units
                            })

        # --- PASS 2: INDEPENDENT PROPS DEEP LOOK (ONLY FOR MLB & NFL) ---
        if SPORT in ["baseball_mlb", "americanfootball_nfl"] and game_id:
            props_to_fetch = "pitcher_strikeouts,pitcher_record_an_out,batter_hits,batter_runs,batter_rbis" if SPORT == "baseball_mlb" else "player_pass_yds,player_rush_yds,player_rec_yds"
            clean_id = str(game_id).strip()
            event_prop_url = f"https://api.the-odds-api.com/v4/sports/{clean_sport}/events/{clean_id}/odds"
            
            prop_params = {
                "apiKey": str(API_KEY).strip(),
                "regions": "us",
                "markets": props_to_fetch,
                "oddsFormat": "american",
                "bookmakers": "fanduel,draftkings"
            }
            
            try:
                prop_response = requests.get(event_prop_url, params=prop_params, timeout=10).json()
                if isinstance(prop_response, dict) and "bookmakers" in prop_response:
                    for p_bm in prop_response.get("bookmakers", []):
                        p_bm_key = p_bm.get("key")
                        if p_bm_key not in ["fanduel", "draftkings"]:
                            continue
                        
                        for p_market in p_bm.get("markets", []):
                            m_key = p_market.get("key")
                            p_outcomes = p_market.get("outcomes", [])
                            
                            df_p = pd.DataFrame(p_outcomes)
                            name_col = extract_player_name(df_p)
                            
                            if name_col and not df_p.empty:
                                for p_name, group in df_p.groupby(name_col):
                                    if len(group) == 2:
                                        rows = group.to_dict(orient="records")
                                        p1_t, p2_t = devig_odds(rows[0]["price"], rows[1]["price"])
                                        
                                        for opt, true_p in zip(rows, [p1_t, p2_t]):
                                            proj_p = min(0.99, true_p * 1.07) 
                                            dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                                            ev = (proj_p * dec_odds) - (1 - proj_p)
                                            wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                                            
                                            if VIEW_MODE == "Show Raw Board (Debug Stream)" or ev > 0:
                                                market_clean = m_key.replace("player_", "").replace("pitcher_", "").replace("_", " ").title()
                                                pt_val = f" {opt.get('point', '')}" if 'point' in opt else ""
                                                player_props_slate.append({
                                                    "Bookmaker": p_bm_key.upper(),
                                                    "Matchup": matchup_name,
                                                    "Market": market_clean,
                                                    "Selection": f"{p_name}: {opt['name']}{pt_val}",
                                                    "Odds": opt["price"], 
                                                    "True Prob.": proj_p, 
                                                    "EV Edge": ev,
                                                    "Wager": wager, 
                                                    "Units": units
                                                })
            except Exception:
                pass 

# --- 8. UI RENDER INTERFACE PANEL ---
with main_tab:
