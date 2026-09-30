from typing import Dict, List, Any, Optional
import uuid

# MT5 Constants Mock
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TIME_GTC = 0
ORDER_FILLING_FOK = 1
ORDER_FILLING_IOC = 2
ORDER_FILLING_RETURN = 4
TRADE_ACTION_DEAL = 1
TRADE_RETCODE_DONE = 10009
TRADE_RETCODE_REJECT = 10006
TRADE_RETCODE_INVALID_PRICE = 10015
TRADE_RETCODE_INVALID_VOLUME = 10014
TRADE_RETCODE_NO_MONEY = 10019
ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2

class FakeMT5SymbolInfo:
    def __init__(self, ask=2000.50, bid=2000.00, filling_mode=SYMBOL_FILLING_IOC, contract_size=100.0, vol_min=0.01, vol_max=100.0, vol_step=0.01):
        self.ask = ask
        self.bid = bid
        self.filling_mode = filling_mode
        self.trade_contract_size = contract_size
        self.volume_min = vol_min
        self.volume_max = vol_max
        self.volume_step = vol_step

class FakeMT5AccountInfo:
    def __init__(self, equity=10000.0, balance=10000.0, trade_mode=ACCOUNT_TRADE_MODE_DEMO):
        self.equity = equity
        self.balance = balance
        self.trade_mode = trade_mode

class FakeMT5OrderResult:
    def __init__(self, retcode=TRADE_RETCODE_DONE, comment="Request executed", order=None, deal=None, price=2000.0):
        self.retcode = retcode
        self.comment = comment
        self.order = order or int(uuid.uuid4().int % 100000)
        self.deal = deal or int(uuid.uuid4().int % 100000)
        self.price = price

class FakeMT5Deal:
    def __init__(self, position_id, profit=10.0, commission=-1.0, swap=-0.5, fee=0.0):
        self.position_id = position_id
        self.profit = profit
        self.commission = commission
        self.swap = swap
        self.fee = fee

class FakeMT5Position:
    def __init__(self, ticket):
        self.ticket = ticket

class FakeMT5:
    def __init__(self):
        self.fail_init = False
        self.fail_login = False
        self.fail_order_send = False
        self.order_retcode = TRADE_RETCODE_DONE
        self.account_equity = 10000.0
        self.trade_mode = ACCOUNT_TRADE_MODE_DEMO
        self.active_positions = {}
        self.deals = {}
        self.last_err = (0, "Success")

        # Expose constants natively
        self.ORDER_TYPE_BUY = ORDER_TYPE_BUY
        self.ORDER_TYPE_SELL = ORDER_TYPE_SELL
        self.ORDER_TIME_GTC = ORDER_TIME_GTC
        self.ORDER_FILLING_FOK = ORDER_FILLING_FOK
        self.ORDER_FILLING_IOC = ORDER_FILLING_IOC
        self.ORDER_FILLING_RETURN = ORDER_FILLING_RETURN
        self.TRADE_ACTION_DEAL = TRADE_ACTION_DEAL
        self.TRADE_RETCODE_DONE = TRADE_RETCODE_DONE
        self.TRADE_RETCODE_REJECT = TRADE_RETCODE_REJECT
        self.ACCOUNT_TRADE_MODE_DEMO = ACCOUNT_TRADE_MODE_DEMO
        self.ACCOUNT_TRADE_MODE_REAL = ACCOUNT_TRADE_MODE_REAL
        self.SYMBOL_FILLING_FOK = SYMBOL_FILLING_FOK
        self.SYMBOL_FILLING_IOC = SYMBOL_FILLING_IOC

    def initialize(self):
        if self.fail_init:
            self.last_err = (-6, 'Terminal: Authorization failed')
            return False
        return True

    def login(self, login, password, server):
        if self.fail_login:
            self.last_err = (-6, 'Terminal: Authorization failed')
            return False
        return True

    def shutdown(self):
        pass

    def last_error(self):
        return self.last_err

    def account_info(self):
        return FakeMT5AccountInfo(equity=self.account_equity, trade_mode=self.trade_mode)

    def symbol_info(self, symbol):
        return FakeMT5SymbolInfo()

    def symbol_info_tick(self, symbol):
        return FakeMT5SymbolInfo() # Has ask/bid

    def order_check(self, request):
        return FakeMT5OrderResult(retcode=self.order_retcode, comment="Check OK")

    def order_send(self, request):
        if self.fail_order_send:
            return FakeMT5OrderResult(retcode=self.order_retcode, comment="Forced Failure")

        res = FakeMT5OrderResult(retcode=self.order_retcode)

        # If it's a market deal, register the position/deal
        if request.get("action") == self.TRADE_ACTION_DEAL:
            # Check if this is a closing order (position field is set)
            pos_id = request.get("position", 0)
            if pos_id > 0:
                if pos_id in self.active_positions:
                    del self.active_positions[pos_id]
                    # Create closing deal
                    self.deals[res.deal] = FakeMT5Deal(position_id=pos_id)
            else:
                # Opening a new position
                self.active_positions[res.order] = FakeMT5Position(ticket=res.order)
                self.deals[res.deal] = FakeMT5Deal(position_id=res.order)

        return res

    def positions_get(self, ticket=None):
        if ticket:
            if ticket in self.active_positions:
                return (self.active_positions[ticket],)
            return ()
        return tuple(self.active_positions.values())

    def history_deals_get(self, position=None, ticket=None):
        res = []
        for d in self.deals.values():
            if position and d.position_id == position:
                res.append(d)
        return tuple(res)

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        mock_data = []
        import random
        price = 2000.0
        for i in range(count):
            price += random.uniform(-5, 5)
            mock_data.append({
                "time": f"2024-01-01T{i%24:02d}:00:00Z",
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + random.uniform(-1, 1),
                "volume": 100
            })
        return mock_data
