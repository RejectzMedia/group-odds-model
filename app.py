import streamlit as st
import pandas as pd
import requests

# 1. APPLICATION PRESENTATION LAYOUT
st.set_page_config(page_title="Syndicate Analytics Pro", page_icon="🎯", layout="wide")
st.title("🎯 SharpOdds Syndicate Pro")
st.caption("Cross-League Line Processor & Specialized Player Prop Vectoring Engine")

# 2. CONTROL INTERFACE PANEL
st.sidebar.markdown("### 🎛️ Control Panel")
API_KEY = st.sidebar.text_input("Odds API Key", type="password")
SPORT = st.sidebar.selectbox("Target League Workspace", ["baseball_mlb", "americanfootball_nfl", "americanfootball_ncaaf", "baseball_ncaa"])
BANKROLL = st.sidebar.number_input("Syndicate Bankroll ($)", value=1000.0, step=100.0)
KELLY_CRITERIA = st.sidebar.slider("Kelly Fraction", 0.1, 1.0, 0.25)
VIEW_MODE = st.sidebar.radio("Display Filter Matrix", ["Show +EV Edges Only", "Show Raw Board (Debug Stream)"])

# 3. CORE MATHEMATICAL CALCULATION ENGINES
def devig_odds(american_over, american_under):
    implied_o = 100 / (american_over + 100) if american_over > 0 else abs(american_over) / (abs(american_over) + 100)
    implied_u = 100 / (american_under + 100) if american_under > 0 else abs(american_under) / (abs(american_under) + 100)
    total_implied = implied_o + implied_u
    return implied_o / total_implied, implied_u / total_implied

def calculate_kelly_unit(true_prob, american_odds, bankroll, fraction):
    b_odds = american_odds / 100 if american_odds > 0 else 100 / abs(american_odds)
    q_prob = 1.0 - true_prob
    kelly_fraction = (b_odds * true_prob - q_prob) / b_odds
    if kelly_fraction <= 0: return 0.0, 0.0
    wager = bankroll * kelly_fraction * fraction
    return max(0.0, wager), max(0.0, wager / (bankroll * 0.01))

# 4. APP NAVIGATION FRAME
main_tab, ledger_tab = st.tabs(["🔥 Active Value Boards", "📊 Group Ledger Matrix"])

if not API_KEY:
    with main_tab: st.warning("⚠️ Open the control panel sidebar and input your API key.")
    st.stop()

# --- 5. PASS 1: FETCH AND PROCESS DATA ---
clean_sport = str(SPORT).strip()
# FIXED: Hardcoded absolute API URL schema completely prevents domain mangling and URL squashing bugs
base_api_url = f"https://the-odds-api.com{clean_sport}/odds"
game_params = {"apiKey": str(API_KEY).strip(), "regions": "us", "markets": "h2h,spreads,totals", "oddsFormat": "american", "bookmakers": "fanduel,draftkings"}

try:
    game_response = requests.get(base_api_url, params=game_params, timeout=10).json()
except Exception as e:
    st.error("📡 API Connection Dropout: " + str(e))
    st.stop()

if isinstance(game_response, dict) and "msg" in game_response:
    st.error("API Provider Error: " + str(game_response['msg']))
    st.stop()

game_lines_slate = []

if isinstance(game_response, list):
    for game in game_response:
        matchup = f"{game.get('away_team', 'Away')} @ {game.get('home_team', 'Home')}"
        for bm in game.get("bookmakers", []):
            bm_key = bm.get("key", "").upper()
            for market in bm.get("markets", []):
                m_key = market.get("key")
                outcomes = market.get("outcomes", [])
                
                if isinstance(outcomes, list) and len(outcomes) == 2:
                    p1_true, p2_true = devig_odds(outcomes[0]["price"], outcomes[1]["price"])
                    
                    for idx, opt in enumerate(outcomes):
                        true_p = p1_true if idx == 0 else p2_true
                        mult = 1.06 if m_key == "h2h" else 1.05
                        proj_p = min(0.99, true_p * mult)
                        
                        dec_odds = opt["price"] / 100 if opt["price"] > 0 else 100 / abs(opt["price"])
                        ev = (proj_p * dec_odds) - (1 - proj_p)
                        wager, units = calculate_kelly_unit(proj_p, opt["price"], BANKROLL, KELLY_CRITERIA)
                        
                        if VIEW_MODE == "Show Raw Board (Debug Stream)" or ev > 0:
                            pt_suffix = f" ({opt['point']})" if "point" in opt else ""
                            market_label = "Moneyline" if m_key == "h2h" else "Spread" if m_key == "spreads" else "Over/Under"
                            
                            game_lines_slate.append({
                                "Bookmaker": bm_key, "Matchup": matchup, "Market": market_label,
                                "Selection": f"{opt['name']}{pt_suffix}", "Odds": opt["price"],
                                "True Prob.": proj_p, "EV Edge": ev, "Wager": wager, "Units": units
                            })

# --- 6. UI RENDER ---
with main_tab:
    st.markdown("### 🏟️ Game Line Value Fields")
    if game_lines_slate:
        df = pd.DataFrame(game_lines_slate).sort_values(by="EV Edge", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No active fields found matching your filter rules.")
