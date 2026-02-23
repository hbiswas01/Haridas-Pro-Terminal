import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import time
import requests
import xml.etree.ElementTree as ET
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import os
from streamlit_autorefresh import st_autorefresh

# --- 1. Page Configuration ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

# ৫ সেকেন্ড পরপর অটো-রিফ্রেশ
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

# --- 2. AUTHENTICATED COINDCX API ENGINE (100% WORKING) ---
@st.cache_data(ttl=5)
def get_coindcx_live_prices():
    url = "https://api.coindcx.com/exchange/ticker"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        api_key = st.secrets.get("COINDCX_API_KEY", "")
        if api_key:
            headers['X-AUTH-APIKEY'] = api_key
    except: pass

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def get_crypto_price_v2(data, coin_prefix):
    if not isinstance(data, list) or len(data) == 0: return 0.0, 0.0, 0.0
    
    # STRICT USDT SEARCH: শুধুমাত্র ডলারের (USDT) দাম খুঁজবে, INR নয়
    target_markets = [f"B-{coin_prefix}_USDT", f"{coin_prefix}USDT", f"{coin_prefix}_USDT"]
    
    for tm in target_markets:
        for item in data:
            if item.get("market") == tm:
                try:
                    ltp = float(item.get('last_price', 0.0))
                    pct_change = float(item.get('change_24_hour', 0.0))
                    chg_abs = (ltp * pct_change) / 100
                    return ltp, chg_abs, round(pct_change, 2)
                except: pass
    return 0.0, 0.0, 0.0

# --- 3. Live Market Data Dictionary ---
FNO_SECTORS = {
    "MIXED WATCHLIST": ["HINDALCO.NS", "NTPC.NS", "WIPRO.NS", "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ITC.NS", "SBIN.NS"],
    "NIFTY BANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS"],
    "NIFTY IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "NIFTY AUTO": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS"]
}

NIFTY_50 = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS"]
ALL_STOCKS = list(set([stock for slist in FNO_SECTORS.values() for stock in slist] + NIFTY_50))

CRYPTO_SECTORS = {
    "ALL COINDCX FUTURES": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD"],
    "TOP WATCHLIST": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "DOGE-USD"],
    "MEME COINS": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "FLOKI-USD", "BONK-USD"]
}
ALL_CRYPTO = list(set([coin for clist in CRYPTO_SECTORS.values() for coin in clist]))

def fmt_price(val):
    if pd.isna(val): return "0.00"
    if val < 0.01: return f"{val:.6f}"
    elif val < 1: return f"{val:.4f}"
    else: return f"{val:,.2f}"

# --- 4. DATA ENGINES ---
@st.cache_data(ttl=15)
def get_live_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period='5d')
        if len(df) >= 2:
            ltp = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            if prev_close > 0:
                change = ltp - prev_close
                pct_change = (change / prev_close) * 100
                return ltp, change, pct_change
    except: pass
    return 0.0, 0.0, 0.0

@st.cache_data(ttl=60)
def get_opening_movers(item_list):
    movers = []
    def fetch_mover(ticker):
        try:
            ltp, chg, pct_chg = get_live_data(ticker)
            if abs(pct_chg) >= 2.0:
                return {"Stock": ticker, "LTP": ltp, "Pct": round(pct_chg, 2)}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_mover, item_list))
    for res in results:
        if res is not None: movers.append(res)
    return sorted(movers, key=lambda x: abs(x['Pct']), reverse=True)

@st.cache_data(ttl=60)
def get_real_sector_performance(sector_dict, ignore_keys=["MIXED WATCHLIST", "TOP WATCHLIST", "ALL COINDCX FUTURES"]):
    results = []
    for sector, items in sector_dict.items():
        if sector in ignore_keys: continue
        total_pct, valid = 0, 0
        for ticker in items:
            _, _, pct = get_live_data(ticker)
            if pct != 0.0:
                total_pct += pct
                valid += 1
        if valid > 0:
            avg_pct = round(total_pct / valid, 2)
            bw = min(abs(avg_pct) * 20, 100) 
            results.append({"Sector": sector, "Pct": avg_pct, "Width": max(bw, 5)})
    return sorted(results, key=lambda x: x['Pct'], reverse=True)

@st.cache_data(ttl=60)
def get_adv_dec(item_list):
    adv, dec = 0, 0
    def fetch_chg(ticker):
        _, change, _ = get_live_data(ticker)
        return change
    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_chg, item_list))
    for change in results:
        if change > 0: adv += 1
        elif change < 0: dec += 1
    return adv, dec

@st.cache_data(ttl=120)
def get_dynamic_market_data(item_list):
    gainers, losers, trends = [], [], []
    def fetch_dynamic(ticker):
        try:
            df = yf.Ticker(ticker).history(period="5d")
            if len(df) >= 3:
                c1, c2, c3 = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2]), float(df['Close'].iloc[-3])
                o1, o2, o3 = float(df['Open'].iloc[-1]), float(df['Open'].iloc[-2]), float(df['Open'].iloc[-3])
                if c2 > 0:
                    pct_chg = ((c1 - c2) / c2) * 100
                    trend_stat, clr = None, None
                    if c1 > o1 and c2 > o2 and c3 > o3: trend_stat, clr = "৩ দিন উত্থান", "green"
                    elif c1 < o1 and c2 < o2 and c3 < o3: trend_stat, clr = "৩ দিন পতন", "red"
                    return {"Stock": ticker, "LTP": c1, "Pct": round(pct_chg, 2), "T_Stat": trend_stat, "Color": clr}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_dynamic, item_list))
        
    for res in results:
        if res:
            obj = {"Stock": res["Stock"], "LTP": res["LTP"], "Pct": res["Pct"]}
            if res["Pct"] > 0: gainers.append(obj)
            elif res["Pct"] < 0: losers.append(obj)
            if res["T_Stat"]: trends.append({"Stock": res["Stock"], "Status": res["T_Stat"], "Color": res["Color"]})
            
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
                    if c1 > c2:
                        signal, color = ("Short Covering 🚀" if c2 < c3 else "Long Buildup 📈"), "green"
                    else:
                        signal, color = ("Long Unwinding ⚠️" if c2 > c3 else "Short Buildup 📉"), "red"
                    setups.append({"Stock": ticker, "Signal": signal, "OI": oi_status, "Color": color})
        except: pass
    return setups

@st.cache_data(ttl=60)
def nse_ha_bb_strategy_5m(stock_list):
    signals = []
    def scan_ha_bb(stock_symbol):
        try:
            df = yf.Ticker(stock_symbol).history(period="5d", interval="5m") 
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
            alert_candle, prev_candle = df.iloc[-2], df.iloc[-3]
            current_ltp = df['Close'].iloc[-1]
            signal, entry, sl, target_bb = None, 0.0, 0.0, 0.0
            
            if (prev_candle['HA_High'] >= prev_candle['Upper_BB']) and (alert_candle['HA_Close'] < alert_candle['HA_Open']) and (alert_candle['HA_High'] < alert_candle['Upper_BB']):
                signal, entry, sl, target_bb = "SHORT", alert_candle['Low'] - 0.10, alert_candle['High'] + 0.10, alert_candle['Lower_BB']
            elif (prev_candle['HA_Low'] <= prev_candle['Lower_BB']) and (alert_candle['HA_Close'] > alert_candle['HA_Open']) and (alert_candle['HA_Low'] > alert_candle['Lower_BB']):
                signal, entry, sl, target_bb = "BUY", alert_candle['High'] + 0.10, alert_candle['Low'] - 0.10, alert_candle['Upper_BB']
            
            if signal and abs(entry - sl) > 0:
                risk = abs(entry - sl)
                return {"Stock": stock_symbol, "Entry": round(entry, 2), "LTP": round(current_ltp, 2), "Signal": signal, "SL": round(sl, 2), "Target(BB)": round(target_bb, 2), "T2(1:3)": round(entry - (risk*3) if signal=="SHORT" else entry + (risk*3), 2), "Time": alert_candle.name.strftime('%H:%M')}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(scan_ha_bb, stock_list))
    for res in results:
        if res: signals.append(res)
    return signals

# 🚨 THE MISSING CRYPTO FUNCTION RESTORED 🚨
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
            alert_candle, prev_candle = df.iloc[-2], df.iloc[-3]
            current_ltp = df['Close'].iloc[-1]
            signal, entry, sl, target_bb = None, 0.0, 0.0, 0.0
            buffer = alert_candle['Close'] * 0.001
            
            if (prev_candle['HA_High'] >= prev_candle['Upper_BB']) and (alert_candle['HA_High'] < alert_candle['Upper_BB']):
                signal, entry, sl, target_bb = "SHORT", alert_candle['Low'] - buffer, alert_candle['High'] + buffer, alert_candle['Lower_BB']
            elif (prev_candle['HA_Low'] <= prev_candle['Lower_BB']) and (alert_candle['HA_Low'] > alert_candle['Lower_BB']):
                signal, entry, sl, target_bb = "BUY", alert_candle['High'] + buffer, alert_candle['Low'] - buffer, alert_candle['Upper_BB']
            
            if signal and abs(entry - sl) > 0:
                risk = abs(entry - sl)
                return {"Stock": coin, "Signal": signal, "Entry": float(entry), "LTP": float(current_ltp), "SL": float(sl), "Target(BB)": float(target_bb), "T2(1:3)": float(entry - (risk*3) if signal=="SHORT" else entry + (risk*3)), "Time": alert_candle.name.strftime('%d %b, %H:%M')}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(scan_coin, crypto_list))
    for res in results:
        if res: signals.append(res)
    return signals

# 🚨 THE MISSING AUTO TRADE FUNCTION RESTORED 🚨
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
                new_trade = {"Date": current_time_str, "Stock": sig['Stock'], "Signal": sig['Signal'], "Entry": sig['Entry'], "SL": sig['SL'], "Target": sig['T2(1:3)'], "Status": "RUNNING"}
                st.session_state.active_trades.append(new_trade)
                save_data(st.session_state.active_trades, ACTIVE_TRADES_FILE)

    trades_to_remove = []
    for trade in st.session_state.active_trades:
        ltp, _, _ = get_live_data(trade['Stock'])
        if ltp == 0.0: continue
        close_reason, exit_price = None, 0.0
        if trade['Signal'] == 'BUY':
            if ltp <= trade['SL']: close_reason, exit_price = "🛑 SL HIT", trade['SL']
            elif ltp >= trade['Target']: close_reason, exit_price = "🎯 TARGET HIT", trade['Target']
        elif trade['Signal'] == 'SHORT':
            if ltp >= trade['SL']: close_reason, exit_price = "🛑 SL HIT", trade['SL']
            elif ltp <= trade['Target']: close_reason, exit_price = "🎯 TARGET HIT", trade['Target']

        if close_reason:
            pnl_pct = ((exit_price - trade['Entry']) / trade['Entry']) * 100 if trade['Signal'] == 'BUY' else ((trade['Entry'] - exit_price) / trade['Entry']) * 100
            completed_trade = {"Date": current_time_str, "Stock": trade['Stock'], "Signal": trade['Signal'], "Entry": trade['Entry'], "Exit": exit_price, "Status": close_reason, "P&L %": round(pnl_pct, 2)}
            st.session_state.trade_history.append(completed_trade)
            trades_to_remove.append(trade)

    if trades_to_remove:
        st.session_state.active_trades = [t for t in st.session_state.active_trades if t not in trades_to_remove]
        save_data(st.session_state.active_trades, ACTIVE_TRADES_FILE)
        save_data(st.session_state.trade_history, HISTORY_TRADES_FILE)


# --- 5. Sidebar & UI ---
with st.sidebar:
    st.markdown("### 🌍 SELECT MARKET")
    market_mode = st.radio("Toggle Global Market:", ["🇮🇳 Indian Market (NSE)", "₿ Crypto Market (24/7)"], index=1)
    st.divider()
    
    st.markdown("### 🎛️ HARIDAS DASHBOARD")
    if market_mode == "🇮🇳 Indian Market (NSE)":
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup", "⚙️ Scanner Settings"]
        sector_dict, all_assets = FNO_SECTORS, ALL_STOCKS
    else:
        menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers", "🔥 Volume Spikes & OI", "⚙️ Scanner Settings"]
        sector_dict, all_assets = CRYPTO_SECTORS, ALL_CRYPTO

    page_selection = st.radio("Select Menu:", menu_options)
    st.divider()
    
    st.markdown("### ⚙️ STRATEGY SETTINGS")
    user_sentiment = st.radio("Market Sentiment:", ["BULLISH", "BEARISH"])
    selected_sector = st.selectbox("Select Watchlist:", list(sector_dict.keys()), index=0)
    current_watchlist = sector_dict[selected_sector]
    st.divider()
    
    if st.button("🗑️ Clear All History Data"):
        st.session_state.active_trades = []
        st.session_state.trade_history = []
        if os.path.exists(ACTIVE_TRADES_FILE): os.remove(ACTIVE_TRADES_FILE)
        if os.path.exists(HISTORY_TRADES_FILE): os.remove(HISTORY_TRADES_FILE)
        st.success("History Cleared!")
        st.rerun()

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .top-nav { background-color: #002b36; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #00ffd0; border-radius: 8px; margin-bottom: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.2); }
    .section-title { background: linear-gradient(90deg, #002b36 0%, #00425a 100%); color: #00ffd0; font-size: 13px; font-weight: 800; padding: 10px 15px; border-left: 5px solid #00ffd0; border-radius: 5px; margin-top: 15px; margin-bottom: 10px; display: flex; align-items: center; }
    .table-container { overflow-x: auto; width: 100%; border-radius: 5px; }
    .v38-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 11px; background: white; border: 1px solid #b0c4de; margin-bottom: 10px; }
    .v38-table th { background-color: #4f81bd; color: white; padding: 8px; border: 1px solid #b0c4de; font-weight: bold; }
    .v38-table td { padding: 8px; border: 1px solid #b0c4de; }
    .idx-container { display: flex; justify-content: space-between; background: white; border: 1px solid #b0c4de; padding: 5px; margin-bottom: 10px; flex-wrap: wrap; border-radius: 5px; }
    .idx-box { text-align: center; width: 31%; border-right: 1px solid #eee; padding: 5px; min-width: 100px; margin-bottom: 5px; }
    .idx-box:nth-child(3n) { border-right: none; }
    .adv-dec-container { background: white; border: 1px solid #b0c4de; padding: 10px; margin-bottom: 10px; text-align: center; border-radius: 5px; }
    .adv-dec-bar { display: flex; height: 14px; border-radius: 4px; overflow: hidden; margin: 8px 0; background: #e0e0e0; }
    .bar-green { background-color: #2e7d32; } .bar-red { background-color: #d32f2f; }
    </style>
""", unsafe_allow_html=True)

ist_tz = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_tz)
term_title = "HARIDAS CRYPTO TERMINAL" if market_mode == "₿ Crypto Market (24/7)" else "HARIDAS NSE TERMINAL"

st.markdown(f"<div class='top-nav'><div style='color:#00ffd0; font-weight:900; font-size:22px; text-shadow: 0px 0px 10px rgba(0, 255, 208, 0.6);'>📊 {term_title}</div>"
            f"<div style='font-size: 14px; color: #ffeb3b; font-weight: bold;'>🕒 {curr_time.strftime('%H:%M:%S')} (IST)</div></div>", unsafe_allow_html=True)

# ==================== MAIN DASHBOARD ====================
if page_selection == "📈 MAIN TERMINAL":
    col1, col2, col3 = st.columns([1, 2.8, 1])

    with col1:
        st.markdown("<div class='section-title'>📊 CATEGORY PERFORMANCE</div>", unsafe_allow_html=True)
        with st.spinner("Wait..."): real_sectors = get_real_sector_performance(sector_dict)
        if real_sectors:
            sec_html = "<div class='table-container'><table class='v38-table'><tr><th>Category</th><th>Avg %</th></tr>"
            for s in real_sectors:
                c = "green" if s['Pct'] >= 0 else "red"
                sec_html += f"<tr><td style='text-align:left; font-weight:bold;'>{s['Sector']}</td><td style='color:{c}; font-weight:bold;'>{s['Pct']}%</td></tr>"
            sec_html += "</table></div>"
            st.markdown(sec_html, unsafe_allow_html=True)

        with st.spinner("Wait..."): gainers, losers, trends = get_dynamic_market_data(all_assets)
        st.markdown("<div class='section-title'>🔍 TREND (3+ DAYS)</div>", unsafe_allow_html=True)
        if trends:
            t_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Status</th></tr>"
            for t in trends: t_html += f"<tr><td style='text-align:left; font-weight:bold;'>{t['Stock']}</td><td style='color:{t['Color']}; font-weight:bold;'>{t['Status']}</td></tr>"
            t_html += "</table></div>"
            st.markdown(t_html, unsafe_allow_html=True)
        else: st.info("No trend found.")

    with col2:
        st.markdown("<div class='section-title'>📉 MARKET INDICES (LIVE)</div>", unsafe_allow_html=True)
        if market_mode == "🇮🇳 Indian Market (NSE)":
            p1_ltp, p1_chg, p1_pct = get_live_data("^BSESN")
            p2_ltp, p2_chg, p2_pct = get_live_data("^NSEI")
            p3_ltp, p3_chg, p3_pct = get_live_data("INR=X")
            indices = [("Sensex", p1_ltp, p1_chg, p1_pct), ("Nifty", p2_ltp, p2_chg, p2_pct), ("USDINR", p3_ltp, p3_chg, p3_pct)]
        else:
            # 🚀 COINDCX API IN ACTION 🚀
            live_data = get_coindcx_live_prices()
            btc_ltp, btc_chg, btc_pct = get_crypto_price_v2(live_data, "BTC")
            eth_ltp, eth_chg, eth_pct = get_crypto_price_v2(live_data, "ETH")
            sol_ltp, sol_chg, sol_pct = get_crypto_price_v2(live_data, "SOL")
            bnb_ltp, bnb_chg, bnb_pct = get_crypto_price_v2(live_data, "BNB")
            xrp_ltp, xrp_chg, xrp_pct = get_crypto_price_v2(live_data, "XRP")
            doge_ltp, doge_chg, doge_pct = get_crypto_price_v2(live_data, "DOGE")
            
            indices = [("BITCOIN", btc_ltp, btc_chg, btc_pct), ("ETHEREUM", eth_ltp, eth_chg, eth_pct), ("SOLANA", sol_ltp, sol_chg, sol_pct), ("BNB", bnb_ltp, bnb_chg, bnb_pct), ("RIPPLE", xrp_ltp, xrp_chg, xrp_pct), ("DOGECOIN", doge_ltp, doge_chg, doge_pct)]

        indices_html = "<div class='idx-container'>"
        for name, val, chg, pct in indices:
            clr = "green" if chg >= 0 else "red"
            sign = "+" if chg >= 0 else ""
            prefix = "₹" if name != "USDINR" and market_mode == "🇮🇳 Indian Market (NSE)" else "$"
            val_str = f"{val:.4f}" if name == "USDINR" else fmt_price(val)
            indices_html += f"<div class='idx-box'><span style='font-size:11px; color:#555; font-weight:bold;'>{name}</span><br><span style='font-size:16px; color:black; font-weight:bold;'>{prefix}{val_str}</span><br><span style='color:{clr}; font-size:11px; font-weight:bold;'>{sign}{fmt_price(chg)} ({sign}{pct:.2f}%)</span></div>"
        indices_html += "</div>"
        st.markdown(indices_html, unsafe_allow_html=True)

        st.markdown("<div class='section-title'>📊 ADVANCE/ DECLINE</div>", unsafe_allow_html=True)
        adv, dec = get_adv_dec(all_assets)
        total_adv_dec = adv + dec
        adv_pct = (adv / total_adv_dec) * 100 if total_adv_dec > 0 else 50
        st.markdown(f"<div class='adv-dec-container'><div class='adv-dec-bar'><div class='bar-green' style='width: {adv_pct}%;'></div><div class='bar-red' style='width: {100-adv_pct}%;'></div></div><div style='display:flex; justify-content:space-between; font-size:12px; font-weight:bold;'><span style='color:green;'>Advances: {adv}</span><span style='color:red;'>Declines: {dec}</span></div></div>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🎯 LIVE SIGNALS (HA+BB)</div>", unsafe_allow_html=True)
        with st.spinner("Scanning Charts..."): 
            live_signals = nse_ha_bb_strategy_5m(current_watchlist) if market_mode == "🇮🇳 Indian Market (NSE)" else crypto_ha_bb_strategy(CRYPTO_SECTORS["ALL COINDCX FUTURES"])
        
        if live_signals:
            sig_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Entry</th><th>Signal</th><th>Target</th></tr>"
            for sig in live_signals:
                sig_clr = "green" if sig['Signal'] == "BUY" else "red"
                sig_html += f"<tr><td style='color:{sig_clr}; font-weight:bold;'>{sig['Stock']}</td><td>{fmt_price(sig['Entry'])}</td><td style='color:white; background:{sig_clr}; font-weight:bold;'>{sig['Signal']}</td><td style='font-weight:bold;'>{fmt_price(sig['T2(1:3)'])}</td></tr>"
            sig_html += "</table></div>"
            st.markdown(sig_html, unsafe_allow_html=True)
        else: st.info("⏳ No fresh signals right now.")

        process_auto_trades(live_signals)

        st.markdown("<div class='section-title'>⏳ ACTIVE TRADES</div>", unsafe_allow_html=True)
        if len(st.session_state.active_trades) > 0:
            st.dataframe(pd.DataFrame(st.session_state.active_trades), use_container_width=True)
        else: st.info("No active trades.")

        st.markdown("<div class='section-title'>📝 TRADE JOURNAL</div>", unsafe_allow_html=True)
        with st.expander("➕ Add New Trade to Journal"):
            with st.form("journal_form"):
                j_col1, j_col2, j_col3, j_col4 = st.columns(4)
                with j_col1: j_asset = st.selectbox("Select Asset", sorted(all_assets))
                with j_col2: j_signal = st.selectbox("Signal", ["BUY", "SHORT"])
                with j_col3: j_entry = st.number_input("Entry Price", min_value=0.0)
                with j_col4: j_exit = st.number_input("Exit Price", min_value=0.0)
                if st.form_submit_button("💾 Save Trade") and j_asset != "" and j_entry > 0 and j_exit > 0:
                    pnl_pct = ((j_exit - j_entry) / j_entry) * 100 if j_signal == "BUY" else ((j_entry - j_exit) / j_entry) * 100
                    st.session_state.trade_history.append({"Date": datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M"), "Stock": j_asset.upper(), "Signal": j_signal, "Entry": j_entry, "Exit": j_exit, "Status": "MANUAL ENTRY", "P&L %": round(pnl_pct, 2)})
                    save_data(st.session_state.trade_history, HISTORY_TRADES_FILE)
                    st.success("✅ Trade saved!")

    with col3:
        st.markdown("<div class='section-title'>🚀 LIVE TOP GAINERS</div>", unsafe_allow_html=True)
        if gainers:
            g_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for g in gainers: g_html += f"<tr><td style='text-align:left; font-weight:bold;'>{g['Stock']}</td><td>{fmt_price(g['LTP'])}</td><td style='color:green; font-weight:bold;'>+{g['Pct']}%</td></tr>"
            g_html += "</table></div>"
            st.markdown(g_html, unsafe_allow_html=True)
        else: st.info("No data")

        st.markdown("<div class='section-title'>🔻 LIVE TOP LOSERS</div>", unsafe_allow_html=True)
        if losers:
            l_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for l in losers: l_html += f"<tr><td style='text-align:left; font-weight:bold;'>{l['Stock']}</td><td>{fmt_price(l['LTP'])}</td><td style='color:red; font-weight:bold;'>{l['Pct']}%</td></tr>"
            l_html += "</table></div>"
            st.markdown(l_html, unsafe_allow_html=True)
        else: st.info("No data")

# ==================== OTHER SECTIONS ====================
elif page_selection in ["🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🚀 24H Crypto Movers"]:
    st.markdown(f"<div class='section-title'>{page_selection}</div>", unsafe_allow_html=True)
    with st.spinner("Scanning ALL Assets..."): movers = get_opening_movers(all_assets)
    if movers:
        m_html = "<div class='table-container'><table class='v38-table'><tr><th>Stock / Coin</th><th>LTP</th><th>Movement %</th></tr>"
        for m in movers: 
            c = "green" if m['Pct'] > 0 else "red"
            m_html += f"<tr><td style='font-weight:bold;'>{m['Stock']}</td><td>{fmt_price(m['LTP'])}</td><td style='color:{c}; font-weight:bold;'>{m['Pct']}%</td></tr>"
        m_html += "</table></div>"
        st.markdown(m_html, unsafe_allow_html=True)
    else: st.info("No significant movement found based on live data.")

elif page_selection in ["🔥 9:20 AM: OI Setup", "🔥 Volume Spikes & OI"]:
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
