import ccxt
import pandas as pd
import talib as ta
import calendar
import pandas_ta as pta

from datetime import datetime, timezone
from pprint import pprint

exchange = ccxt.hyperliquid()

symbol = "SOL/USDC:USDC"
timeframe = "1h"
days = 90


now = datetime.now(timezone.utc)
unixtime = calendar.timegm(now.utctimetuple())
since = (unixtime - 60 * 60 * 24 * days) * 1000  # UTC timestamp in milliseconds


"""
markets = exchange.load_markets()

for market in markets:
    print(market)
"""


def df_rsi(symbol=symbol, timeframe=timeframe, since=since):

    print("starting indis...")

    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=10000)

    # pandas & TA, talib
    df_rsi = pd.DataFrame(
        bars, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df_rsi["timestamp"] = pd.to_datetime(df_rsi["timestamp"], unit="ms")

    # RSI
    rsi = ta.RSI(df_rsi["close"], timeperiod=14)
    df_rsi["rsi"] = rsi

    ema = pta.ema(df_rsi["close"], length=5)
    df_rsi["ema"] = ema

    print(df_rsi)


df_rsi()
