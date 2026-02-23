import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- CoinDCX API তথ্য (Streamlit Secrets থেকে নেওয়া) ---
# নিশ্চিত করুন যে আপনি Streamlit Cloud-এর Secrets সেকশনে এগুলো সেভ করেছেন
try:
    COINDCX_API_KEY = st.secrets["COINDCX_API_KEY"]
    COINDCX_SECRET = st.secrets["COINDCX_SECRET"]
except:
    st.error("🚨 API Keys not found in Streamlit Secrets!")

# --- CoinDCX রিয়েল-টাইম ডেটা ইঞ্জিন ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    """
    সরাসরি CoinDCX পাবলিক টিকার থেকে সব কয়েনের লাইভ প্রাইস নিয়ে আসে।
    এটি yfinance এর তুলনায় অনেক বেশি ফাস্ট।
    """
    url = "https://public.coindcx.com/market_data/ticker"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return data
    except Exception as e:
        return []

def get_crypto_price_v2(data, market_pair):
    """
    CoinDCX এর পেয়ার ফরম্যাট অনুযায়ী প্রাইস খুঁজে বের করে।
    উদাহরণ: 'B-BTC_USDT'
    """
    ticker = next((item for item in data if item["market"] == market_pair), None)
    if ticker:
        return float(ticker['last_price']), float(ticker.get('change_24h', 0.0))
    return 0.0, 0.0

# --- আপনার মেইন টার্মিনালের ইনডেক্স সেকশন আপডেট ---
# কোডের ভেতরে যেখানে Crypto Indices দেখানো হয়েছে, সেখানে নিচের লজিকটি বসান:

if market_mode != "🇮🇳 Indian Market (NSE)":
    live_crypto_data = get_coindcx_live_prices()
    
    # আপনার পছন্দের কয়েনগুলোর জন্য ডেটা নেওয়া
    btc_ltp, btc_chg = get_crypto_price_v2(live_crypto_data, "B-BTC_USDT")
    eth_ltp, eth_chg = get_crypto_price_v2(live_crypto_data, "B-ETH_USDT")
    sol_ltp, sol_chg = get_crypto_price_v2(live_crypto_data, "B-SOL_USDT")
    
    # ইন্ডেক্স বক্সে দেখানোর জন্য লিস্ট তৈরি
    indices = [
        ("BITCOIN", btc_ltp, (btc_ltp * btc_chg / 100) if btc_chg else 0, btc_chg),
        ("ETHEREUM", eth_ltp, (eth_ltp * eth_chg / 100) if eth_chg else 0, eth_chg),
        ("SOLANA", sol_ltp, (sol_ltp * sol_chg / 100) if sol_chg else 0, sol_chg)
    ]
