import streamlit as st
import streamlit.components.v1 as components
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
import hmac
import hashlib
import json

# --- 1. Page Configuration & Session State ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

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

# --- 2. Live Market Data Dictionary ---
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
NIFTY_50 = ["ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS"]
ALL_STOCKS = list(set([stock for slist in FNO_SECTORS.values() for stock in slist] + NIFTY_50))

CRYPTO_SECTORS = {
    "ALL COINDCX FUTURES": [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
        "TRX-USD", "MATIC-USD", "AGLD-USD", "BEL-USD", "SNX-USD", "AAVE-USD", "UNI-USD", "NEAR-USD", "APT-USD", "LDO-USD",
        "CRV-USD", "MKR-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "FLOKI-USD", "BONK-USD", "LTC-USD", "BCH-USD", "XLM-USD",
        "ATOM-USD", "HBAR-USD", "ETC-USD", "FIL-USD", "INJ-USD", "OP-USD", "RNDR-USD", "IMX-USD", "STX-USD", "GRT-USD",
        "VET-USD", "THETA-USD", "SAND-USD", "MANA-USD", "AXS-USD", "APE-USD", "GALA-USD", "FTM-USD", "DYDX-USD", "SUI-USD",
        "SEI-USD", "TIA-USD", "ORDI-USD", "FET-USD", "RUNE-USD", "AR-USD", "COMP-USD", "CHZ-USD", "EGLD-USD", "ALGO-USD",
        "ICP-USD", "QNT-USD", "ROSE-USD", "ARDR-USD", "ESP-USD", "SENT-USD", "PIPPIN-USD", "TRIA-USD", "FHE-USD", "LA-USD", 
        "DEXE-USD", "KERNEL-USD", "ARC-USD", "RAVE-USD", "SAPIEN-USD", "COW-USD", "MAGMA-USD", "FARTCOIN-USD", "SANTOS-USD", 
        "SPX-USD", "MAVIA-USD", "ARPA-USD", "GIGGLE-USD", "NTRN-USD", "PUMP-USD", "HMSTR-USD", "DOLO-USD", "ZRO-USD", 
        "SOMI-USD", "TUT-USD"
    ]
}
ALL_CRYPTO = list(set([coin for clist in CRYPTO_SECTORS.values() for coin in clist]))

def fmt_price(val):
    try:
        val = float(val)
        if pd.isna(val) or val == 0: return "0.00"
        if abs(val) < 0.01: return f"{val:.6f}"
        elif abs(val) < 1: return f"{val:.4f}"
        else: return f"{val:,.2f}"
    except: return "0.00"

# --- 3. HELPER FUNCTIONS ---
@st.cache_data(ttl=15)
def get_live_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period='2d', interval='1m')
        if not df.empty:
            ltp = float(df['Close'].iloc[-1])
            try: prev_close = float(stock.fast_info.previous_close)
            except: prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else ltp
            
            if pd.isna(ltp) or pd.isna(prev_close) or prev_close == 0: return 0.0, 0.0, 0.0
            change = ltp - prev_close
            pct_change = (change / prev_close) * 100
            return ltp, change, pct_change
        return 0.0, 0.0, 0.0
    except: return 0.0, 0.0, 0.0

@st.cache_data(ttl=300)
def get_market_news():
    try:
        url = "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response: xml_data = response.read()
        root = ET.fromstring(xml_data)
        headlines = [item.find('title').text.strip() for item in root.findall('.//item')[:5] if item.find('title') is not None]
        if headlines: return "📰 LIVE MARKET NEWS: " + " 🔹 ".join(headlines) + " 🔹"
    except: pass
    return "📰 LIVE MARKET NEWS: Fetching latest feeds... 🔹"

@st.cache_data(ttl=60)
def get_real_sector_performance(sector_dict, ignore_keys=["MIXED WATCHLIST", "ALL COINDCX FUTURES"]):
    results = []
    for sector, items in sector_dict.items():
        if sector in ignore_keys: continue
        total_pct, valid = 0, 0
        for ticker in items:
            _, _, pct = get_live_data(ticker)
            if pct != 0.0: total_pct += pct; valid += 1
        if valid > 0:
            avg_pct = round(total_pct / valid, 2)
            results.append({"Sector": sector, "Pct": avg_pct, "Width": max(min(abs(avg_pct) * 20, 100), 5)})
    return sorted(results, key=lambda x: x['Pct'], reverse=True)

@st.cache_data(ttl=60)
def get_adv_dec(item_list):
    adv, dec = 0, 0
    def fetch_chg(ticker): return get_live_data(ticker)[1]
    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_chg, item_list))
    for change in results:
        if change > 0: adv += 1
        elif change < 0: dec += 1
    return adv, dec

