# Import libraries
import oandapyV20
from oandapyV20.endpoints.instruments import InstrumentsCandles
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.positions import PositionList
from oandapyV20.endpoints.pricing import PricingStream
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone, timedelta
import random
import json

# OANDA API Credentials
# Note: Replace with your own credentials securely (see README for instructions)
OANDA_API_KEY = "YOUR_OANDA_API_KEY_HERE"  # Placeholder
ACCOUNT_ID = "YOUR_ACCOUNT_ID_HERE"  # Placeholder
client = oandapyV20.API(access_token=OANDA_API_KEY)

class RealisticExecution:
    def __init__(self):
        self.slippage = 0.02
        self.partial_fill_prob = 0.1
        self.spread = 0.02
        self.commission_per_lot = 0.5

    def adjust_price(self, price, trade_type):
        slippage = self.slippage if random.random() > 0.5 else -self.slippage
        if trade_type == 'BUY':
            adjusted_price = price + self.spread + slippage
        else:
            adjusted_price = price - self.spread + slippage
        adjusted_price += self.commission_per_lot * 0.01
        if random.random() < self.partial_fill_prob:
            return round(adjusted_price * 0.5, 3)
        return round(adjusted_price, 3)

def fetch_latest_data(instrument, granularity="H4", count=3):
    print(f"{datetime.now(timezone.utc)} - Fetching latest data for {instrument}")
    params = {"granularity": granularity, "count": count}
    request = InstrumentsCandles(instrument=instrument, params=params)
    response = client.request(request)
    data = [candle for candle in response['candles'] if candle.get('complete')]
    df = pd.DataFrame([{
        'time': candle['time'],
        'open': float(candle['mid']['o']),
        'high': float(candle['mid']['h']),
        'low': float(candle['mid']['l']),
        'close': float(candle['mid']['c'])
    } for candle in data])
    df['time'] = pd.to_datetime(df['time'], utc=True)
    print(f"{datetime.now(timezone.utc)} - Fetched {len(df)} candles")
    return df

def get_current_price(instrument, timeout=10):
    print(f"{datetime.now(timezone.utc)} - Getting current price for {instrument}")
    params = {"instruments": instrument}
    stream = PricingStream(accountID=ACCOUNT_ID, params=params)
    start_time = time.time()
    
    try:
        response = client.request(stream)
        for msg in response:
            if time.time() - start_time > timeout:
                print(f"{datetime.now(timezone.utc)} - Timeout ({timeout}s) reached while waiting for price")
                return None
            if msg['type'] == 'PRICE':
                bid = float(msg['bids'][0]['price'])
                ask = float(msg['asks'][0]['price'])
                price = round((bid + ask) / 2, 3)
                print(f"{datetime.now(timezone.utc)} - Current price: {price}")
                return price
            time.sleep(0.1)
    except Exception as e:
        print(f"{datetime.now(timezone.utc)} - Error getting price: {str(e)}")
        return None
    print(f"{datetime.now(timezone.utc)} - No price received")
    return None

def is_market_open(instrument):
    price = get_current_price(instrument)
    is_open = price is not None
    print(f"{datetime.now(timezone.utc)} - Market open check for {instrument}: {is_open}")
    return is_open

def is_trading_allowed():
    now = datetime.now(timezone.utc)
    hour = now.hour
    allowed = not (21 <= hour < 23)
    print(f"{datetime.now(timezone.utc)} - Trading allowed check: {allowed}")
    return allowed

def detect_equal_highs_lows(data, tolerance, pip_value):
    eq_high = (data['high'] - data['high'].shift(1)).abs() < tolerance * pip_value
    eq_low = (data['low'] - data['low'].shift(1)).abs() < tolerance * pip_value
    eq_buy = eq_low & (data['close'] > data['open'])
    eq_sell = eq_high & (data['close'] < data['open'])
    buy = eq_buy.iloc[-1]
    sell = eq_sell.iloc[-1]
    print(f"{datetime.now(timezone.utc)} - Signal detection - Buy: {buy}, Sell: {sell}")
    return buy, sell

def create_order(instrument, units, price, sl_price, tp_price, trade_type):
    price = round(price, 3)
    sl_price = round(sl_price, 3)
    tp_price = round(tp_price, 3)
    
    order_data = {
        "order": {
            "instrument": instrument,
            "units": str(units) if trade_type == 'BUY' else str(-units),
            "type": "MARKET",
            "stopLossOnFill": {
                "price": str(sl_price),
                "timeInForce": "GTC"
            },
            "takeProfitOnFill": {
                "price": str(tp_price),
                "timeInForce": "GTC"
            }
        }
    }
    print(f"{datetime.now(timezone.utc)} - Creating {trade_type} order: Price={price}, SL={sl_price}, TP={tp_price}")
    request = OrderCreate(accountID=ACCOUNT_ID, data=order_data)
    response = client.request(request)
    return response

def check_position(instrument):
    request = PositionList(accountID=ACCOUNT_ID)
    response = client.request(request)
    positions = response.get('positions', [])
    for pos in positions:
        if pos['instrument'] == instrument:
            has_position = pos['long']['units'] != "0" or pos['short']['units'] != "0"
            print(f"{datetime.now(timezone.utc)} - Position check for {instrument}: {has_position}")
            return has_position
    print(f"{datetime.now(timezone.utc)} - No position found for {instrument}")
    return False

