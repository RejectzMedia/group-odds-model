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
SPORT = st.sidebar.selectbox(
    "Target League Workspace", 
    ["baseball_mlb", "americanfootball_nfl", "americanfootball_ncaaf", "baseball_ncaa"]
)
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

# --- 5. PASS 1: FETCH MAIN LINE ODDS & EVENT IDS ---
clean_sport = str(SPORT).strip()
base_api_url = f"https://the-odds-api.com{clean_sport}/odds"

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
    st.error("📡 API Connection Dropout on Main Lines: " + str(e))
    st.stop()

if isinstance(game_response, dict) and "msg" in game_response:
    st.error("API Provider Error: " + str(game_response['msg']))
    st.stop()

game_lines_slate = []

# Mapping dictionary for clean market display
MARKET_MAPPER = {
    "h2h": "Moneyline",
    "spreads": "Spread",
    "totals": "Over/Under",
    "batter_home_runs": "Prop: Batter HR",
    "player_pass_tds": "Prop: Passing TDs",
    "player_rush_yds": "Prop: Rushing Yds",
    "player_pass_yds": "Prop: Passing Yds"
}

# Processes list data cleanly
def process_market_outcomes(outcomes, m_key, matchup, bm_key):
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
                market_label = MARKET_MAPPER.get(m_key, m_key.replace("_", " ").title())
                
                game_lines_slate.append({
                    "Bookmaker": bm_key, "Matchup": matchup, "Market": market_label,
                    "Selection": f"{opt['name']}{pt_suffix}", "Odds": int(opt["price"]),
                    "True Prob.": float(proj_p * 100), "EV Edge": float(ev * 100), 
                    "Wager": float(wager), "Units": float(units)
                })

# Loop main lines
if isinstance(game_response, list):
    for game in game_response:
        game_id = game.get("id")
        matchup = f"{game.get('away_team', 'Away')} @ {game.get('home_team', 'Home')}"
        
        # Parse Main Game Lines
        for bm in game.get("bookmakers", []):
            bm_key = bm.get("key", "").upper()
            for market in bm.get("markets", []):
                process_market_outcomes(market.get("outcomes", []), market.get("key"), matchup, bm_key)
                
        # --- PASS 2: SUB-LOOP SUB-COLLECTOR FOR DEDICATED PLAYER PROPS ---
        if game_id:
            prop_url = f"https://the-odds-api.com{clean_sport}/events/{game_id}/odds"
            prop_params = {
                "apiKey": str(API_KEY).strip(),
                "regions": "us",
                "markets": "batter_home_runs,player_pass_tds,player_rush_yds,player_pass_yds",
                "oddsFormat": "american",
                "bookmakers": "fanduel,draftkings"
            }
            try:
                prop_response = requests.get(prop_url, params=prop_params, timeout=10).json()
                if isinstance(prop_response, dict) and "bookmakers" in prop_response:
                    for p_bm in prop_response.get("bookmakers", []):
                        p_bm_key = p_bm.get("key", "").upper()
                        for p_market in p_bm.get("markets", []):
                            process_market_outcomes(p_market.get("outcomes", []), p_market.get("key"), matchup, p_bm_key)
            except Exception:
                pass # Gracefully skip if a specific game lacks prop lines to keep app running cleanly

# --- 6. UI RENDER ---
with main_tab:
    st.markdown("### 🏟️ Game Line & Player Prop Value Fields")
    if game_lines_slate:
        master_df = pd.DataFrame(game_lines_slate)
        unique_games = master_df["Matchup"].unique()
        
        for game_matchup in unique_games:
            game_df = master_df[master_df["Matchup"] == game_matchup].copy()
            game_df = game_df.sort_values(by="EV Edge", ascending=False)
            
            ev_count = len(game_df[game_df["EV Edge"] > 0])
            header_label = f"🏈 {game_matchup} ({ev_count} Value Opportunities)" if ev_count > 0 else f"⚪ {game_matchup}"
            
            with st.expander(header_label, expanded=False):
                display_df = game_df.drop(columns=["Matchup"])
                
                # Highlight rows with EV Edge >= 5.0% green
                def highlight_high_ev(row):
                    is_high_edge = row["EV Edge"] >= 5.0
                    return ['background-color: rgba(46, 204, 113, 0.20); color: #ffffff;' if is_high_edge else '' for _ in row]
                
                styled_df = display_df.style.apply(highlight_high_ev, axis=1)
                
                st.dataframe(
                    styled_df,
                    column_config={
                        "Odds": st.column_config.NumberColumn("Odds", format="%d"),
                        "True Prob.": st.column_config.NumberColumn("True Prob.", format="%.1f%%"),
                        "EV Edge": st.column_config.NumberColumn("EV Edge", format="%.1f%%"),
                        "Wager": st.column_config.NumberColumn("Wager ($)", format="$%.2f"),
                        "Units": st.column_config.NumberColumn("Units", format="%.2f")
                    },
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.info("No active fields found matching your filter rules.")
