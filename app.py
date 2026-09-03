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
def calculate_kelly_unit(true_prob, american_odds, bankroll, fraction):
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
        event_prop_url = f"https://the-odds-api.com{SPORT}/events/{game_id}/odds"
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
                                        
                                        if ev > 0:
                                            market_clean = m_key.replace("player_", "").replace("pitcher_", "").replace("_", " ").title()
                                            pt_val = f" {opt.get('point', '')}" if 'point' in opt else ""
                                            player_props_slate.append({
                                                "Matchup": matchup_name,
                                                "Selection": f"{p_name} [{market_clean}]: {opt['name']}{pt_val}",
                                                "Odds": opt["price"], "True Prob.": proj_p, "EV Edge": ev,
                                                "Wager": wager, "Units": units
                                            })
                        elif not df_p.empty:
                            st.sidebar.caption(f"⚠️ Unexpected columns in market {m_key}: {list(df_p.columns)}")
        except Exception:
            pass 

# --- TAB 1: DISPLAY MATRICES ---
with main_tab:
    st.markdown("### 🛠️ Interactive Sorting Filter Canvas")
    col_sort, col_order = st.columns(2)
    
    with col_sort:
        sort_metric = st.selectbox("Sort Data Metric By", ["EV Edge", "True Prob.", "Odds", "Wager"])
    with col_order:
        sort_order = st.selectbox("Order Direction", ["Highest to Lowest", "Lowest to Highest"])
    
    ascending_flag = True if sort_order == "Lowest to Highest" else False

    # Game Lines Canvas
    st.markdown("#### 🏛️ Game Line Value Fields")
    if game_lines_slate:
        df_games = pd.DataFrame(game_lines_slate).sort_values(by=sort_metric, ascending=ascending_flag)
        st.dataframe(df_games.style.format({"True Prob.": "{:.2%}", "EV Edge": "{:.2%}", "Wager": "${:.2f}", "Units": "{:.2f}"}), use_container_width=True)
    else:
        st.info("No +EV game line markets found for this slate.")

    # Player Props Canvas
    st.markdown("#### 🎯 Player Prop Value Fields")
    if player_props_slate:
        df_props = pd.DataFrame(player_props_slate).sort_values(by=sort_metric, ascending=ascending_flag)
        st.dataframe(df_props.style.format({"True Prob.": "{:.2%}", "EV Edge": "{:.2%}", "Wager": "${:.2f}", "Units": "{:.2f}"}), use_container_width=True)
    else:
        st.info("No +EV player prop fields identified or league selection does not support active prop extraction queries.")

# --- TAB 2: GROUP LEDGER MATRIX ---
with ledger_tab:
    st.markdown("### 📝 Shared Syndicate Ledger Matrix")
    if not st.session_state.ledger.empty:
        st.dataframe(st.session_state.ledger, use_container_width=True)
    else:
        st.info("The ledger is currently clear. No committed value profiles recorded yet.")