def live_trading_loop(instrument, params):
    executor = RealisticExecution()
    pip_value = 0.01
    units = 1000
    
    print(f"{datetime.now(timezone.utc)} - Starting live trading for {instrument}...")
    
    while True:
        try:
            print(f"{datetime.now(timezone.utc)} - Starting new trading loop iteration")
            
            # Check if market is open
            if not is_market_open(instrument):
                print(f"{datetime.now(timezone.utc)} - Market is closed for {instrument}")
                time.sleep(60 * 60)
                continue

            # Check trading time restrictions
            if not is_trading_allowed():
                now = datetime.now(timezone.utc)
                print(f"{datetime.now(timezone.utc)} - Trading restricted between 21:00-23:00 UTC")
                next_open = now.replace(hour=23, minute=0, second=0, microsecond=0)
                if now.hour >= 23:
                    next_open += timedelta(days=1)
                wait_seconds = (next_open - now).total_seconds()
                print(f"{datetime.now(timezone.utc)} - Waiting {wait_seconds/3600:.2f} hours until 23:00 UTC")
                time.sleep(wait_seconds)
                continue
                
            # Fetch latest data
            data = fetch_latest_data(instrument)
            if len(data) < 2:
                print(f"{datetime.now(timezone.utc)} - Insufficient candle data")
                time.sleep(60)
                continue
                
            # Check if we already have a position
            if check_position(instrument):
                print(f"{datetime.now(timezone.utc)} - Existing position detected, waiting")
                time.sleep(60)
                continue
                
            # Generate signal
            buy_signal, sell_signal = detect_equal_highs_lows(data, params['tolerance'], pip_value)
            
            if buy_signal or sell_signal:
                entry_price = get_current_price(instrument)
                if entry_price is None:
                    print(f"{datetime.now(timezone.utc)} - Failed to get current price")
                    time.sleep(60)
                    continue
                    
                adjusted_entry = executor.adjust_price(entry_price, 'BUY' if buy_signal else 'SELL')
                
                if buy_signal:
                    sl_price = adjusted_entry - params['sl_pips'] * pip_value
                    tp_price = adjusted_entry + params['tp_pips'] * pip_value
                    print(f"{datetime.now(timezone.utc)} - BUY signal detected - Entry: {adjusted_entry}")
                    response = create_order(instrument, units, adjusted_entry, sl_price, tp_price, 'BUY')
                    print(f"{datetime.now(timezone.utc)} - Order placed: {response}")
                    
                elif sell_signal:
                    sl_price = adjusted_entry + params['sl_pips'] * pip_value
                    tp_price = adjusted_entry - params['tp_pips'] * pip_value
                    print(f"{datetime.now(timezone.utc)} - SELL signal detected - Entry: {adjusted_entry}")
                    response = create_order(instrument, units, adjusted_entry, sl_price, tp_price, 'SELL')
                    print(f"{datetime.now(timezone.utc)} - Order placed: {response}")
            
            print(f"{datetime.now(timezone.utc)} - Waiting for next H4 candle")
            time.sleep(60 * 60 * 4)
            
        except Exception as e:
            print(f"{datetime.now(timezone.utc)} - Error occurred: {str(e)}")
            time.sleep(60)

# Trading Parameters
pair_params = {
    "GBP_JPY": {
        "equal": {
            "tolerance": 29.80,
            "sl_pips": 49.01,
            "tp_pips": 149.35
        }
    }
}

if __name__ == "__main__":
    instrument = "GBP_JPY"
    strategy = "equal"
    params = pair_params[instrument][strategy]
    live_trading_loop(instrument, params)

# README
# Overview:
# This script implements a live forex trading system for GBP/JPY using the OANDA v20 API. It fetches H4 candlestick data, detects buy/sell signals based on equal highs and lows, and places market orders with stop-loss and take-profit levels, factoring in realistic execution costs (slippage, spread, commission). The system runs continuously, checking market status and trading restrictions, and is designed for Google Colab.
#
# Usage Instructions:
# 1. Open Google Colab (colab.research.google.com) and create a new notebook.
# 2. Install the OANDA library: `!pip install oandapyV20`.
# 3. Set up OANDA credentials securely:
#    - Replace placeholders (e.g., `OANDA_API_KEY = "YOUR_OANDA_API_KEY_HERE"`) with your API key and account ID.
#    - For security, use Colab’s input prompt:
#      ```python
#      OANDA_API_KEY = input("Enter OANDA API Key: ")
#      ACCOUNT_ID = input("Enter OANDA Account ID: ")
#      ```
#    - Do not hardcode credentials to prevent exposure.
# 4. Copy and paste this code into a cell and run it using Shift + Enter.
# 5. Monitor outputs: market status, candle data, signal detection, and order placement details.
#
# Dependencies:
# - Python 3.x
# - Libraries: oandapyV20, pandas, numpy
# - Note: Install `oandapyV20` in Colab; pandas and numpy are pre-installed.
#
# Adapting to Your Needs:
# - Change the instrument by modifying `instrument = "GBP_JPY"` (e.g., to "EUR_USD").
# - Update `pair_params` to adjust strategy parameters (tolerance, stop-loss, take-profit) for each pair.
# - Modify `is_trading_allowed` to change trading restrictions (e.g., remove 21:00–23:00 UTC limit).
# - Customize `detect_equal_highs_lows` for alternative signal logic (e.g., different patterns).
# - Adjust `RealisticExecution` parameters (slippage, spread, commission) to match your account conditions.
# - Change `units` in `live_trading_loop` to adjust position size (e.g., 2000 for 0.02 lots).
#
# Notes:
# - Ensure a stable internet connection for OANDA API calls; rate limits may apply.
# - This uses a live account by default. For demo trading, use a practice account ID and update `client` to `environment="practice"`.
# - The script runs indefinitely, waiting 4 hours between H4 candles; interrupt with Ctrl+C to stop.
# - Monitor Colab’s resource usage, as continuous loops may strain the free tier.
# - Test with small units initially to verify functionality and avoid unintended losses.
# - Contact for support or enhancements (e.g., adding pairs, strategies, or logging).