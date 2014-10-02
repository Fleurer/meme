import time

class BalanceDiff(object):
    def __init__(self, account_id, coin_type, old_active, old_frozen, new_active, new_frozen):
        self.coin_type = coin_type
        self.account_id = account_id
        self.old_active = old_active
        self.old_frozen = old_frozen
        self.new_active = new_active
        self.new_frozen = new_frozen

    @classmethod
    def build(cls, repo, account_id, coin_type, active_diff=0, frozen_diff=0):
        account = repo.accounts.find(account_id)
        old_active = account.active_balances.get(coin_type, 0)
        old_frozen = account.frozen_balances.get(coin_type, 0)
        new_active = old_active + active_diff
        new_frozen = old_frozen + frozen_diff
        assert self.new_frozen >= 0
        assert self.new_active >= 0
        return cls(account_id, coin_type, old_active, old_frozen, new_active, new_frozen)

class Deal(object):
    def __init__(self, bid_order_id, ask_order_id, price, amount, timestamp=None):
        self.bid_order_id = bid_order_id
        self.ask_order_id = ask_order_id
        self.price = price
        self.amount = amount
        self.timestamp = timestamp or int(time.time())

    @classmethod
    def build(cls, repo, bid_order_id, ask_order_id, price, amount):
        bid_order = repo.orders.find(bid_order_id)
        ask_order = repo.orders.find(ask_order_id)
        assert bid_order.rest_amount >= amount
        assert ask_order.rest_amount >= amount
        return cls(bid_order_id, ask_order_id, price, amount)
