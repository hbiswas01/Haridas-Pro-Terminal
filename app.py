import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import os
import requests

# --- 1. Page Configuration ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

# --- 2. CoinDCX API Logic (New & Optimized) ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except:
        return []

def get_crypto_price_v2(data, market_pair):
    ticker = next((item for item in data if item["market"] == market_pair), None)
    if ticker:
        # last_price এবং change_24h রিটার্ন করছে
        return float(ticker['last_price']), float(ticker.get('change_24h', 0.0))
    return 0.0, 0.0

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

# --- 3. Sidebar & Market Toggle (Moved up to fix NameError) ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    # এখানেই market_mode তৈরি হচ্ছে, তাই এর নিচে এখন যেকোনো জায়গায় এটি ব্যবহার করা যাবে
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=0)
    st.divider()

# --- 4. Market Data Dictionary ---
FNO_SECTORS = {
    "MIXED WATCHLIST": ["HINDALCO.NS", "NTPC.NS", "WIPRO.NS", "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS"],
    "NIFTY METAL": ["HINDALCO.NS", "TATASTEEL.NS", "VEDL.NS", "JSWSTEEL.NS", "NMDC.NS", "COALINDIA.NS"],
    "NIFTY BANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS"],
    "NIFTY IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"],
    "NIFTY ENERGY": ["RELIANCE.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "TATAPOWER.NS"],
    "NIFTY AUTO": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
    "NIFTY PHARMA": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    "NIFTY FMCG": ["ITC.NS", "HUL.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
    "NIFTY INFRA": ["LT.NS", "LICI.NS", "ULTRACEMCO.NS"],
    "NIFTY REALTY": ["DLF.NS", "GODREJPROP.NS", "MACROTECH.NS"],
    "NIFTY PSU BANK": ["SBIN.NS", "PNB.NS", "BOB.NS", "CANBK.NS"]
}

CRYPTO_SECTORS = {
    "TOP WATCHLIST": ["B-BTC_USDT", "B-ETH_USDT", "B-SOL_USDT", "B-BNB_USDT", "B-XRP_USDT", "B-DOGE_USDT"]
}

# --- 5. Logic for Page Selection ---
if market_mode == "🇮🇳 Indian Market (NSE)":
    menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup"]
    sector_dict = FNO_SECTORS
else:
    menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers", "🔥 Volume Spikes & OI"]
    sector_dict = CRYPTO_SECTORS

# --- আপনার বাকি সব ফাংশন (fmt_price, get_live_data, etc.) নিচে থাকবে ---
# ... (বাকি কোড আপনার আগের মতোই কাজ করবে) ...

st.write(f"Selected Mode: {market_mode}") # এখন আর এরর আসবে না
