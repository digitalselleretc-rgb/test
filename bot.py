# bot.py
# --- RUN THIS WITH LINUX PYTHON ---
import time
import json
import google.generativeai as genai
import rpyc
import pandas as pd
import pandas_ta as ta 

# ================= CONFIGURATION =================
API_KEY = "AIzaSyDqlz6OT3U4WkCZoJhXgqDibH62Yq54Wlg" # <--- PASTE KEY HERE
SYMBOL = "EURUSD"     # Check your broker (might be "EURUSD.m")
TIMEFRAME = 16385     # MT5 code for H1 Timeframe
VOLUME = 0.01         # Lot size
# =================================================

# 1. CONNECT TO GEMINI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. CONNECT TO BRIDGE (WINE)
try:
    conn = rpyc.connect("localhost", 18812)
    mt5 = conn.root.get_mt5() # Get the MT5 object from Wine
    print("✅ Connected to Bridge!")
except Exception as e:
    print(f"❌ Could not connect to bridge. Is bridge.py running? Error: {e}")
    quit()

def get_market_data():
    # Get last 50 candles
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 50)
    
    if rates is None:
        print(f"❌ MT5 Error: {mt5.last_error()}")
        return None

    # Convert to DataFrame (Gemini likes nice tables)
    df = pd.DataFrame(list(rates), columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Calculate Technical Indicators (Crucial for AI)
    df['RSI'] = df.ta.rsi(length=14)
    df['EMA_50'] = df.ta.ema(length=50)
    df['ATR'] = df.ta.atr(length=14)
    
    # Drop empty rows and convert to string for Gemini
    return df.tail(10).to_string()

def ask_gemini(data_str):
    prompt = f"""
    Act as a professional Forex Scalper using Price Action and RSI.
    Analyze this recent H1 data for {SYMBOL}:
    {data_str}

    Logic:
    - BUY if price is above EMA_50 and RSI < 70 (Trend pullbacks).
    - SELL if price is below EMA_50 and RSI > 30.
    - WAIT if no clear signal.
    
    Provide output STRICTLY in this JSON format (no other text):
    {{
      "action": "BUY" or "SELL" or "WAIT",
      "entry": float,
      "sl": float,
      "tp": float,
      "reason": "short explanation"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini Brain Freeze: {e}")
        return None

def execute_trade(signal):
    if signal['action'] == "WAIT":
        print(f"😴 Gemini says WAIT: {signal['reason']}")
        return

    # Prepare Order
    action_type = mt5.ORDER_TYPE_BUY if signal['action'] == "BUY" else mt5.ORDER_TYPE_SELL
    
    # Get current ASK/BID
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        print("Failed to get tick prices")
        return
        
    price = tick.ask if signal['action'] == "BUY" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,
        "type": action_type,
        "price": price,
        "sl": float(signal['sl']),
        "tp": float(signal['tp']),
        "magic": 123456,
        "comment": "Gemini AutoTrade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send Order
    print(f"🚀 Sending {signal['action']} Order...")
    result = mt5.order_send(request)
    print(f"Trade Result: {result}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    while True:
        print(f"\n--- Analyzing {SYMBOL} ---")
        data = get_market_data()
        
        if data:
            signal = ask_gemini(data)
            if signal:
                print(f"💡 Strategy: {signal}")
                execute_trade(signal)
        
        print("Sleeping for 1 hour (candle close)...")
        time.sleep(3600) 
