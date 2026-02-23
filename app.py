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
    "</div>"
    "<div>"
    "<span style='background:#1a73e8; padding:5px 15px; font-size:11px; color:white; font-weight:bold; border-radius:4px; cursor:pointer;'>SCAN MARKET</span>"
    "</div></div>"
)
st.markdown(nav_html, unsafe_allow_html=True)

# ==================== MAIN TERMINAL ====================
if page_selection == "📈 MAIN TERMINAL":
    col1, col2, col3 = st.columns([1, 2.8, 1])

    # --- COLUMN 1 (SECTORS & TRENDS) ---
    with col1:
        title = "📊 SECTOR PERFORMANCE" if market_mode == "🇮🇳 Indian Market (NSE)" else "📊 CRYPTO CATEGORIES"
        st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        with st.spinner("Fetching Live Sectors..."):
            real_sectors = get_real_sector_performance(sector_dict)
        if real_sectors:
            sec_html = "<div class='table-container'><table class='v38-table'><tr><th>Category</th><th>Avg %</th><th style='width:40%;'>Trend</th></tr>"
            for s in real_sectors:
                c = "green" if s['Pct'] >= 0 else "red"
                bc = "bar-fg-green" if s['Pct'] >= 0 else "bar-fg-red"
                sec_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{s['Sector']}</td><td style='color:{c}; font-weight:bold;'>{s['Pct']}%</td><td style='padding:4px 8px;'><div class='bar-bg'><div class='{bc}' style='width:{s['Width']}%;'></div></div></td></tr>"
            sec_html += "</table></div>"
            st.markdown(sec_html, unsafe_allow_html=True)

        with st.spinner("Fetching Live Market Movers & Trends..."):
            gainers, losers, trends = get_dynamic_market_data(all_assets)

        st.markdown("<div class='section-title'>🔍 TREND CONTINUITY (3+ Days)</div>", unsafe_allow_html=True)
        if trends:
            t_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>Status</th></tr>"
            for t in trends: t_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{t['Stock']}</td><td style='color:{t['Color']}; font-weight:bold;'>{t['Status']}</td></tr>"
            t_html += "</table></div>"
            st.markdown(t_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center; color:#888;'>No 3-day continuous trend found.</p>", unsafe_allow_html=True)

    # --- COLUMN 2 (INDICES, ADV/DEC, SIGNALS, JOURNAL) ---
    with col2:
        st.markdown("<div class='section-title'>📉 MARKET INDICES (LIVE)</div>", unsafe_allow_html=True)
        
        if market_mode == "🇮🇳 Indian Market (NSE)":
            p1_ltp, p1_chg, p1_pct = get_live_data("^BSESN")
            p2_ltp, p2_chg, p2_pct = get_live_data("^NSEI")
            p3_ltp, p3_chg, p3_pct = get_live_data("INR=X")
            p4_ltp, p4_chg, p4_pct = get_live_data("^NSEBANK")
            p5_ltp, p5_chg, p5_pct = get_live_data("^CRSMY")
            p6_ltp, p6_chg, p6_pct = get_live_data("^CRSLDX")
            indices = [("Sensex", p1_ltp, p1_chg, p1_pct), ("Nifty", p2_ltp, p2_chg, p2_pct), ("USDINR", p3_ltp, p3_chg, p3_pct), ("Nifty Bank", p4_ltp, p4_chg, p4_pct), ("Nifty Mid100", p5_ltp, p5_chg, p5_pct), ("Nifty Small100", p6_ltp, p6_chg, p6_pct)]
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
            val_str = f"{val:,.6f}".rstrip('0').rstrip('.') if val < 1 else f"{val:,.2f}"
            indices_html += f"<div class='idx-box'><span style='font-size:11px; color:#555; font-weight:bold;'>{name}</span><br><span style='font-size:15px; color:black; font-weight:bold;'>{prefix}{val_str}</span><br><span style='color:{clr}; font-size:11px; font-weight:bold;'>{sign}{fmt_price(chg)} ({sign}{pct:.2f}%)</span></div>"
        indices_html += "</div>"
        st.markdown(indices_html, unsafe_allow_html=True)

        with st.spinner("Calculating Breadth..."):
            adv, dec = get_adv_dec(all_assets)
        
        total_adv_dec = adv + dec
        adv_pct = (adv / total_adv_dec) * 100 if total_adv_dec > 0 else 50
        adv_title = "Advance/ Decline (NSE)" if market_mode == "🇮🇳 Indian Market (NSE)" else "Advance/ Decline (Top Crypto)"
        
        st.markdown(f"<div class='section-title'>📊 {adv_title}</div>", unsafe_allow_html=True)
        adv_dec_html = (
            "<div class='adv-dec-container'>"
            "<div class='adv-dec-bar'>"
            f"<div class='bar-green' style='width: {adv_pct}%;'></div>"
            f"<div class='bar-red' style='width: {100-adv_pct}%;'></div>"
            "</div>"
            "<div style='display:flex; justify-content:space-between; font-size:12px; font-weight:bold;'>"
            f"<span style='color:green;'>Advances: {adv}</span><span style='color:red;'>Declines: {dec}</span>"
            "</div>"
            f"<div style='font-size:10px; color:#555; margin-top:5px;'>Strategy Sentiment: <b>{user_sentiment}</b></div>"
            "</div>"
        )
        st.markdown(adv_dec_html, unsafe_allow_html=True)

        # 🚨 LIVE SIGNALS ENGINE 🚨
        if market_mode == "🇮🇳 Indian Market (NSE)":
            st.markdown(f"<div class='section-title'>🎯 LIVE SIGNALS FOR: {selected_sector} (5M HA+BB)</div>", unsafe_allow_html=True)
            with st.spinner(f"Scanning 5m HA Charts for Strict Breakouts..."):
                live_signals = nse_ha_bb_strategy_5m(current_watchlist, market_sentiment=user_sentiment)
            
            if len(live_signals) > 0:
                sig_html = "<div class='table-container'><table class='v38-table'><tr><th>Stock</th><th>Entry</th><th>LTP</th><th>Signal</th><th>SL</th><th>Target (BB)</th><th>Target (1:3)</th><th>Time</th></tr>"
                for sig in live_signals:
                    sig_clr = "green" if sig['Signal'] == "BUY" else "red"
                    sig_html += f"<tr><td style='color:{sig_clr}; font-weight:bold;'>{sig['Stock']}</td><td>{fmt_price(sig['Entry'])}</td><td>{fmt_price(sig['LTP'])}</td><td style='color:white; background:{sig_clr}; font-weight:bold;'>{sig['Signal']}</td><td>{fmt_price(sig['SL'])}</td><td style='font-weight:bold; color:#1a73e8;'>{fmt_price(sig['Target(BB)'])}</td><td style='font-weight:bold; color:#856404;'>{fmt_price(sig['T2(1:3)'])}</td><td>{sig['Time']}</td></tr>"
                sig_html += "</table></div>"
                st.markdown(sig_html, unsafe_allow_html=True)
            else:
                st.info("⏳ Waiting for setup... No strict 5m HA+BB breakout found yet.")
        else:
            st.markdown("<div class='section-title'>🎯 LIVE SIGNALS (ALL CRYPTO FUTURES - 1H HA+BB)</div>", unsafe_allow_html=True)
            with st.spinner("Scanning ALL 70+ CoinDCX Crypto Futures..."):
                crypto_signals = crypto_ha_bb_strategy(CRYPTO_SECTORS["ALL COINDCX FUTURES"])
            
            if len(crypto_signals) > 0:
                c_sig_html = "<div class='table-container'><table class='v38-table'><tr><th>Coin</th><th>Entry (Norm)</th><th>LTP</th><th>Signal</th><th>SL (Norm)</th><th>Target (BB)</th><th>Target (1:3)</th><th>Alert Time</th></tr>"
                for sig in crypto_signals:
                    sig_clr = "green" if sig['Signal'] == "BUY" else "red"
                    c_sig_html += f"<tr><td style='color:{sig_clr}; font-weight:bold;'>{sig['Coin']}</td><td>${fmt_price(sig['Entry'])}</td><td>${fmt_price(sig['LTP'])}</td><td style='color:white; background:{sig_clr}; font-weight:bold;'>{sig['Signal']}</td><td>${fmt_price(sig['SL'])}</td><td style='font-weight:bold; color:#1a73e8;'>${fmt_price(sig['Target(BB)'])}</td><td style='font-weight:bold; color:#856404;'>${fmt_price(sig['Target(1:3)'])}</td><td>{sig['Time']}</td></tr>"
                c_sig_html += "</table></div>"
                st.markdown(c_sig_html, unsafe_allow_html=True)
            else:
                st.info("⏳ Waiting for setup... No 1-Hour Heikin-Ashi BB Signal found yet.")

        # 🚨 NEW: INTERACTIVE TRADE JOURNAL 🚨
        st.markdown("<div class='section-title'>📝 TRADE JOURNAL (MANUAL LOG)</div>", unsafe_allow_html=True)
        
        with st.expander("➕ Add New Trade to Journal"):
            with st.form("journal_form"):
                j_col1, j_col2, j_col3, j_col4 = st.columns(4)
                with j_col1: j_asset = st.text_input("Asset (e.g. ITC.NS / BTC-USD)")
                with j_col2: j_signal = st.selectbox("Signal", ["BUY", "SHORT"])
                with j_col3: j_entry = st.number_input("Entry Price", min_value=0.0, format="%.4f")
                with j_col4: j_exit = st.number_input("Exit Price", min_value=0.0, format="%.4f")
                
                submit_trade = st.form_submit_button("💾 Save Trade")
                
                if submit_trade and j_asset != "":
                    if j_entry > 0 and j_exit > 0:
                        if j_signal == "BUY": pnl_pct = ((j_exit - j_entry) / j_entry) * 100
                        else: pnl_pct = ((j_entry - j_exit) / j_entry) * 100
                        
                        st.session_state['trade_journal'].append({
                            "Date": datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M"),
                            "Asset": j_asset.upper(),
                            "Signal": j_signal,
                            "Entry": j_entry,
                            "Exit": j_exit,
                            "P&L %": round(pnl_pct, 2)
                        })
                        st.success("✅ Trade saved successfully! (Note: Journal resets on page hard-refresh)")

        if len(st.session_state['trade_journal']) > 0:
            df_journal = pd.DataFrame(st.session_state['trade_journal'])
            
            df_display = df_journal.copy()
            df_display['Entry'] = df_display['Entry'].apply(lambda x: fmt_price(x))
            df_display['Exit'] = df_display['Exit'].apply(lambda x: fmt_price(x))
            df_display['P&L %'] = df_display['P&L %'].apply(lambda x: f"+{x}%" if x >= 0 else f"{x}%")
            
            st.dataframe(df_display, use_container_width=True)
            
            csv_journal = df_journal.to_csv(index=False).encode('utf-8')
            c_btn1, c_btn2 = st.columns([1, 1])
            with c_btn1:
                st.download_button("📥 Export Journal to Excel", data=csv_journal, file_name=f"Haridas_Journal_{datetime.date.today()}.csv", mime="text/csv")
            with c_btn2:
                if st.button("🗑️ Clear Journal"):
                    st.session_state['trade_journal'] = []
                    st.rerun()
        else:
            st.info("No trades logged yet today. Use the '+ Add New Trade' button above to track your P&L.")

    # --- COLUMN 3 (GAINERS & LOSERS) ---
    with col3:
        st.markdown("<div class='section-title'>🚀 LIVE TOP GAINERS</div>", unsafe_allow_html=True)
        if gainers:
            g_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for g in gainers: 
                prefix = "$" if market_mode != "🇮🇳 Indian Market (NSE)" else "₹"
                g_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{g['Stock']}</td><td>{prefix}{fmt_price(g['LTP'])}</td><td style='color:green; font-weight:bold;'>+{g['Pct']}%</td></tr>"
            g_html += "</table></div>"
            st.markdown(g_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center;'>No live gainers data.</p>", unsafe_allow_html=True)

        st.markdown("<div class='section-title'>🔻 LIVE TOP LOSERS</div>", unsafe_allow_html=True)
        if losers:
            l_html = "<div class='table-container'><table class='v38-table'><tr><th>Asset</th><th>LTP</th><th>%</th></tr>"
            for l in losers: 
                prefix = "$" if market_mode != "🇮🇳 Indian Market (NSE)" else "₹"
                l_html += f"<tr><td style='text-align:left; font-weight:bold; color:#003366;'>{l['Stock']}</td><td>{prefix}{fmt_price(l['LTP'])}</td><td style='color:red; font-weight:bold;'>{l['Pct']}%</td></tr>"
            l_html += "</table></div>"
            st.markdown(l_html, unsafe_allow_html=True)
        else: st.markdown("<p style='font-size:12px;text-align:center;'>No live losers data.</p>", unsafe_allow_html=True)

# ==================== OTHER SECTIONS ====================
elif page_selection in ["🌅 9:10 AM: Pre-Market Gap", "🚀 9:15 AM: Opening Movers", "🚀 24H Crypto Movers"]:
    st.markdown(f"<div class='section-title'>{page_selection}</div>", unsafe_allow_html=True)
    with st.spinner("Scanning ALL Assets..."):
        movers = get_opening_movers(all_assets)
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

elif page_selection == "⚙️ Scanner Settings":
    st.markdown("<div class='section-title'>⚙️ Scanner Settings</div>", unsafe_allow_html=True)
    st.success("Your terminal is fully integrated. PURE LIVE data mode is active with dynamic decimal formatting.")

elif page_selection == "📊 Backtest Engine":
    st.markdown("<div class='section-title'>📊 Backtest Engine (Real Historical Data)</div>", unsafe_allow_html=True)
    bt_col1, bt_col2 = st.columns(2)
    with bt_col1:
        bt_stock = st.selectbox("Select Asset to Backtest:", all_assets, index=0)
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

if auto_refresh:
    time.sleep(refresh_time * 60)
    st.rerun()
