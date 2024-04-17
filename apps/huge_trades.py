import asyncio
import json
import os
import pytz

from datetime import datetime
from websockets import connect
from termcolor import cprint

symbols = ["dogeusdt", "shibusdt", "solusdt", "dotusdt"]
websocket_url_base = "wss://fstream.binance.com/ws/"
my_timezone = pytz.timezone("Europe/Berlin")
lower_border = 10000
higher_border = 100000


class TradeAggregator:
    def __init__(self):
        self.trade_buckets = {}

    async def add_trade(self, symbol, second, usd_size, is_buyer_maker):
        trade_key = (symbol, second, is_buyer_maker)
        self.trade_buckets[trade_key] = self.trade_buckets.get(trade_key, 0) + usd_size

    async def check_and_print_trades(self):
        timestamp_now = datetime.now(my_timezone).strftime("%H:%M:%S")
        deletetions = []
        for trade_key, usd_size in self.trade_buckets.items():
            symbol, second, is_buyer_maker = trade_key
            if second < timestamp_now and usd_size > higher_border:
                attrs = ["bold"]
                back_color = "on_blue" if not is_buyer_maker else "on_magenta"
                trade_type = "BUY" if not is_buyer_maker else "SELL"
                if usd_size > higher_border:
                    usd_size = usd_size / 1000000
                    cprint(
                        f"\033[5m{trade_type} {symbol} {second} ${usd_size:.2f}m\033[0m",
                        "white",
                        back_color,
                        attrs=attrs,
                    )
                else:
                    usd_size = usd_size / 1000000
                    cprint(
                        f"{trade_type} {symbol} {second} ${usd_size:.2f}m",
                        "white",
                        back_color,
                        attrs=attrs,
                    )
                deletetions.append(trade_key)

        for key in deletetions:
            del self.trade_buckets[key]


trade_aggregator = TradeAggregator()


async def binance_trade_stream(uri, symbol, filename, aggregator):
    async with connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                usd_size = float(data["p"]) * float(data["q"])
                trade_time = datetime.fromtimestamp(data["T"] / 1000, my_timezone)
                readable_trade_time = trade_time.strftime("%H:%M:%S")

                await aggregator.add_trade(
                    symbol.upper().replace("USDT", ""),
                    readable_trade_time,
                    usd_size,
                    data["m"],
                )

            except:
                await asyncio.slep(5)


async def print_aggregated_trades_every_second(aggregator):
    while True:
        await asyncio.sleep(1)
        await aggregator.check_and_print_trades()


async def main():
    filename = "binance_trades_big.csv"
    trade_stream_tasks = [
        binance_trade_stream(
            f"{websocket_url_base}{symbol}@aggTrade", symbol, filename, trade_aggregator
        )
        for symbol in symbols
    ]
    print_task = asyncio.create_task(
        print_aggregated_trades_every_second(trade_aggregator)
    )
    await asyncio.gather(*trade_stream_tasks, print_task)


asyncio.run(main())
