import streamlit as st
import datetime
import pytz
import yfinance as yf
import pandas as pd
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# --- 1. Page Configuration & Session State for Journal ---
st.set_page_config(layout="wide", page_title="Haridas Master Terminal", initial_sidebar_state="expanded")

if 'trade_journal' not in st.session_state:
    st.session_state['trade_journal'] = []

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
NIFTY_NEXT_50 = ["ABB.NS", "ADANIENSOL.NS", "ADANIGREEN.NS", "AMBUJACEM.NS", "DMART.NS", "BAJAJHLDNG.NS", "BANKBARODA.NS", "BEL.NS", "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS", "CGPOWER.NS", "COLPAL.NS", "DLF.NS", "DABUR.NS", "GAIL.NS", "GODREJCP.NS", "HAL.NS", "HAVELLS.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDBI.NS", "INDIGO.NS", "IOC.NS", "IRFC.NS", "JINDALSTEL.NS", "JIOFIN.NS", "LODHA.NS", "MARICO.NS", "MUTHOOTFIN.NS", "NAUKRI.NS", "PIDILITIND.NS", "PFC.NS", "PNB.NS", "RECLTD.NS", "SRF.NS", "MOTHERSON.NS", "SHREECEM.NS", "SIEMENS.NS", "TVSMOTOR.NS", "TORNTPHARM.NS", "TRENT.NS", "UBL.NS", "MCDOWELL-N.NS", "VBL.NS", "VEDL.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"]
ALL_STOCKS = list(set([stock for slist in FNO_SECTORS.values() for stock in slist] + NIFTY_50 + NIFTY_NEXT_50))

CRYPTO_SECTORS = {
    "ALL COINDCX FUTURES": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD",
        "LINK-USD", "DOT-USD", "TRX-USD", "MATIC-USD", "AGLD-USD", "BEL-USD", "SNX-USD", "AAVE-USD",
        "UNI-USD", "NEAR-USD", "APT-USD", "LDO-USD", "CRV-USD", "MKR-USD", "SHIB-USD", "PEPE-USD",
        "WIF-USD", "FLOKI-USD", "BONK-USD", "LTC-USD", "BCH-USD", "XLM-USD", "ATOM-USD", "HBAR-USD",
        "ETC-USD", "FIL-USD", "INJ-USD", "OP-USD", "RNDR-USD", "IMX-USD", "STX-USD", "GRT-USD",
        "VET-USD", "THETA-USD", "SAND-USD", "MANA-USD", "AXS-USD", "APE-USD", "GALA-USD", "FTM-USD",
        "DYDX-USD", "SUI-USD", "SEI-USD", "TIA-USD", "ORDI-USD", "FET-USD", "RUNE-USD", "AR-USD",
        "COMP-USD", "CHZ-USD", "EGLD-USD", "ALGO-USD", "ICP-USD", "QNT-USD", "ROSE-USD", "ARDR-USD"
    ],
    "TOP WATCHLIST": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "DOGE-USD"],
    "LAYER 1": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "NEAR-USD"],
    "MEME COINS": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "FLOKI-USD", "BONK-USD"],
    "DEFI & WEB3": ["LINK-USD", "UNI-USD", "AAVE-USD", "CRV-USD", "MKR-USD", "LDO-USD", "AGLD-USD", "BEL-USD"],
    "ALTCOINS": ["XRP-USD", "TRX-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "XLM-USD", "APT-USD", "SNX-USD"]
}
ALL_CRYPTO = list(set([coin for clist in CRYPTO_SECTORS.values() for coin in clist]))

def fmt_price(val):
    if pd.isna(val): return "0.00"
    if val < 0.01: return f"{val:.6f}"
    elif val < 1: return f"{val:.4f}"
    else: return f"{val:,.2f}"

# --- 3. HELPER FUNCTIONS ---
@st.cache_data(ttl=30)
def get_live_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period='5d')
        if not df.empty:
            ltp = df['Close'].iloc[-1]
            try: prev_close = stock.fast_info.previous_close
            except: prev_close = df['Close'].iloc[-2] if len(df) > 1 else ltp
            
            if pd.isna(ltp) or pd.isna(prev_close) or prev_close == 0: return 0.0, 0.0, 0.0
            
            change = ltp - prev_close
            pct_change = (change / prev_close) * 100
            return float(ltp), float(change), float(pct_change)
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
def get_real_sector_performance(sector_dict, ignore_keys=["MIXED WATCHLIST", "TOP WATCHLIST", "ALL COINDCX FUTURES"]):
    results = []
    for sector, items in sector_dict.items():
        if sector in ignore_keys: continue
        total_pct = 0
        valid = 0
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
    for ticker in item_list:
        try:
            df = yf.Ticker(ticker).history(period="10d")
            if len(df) >= 3:
                c1, o1 = df['Close'].iloc[-1], df['Open'].iloc[-1]
                c2, o2 = df['Close'].iloc[-2], df['Open'].iloc[-2]
                c3, o3 = df['Close'].iloc[-3], df['Open'].iloc[-3]
                
                if c2 == 0 or pd.isna(c1): continue
                
                pct_chg = ((c1 - c2) / c2) * 100
                obj = {"Stock": ticker, "LTP": float(c1), "Pct": round(pct_chg, 2)}
                
                if pct_chg > 0: gainers.append(obj)
                elif pct_chg < 0: losers.append(obj)
                if c1 > o1 and c2 > o2 and c3 > o3: trends.append({"Stock": ticker, "Status": "৩ দিন উত্থান", "Color": "green"})
                elif c1 < o1 and c2 < o2 and c3 < o3: trends.append({"Stock": ticker, "Status": "৩ দিন পতন", "Color": "red"})
        except: pass
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
                        signal = "Short Covering 🚀" if c2 < c3 else "Long Buildup 📈"
                        color = "green"
                    else:
                        signal = "Long Unwinding ⚠️" if c2 > c3 else "Short Buildup 📉"
                        color = "red"
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
            if completed_idx < 1: continue
            
            alert_candle = df.iloc[completed_idx]
            prev_candle = df.iloc[completed_idx - 1]
            current_ltp = df['Close'].iloc[-1]
            
            signal = None
            entry = sl = target_bb = 0.0
            
            prev_touched_upper = prev_candle['HA_High'] >= prev_candle['Upper_BB']
            alert_red = alert_candle['HA_Close'] < alert_candle['HA_Open']
            alert_inside_upper = alert_candle['HA_High'] < alert_candle['Upper_BB']
            
            prev_touched_lower = prev_candle['HA_Low'] <= prev_candle['Lower_BB']
            alert_green = alert_candle['HA_Close'] > alert_candle['HA_Open']
            alert_inside_lower = alert_candle['HA_Low'] > alert_candle['Lower_BB']
            
            if prev_touched_upper and alert_red and alert_inside_upper:
                signal = "SHORT"
                entry = alert_candle['Low'] - 0.10
                sl = alert_candle['High'] + 0.10
                target_bb = alert_candle['Lower_BB']
            elif prev_touched_lower and alert_green and alert_inside_lower:
                signal = "BUY"
                entry = alert_candle['High'] + 0.10
                sl = alert_candle['Low'] - 0.10
                target_bb = alert_candle['Upper_BB']
                
            if signal:
                risk = abs(entry - sl)
                if risk > 0:
                    signals.append({
                        "Stock": stock_symbol, "Entry": round(entry, 2), "LTP": round(current_ltp, 2),
                        "Signal": signal, "SL": round(sl, 2), "Target(BB)": round(target_bb, 2), 
                        "T2(1:3)": round(entry - (risk*3) if signal=="SHORT" else entry + (risk*3), 2),
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
            if completed_idx < 1: return None
            
            alert_candle = df.iloc[completed_idx]
            prev_candle = df.iloc[completed_idx - 1]
            current_ltp = df['Close'].iloc[-1]
            
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
                        "Coin": coin, "Signal": signal, "Entry": float(entry), "LTP": float(current_ltp),
                        "SL": float(sl), "Target(BB)": float(target_bb), "Target(1:3)": float(entry - (risk*3) if signal=="SHORT" else entry + (risk*3)),
                        "Time": alert_candle.name.strftime('%d %b, %H:%M')
                    }
        except: return None
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(scan_coin, crypto_list))
        
    for res in results:
        if res is not None: signals.append(res)
    return signals

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
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup", "⚙️ Scanner Settings", "📊 Backtest Engine"]
        sector_dict = FNO_SECTORS
        all_assets = ALL_STOCKS
    else:
        menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers", "🔥 Volume Spikes & OI", "🧮 Futures Risk Calculator", "⚙️ Scanner Settings", "📊 Backtest Engine"]
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
    refresh_time = st.selectbox("Interval (Mins):", [1, 3, 5, 15], index=0) 
    if st.button("🔄 Force Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. Top Navigation ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
t_915 = curr_time.replace(hour=9, minute=15, second=0, microsecond=0)
t_1530 = curr_time.replace(hour=15, minute=30, second=0, microsecond=0)

if market_mode == "🇮🇳 Indian Market (NSE)":
    terminal_title = "HARIDAS NSE TERMINAL"
    if curr_time < t_915: session, session_color = "PRE-MARKET", "#ff9800" 
    elif curr_time <= t_1530: session, session_color = "LIVE MARKET", "#28a745" 
    else: session, session_color = "POST MARKET", "#dc3545"            try: prev_close = stock.fast_info.previous_close
            except: prev_close = df['Close'].iloc[-2] if len(df) > 1 else ltp
            
            if pd.isna(ltp) or pd.isna(prev_close) or prev_close == 0: return 0.0, 0.0, 0.0
            
            change = ltp - prev_close
            pct_change = (change / prev_close) * 100
            return float(ltp), float(change), float(pct_change)
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
def get_real_sector_performance(sector_dict, ignore_keys=["MIXED WATCHLIST", "TOP WATCHLIST", "ALL COINDCX FUTURES"]):
    results = []
    for sector, items in sector_dict.items():
        if sector in ignore_keys: continue
        total_pct = 0
        valid = 0
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
    for ticker in item_list:
        try:
            df = yf.Ticker(ticker).history(period="10d")
            if len(df) >= 3:
                c1, o1 = df['Close'].iloc[-1], df['Open'].iloc[-1]
                c2, o2 = df['Close'].iloc[-2], df['Open'].iloc[-2]
                c3, o3 = df['Close'].iloc[-3], df['Open'].iloc[-3]
                
                if c2 == 0 or pd.isna(c1): continue
                
                pct_chg = ((c1 - c2) / c2) * 100
                obj = {"Stock": ticker, "LTP": float(c1), "Pct": round(pct_chg, 2)}
                
                if pct_chg > 0: gainers.append(obj)
                elif pct_chg < 0: losers.append(obj)
                if c1 > o1 and c2 > o2 and c3 > o3: trends.append({"Stock": ticker, "Status": "৩ দিন উত্থান", "Color": "green"})
                elif c1 < o1 and c2 < o2 and c3 < o3: trends.append({"Stock": ticker, "Status": "৩ দিন পতন", "Color": "red"})
        except: pass
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
                        signal = "Short Covering 🚀" if c2 < c3 else "Long Buildup 📈"
                        color = "green"
                    else:
                        signal = "Long Unwinding ⚠️" if c2 > c3 else "Short Buildup 📉"
                        color = "red"
                    setups.append({"Stock": ticker, "Signal": signal, "OI": oi_status, "Color": color})
        except: pass
    return setups

# 🚨 FIXED NSE SCANNER: Now strictly uses 5m HA + BB (Filters Fake Breakouts) 🚨
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
            if completed_idx < 1: continue
            
            alert_candle = df.iloc[completed_idx]
            prev_candle = df.iloc[completed_idx - 1]
            current_ltp = df['Close'].iloc[-1]
            
            signal = None
            entry = sl = target_bb = 0.0
            
            # Strict HA+BB Logic to prevent false signals like ITC
            prev_touched_upper = prev_candle['HA_High'] >= prev_candle['Upper_BB']
            alert_red = alert_candle['HA_Close'] < alert_candle['HA_Open']
            alert_inside_upper = alert_candle['HA_High'] < alert_candle['Upper_BB']
            
            prev_touched_lower = prev_candle['HA_Low'] <= prev_candle['Lower_BB']
            alert_green = alert_candle['HA_Close'] > alert_candle['HA_Open']
            alert_inside_lower = alert_candle['HA_Low'] > alert_candle['Lower_BB']
            
            if prev_touched_upper and alert_red and alert_inside_upper:
                signal = "SHORT"
                entry = alert_candle['Low'] - 0.10
                sl = alert_candle['High'] + 0.10
                target_bb = alert_candle['Lower_BB']
            elif prev_touched_lower and alert_green and alert_inside_lower:
                signal = "BUY"
                entry = alert_candle['High'] + 0.10
                sl = alert_candle['Low'] - 0.10
                target_bb = alert_candle['Upper_BB']
                
            if signal:
                risk = abs(entry - sl)
                if risk > 0:
                    signals.append({
                        "Stock": stock_symbol, "Entry": round(entry, 2), "LTP": round(current_ltp, 2),
                        "Signal": signal, "SL": round(sl, 2), "Target(BB)": round(target_bb, 2), 
                        "T2(1:3)": round(entry - (risk*3) if signal=="SHORT" else entry + (risk*3), 2),
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
            if completed_idx < 1: return None
            
            alert_candle = df.iloc[completed_idx]
            prev_candle = df.iloc[completed_idx - 1]
            current_ltp = df['Close'].iloc[-1]
            
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
                        "Coin": coin, "Signal": signal, "Entry": float(entry), "LTP": float(current_ltp),
                        "SL": float(sl), "Target(BB)": float(target_bb), "Target(1:3)": float(entry - (risk*3) if signal=="SHORT" else entry + (risk*3)),
                        "Time": alert_candle.name.strftime('%d %b, %H:%M')
                    }
        except: return None
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(scan_coin, crypto_list))
        
    for res in results:
        if res is not None: signals.append(res)
    return signals

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
        menu_options = ["📈 MAIN TERMINAL", "🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🔥 9:20 AM: OI Setup", "⚙️ Scanner Settings", "📊 Backtest Engine"]
        sector_dict = FNO_SECTORS
        all_assets = ALL_STOCKS
    else:
        menu_options = ["📈 MAIN TERMINAL", "🚀 24H Crypto Movers", "🔥 Volume Spikes & OI", "🧮 Futures Risk Calculator", "⚙️ Scanner Settings", "📊 Backtest Engine"]
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
    refresh_time = st.selectbox("Interval (Mins):", [1, 3, 5, 15], index=0) 
    if st.button("🔄 Force Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. Top Navigation ---
ist_timezone = pytz.timezone('Asia/Kolkata')
curr_time = datetime.datetime.now(ist_timezone)
t_915 = curr_time.replace(hour=9, minute=15, second=0, microsecond=0)
t_1530 = curr_time.replace(hour=15, minute=30, second=0, microsecond=0)

if market_mode == "🇮🇳 Indian Market (NSE)":
    terminal_title = "HARIDAS NSE TERMINAL"
    if curr_time < t_915: session, session_color = "PRE-MARKE
