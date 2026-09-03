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

# --- 7. PASS 1: FETCH BASE BULK GAME ML LINES ---
base_api_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
game_params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "american",
    "bookmakers": "fanduel"
}

try:
    game_response = requests.get(base_api_url, params=game_params, timeout=10).json()
except Exception as e:
    st.error(f"📡 API Game Line Connection Dropout: {e}")
    st.stop()

if isinstance(game_response, dict) and "msg" in game_response:
    st.error(f"API Provider Error: {game_response['msg']}")
    st.stop()

game_lines_slate = []
player_props_slate = []

# Process Game Moneylines
for game in game_response:
    if not isinstance(game, dict): continue
    matchup_name = f"{game.get('away_team')} @ {game.get('home_team')}"
    game_id = game.get("id")
    bookmakers = game.get("bookmakers", [])
    
    for bm in bookmakers:
        if bm.get("key") != "fanduel": continue
        markets = bm.get("markets", [])
        for market in markets:
            if market.get("key") == "h2h":
                outcomes = market.get("outcomes", [])
                if len(outcomes) == 2:
                    p1_true, p2_true = devig_odds(outcomes[0]["price"], outcomes[1]["price"])
                    for opt, true_p in zip(outcomes, [p1_true, p2_true]):
                        proj_p = min(0.99, true_p * 1.06) 
                        dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                        ev = (proj_p * dec_odds) - (1 - proj_p)
                        wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                        
                        if ev > 0:
                            game_lines_slate.append({
                                "Matchup": matchup_name, "Selection": opt["name"], "Odds": opt["price"],
                                "True Prob.": proj_p, "EV Edge": ev, "Wager": wager, "Units": units
                            })

    # --- PASS 2: INDEPENDENT PROPS DEEP LOOK (ONLY FOR MLB & NFL) ---
    if SPORT in ["baseball_mlb", "americanfootball_nfl"] and game_id:
        props_to_fetch = "pitcher_strikeouts,pitcher_record_an_out,batter_hits,batter_runs,batter_rbis" if SPORT == "baseball_mlb" else "player_pass_yds,player_rush_yds,player_rec_yds"
        event_prop_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{game_id}/odds"
        prop_params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": props_to_fetch,
            "oddsFormat": "american",
            "bookmakers": "fanduel"
        }
        
        try:
            prop_response = requests.get(event_prop_url, params=prop_params, timeout=10).json()
            if isinstance(prop_response, dict) and "bookmakers" in prop_response:
                for p_bm in prop_response.get("bookmakers", []):
                    if p_bm.get("key") != "fanduel": continue
                    for p_market in p_bm.get("markets", []):
                        m_key = p_market.get("key")
                        p_outcomes = p_market.get("outcomes", [])
                        
                        # Process Over/Under Pairs cleanly via structured data frames
                        df_p = pd.DataFrame(p_outcomes)
                        if "description" in df_p.columns:
                            for p_name, group in df_p.groupby("description"):
                                if len(group) == 2:
                                    rows = group.to_dict(orient="records")
                                    p1_t, p2_t = devig_odds(rows[0]["price"], rows[1]["price"])
                                    
                                    for opt, true_p in zip(rows, [p1_t, p2_t]):
                                        proj_p = min(0.99, true_p * 1.07) 
                                        dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                                        ev = (proj_p * dec_odds) - (1 - proj_p)
                                        wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                                        
                                        if ev > 0:
                                            market_clean = m_key.replace("player_", "").replace("pitcher_", "").replace("_", " ").title()
                                            pt_val = f" {opt.get('point', '')}" if 'point' in opt else ""
                                            player_props_slate.append({
                                                "Matchup": matchup_name,
                                                "Selection": f"{p_name} [{market_clean}]: {opt['name']}{pt_val}",
                                                "Odds": opt["price"], "True Prob.": proj_p, "EV Edge": ev,
                                                "Wager": wager, "Units": units
                                            })
        except Exception:
            pass # Gracefully handle unpopulated event schedules early in the week

# --- TAB 1: DISPLAY MATRICES ---
with main_tab:
    st.markdown("### 🛠️ Interactive Sorting Filter Canvas")
    col_sort, col_order = st.columns(2)
    sort_metric = st.selectbox("Sort Data Metric By", ["Expected Value (EV)", "True Win Probability", "Matchup Alphabetical"])
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
        if not sorted_games_df.empty: st.dataframe(sorted_games_df, use_container_width=True, hide_index=True)
        else: st.info("No high-value game line opportunities discovered currently for this sport tier.")

    with sub_tab_props:
        sorted_props_df = sort_extracted_df(player_props_slate)
        if not sorted_props_df.empty: st.dataframe(sorted_props_df, use_container_width=True, hide_index=True)
        else: st.info("No high-value specialized player prop opportunities found currently on this slate.")
    
    st.markdown("---")
    st.markdown("### 📝 Log a Play to the Syndicate Ledger")
    
    options_pool = {}
    if game_lines_slate:
        for p in game_lines_slate: options_pool[f"Game Line: {p['Selection']} ({p['Matchup']})"] = ("Game Line", p)
    if player_props_slate:
