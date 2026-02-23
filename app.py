import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import requests
import os
from streamlit_autorefresh import st_autorefresh

# --- ১. পেজ কনফিগারেশন ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

# ৫ সেকেন্ড পরপর অটো-রিফ্রেশ
st_autorefresh(interval=5000, key="datarefresh")

# --- ২. সাইডবার ও মার্কেট টগল (NameError ফিক্স করার জন্য এটি উপরে আনা হয়েছে) ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=0)
    st.divider()
    st.markdown("### 🎛️ HARIDAS DASHBOARD")

# --- ৩. CoinDCX API ইঞ্জিন ---
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except: return []

def get_crypto_price_v2(data, market_pair):
    ticker = next((item for item in data if item["market"] == market_pair), None)
    if ticker:
        return float(ticker['last_price']), float(ticker.get('change_24h', 0.0))
    return 0.0, 0.0

# --- ৪. সিএসএস (আপনার আগের সেই সুন্দর লুক ফিরিয়ে আনতে) ---
st.markdown("""
    <style>
    .top-nav { background-color: #002b36; padding: 15px; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 20px; }
    .section-title { background: linear-gradient(90deg, #002b36 0%, #00425a 100%); color: #00ffd0; font-size: 14px; padding: 10px; border-left: 5px solid #00ffd0; border-radius: 5px; margin: 15px 0; }
    .idx-container { display: flex; justify-content: space-between; background: white; padding: 10px; border-radius: 5px; border: 1px solid #b0c4de; margin-bottom: 20px; }
    .idx-box { text-align: center; width: 16%; }
    </style>
""", unsafe_allow_html=True)

# --- ৫. টপ নেভিগেশন ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
terminal_title = "HARIDAS NSE TERMINAL" if market_mode == "🇮🇳 Indian Market (NSE)" else "HARIDAS CRYPTO TERMINAL"

st.markdown(f"""
    <div class='top-nav'>
        <div style='color:#00ffd0; font-weight:900; font-size:24px; text-align:center;'>📊 {terminal_title}</div>
        <div style='color:white; text-align:center;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div>
    </div>
""", unsafe_allow_html=True)

# --- ৬. মেইন টার্মিনাল লজিক ---
col1, col2, col3 = st.columns([1, 2.5, 1])

with col2:
    st.markdown("<div class='section-title'>📉 LIVE MARKET INDICES</div>", unsafe_allow_html=True)
    if market_mode == "₿ Crypto Market (24/7)":
        live_data = get_coindcx_live_prices()
        # BTC, ETH, SOL এর জন্য ইনডেক্স বক্স
        btc_p, btc_c = get_crypto_price_v2(live_data, "B-BTC_USDT")
        eth_p, eth_c = get_crypto_price_v2(live_data, "B-ETH_USDT")
        
        st.markdown(f"""
            <div class='idx-container'>
                <div class='idx-box'><b>BITCOIN</b><br><span style='font-size:18px;'>${btc_p:,.2f}</span><br><span style='color:green;'>{btc_c}%</span></div>
                <div class='idx-box'><b>ETHEREUM</b><br><span style='font-size:18px;'>${eth_p:,.2f}</span><br><span style='color:green;'>{eth_c}%</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("NSE Market Indices (yfinance থেকে লোড হচ্ছে...)")

# আপনার বাকি টেবিল এবং গ্রাফগুলো এখানে আগের মতো যোগ হবে।
