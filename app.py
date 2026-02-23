import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import os
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="datarefresh")

# --- 2. Database Setup ---
ACTIVE_TRADES_FILE = "active_trades.csv"
HISTORY_TRADES_FILE = "trade_history.csv"

def load_data(file_name):
    if os.path.exists(file_name):
        try: return pd.read_csv(file_name).to_dict('records')
        except: return []
    return []

def save_data(data, file_name):
    pd.DataFrame(data).to_csv(file_name, index=False)

if 'active_trades' not in st.session_state:
    st.session_state.active_trades = load_data(ACTIVE_TRADES_FILE)
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = load_data(HISTORY_TRADES_FILE)

# --- 3. CoinDCX Bulletproof Engine ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200: return response.json()
    except: pass
    return []

def get_crypto_price_v2(data, base_coin):
    """Smart Search: এটি BTC দিলে BTCUSDT বা B-BTC_USDT নিজে থেকেই খুঁজে নেবে"""
    if not isinstance(data, list) or len(data) == 0: return 0.0, 0.0
    
    target_markets = [f"{base_coin}USDT", f"B-{base_coin}_USDT", f"{base_coin}_USDT", f"{base_coin}INR"]
    for item in data:
        if item.get("market") in target_markets:
            try:
                ltp = float(item.get('last_price', 0.0))
                change_abs = float(item.get('change_24h', 0.0))
                if ltp > 0:
                    prev_close = ltp - change_abs
                    pct_change = (change_abs / prev_close * 100) if prev_close > 0 else 0.0
                    return ltp, round(pct_change, 2)
            except: pass
    return 0.0, 0.0

# --- 4. Market Dictionaries ---
FNO_SECTORS = {
    "MIXED WATCHLIST": ["HINDALCO.NS", "NTPC.NS", "WIPRO.NS", "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ITC.NS", "SBIN.NS"],
    "NIFTY BANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS"],
    "NIFTY IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "NIFTY AUTO": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS"]
}
NIFTY_50 = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"]
ALL_STOCKS = list(set([s for slist in FNO_SECTORS.values() for s in slist] + NIFTY_50))

CRYPTO_SECTORS = {
    "TOP WATCHLIST": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "DOGE-USD"],
    "MEME COINS": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "FLOKI-USD", "BONK-USD"],
    "LAYER 1": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD", "DOT-USD"]
}
ALL_CRYPTO = list(set([c for clist in CRYPTO_SECTORS.values() for c in clist]))

def fmt_price(val):
    if pd.isna(val): return "0.00"
    if val < 0.01: return f"{val:.6f}"
    elif val < 1: return f"{val:.4f}"
    else: return f"{val:,.2f}"

# --- 5. Turbo Scanner Engines (Fast Threading) ---
def fetch_single_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period='5d')
        if len(df) >= 2:
            ltp = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            chg = ltp - prev
            pct = (chg / prev) * 100 if prev > 0 else 0.0
            return ticker, ltp, chg, pct
    except: pass
    return ticker, 0.0, 0.0, 0.0

@st.cache_data(ttl=30)
def get_live_data(ticker_symbol):
    _, ltp, chg, pct = fetch_single_ticker(ticker_symbol)
    return ltp, chg, pct

@st.cache_data(ttl=60)
def get_adv_dec(item_list):
    adv, dec = 0, 0
    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_single_ticker, item_list))
    for res in results:
        if res[2] > 0: adv += 1
        elif res[2] < 0: dec += 1
    return adv, dec

@st.cache_data(ttl=60)
def get_dynamic_market_data(item_list):
    gainers, losers, trends = [], [], []
    def fetch_full(ticker):
        try:
            df = yf.Ticker(ticker).history(period="5d")
            if len(df) >= 3:
                c1, c2, c3 = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2]), float(df['Close'].iloc[-3])
                o1, o2, o3 = float(df['Open'].iloc[-1]), float(df['Open'].iloc[-2]), float(df['Open'].iloc[-3])
                if c2 > 0:
                    pct = ((c1 - c2) / c2) * 100
                    trend_stat, clr = None, None
                    if c1 > o1 and c2 > o2 and c3 > o3: trend_stat, clr = "৩ দিন উত্থান", "green"
                    elif c1 < o1 and c2 < o2 and c3 < o3: trend_stat, clr = "৩ দিন পতন", "red"
                    return {"Stock": ticker, "LTP": c1, "Pct": round(pct, 2), "T_Stat": trend_stat, "T_Clr": clr}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_full, item_list))
        
    for res in results:
        if res:
            obj = {"Stock": res["Stock"], "LTP": res["LTP"], "Pct": res["Pct"]}
            if res["Pct"] > 0: gainers.append(obj)
            elif res["Pct"] < 0: losers.append(obj)
            if res["T_Stat"]: trends.append({"Stock": res["Stock"], "Status": res["T_Stat"], "Color": res["T_Clr"]})
            
    return sorted(gainers, key=lambda x: x['Pct'], reverse=True)[:5], sorted(losers, key=lambda x: x['Pct'])[:5], trends