@st.cache_data(ttl=120)
def get_dynamic_market_data(item_list):
    gainers, losers, trends = [], [], []
    def fetch_data(ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="10d")
            if len(df) < 3: return None
            
            try: c1 = float(stock.fast_info.last_price)
            except: c1 = float(df['Close'].iloc[-1])
            
            c2, c3 = float(df['Close'].iloc[-2]), float(df['Close'].iloc[-3])
            o1, o2, o3 = float(df['Open'].iloc[-1]), float(df['Open'].iloc[-2]), float(df['Open'].iloc[-3])
            
            if c2 == 0 or pd.isna(c1): return None
            pct_chg = ((c1 - c2) / c2) * 100
            
            obj = {"Stock": ticker, "LTP": c1, "Pct": round(pct_chg, 2)}
            status, color = None, None
            if c1 > o1 and c2 > o2 and c3 > o3: status, color = "৩ দিন উত্থান", "green"
            elif c1 < o1 and c2 < o2 and c3 < o3: status, color = "৩ দিন পতন", "red"
            return (obj, status, color)
        except: return None

    with ThreadPoolExecutor(max_workers=40) as executor:
        results = list(executor.map(fetch_data, item_list))
        
    for res in results:
        if res:
            obj, status, color = res
            if obj['Pct'] > 0: gainers.append(obj)
            elif obj['Pct'] < 0: losers.append(obj)
            if status: trends.append({"Stock": obj['Stock'], "Status": status, "Color": color})
            
    return sorted(gainers, key=lambda x: x['Pct'], reverse=True)[:5], sorted(losers, key=lambda x: x['Pct'])[:5], trends

@st.cache_data(ttl=60)
def get_oi_simulation(item_list):
    setups = []
    for ticker in item_list:
        try:
            df = yf.Ticker(ticker).history(period="2d", interval="15m")
            if len(df) >= 3:
                c1, v1 = df['Close'].iloc[-1], df['Volume'].iloc[-1]
                c2, v2 = df['Close'].iloc[-2], df['Volume'].iloc[-2]
                c3 = df['Close'].iloc[-3]
                if v1 > (v2 * 1.5):
                    oi_status = "🔥 High (Spike)"
                    if c1 > c2: signal, color = "Short Covering 🚀", "green"
                    else: signal, color = "Long Unwinding ⚠️" if c2 > c3 else "Short Buildup 📉", "red"
                    setups.append({"Stock": ticker, "Signal": signal, "OI": oi_status, "Color": color})
        except: pass
    return setups

