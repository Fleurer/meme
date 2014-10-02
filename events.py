class Event(object):
    def apply(self, repo):
        raise NotImplementedError

    def as_json(self):
        raise NotImplementedError

    def to_json(self):
        raise NotImplementedError

    @classmethod
    def build_by_json(cls, json):
        raise NotImplementedError

class AccountCredited(Event):
    def __init__(self, repo, revision, account_id, coin_type, balance_diff):
        self.repo = repo
        self.revision = revision
        self.account_id = account_id
        self.coin_type = coin_type
        self.balance_diffs = balance_diffs

    def apply(self):
        account = self.repo.accounts.find(self.account_id)
        account.active_balances[self.coin_type] = balance_diff.new_active

    @classmethod
    def build(self, repo, account_id, coin_type, amount):
        pass

class AccountDebited(Event):
    def __init__(self, revision, account_id, coin_type, amount, balance_diffs):
        pass

class BidOrderCreated(Event):
    def __init__(self, revision, id, account_id, exchange_id, price, amount, balance_diffs):
        self.revision = revision
        self.account_id = account_id
        self.exchange_id = exchange_id

class AskOrderCreated(Event):
    def __init__(self, revision, id, account_id, exchange_id, price, amount, balance_diffs):
        pass

class OrderCanceled(Event):
    def __init__(self, revision, order_id, balance_diffs):
        pass

class OrderDealed(Event):
    def __init__(self, revision, deal, balance_diffs):
        pass

    def build(self, repo, ask_order_id, bid_order_id):
        pass
