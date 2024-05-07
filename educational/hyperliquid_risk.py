import educational.hyperliquid_testnet_funcs as funcs

account = funcs.account

symbol = "WIF"
max_loss = -5
target = 4
acct_min = 9
timeframe = "4h"
size = 10
coin = symbol

acct_min = 7


def bot():

    print("this is our bot")

    print("controlling risk with our pnl close")

    # check pnl close
    funcs.pnl_close(symbol, target, max_loss, account)

    # if we have over X positions

    # if my account size goes under $100, and never $70
    acct_val = float(funcs.acct_bal(account))

    if acct_val < acct_min:
        print(f"account value is {acct_val} and closing because out low is {acct_min}")
        funcs.kill_switch(symbol, account)


bot()