@st.cache_data(ttl=60)
def get_opening_movers(item_list):
    movers = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_single_ticker, item_list))
    for res in results:
        ticker, ltp, chg, pct = res
        if abs(pct) >= 2.0:  # 2% or more movement
            movers.append({"Stock": ticker, "LTP": ltp, "Pct": round(pct, 2)})
    return sorted(movers, key=lambda x: abs(x['Pct']), reverse=True)

# --- 6. Sidebar ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=1)
    st.divider()
    
    st.markdown("### 🎛️ HARIDAS DASHBOARD")
    if market_mode == "🇮🇳 Indian Market (NSE)":
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers"]
        sector_dict, all_assets = FNO_SECTORS, ALL_STOCKS
    else:
        menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers"]
        sector_dict, all_assets = CRYPTO_SECTORS, ALL_CRYPTO

    page_selection = st.radio("Select Menu:", menu_options)
    
    if st.button("🗑️ Clear All History Data"):
        st.session_state.active_trades = []
        st.session_state.trade_history = []
        if os.path.exists(ACTIVE_TRADES_FILE): os.remove(ACTIVE_TRADES_FILE)
        if os.path.exists(HISTORY_TRADES_FILE): os.remove(HISTORY_TRADES_FILE)
        st.success("History Cleared!")
        st.rerun()

# --- 7. CSS & Top Nav ---
st.markdown("""
    <style>
    .top-nav { background-color: #002b36; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 10px; }
    .section-title { background: linear-gradient(90deg, #002b36 0%, #00425a 100%); color: #00ffd0; font-size: 13px; font-weight: 800; padding: 10px 15px; border-left: 5px solid #00ffd0; border-radius: 5px; margin-top: 15px; margin-bottom: 10px; text-transform: uppercase; }
    .table-container { overflow-x: auto; width: 100%; border-radius: 5px; }
    .v38-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; background: white; border: 1px solid #b0c4de; margin-bottom: 10px; }
    .v38-table th { background-color: #4f81bd; color: white; padding: 8px; border: 1px solid #b0c4de; }
    .v38-table td { padding: 8px; border: 1px solid #b0c4de; }
    .idx-container { display: flex; justify-content: space-between; background: white; border: 1px solid #b0c4de; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
    .idx-box { text-align: center; width: 31%; min-width: 100px; }
    .adv-dec-bar { display: flex; height: 14px; border-radius: 4px; overflow: hidden; margin: 8px 0; background: #e0e0e0; }
    .bar-green { background-color: #2e7d32; } .bar-red { background-color: #d32f2f; }
    </style>
""", unsafe_allow_html=True)

ist_tz = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_tz)
title = "HARIDAS CRYPTO TERMINAL" if market_mode == "₿ Crypto Market (24/7)" else "HARIDAS NSE TERMINAL"

st.markdown(f"<div class='top-nav'><div style='color:#00ffd0; font-weight:900; font-size:22px;'>📊 {title}</div>"
            f"<div style='color:white; font-weight:bold;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div></div>", unsafe_allow_html=True)

