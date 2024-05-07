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
exchange = Exchange(account, base_url)


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


def acct_bal(account):

    # account = LocalAccount = eth_account.Account.from_key(key)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)

    print(
        f'this is current account value: {user_state["marginSummary"]["accountValue"]}'
    )

    acct_value = user_state["marginSummary"]["accountValue"]

    return acct_value


def get_position(symbol, account):
    """
    gets the current position info, like size etc.
    """

    # account = LocalAccount = eth_account.Account.from_key(key)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)

    print(
        f'this is current account value: {user_state["marginSummary"]["accountValue"]}'
    )

    positions = []
    print(f"this is the symbol {symbol}")
    print(user_state["assetPositions"])

    for position in user_state["assetPositions"]:
        if (position["position"]["coin"] == symbol) and float(
            position["position"]["szi"]
        ) != 0:
            positions.append(position["position"])
            in_pos = True
            size = float(position["position"]["szi"])
            pos_sym = position["position"]["coin"]
            entry_px = float(position["position"]["entryPx"])
            pnl_perc = float(position["position"]["returnOnEquity"]) * 100
            print(f"this is the pnl perc {pnl_perc}")
            break
    else:
        in_pos = False
        size = 0
        pos_sym = None
        entry_px = 0
        pnl_perc = 0

    if size > 0:
        long = True
    elif size < 0:
        long = False
    else:
        long = None

    return positions, in_pos, size, pos_sym, entry_px, pnl_perc, long


def cancel_all_orders(account):

    # this cancels all open orders
    # account = LocalAccount = eth_account.Account.from_key(key)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    open_orders = info.open_orders(account.address)

    print("above are the open orders... need to cancel any...")
    for open_order in open_orders:
        # print(f'cancelling order {open_order}')
        exchange.cancel(open_order["coin"], open_order["oid"])


def kill_switch(symbol, account):

    position, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position(
        symbol, account
    )

    while im_in_pos == True:

        cancel_all_orders(account)

        ask, bid, l2 = ask_bid(symbol)

        pos_size = abs(pos_size)

        if long == True:
            limit_order(pos_sym, False, pos_size, ask, True, account)
            print("kill switch - SELL TO CLOSE SUBMITTED ")
            time.sleep(5)
        elif long == False:
            limit_order(pos_sym, True, pos_size, bid, True, account)
            print("kill switch - BUY TO CLOSE SUBMITTED ")
            time.sleep(5)

        position, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position(
            symbol, account
        )

    print("position succesfully closed in the kill switch")


def pnl_close(symbol, target, max_loss, account):
    """
    monitors positions for their pnl and will close the position when you hit the tp/sl

    """

    print("starting pnl close")

    position, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position(
        symbol, account
    )

    if pnl_perc > target:
        print(f"pnl gain is {pnl_perc} and target is {target}... closing position WIN")
        kill_switch(pos_sym, account)
    elif pnl_perc <= max_loss:
        print(
            f"pnl loss is {pnl_perc} and max loss is {max_loss}... closing position LOSS"
        )
        kill_switch(pos_sym, account)
    else:
        print(
            f"pnl loss is {pnl_perc} and max loss is {max_loss} and target {target}... not closing position"
        )

    print("finished with pnl close")
