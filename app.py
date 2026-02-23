import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import requests
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import os
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration ---
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

# --- 2. CoinDCX API ইঞ্জিন (Price Fix & Real-time) ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    """সরাসরি CoinDCX পাবলিক টিকার থেকে ডেটা আনে।"""
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def get_crypto_price_v2(data, market_pair):
    """লিস্ট থেকে নির্দিষ্ট কয়েনের দাম এবং ২৪ ঘণ্টার পরিবর্তন বের করে।"""
    if not isinstance(data, list): return 0.0, 0.0
    try:
        # CoinDCX-এ পেয়ার ফরম্যাট সাধারণত 'BTCUSDT' বা 'ETHUSDT'
        ticker = next((item for item in data if item.get("market") == market_pair), None)
        if ticker:
            return float(ticker.get('last_price', 0.0)), float(ticker.get('change_24h', 0.0))
    except: pass
    return 0.0, 0.0

# --- 3. মার্কেট ডেটা ও ডিকশনারি ---
# ... (আপনার আগের FNO_SECTORS এবং NIFTY_50 লিস্ট এখানে থাকবে) ...
# (সংক্ষিপ্ত করার জন্য এখানে সব লিস্ট পুনরায় লিখলাম না, আপনি আগের কোড থেকে এগুলো রাখবেন)

# --- 4. Sidebar & Market Toggle ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=1)
    st.divider()
    
    if market_mode == "🇮🇳 Indian Market (NSE)":
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup"]
        # FNO Sectors logic
    else:
        menu_options = ["📈 MAIN TERMINAL", "📊 LIVE CHART VIEW", "🚀 24H Crypto Movers", "🔥 Volume Spikes & OI"]
    
    page_selection = st.radio("Select Menu:", menu_options)
    st.divider()
    
    # চার্ট সিলেকশন (শুধুমাত্র ক্রিপ্টোর জন্য)
    chart_coin = st.selectbox("Select Crypto for Chart:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]) if market_mode == "₿ Crypto Market (24/7)" else None

# --- 5. CSS Styling ---
st.markdown("""
    <style>
    .top-nav { background-color: #002b36; padding: 15px; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 10px; text-align: center; }
    .section-title { background-color: #00425a; color: #00ffd0; font-size: 14px; padding: 10px; border-left: 5px solid #00ffd0; border-radius: 5px; margin: 15px 0; }
    .idx-container { display: flex; justify-content: space-around; background: white; padding: 15px; border-radius: 8px; border: 1px solid #b0c4de; }
    </style>
""", unsafe_allow_html=True)

# --- 6. Header ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
terminal_title = "HARIDAS CRYPTO TERMINAL" if market_mode == "₿ Crypto Market (24/7)" else "HARIDAS NSE TERMINAL"

st.markdown(f"<div class='top-nav'><div style='color:#00ffd0; font-weight:900; font-size:24px;'>📊 {terminal_title}</div>"
            f"<div style='color:white;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div></div>", unsafe_allow_html=True)

# --- 7. Main Dashboard লজিক ---
if page_selection == "📈 MAIN TERMINAL":
    if market_mode == "₿ Crypto Market (24/7)":
        st.markdown("<div class='section-title'>📉 LIVE CRYPTO INDICES (COINDCX)</div>", unsafe_allow_html=True)
        live_data = get_coindcx_live_prices()
        
        # কয়েন প্রাইস ফেচ
        btc_p, btc_c = get_crypto_price_v2(live_data, "BTCUSDT")
        eth_p, eth_c = get_crypto_price_v2(live_data, "ETHUSDT")
        sol_p, sol_c = get_crypto_price_v2(live_data, "SOLUSDT")
        
        # মেট্রিক ডিসপ্লে
        c1, c2, c3 = st.columns(3)
        c1.metric("BITCOIN", f"${btc_p:,.2f}", f"{btc_c}%")
        c2.metric("ETHEREUM", f"${eth_p:,.2f}", f"{eth_c}%")
        c3.metric("SOLANA", f"${sol_p:,.2f}", f"{sol_c}%")
        
        st.divider()
        # এখানে আপনার আগের সিগন্যাল এবং ট্রেড জার্নাল সেকশনগুলো বসাবেন
    else:
        st.info("NSE ডেটা yfinance থেকে লোড হচ্ছে...")
        # আপনার আগের NSE লজিকগুলো এখানে থাকবে

elif page_selection == "📊 LIVE CHART VIEW" and chart_coin:
    st.markdown(f"<div class='section-title'>📈 REAL-TIME CHART: {chart_coin}</div>", unsafe_allow_html=True)
    chart_url = f"https://s.tradingview.com/widgetembed/?symbol=BINANCE:{chart_coin}&interval=5&theme=dark"
    st.components.v1.iframe(chart_url, height=600)