# ==================== MAIN TERMINAL DISPLAY ====================
if page_selection == "📈 MAIN TERMINAL":
    col1, col2, col3 = st.columns([1.2, 2.5, 1.2])

    # --- LEFT COLUMN ---
    with col1:
        st.markdown("<div class='section-title'>🔍 TREND CONTINUITY (3+ DAYS)</div>", unsafe_allow_html=True)
        with st.spinner("Scanning..."):
            gainers, losers, trends = get_dynamic_market_data(all_assets)
        if trends:
            t_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Status</th></tr>"
            for t in trends: t_html += f"<tr><td style='font-weight:bold;'>{t['Stock']}</td><td style='color:{t['Color']}; font-weight:bold;'>{t['Status']}</td></tr>"
            t_html += "</table></div>"
            st.markdown(t_html, unsafe_allow_html=True)
        else: st.info("No continuous trend found.")

    # --- MIDDLE COLUMN ---
    with col2:
        st.markdown("<div class='section-title'>📉 MARKET INDICES (LIVE)</div>", unsafe_allow_html=True)
        
        if market_mode == "🇮🇳 Indian Market (NSE)":
            p1_ltp, p1_chg, p1_pct = get_live_data("^BSESN")
            p2_ltp, p2_chg, p2_pct = get_live_data("^NSEI")
            p3_ltp, p3_chg, p3_pct = get_live_data("INR=X")
            indices = [("Sensex", p1_ltp, p1_chg, p1_pct), ("Nifty", p2_ltp, p2_chg, p2_pct), ("USDINR", p3_ltp, p3_chg, p3_pct)]
        else:
            live_data = get_coindcx_live_prices()
            # স্মার্ট সার্চ: শুধু বেস কয়েনের নাম দিলেই হবে (যেমন: BTC)
            btc_ltp, btc_pct = get_crypto_price_v2(live_data, "BTC")
            eth_ltp, eth_pct = get_crypto_price_v2(live_data, "ETH")
            sol_ltp, sol_pct = get_crypto_price_v2(live_data, "SOL")
            
            indices = [
                ("BITCOIN", btc_ltp, (btc_ltp * btc_pct / 100) if btc_pct else 0, btc_pct),
                ("ETHEREUM", eth_ltp, (eth_ltp * eth_pct / 100) if eth_pct else 0, eth_pct),
                ("SOLANA", sol_ltp, (sol_ltp * sol_pct / 100) if sol_pct else 0, sol_pct)
            ]

        idx_html = "<div class='idx-container'>"
        for name, val, chg, pct in indices:
            clr = "green" if chg >= 0 else "red"
            sign = "+" if chg >= 0 else ""
            prefix = "₹" if market_mode == "🇮🇳 Indian Market (NSE)" and name != "USDINR" else "$"
            val_str = f"{val:.4f}" if name == "USDINR" else fmt_price(val)
            idx_html += f"<div class='idx-box'><span style='font-size:12px; color:#555; font-weight:bold;'>{name}</span><br><span style='font-size:18px; font-weight:bold;'>{prefix}{val_str}</span><br><span style='color:{clr}; font-weight:bold;'>{sign}{pct}%</span></div>"
        idx_html += "</div>"
        st.markdown(idx_html, unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📊 ADVANCE / DECLINE</div>", unsafe_allow_html=True)
        adv, dec = get_adv_dec(all_assets)
        total = adv + dec
        adv_pct = (adv / total) * 100 if total > 0 else 50
        st.markdown(f"<div class='adv-dec-container'><div class='adv-dec-bar'><div class='bar-green' style='width: {adv_pct}%;'></div><div class='bar-red' style='width: {100-adv_pct}%;'></div></div><div style='display:flex; justify-content:space-between; font-weight:bold;'><span style='color:green;'>Advances: {adv}</span><span style='color:red;'>Declines: {dec}</span></div></div>", unsafe_allow_html=True)

    # --- RIGHT COLUMN ---
    with col3:
        st.markdown("<div class='section-title'>🚀 LIVE TOP GAINERS</div>", unsafe_allow_html=True)
        if gainers:
            g_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for g in gainers: 
                g_html += f"<tr><td style='font-weight:bold;'>{g['Stock']}</td><td>{fmt_price(g['LTP'])}</td><td style='color:green; font-weight:bold;'>+{g['Pct']}%</td></tr>"
            g_html += "</table></div>"
            st.markdown(g_html, unsafe_allow_html=True)
        else: st.info("No data")

        st.markdown("<div class='section-title'>🔻 LIVE TOP LOSERS</div>", unsafe_allow_html=True)
        if losers:
            l_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for l in losers: 
                l_html += f"<tr><td style='font-weight:bold;'>{l['Stock']}</td><td>{fmt_price(l['LTP'])}</td><td style='color:red; font-weight:bold;'>{l['Pct']}%</td></tr>"
            l_html += "</table></div>"
            st.markdown(l_html, unsafe_allow_html=True)
        else: st.info("No data")

# ==================== OTHER SECTIONS (RESTORED) ====================
elif page_selection in ["🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🚀 24H Crypto Movers"]:
    st.markdown(f"<div class='section-title'>📊 {page_selection} (2%+ Movers)</div>", unsafe_allow_html=True)
    with st.spinner(f"Scanning {len(all_assets)} Assets extremely fast..."):
        movers = get_opening_movers(all_assets)
    if movers:
        m_html = "<div class='table-container'><table class='v38-table'><tr><th>Stock / Coin</th><th>LTP</th><th>Movement %</th></tr>"
        for m in movers: 
            c = "green" if m['Pct'] > 0 else "red"
            m_html += f"<tr><td style='font-weight:bold;'>{m['Stock']}</td><td>{fmt_price(m['LTP'])}</td><td style='color:{c}; font-weight:bold;'>{m['Pct']}%</td></tr>"
        m_html += "</table></div>"
        st.markdown(m_html, unsafe_allow_html=True)
    else: st.info("No assets with >2% movement found.")
