from eth_account.signers.local import LocalAccount
import eth_account
import json
import time
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import pandas as pd
import datetime
import schedule
import requests

from decouple import config

account: LocalAccount = eth_account.Account.from_key(config("web3_private_key"))
base_url = constants.TESTNET_API_URL


def ask_bid(symbol):

    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}

    data = {"type": "l2Book", "coin": symbol}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    l2_data = l2_data["levels"]
    # print(l2_data)

    # get bid and ask
    bid = float(l2_data[0][0]["px"])
    ask = float(l2_data[1][0]["px"])

    return ask, bid, l2_data


def limit_order(coin, is_buy, sz, limit_px, reduce_only):

    exchange = Exchange(account, base_url)

    rounding = get_sz_px_decimals(coin)[0]
    sz = round(sz, rounding)
    # limit_px = round(limit_px,rounding)
    print(f"placing limit order for {coin} {sz} @ {limit_px}")
    order_result = exchange.order(
        coin, is_buy, sz, limit_px, {"limit": {"tif": "Gtc"}}, reduce_only=reduce_only
    )

    if is_buy == True:
        print(
            f"limit BUY order placed thanks moon, resting: {order_result['response']['data']['statuses'][0]}"
        )
    else:
        print(
            f"limit SELL order placed thanks moon, resting: {order_result['response']['data']['statuses'][0]}"
        )

    return order_result


def get_sz_px_decimals(symbol):
    """
    this is succesfully returns Size decimals and Price decimals

    this outputs the size decimals for a given symbol
    which is - the SIZE you can buy or sell at
    ex. if sz decimal == 1 then you can buy/sell 1.4
    if sz decimal == 2 then you can buy/sell 1.45
    if sz decimal == 3 then you can buy/sell 1.456

    if size isnt right, we get this error. to avoid it use the sz decimal func
    {'error': 'Invalid order size'}
    """
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    data = {"type": "meta"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        # Success
        data = response.json()
        # print(data)
        symbols = data["universe"]
        symbol_info = next((s for s in symbols if s["name"] == symbol), None)
        if symbol_info:
            sz_decimals = symbol_info["szDecimals"]

        else:
            print("Symbol not found")
    else:
        # Error
        print("Error:", response.status_code)

    ask = ask_bid(symbol)[0]
    # print(f'this is the ask {ask}')

    # Compute the number of decimal points in the ask price
    ask_str = str(ask)
    if "." in ask_str:
        px_decimals = len(ask_str.split(".")[1])
    else:
        px_decimals = 0

    print(f"{symbol} this is the price {sz_decimals} decimal(s)")

    return sz_decimals, px_decimals
