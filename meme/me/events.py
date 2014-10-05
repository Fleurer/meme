from .entities import Account
from .utils import validate_id
from .errors import CancelError

class Event(object):
    # 实施修改，修改前务必做完所有的检查
    def apply(self, repo):
        raise NotImplementedError

    def as_json(self):
        raise NotImplementedError

    def to_json(self):
        raise NotImplementedError

    @classmethod
    def build_by_json(cls, json):
        raise NotImplementedError

class AccountCreated(Event):
    def __init__(self, revision, account_id):
        self.revision = revision
        self.account_id = account_id

    @classmethod
    def build(cls, repo, account_id):
        return cls(repo.revision + 1, account_id)

    def apply(self, repo):
        if repo.accounts.get(self.account_id):
            return
        account = Account(self.account_id)
        repo.accounts.add(account)

class AccountCanceled(Event):
    def __init__(self, revision, account_id):
        self.revision = revision
        self.account_id = account_id

    @classmethod
    def build(cls, repo, account_id):
        return cls(repo.revision + 1, account_id)

    def apply(self, repo):
        account = repo.accounts.get(self.account_id)
        if account and not account.is_empty():
            raise CancelError("Account #%s is not empty, can not cancel" % self.account_id)
        repo.accounts.remove(self.account_id)

class AccountCredited(Event):
    def __init__(self, revision, id, account_id, coin_type, balance_diff):
        self.id = id
        self.revision = revision
        self.account_id = account_id
        self.coin_type = coin_type
        self.balance_diff = balance_diff

    @classmethod
    def build(cls, repo, id, account_id, coin_type, amount):
        account = repo.accounts.find(account_id)
        balance_diff = account.build_balance_diff(coin_type, active_diff=amount)
        return cls(repo.revision + 1, id, account_id, coin_type, balance_diff)

    def apply(self, repo):
        if not validate_id(self.id):
            raise InvalidId("Invalid credit id format %s" % self.id)
        if self.id in repo.credits_bloom:
            raise InvalidId("Credit id %s is already occupied" % self.id)
        account = repo.accounts.find(self.account_id)
        account.adjust(self.balance_diff)
        repo.credits_bloom.add(self.id)

class AccountDebited(Event):
    def __init__(self, revision, id, account_id, coin_type, balance_diff):
        self.id = id
        self.revision = revision
        self.account_id = account_id
        self.coin_type = coin_type
        self.balance_diff = balance_diff

    @classmethod
    def build(cls, repo, id, account_id, coin_type, amount):
        account = repo.accounts.find(account_id)
        balance_diff = account.build_balance_diff(coin_type, active_diff=0-amount)
        return cls(repo.revision + 1, id, account_id, coin_type, balance_diff)

    def apply(self, repo):
        if not validate_id(self.id):
            raise InvalidId("Invalid debit id format %s" % self.id)
        if self.id in repo.debits_bloom:
            raise InvalidId("Debit id %s is already occupied" % self.id)
        account = repo.accounts.find(self.account_id)
        account.adjust(self.balance_diff)
        repo.debits_bloom.add(self.id)

class BidOrderCreated(Event):
    def __init__(self, revision, id, account_id, exchange_id, price, amount, balance_diffs):
        self.revision = revision
        self.account_id = account_id
        self.exchange_id = exchange_id

class AskOrderCreated(Event):
    def __init__(self, revision, id, account_id, exchange_id, price, amount, balance_diffs):
        self.revision = revision

class OrderCanceled(Event):
    def __init__(self, revision, order_id, balance_diffs):
        pass

class OrderDealed(Event):
    def __init__(self, revision, deal, balance_diffs):
        pass

    def build(self, repo, ask_order_id, bid_order_id):
        pass
