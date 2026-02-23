import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# --- ১. পেজ কনফিগারেশন ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal")
st_autorefresh(interval=5000, key="datarefresh") # ৫ সেকেন্ড পরপর রিফ্রেশ

# --- ২. CoinDCX API ইঞ্জিন (Price Fix) ---
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except: return []

def get_crypto_price_v2(data, market_pair):
    if not isinstance(data, list): return 0.0, 0.0
    # CoinDCX-এ USDT পেয়ারগুলো সাধারণত 'BTCUSDT' ফরম্যাটে থাকে (B- সরিয়ে দেখুন)
    ticker = next((item for item in data if item.get("market") == market_pair), None)
    if ticker:
        return float(ticker.get('last_price', 0.0)), float(ticker.get('change_24h', 0.0))
    return 0.0, 0.0

# --- ৩. সাইডবার ---
with st.sidebar:
    st.title("⚙️ SETTINGS")
    market_mode = st.radio("Market:", ["🇮🇳 NSE", "₿ Crypto"], index=1)
    chart_coin = st.selectbox("Select Chart:", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

# --- ৪. মেইন ডিসপ্লে ও ইনডেক্স (Price Fix) ---
live_data = get_coindcx_live_prices()
btc_p, btc_c = get_crypto_price_v2(live_data, "BTCUSDT") # 'B-' সরিয়ে দিয়েছি
eth_p, eth_c = get_crypto_price_v2(live_data, "ETHUSDT")

st.markdown(f"### 🚀 HARIDAS CRYPTO TERMINAL")
col1, col2 = st.columns(2)
col1.metric("BITCOIN (BTC)", f"${btc_p:,.2f}", f"{btc_c}%")
col2.metric("ETHEREUM (ETH)", f"${eth_p:,.2f}", f"{eth_c}%")

# --- ৫. TradingView লাইভ চার্ট (নতুন সংযোজন) ---
st.markdown(f"### 📊 LIVE CHART: {chart_coin}")
chart_url = f"https://s.tradingview.com/widgetembed/?symbol=BINANCE:{chart_coin}&interval=5&theme=dark"
st.components.v1.iframe(chart_url, height=500)
