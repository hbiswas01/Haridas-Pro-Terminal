import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import requests
import os
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration (মাস্ট বি টপে থাকতে হবে) ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

# ৫ সেকেন্ড পরপর অটো-রিফ্রেশ (CoinDCX এর লাইভ ডেটার জন্য)
st_autorefresh(interval=5000, key="datarefresh")

# --- AUTO-SAVE DATABASE SETUP ---
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

# --- 2. CoinDCX API ইঞ্জিন (নিরাপদ লজিক) ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except:
        return []

def get_crypto_price_v2(data, market_pair):
    if not isinstance(data, list): return 0.0, 0.0
    try:
        ticker = next((item for item in data if isinstance(item, dict) and item.get("market") == market_pair), None)
        if ticker:
            return float(ticker.get('last_price', 0.0)), float(ticker.get('change_24h', 0.0))
    except: pass
    return 0.0, 0.0

# --- 3. মার্কেট ডেটা ও ডিকশনারি ---
FNO_SECTORS = {
    "NIFTY BANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"],
    "MIXED WATCHLIST": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "ITC.NS"]
}

CRYPTO_SECTORS = {
    "TOP WATCHLIST": ["B-BTC_USDT", "B-ETH_USDT", "B-SOL_USDT", "B-DOGE_USDT"]
}

# --- 4. Sidebar & Market Toggle (NameError ফিক্স) ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=0)
    st.divider()
    
    if market_mode == "🇮🇳 Indian Market (NSE)":
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers"]
        all_assets = ["SBIN.NS", "RELIANCE.NS", "TCS.NS"] # উদাহরণ হিসেবে
    else:
        menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers"]
        all_assets = ["B-BTC_USDT", "B-ETH_USDT"]

    page_selection = st.radio("Select Menu:", menu_options)

# --- 5. CSS (আপনার সুন্দর ইন্টারফেসের জন্য) ---
st.markdown("""
    <style>
    .top-nav { background-color: #002b36; padding: 15px; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 10px; }
    .section-title { background: linear-gradient(90deg, #002b36 0%, #00425a 100%); color: #00ffd0; font-size: 14px; padding: 10px; border-left: 5px solid #00ffd0; border-radius: 5px; margin: 15px 0; }
    .idx-container { display: flex; justify-content: space-around; background: white; padding: 10px; border-radius: 5px; border: 1px solid #b0c4de; margin-bottom: 15px; }
    .idx-box { text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 6. টপ নেভিগেশন ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
terminal_title = "HARIDAS NSE TERMINAL" if market_mode == "🇮🇳 Indian Market (NSE)" else "HARIDAS CRYPTO TERMINAL"

st.markdown(f"""
    <div class='top-nav'>
        <div style='color:#00ffd0; font-weight:900; font-size:24px; text-align:center;'>📊 {terminal_title}</div>
        <div style='color:white; text-align:center;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div>
    </div>
""", unsafe_allow_html=True)

# --- 7. মেইন ড্যাশবোর্ড ডিসপ্লে ---
if page_selection == "📈 MAIN TERMINAL":
    col1, col2, col3 = st.columns([1, 2.5, 1])
    
    with col2:
        st.markdown("<div class='section-title'>📉 LIVE MARKET INDICES</div>", unsafe_allow_html=True)
        if market_mode == "₿ Crypto Market (24/7)":
            live_data = get_coindcx_live_prices()
            btc_p, btc_c = get_crypto_price_v2(live_data, "B-BTC_USDT")
            eth_p, eth_c = get_crypto_price_v2(live_data, "B-ETH_USDT")
            sol_p, sol_c = get_crypto_price_v2(live_data, "B-SOL_USDT")
            
            st.markdown(f"""
                <div class='idx-container'>
                    <div class='idx-box'><b>BITCOIN</b><br><span style='font-size:18px;'>${btc_p:,.2f}</span><br><span style='color:{"green" if btc_c >= 0 else "red"};'>{btc_c}%</span></div>
                    <div class='idx-box'><b>ETHEREUM</b><br><span style='font-size:18px;'>${eth_p:,.2f}</span><br><span style='color:{"green" if eth_c >= 0 else "red"};'>{eth_c}%</span></div>
                    <div class='idx-box'><b>SOLANA</b><br><span style='font-size:18px;'>${sol_p:,.2f}</span><br><span style='color:{"green" if sol_c >= 0 else "red"};'>{sol_c}%</span></div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("NSE ডেটা yfinance থেকে লোড হচ্ছে...")