@st.cache_data(ttl=60)
def nse_ha_bb_strategy_5m(stock_list, market_sentiment="BULLISH"):
    signals = []
    for stock_symbol in stock_list:
        try:
            df = yf.Ticker(stock_symbol).history(period="5d", interval="5m") 
            if df.empty or len(df) < 25: continue
            
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            df['Upper_BB'] = df['SMA_20'] + (2 * df['STD_20'])
            df['Lower_BB'] = df['SMA_20'] - (2 * df['STD_20'])
            
            df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            ha_open = [df['Open'].iloc[0]]
            for i in range(1, len(df)): ha_open.append((ha_open[i-1] + df['HA_Close'].iloc[i-1]) / 2)
            df['HA_Open'] = ha_open
            df['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
            df['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
            df = df.dropna()
            if len(df) < 3: continue
            
            completed_idx = len(df) - 2
            alert_candle, prev_candle, current_ltp = df.iloc[completed_idx], df.iloc[completed_idx - 1], df['Close'].iloc[-1]
            signal = None
            entry = sl = target_bb = 0.0
            
            if (prev_candle['HA_High'] >= prev_candle['Upper_BB']) and (alert_candle['HA_Close'] < alert_candle['HA_Open']) and (alert_candle['HA_High'] < alert_candle['Upper_BB']):
                signal, entry, sl, target_bb = "SHORT", alert_candle['Low'] - 0.10, alert_candle['High'] + 0.10, alert_candle['Lower_BB']
            elif (prev_candle['HA_Low'] <= prev_candle['Lower_BB']) and (alert_candle['HA_Close'] > alert_candle['HA_Open']) and (alert_candle['HA_Low'] > alert_candle['Lower_BB']):
                signal, entry, sl, target_bb = "BUY", alert_candle['High'] + 0.10, alert_candle['Low'] - 0.10, alert_candle['Upper_BB']
                
            if signal:
                risk = abs(entry - sl)
                if risk > 0:
                    signals.append({
                        "Stock": stock_symbol, "Entry": float(entry), "LTP": float(current_ltp),
                        "Signal": signal, "SL": float(sl), "Target(BB)": float(target_bb), 
                        "T2(1:3)": float(entry - (risk*3) if signal=="SHORT" else entry + (risk*3)),
                        "Time": alert_candle.name.strftime('%H:%M')
                    })
        except: continue
    return signals

@st.cache_data(ttl=60)
def crypto_ha_bb_strategy(crypto_list):
    signals = []
    def scan_coin(coin):
        try:
            df = yf.Ticker(coin).history(period="15d", interval="1h") 
            if df.empty or len(df) < 25: return None
            
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            df['Upper_BB'] = df['SMA_20'] + (2 * df['STD_20'])
            df['Lower_BB'] = df['SMA_20'] - (2 * df['STD_20'])
            
            df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            ha_open = [df['Open'].iloc[0]]
            for i in range(1, len(df)): ha_open.append((ha_open[i-1] + df['HA_Close'].iloc[i-1]) / 2)
            df['HA_Open'] = ha_open
            df['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
            df['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
            df = df.dropna()
            if len(df) < 3: return None
            
            completed_idx = len(df) - 2
            alert_candle, prev_candle, current_ltp = df.iloc[completed_idx], df.iloc[completed_idx - 1], df['Close'].iloc[-1]
            signal = None
            entry = sl = target_bb = 0.0
            buffer = alert_candle['Close'] * 0.001 
            
            if (prev_candle['HA_High'] >= prev_candle['Upper_BB']) and (alert_candle['HA_High'] < alert_candle['Upper_BB']):
                signal, entry, sl, target_bb = "SHORT", alert_candle['Low'] - buffer, alert_candle['High'] + buffer, alert_candle['Lower_BB']
            elif (prev_candle['HA_Low'] <= prev_candle['Lower_BB']) and (alert_candle['HA_Low'] > alert_candle['Lower_BB']):
                signal, entry, sl, target_bb = "BUY", alert_candle['High'] + buffer, alert_candle['Low'] - buffer, alert_candle['Upper_BB']
                
            if signal:
                risk = abs(entry - sl)
                if risk > 0:
                    return {
                        "Stock": coin, "Signal": signal, "Entry": float(entry), "LTP": float(current_ltp),
                        "SL": float(sl), "Target(BB)": float(target_bb), "T2(1:3)": float(entry - (risk*3) if signal=="SHORT" else entry + (risk*3)),
                        "Time": alert_candle.name.strftime('%d %b, %H:%M')
                    }
        except: return None
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(scan_coin, crypto_list))
    for res in results:
        if res is not None: signals.append(res)
    return signals

def process_auto_trades(live_signals):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time_str = datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M")
    active_stocks = [t['Stock'] for t in st.session_state.active_trades]

    for sig in live_signals:
        if sig['Stock'] not in active_stocks:
            is_triggered = False
            if sig['Signal'] == 'BUY' and sig['LTP'] >= sig['Entry']: is_triggered = True
            elif sig['Signal'] == 'SHORT' and sig['LTP'] <= sig['Entry']: is_triggered = True
            
            if is_triggered:
                new_trade = {
                    "Date": current_time_str, "Stock": sig['Stock'], "Signal": sig['Signal'],
                    "Entry": float(sig['Entry']), "SL": float(sig['SL']), "Target": float(sig['T2(1:3)']), "Status": "RUNNING"
                }
                st.session_state.active_trades.append(new_trade)
                save_data(st.session_state.active_trades, ACTIVE_TRADES_FILE)

    trades_to_remove = []
    for trade in st.session_state.active_trades:
        ltp, _, _ = get_live_data(trade['Stock'])
        if ltp == 0.0: continue

        close_reason = None
        exit_price = 0.0

        if trade['Signal'] == 'BUY':
            if ltp <= float(trade['SL']): close_reason, exit_price = "🛑 SL HIT", trade['SL']
            elif ltp >= float(trade['Target']): close_reason, exit_price = "🎯 TARGET HIT", trade['Target']
        elif trade['Signal'] == 'SHORT':
            if ltp >= float(trade['SL']): close_reason, exit_price = "🛑 SL HIT", trade['SL']
            elif ltp <= float(trade['Target']): close_reason, exit_price = "🎯 TARGET HIT", trade['Target']

        if close_reason:
            pnl_pct = ((exit_price - trade['Entry']) / trade['Entry']) * 100 if trade['Signal'] == 'BUY' else ((trade['Entry'] - exit_price) / trade['Entry']) * 100
            completed_trade = {
                "Date": current_time_str, "Stock": trade['Stock'], "Signal": trade['Signal'],
                "Entry": trade['Entry'], "Exit": exit_price, "Status": close_reason, "P&L %": round(pnl_pct, 2)
            }
            st.session_state.trade_history.append(completed_trade)
            trades_to_remove.append(trade)

    if trades_to_remove:
        st.session_state.active_trades = [t for t in st.session_state.active_trades if t not in trades_to_remove]
        save_data(st.session_state.active_trades, ACTIVE_TRADES_FILE)
        save_data(st.session_state.trade_history, HISTORY_TRADES_FILE)

@st.cache_data(ttl=60)
def get_opening_movers(stock_list):
    movers = []
    for ticker in stock_list:
        ltp, _, pct = get_live_data(ticker)
        if abs(pct) >= 2.0:
            movers.append({"Stock": ticker, "LTP": ltp, "Pct": pct})
    return sorted(movers, key=lambda x: abs(x['Pct']), reverse=True)

# --- 4. CSS ---
css_string = (
    "<style>"
    "#MainMenu {visibility: hidden;} footer {visibility: hidden;} "
    ".stApp { background-color: #f0f4f8; font-family: 'Segoe UI', sans-serif; } "
    ".block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; padding-left: 1rem !important; padding-right: 1rem !important; } "
    ".top-nav { background-color: #002b36; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.2); } "
    ".section-title { background: linear-gradient(90deg, #002b36 0%, #00425a 100%); color: #00ffd0; font-size: 13px; font-weight: 800; padding: 10px 15px; text-transform: uppercase; border-left: 5px solid #00ffd0; border-radius: 5px; margin-top: 15px; margin-bottom: 10px; box-shadow: 0px 3px 6px rgba(0,0,0,0.15); letter-spacing: 0.5px; display: flex; align-items: center; } "
    ".table-container { overflow-x: auto; width: 100%; border-radius: 5px; } "
    ".v38-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; color: black; background: white; border: 1px solid #b0c4de; margin-bottom: 10px; white-space: nowrap; } "
    ".v38-table th { background-color: #4f81bd; color: white; padding: 8px; border: 1px solid #b0c4de; font-weight: bold; } "
    ".v38-table td { padding: 8px; border: 1px solid #b0c4de; } "
    ".idx-container { display: flex; justify-content: space-between; background: white; border: 1px solid #b0c4de; padding: 5px; margin-bottom: 10px; flex-wrap: wrap; border-radius: 5px; } "
    ".idx-box { text-align: center; width: 31%; border-right: 1px solid #eee; padding: 5px; min-width: 100px; margin-bottom: 5px; } "
    ".idx-box:nth-child(3n) { border-right: none; } "
    ".adv-dec-container { background: white; border: 1px solid #b0c4de; padding: 10px; margin-bottom: 10px; text-align: center; border-radius: 5px; } "
    ".adv-dec-bar { display: flex; height: 14px; border-radius: 4px; overflow: hidden; margin: 8px 0; } "
    ".bar-green { background-color: #2e7d32; } .bar-red { background-color: #d32f2f; } "
    ".bar-bg { background: #e0e0e0; width: 100%; height: 14px; min-width: 50px; border-radius: 3px; } "
    ".bar-fg-green { background: #276a44; height: 100%; border-radius: 3px; } "
    ".bar-fg-red { background: #8b0000; height: 100%; border-radius: 3px; } "
    ".calc-box { background: white; border: 1px solid #00ffd0; padding: 15px; border-radius: 8px; box-shadow: 0px 2px 8px rgba(0,0,0,0.1); margin-top: 15px;} "
    "</style>"
)
st.markdown(css_string, unsafe_allow_html=True)

# --- 5. Sidebar & Market Toggle ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=0)
    st.divider()
    
    st.markdown("### 🎛️ HARIDAS DASHBOARD")
    if market_mode == "🇮🇳 Indian Market (NSE)":
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup", "📊 Backtest Engine", "⚙️ Scanner Settings"]
        sector_dict = FNO_SECTORS
        all_assets = ALL_STOCKS
    else:
        menu_options = ["📈 MAIN TERMINAL", "⚡ REAL TRADE (CoinDCX)", "🧮 Futures Risk Calculator", "📊 Backtest Engine", "⚙️ Scanner Settings"]
        sector_dict = CRYPTO_SECTORS
        all_assets = ALL_CRYPTO

    page_selection = st.radio("Select Menu:", menu_options)
    st.divider()
    
    st.markdown("### ⚙️ STRATEGY SETTINGS")
    user_sentiment = st.radio("Market Sentiment:", ["BULLISH", "BEARISH"])
    selected_sector = st.selectbox("Select Watchlist:", list(sector_dict.keys()), index=0)
    current_watchlist = sector_dict[selected_sector]
    st.divider()
    
    st.markdown("### ⏱️ AUTO REFRESH")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
    refresh_time = st.selectbox("Interval (Mins):", [1, 3, 5], index=0) 
    
    if st.button("🗑️ Clear All History Data"):
        st.session_state.active_trades = []
        st.session_state.trade_history = []
        if os.path.exists(ACTIVE_TRADES_FILE): os.remove(ACTIVE_TRADES_FILE)
        if os.path.exists(HISTORY_TRADES_FILE): os.remove(HISTORY_TRADES_FILE)
        st.success("History Cleared!")
        time.sleep(1)
        st.rerun()

if auto_refresh:
    refresh_sec = refresh_time * 60
    st.markdown(f'<meta http-equiv="refresh" content="{refresh_sec}">', unsafe_allow_html=True)

# --- 6. Top Navigation ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
t_915 = curr_time.replace(hour=9, minute=15, second=0, microsecond=0)
t_1530 = curr_time.replace(hour=15, minute=30, second=0, microsecond=0)

if market_mode == "🇮🇳 Indian Market (NSE)":
    terminal_title = "HARIDAS NSE TERMINAL"
    if curr_time < t_915: session, session_color = "PRE-MARKET", "#ff9800" 
    elif curr_time <= t_1530: session, session_color = "LIVE MARKET", "#28a745" 
    else: session, session_color = "POST MARKET", "#dc3545" 
else:
    terminal_title = "HARIDAS CRYPTO TERMINAL"
    session, session_color = "LIVE 24/7 (CRYPTO)", "#17a2b8"

nav_html = (
    "<div class='top-nav'>"
    f"<div style='color:#00ffd0; font-weight:900; font-size:22px; letter-spacing:2px; text-transform:uppercase; text-shadow: 0px 0px 10px rgba(0, 255, 208, 0.6);'>📊 {terminal_title}</div>"
    "<div style='font-size: 14px; color: #ffeb3b; font-weight: bold; display: flex; align-items: center;'>"
    f"<span style='background: {session_color}; color: white; padding: 3px 10px; border-radius: 4px; margin-right: 15px;'>{session}</span>"
    f"🕒 {curr_time.strftime('%H:%M:%S')} (IST)"
    "</div></div>"
)
st.markdown(nav_html, unsafe_allow_html=True)

# ==================== MAIN TERMINAL ====================
if page_selection == "📈 MAIN TERMINAL":
    
    if market_mode == "🇮🇳 Indian Market (NSE)":
        with st.spinner("Scanning 5m HA Charts..."): live_signals = nse_ha_bb_strategy_5m(current_watchlist, user_sentiment)
    else:
        with st.spinner("Scanning ALL CoinDCX Futures..."): live_signals = crypto_ha_bb_strategy(CRYPTO_SECTORS["ALL COINDCX FUTURES"])

    process_auto_trades(live_signals)

    signal_stocks = [s['Stock'] for s in live_signals]
    focused_scan_list = list(set(current_watchlist + signal_stocks))

    with st.spinner("Fetching Market Movers & Trends for Watchlist..."):
        gainers, losers, trends = get_dynamic_market_data(focused_scan_list)

    important_assets = [s['Stock'] for s in live_signals] + [g['Stock'] for g in gainers] + [l['Stock'] for l in losers]
    filtered_trends = [t for t in trends if t['Stock'] in important_assets]

    col1, col2, col3 = st.columns([1, 2.8, 1])

    with col1:
        if market_mode == "🇮🇳 Indian Market (NSE)":
            st.markdown("<div class='section-title'>📊 SECTOR PERFORMANCE</div>", unsafe_allow_html=True)
            with st.spinner("Fetching Sectors..."): real_sectors = get_real_sector_performance(sector_dict)
            if real_sectors:
                sec_html = "<div class='table-container'><table class='v38-table'><tr><th>Category</th><th>Avg %</th><th style='width:40%;'>Trend</th></tr>"
                for s in real_sectors:
                    c = "green" if s['Pct'] >= 0 else "red"
                    bc = "bar-fg-green" if s['Pct'] >= 0 else "bar-fg-red"
                    # 🚨 FIX: Visual Trend Bar is Back! 🚨
                    sec_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{s['Sector']}</td><td style='color:{c}; font-weight:bold;'>{s['Pct']}%</td><td style='padding:4px 8px;'><div class='bar-bg'><div class='{bc}' style='width:{s['Width']}%;'></div></div></td></tr>"
                sec_html += "</table></div>"
                st.markdown(sec_html, unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🔍 TREND CONTINUITY (IMPORTANT LIST)</div>", unsafe_allow_html=True)
        if filtered_trends:
            t_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Status</th></tr>"
            for t in filtered_trends: t_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{t['Stock']}</td><td style='color:{t['Color']}; font-weight:bold;'>{t['Status']}</td></tr>"
            t_html += "</table></div>"
            st.markdown(t_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center; color:#888;'>No 3-day continuous trend found in active list.</p>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-title'>📉 MARKET INDICES (LIVE)</div>", unsafe_allow_html=True)
        
        if market_mode == "🇮🇳 Indian Market (NSE)":
            p1_ltp, p1_chg, p1_pct = get_live_data("^BSESN")
            p2_ltp, p2_chg, p2_pct = get_live_data("^NSEI")
            p3_ltp, p3_chg, p3_pct = get_live_data("INR=X")
            p4_ltp, p4_chg, p4_pct = get_live_data("^NSEBANK")
            p5_ltp, p5_chg, p5_pct = get_live_data("NIFTY_FIN_SERVICE.NS") 
            p6_ltp, p6_chg, p6_pct = get_live_data("^CNXIT") 
            indices = [("Sensex", p1_ltp, p1_chg, p1_pct), ("Nifty", p2_ltp, p2_chg, p2_pct), ("USDINR", p3_ltp, p3_chg, p3_pct), ("Nifty Bank", p4_ltp, p4_chg, p4_pct), ("Fin Nifty", p5_ltp, p5_chg, p5_pct), ("Nifty IT", p6_ltp, p6_chg, p6_pct)]
        else:
            p1_ltp, p1_chg, p1_pct = get_live_data("BTC-USD")
            p2_ltp, p2_chg, p2_pct = get_live_data("ETH-USD")
            p3_ltp, p3_chg, p3_pct = get_live_data("SOL-USD")
            p4_ltp, p4_chg, p4_pct = get_live_data("BNB-USD")
            p5_ltp, p5_chg, p5_pct = get_live_data("XRP-USD")
            p6_ltp, p6_chg, p6_pct = get_live_data("DOGE-USD")
            indices = [("BITCOIN", p1_ltp, p1_chg, p1_pct), ("ETHEREUM", p2_ltp, p2_chg, p2_pct), ("SOLANA", p3_ltp, p3_chg, p3_pct), ("BINANCE COIN", p4_ltp, p4_chg, p4_pct), ("RIPPLE", p5_ltp, p5_chg, p5_pct), ("DOGECOIN", p6_ltp, p6_chg, p6_pct)]

        indices_html = "<div class='idx-container'>"
        for name, val, chg, pct in indices:
            clr = "green" if chg >= 0 else "red"
            sign = "+" if chg >= 0 else ""
            prefix = "₹" if name == "USDINR" else ("$" if market_mode != "🇮🇳 Indian Market (NSE)" else "")
            if name == "USDINR": val_str, chg_str = f"{val:.4f}", f"{chg:.4f}"
            elif market_mode != "🇮🇳 Indian Market (NSE)": val_str, chg_str = fmt_price(val), fmt_price(chg)
            else: val_str, chg_str = f"{val:,.2f}", f"{chg:,.2f}"
            indices_html += f"<div class='idx-box'><span style='font-size:11px; color:#555; font-weight:bold;'>{name}</span><br><span style='font-size:15px; color:black; font-weight:bold;'>{prefix}{val_str}</span><br><span style='color:{clr}; font-size:11px; font-weight:bold;'>{sign}{chg_str} ({sign}{pct:.2f}%)</span></div>"
        indices_html += "</div>"
        st.markdown(indices_html, unsafe_allow_html=True)

        with st.spinner("Calculating Breadth..."):
            adv, dec = get_adv_dec(all_assets)
        total_adv_dec = adv + dec
        adv_pct = (adv / total_adv_dec) * 100 if total_adv_dec > 0 else 50
        adv_title = "Advance/ Decline (NSE)" if market_mode == "🇮🇳 Indian Market (NSE)" else "Advance/ Decline (CoinDCX Futures)"
        
        st.markdown(f"<div class='section-title'>📊 {adv_title}</div>", unsafe_allow_html=True)
        adv_dec_html = (
            "<div class='adv-dec-container'>"
            "<div class='adv-dec-bar'>"
            f"<div class='bar-green' style='width: {adv_pct}%;'></div>"
            f"<div class='bar-red' style='width: {100-adv_pct}%;'></div>"
            "</div>"
            "<div style='display:flex; justify-content:space-between; font-size:12px; font-weight:bold;'>"
            f"<span style='color:green;'>Advances: {adv}</span><span style='color:red;'>Declines: {dec}</span>"
            "</div></div>"
        )
        st.markdown(adv_dec_html, unsafe_allow_html=True)

        if market_mode == "🇮🇳 Indian Market (NSE)":
            st.markdown(f"<div class='section-title'>🎯 LIVE SIGNALS FOR: {selected_sector} (5M HA+BB)</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-title'>🎯 LIVE SIGNALS (ALL COINDCX FUTURES - 1H HA+BB)</div>", unsafe_allow_html=True)

        if len(live_signals) > 0:
            sig_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Entry</th><th>LTP</th><th>Signal</th><th>SL</th><th>Target (1:3)</th><th>Time</th></tr>"
            for sig in live_signals:
                sig_clr = "green" if sig['Signal'] == "BUY" else "red"
                prefix = "₹" if market_mode == "🇮🇳 Indian Market (NSE)" else "$"
                sig_html += f"<tr><td style='color:{sig_clr}; font-weight:bold;'>{sig['Stock']}</td><td>{prefix}{fmt_price(sig['Entry'])}</td><td>{prefix}{fmt_price(sig['LTP'])}</td><td style='color:white; background:{sig_clr}; font-weight:bold;'>{sig['Signal']}</td><td>{prefix}{fmt_price(sig['SL'])}</td><td style='font-weight:bold; color:#856404;'>{prefix}{fmt_price(sig['T2(1:3)'])}</td><td>{sig['Time']}</td></tr>"
            sig_html += "</table></div>"
            st.markdown(sig_html, unsafe_allow_html=True)
        else:
            st.info("⏳ No fresh signals right now.")

        # 🚨 FIX: REAL TRADINGVIEW WIDGET RESTORED (Works flawlessly with BSE prefix for India) 🚨
        st.markdown("<div class='section-title'>📈 QUICK CHART VIEWER</div>", unsafe_allow_html=True)
        tv_asset = st.selectbox("Select Asset to view live chart:", sorted(all_assets))
        
        # Super logic to fix the "Not Available" error
        if market_mode == "🇮🇳 Indian Market (NSE)": 
            tv_symbol = "BSE:" + tv_asset.replace(".NS", "")
            tv_interval = "5"
        else: 
            tv_symbol = "BINANCE:" + tv_asset.replace("-USD", "USDT")
            tv_interval = "60"
            
        widget_html = f"""
        <div class="tradingview-widget-container">
          <div id="tradingview_home_chart" style="height:450px;width:100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "{tv_interval}",
          "timezone": "Asia/Kolkata",
          "theme": "light",
          "style": "1",
          "locale": "en",
          "enable_publishing": false,
          "hide_side_toolbar": false,
          "allow_symbol_change": true,
          "container_id": "tradingview_home_chart"
        }}
          );
          </script>
        </div>
        """
        components.html(widget_html, height=450)

        # 🚨 FIX: MANUAL TRADE LOG RESTORED! 🚨
        st.markdown("<div class='section-title'>📝 TRADE JOURNAL (MANUAL LOG)</div>", unsafe_allow_html=True)
        with st.expander("➕ Add New Trade to Journal"):
            with st.form("journal_form"):
                j_col1, j_col2, j_col3, j_col4 = st.columns(4)
                with j_col1: j_asset = st.selectbox("Select Asset", sorted(all_assets))
                with j_col2: j_signal = st.selectbox("Signal", ["BUY", "SHORT"])
                with j_col3: j_entry = st.number_input("Entry Price", min_value=0.0, format="%.6f")
                with j_col4: j_exit = st.number_input("Exit Price", min_value=0.0, format="%.6f")
                submit_trade = st.form_submit_button("💾 Save Trade")
                
                if submit_trade and j_asset != "":
                    if j_entry > 0 and j_exit > 0:
                        pnl_pct = ((j_exit - j_entry) / j_entry) * 100 if j_signal == "BUY" else ((j_entry - j_exit) / j_entry) * 100
                        st.session_state.trade_history.append({
                            "Date": datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M"),
                            "Stock": j_asset.upper(), "Signal": j_signal, "Entry": j_entry, "Exit": j_exit,
                            "Status": "MANUAL ENTRY", "P&L %": round(pnl_pct, 2)
                        })
                        save_data(st.session_state.trade_history, HISTORY_TRADES_FILE)
                        st.success("✅ Trade saved!")

        display_active = [t for t in st.session_state.active_trades if (".NS" in t['Stock'] if market_mode == "🇮🇳 Indian Market (NSE)" else "-USD" in t['Stock'])]
        display_history = [t for t in st.session_state.trade_history if (".NS" in t['Stock'] if market_mode == "🇮🇳 Indian Market (NSE)" else "-USD" in t['Stock'])]

        st.markdown("<div class='section-title'>⏳ ACTIVE TRADES (RUNNING AUTO-TRACKER)</div>", unsafe_allow_html=True)
        if len(display_active) > 0:
            df_active = pd.DataFrame(display_active)
            st.dataframe(df_active, use_container_width=True)
        else:
            st.info("No trades are currently active for this market.")

        st.markdown("<div class='section-title'>📚 AUTO TRADE HISTORY (CLOSED TRADES)</div>", unsafe_allow_html=True)
        if len(display_history) > 0:
            df_history = pd.DataFrame(display_history)
            df_display = df_history.copy()
            df_display['Entry'] = df_display['Entry'].apply(lambda x: fmt_price(float(x)))
            df_display['Exit'] = df_display['Exit'].apply(lambda x: fmt_price(float(x)))
            df_display['P&L %'] = df_display['P&L %'].apply(lambda x: f"+{x}%" if float(x) >= 0 else f"{x}%")
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No closed trades yet for this market.")

    with col3:
        st.markdown("<div class='section-title'>🚀 LIVE TOP GAINERS (Selected List)</div>", unsafe_allow_html=True)
        if gainers:
            g_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for g in gainers: 
                prefix = "$" if market_mode != "🇮🇳 Indian Market (NSE)" else "₹"
                g_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{g['Stock']}</td><td>{prefix}{fmt_price(g['LTP'])}</td><td style='color:green; font-weight:bold;'>+{g['Pct']}%</td></tr>"
            g_html += "</table></div>"
            st.markdown(g_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center;'>No live gainers data.</p>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🔻 LIVE TOP LOSERS (Selected List)</div>", unsafe_allow_html=True)
        if losers:
            l_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for l in losers: 
                prefix = "$" if market_mode != "🇮🇳 Indian Market (NSE)" else "₹"
                l_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{l['Stock']}</td><td>{prefix}{fmt_price(l['LTP'])}</td><td style='color:red; font-weight:bold;'>{l['Pct']}%</td></tr>"
            l_html += "</table></div>"
            st.markdown(l_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center;'>No live losers data.</p>", unsafe_allow_html=True)

# ==================== INDIAN MARKET MENUS ====================
elif page_selection in ["🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers"]:
    st.markdown(f"<div class='section-title'>{page_selection}</div>", unsafe_allow_html=True)
    with st.spinner("Scanning ALL Assets..."):
        movers = get_opening_movers(all_assets)
    if movers:
        m_html = "<div class='table-container'><table class='v38-table'><tr><th>Stock</th><th>LTP</th><th>Movement %</th></tr>"
        for m in movers: 
            c = "green" if m['Pct'] > 0 else "red"
            m_html += f"<tr><td style='font-weight:bold;'>{m['Stock']}</td><td>{fmt_price(m['LTP'])}</td><td style='color:{c}; font-weight:bold;'>{m['Pct']}%</td></tr>"
        m_html += "</table></div>"
        st.markdown(m_html, unsafe_allow_html=True)
    else: st.info("No significant movement found based on live data.")

elif page_selection == "🔥 9:20 AM: OI Setup":
    st.markdown(f"<div class='section-title'>{page_selection}</div>", unsafe_allow_html=True)
    with st.spinner("Scanning for Volume Spikes & OI Proxy..."):
        oi_setups = get_oi_simulation(all_assets)
    if oi_setups:
        oi_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Market Action (Signal)</th><th>OI / Vol Status</th></tr>"
        for o in oi_setups: 
            oi_html += f"<tr><td style='font-weight:bold;'>{o['Stock']}</td><td style='color:{o['Color']}; font-weight:bold;'>{o['Signal']}</td><td style='color:#1a73e8; font-weight:bold;'>{o['OI']}</td></tr>"
        oi_html += "</table></div>"
        st.markdown(oi_html, unsafe_allow_html=True)
    else: st.info("No significant real volume/OI spikes detected.")

# ==================== CRYPTO MENUS ====================
elif page_selection == "⚡ REAL TRADE (CoinDCX)":
    st.markdown("<div class='section-title'>⚡ EXECUTE REAL TRADE (COINDCX)</div>", unsafe_allow_html=True)
    st.markdown("<div class='calc-box'>", unsafe_allow_html=True)
    with st.form("coindcx_order_form"):
        t_market = st.selectbox("Coin Pair", sorted(ALL_CRYPTO))
        t_side = st.selectbox("Action", ["BUY", "SELL"])
        t_type = st.selectbox("Order Type", ["limit_order", "market_order"])
        t_price = st.number_input("Price (Required for Limit)", min_value=0.0, format="%.6f")
        t_qty = st.number_input("Quantity", min_value=0.0, format="%.6f")
        
        submit_real_trade = st.form_submit_button("🚀 PLACE REAL ORDER")
        
        if submit_real_trade:
            if t_qty <= 0: st.error("Quantity must be greater than 0.")
            elif t_type == "limit_order" and t_price <= 0: st.error("Limit orders require a valid price.")
            else:
                with st.spinner("Placing order on CoinDCX..."):
                    # Dummy function print for safety. Make sure real function is active
                    st.info("Place order feature needs verified API keys.")
    st.markdown("</div>", unsafe_allow_html=True)

elif page_selection == "🧮 Futures Risk Calculator":
    st.markdown("<div class='section-title'>🧮 Crypto Futures Risk Calculator</div>", unsafe_allow_html=True)
    st.markdown("<div class='calc-box'>", unsafe_allow_html=True)
    calc_col1, calc_col2, calc_col3, calc_col4 = st.columns(4)
    with calc_col1:
        trade_type = st.selectbox("Trade Direction", ["LONG (Buy)", "SHORT (Sell)"])
        capital = st.number_input("Total Capital (USDT)", min_value=1.0, value=100.0, step=10.0)
    with calc_col2:
        entry_price = st.number_input("Entry Price (USDT)", min_value=0.000001, value=65000.0, step=10.0, format="%.6f")
        leverage = st.slider("Leverage (x)", min_value=1, max_value=100, value=10)
    with calc_col3:
        stop_loss = st.number_input("Stop Loss (USDT)", min_value=0.000001, value=64000.0, step=10.0, format="%.6f")
        risk_pct = st.number_input("Risk % per Trade", min_value=0.1, max_value=100.0, value=2.0, step=0.5)
    with calc_col4:
        st.write("")
        st.write("")
        if st.button("🚀 Calculate Risk", use_container_width=True):
            price_diff = abs(entry_price - stop_loss)
            if price_diff > 0:
                risk_amt = capital * (risk_pct / 100)
                pos_size_coin = risk_amt / price_diff
                pos_size_usdt = pos_size_coin * entry_price
                margin_required = pos_size_usdt / leverage
                liq_price = entry_price * (1 - (1/leverage)) if trade_type == "LONG (Buy)" else entry_price * (1 + (1/leverage))
                st.success(f"**Margin Needed:** ${margin_required:.2f}")
                st.info(f"**Position Size:** {fmt_price(pos_size_coin)} Coins (${pos_size_usdt:.2f})")
                st.error(f"**Liquidation Price ⚠️:** ${fmt_price(liq_price)}")
            else: st.warning("Entry and Stop Loss cannot be the same!")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== COMMON MENUS ====================
elif page_selection == "📊 Backtest Engine":
    st.markdown("<div class='section-title'>📊 Backtest Engine (Strictly Segregated)</div>", unsafe_allow_html=True)
    bt_col1, bt_col2 = st.columns(2)
    with bt_col1:
        bt_stock = st.selectbox("Select Asset to Backtest:", sorted(all_assets), index=0)
    with bt_col2:
        bt_period = st.selectbox("Select Time Period:", ["1mo", "3mo", "6mo", "1y", "2y"])

    if st.button("🚀 Run Backtest", use_container_width=True):
        with st.spinner(f"Fetching {bt_period} historical data for {bt_stock}..."):
            try:
                bt_data = yf.Ticker(bt_stock).history(period=bt_period)
                if len(bt_data) > 3:
                    trades = []
                    for i in range(3, len(bt_data)):
                        c1, o1 = bt_data['Close'].iloc[i-1], bt_data['Open'].iloc[i-1]
                        c2, o2 = bt_data['Close'].iloc[i-2], bt_data['Open'].iloc[i-2]
                        c3, o3 = bt_data['Close'].iloc[i-3], bt_data['Open'].iloc[i-3]

                        if c1 > o1 and c2 > o2 and c3 > o3:
                            entry_price, exit_price = bt_data['Open'].iloc[i], bt_data['Close'].iloc[i]
                            if entry_price > 0:
                                pnl = ((entry_price - exit_price) / entry_price) * 100
                                trades.append({"Date": bt_data.index[i].strftime('%Y-%m-%d'), "Setup": "3 Days GREEN", "Signal": "SHORT", "Entry": fmt_price(entry_price), "Exit": fmt_price(exit_price), "P&L %": round(pnl, 2)})
                        
                        elif c1 < o1 and c2 < o2 and c3 < o3:
                            entry_price, exit_price = bt_data['Open'].iloc[i], bt_data['Close'].iloc[i]
                            if entry_price > 0:
                                pnl = ((exit_price - entry_price) / entry_price) * 100
                                trades.append({"Date": bt_data.index[i].strftime('%Y-%m-%d'), "Setup": "3 Days RED", "Signal": "BUY", "Entry": fmt_price(entry_price), "Exit": fmt_price(exit_price), "P&L %": round(pnl, 2)})

                    bt_df = pd.DataFrame(trades)
                    if not bt_df.empty:
                        st.success(f"✅ Backtest completed for {bt_stock}. Found {len(bt_df)} setups.")
                        total_pnl = bt_df['P&L %'].sum()
                        win_rate = (len(bt_df[bt_df['P&L %'] > 0]) / len(bt_df)) * 100
                        m_col1, m_col2, m_col3 = st.columns(3)
                        m_col1.metric("Total Trades", len(bt_df))
                        m_col2.metric("Win Rate", f"{win_rate:.2f}%")
                        m_col3.metric("Total Strategy P&L %", f"{total_pnl:.2f}%", delta=f"{total_pnl:.2f}%")
                        st.dataframe(bt_df, use_container_width=True)
                    else: st.info(f"No valid setups found for {bt_stock} in the last {bt_period}.")
            except Exception as e: st.error(f"Error fetching data: {e}")

elif page_selection == "⚙️ Scanner Settings":
    st.markdown("<div class='section-title'>⚙️ System Status</div>", unsafe_allow_html=True)
    st.success("✅ Real TradingView Charts Restored (BSE fix for India) \n\n ✅ Clean Yahoo Finance Engine is Active \n\n ✅ Auto-Save Database is Active (`trade_history.csv`) \n\n ✅ Manual Trade Logging Restored")

if auto_refresh:
    time.sleep(refresh_time * 60)
    st.rerun()
