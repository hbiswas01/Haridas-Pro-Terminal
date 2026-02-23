import streamlit as st
import datetime
import pytz
import pandas as pd
import requests
import os
from streamlit_autorefresh import st_autorefresh

# --- ১. পেজ কনফিগারেশন ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

# ৫ সেকেন্ড পরপর অটো-রিফ্রেশ
st_autorefresh(interval=5000, key="datarefresh")

# --- ২. CoinDCX API ইঞ্জিন (নিরাপদ লজিক) ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def get_crypto_price_v2(data, market_pair):
    if not isinstance(data, list): return 0.0, 0.0
    try:
        ticker = next((item for item in data if isinstance(item, dict) and item.get("market") == market_pair), None)
        if ticker:
            return float(ticker.get('last_price', 0.0)), float(ticker.get('change_24h', 0.0))
    except:
        pass
    return 0.0, 0.0

# --- ৩. সাইডবার ও মার্কেট টগল ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=1)
    st.divider()
    page_selection = st.radio("Select Menu:", ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers"])

# --- ৪. সিএসএস ও ইন্টারফেস ডিজাইন ---
st.markdown("""
    <style>
    .top-nav { background-color: #002b36; padding: 15px; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 20px; text-align: center; }
    .section-title { background-color: #00425a; color: #00ffd0; font-size: 14px; padding: 10px; border-left: 5px solid #00ffd0; border-radius: 5px; margin-bottom: 10px; }
    .idx-container { display: flex; justify-content: space-around; background: white; padding: 15px; border-radius: 8px; border: 1px solid #b0c4de; }
    .idx-box { text-align: center; width: 30%; }
    </style>
""", unsafe_allow_html=True)

# --- ৫. টপ নেভিগেশন ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
terminal_title = "HARIDAS CRYPTO TERMINAL" if market_mode == "₿ Crypto Market (24/7)" else "HARIDAS NSE TERMINAL"

st.markdown(f"<div class='top-nav'><div style='color:#00ffd0; font-weight:900; font-size:24px;'>📊 {terminal_title}</div>"
            f"<div style='color:white;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div></div>", unsafe_allow_html=True)

# --- ৬. মেইন টার্মিনাল ডিসপ্লে ---
if page_selection == "📈 MAIN TERMINAL":
    st.markdown("<div class='section-title'>📉 LIVE MARKET INDICES</div>", unsafe_allow_html=True)
    
    if market_mode == "₿ Crypto Market (24/7)":
        # ডেটা ফেচ করা
        live_data = get_coindcx_live_prices()
        
        # কয়েন প্রাইস সেট করা
        btc_p, btc_c = get_crypto_price_v2(live_data, "B-BTC_USDT")
        eth_p, eth_c = get_crypto_price_v2(live_data, "B-ETH_USDT")
        sol_p, sol_c = get_crypto_price_v2(live_data, "B-SOL_USDT")
        
        # এইচটিএমএল ডিসপ্লে
        st.markdown(f"""
            <div class='idx-container'>
                <div class='idx-box'><b>BITCOIN</b><br><span style='font-size:20px;'>${btc_p:,.2f}</span><br><span style='color:{"green" if btc_c >= 0 else "red"};'>{btc_c}%</span></div>
                <div class='idx-box'><b>ETHEREUM</b><br><span style='font-size:20px;'>${eth_p:,.2f}</span><br><span style='color:{"green" if eth_c >= 0 else "red"};'>{eth_c}%</span></div>
                <div class='idx-box'><b>SOLANA</b><br><span style='font-size:20px;'>${sol_p:,.2f}</span><br><span style='color:{"green" if sol_c >= 0 else "red"};'>{sol_c}%</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("NSE ইক্যুইটি ডেটা বর্তমানে নিষ্ক্রিয়।")
