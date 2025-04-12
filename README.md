# liveoandacode
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
