# coding: utf-8
from copy import deepcopy
from .entities import Account, Exchange
from .utils import validate_id
from .errors import CancelError, ConflictedError

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
            raise ValidationError("Invalid credit id format %s" % self.id)
        if self.id in repo.credits_bloom:
            raise ConflictedError("Credit id %s is already occupied" % self.id)
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
            raise ValidationError("Invalid debit id format %s" % self.id)
        if self.id in repo.debits_bloom:
            raise ConflictedError("Debit id %s is already occupied" % self.id)
        account = repo.accounts.find(self.account_id)
        account.adjust(self.balance_diff)
        repo.debits_bloom.add(self.id)

class ExchangeCreated(Event):
    def __init__(self, revision, coin_type, price_type):
        self.id = id
        self.revision = revision
        self.coin_type = coin_type
        self.price_type = price_type

    @classmethod
    def build(cls, repo, coin_type, price_type):
        return cls(repo.revision + 1, coin_type, price_type)

    def apply(self, repo):
        exchange = Exchange(self.coin_type, self.price_type)
        if not repo.exchanges.get(exchange.id):
            repo.exchanges.add(exchange)

class OrderCreated(Event):
    def __init__(self, revision, order, balance_diff):
        self.revision = revision
        self.order = deepcopy(order)
        self.balance_diff = balance_diff

    @classmethod
    def build(cls, repo, id, klass, account_id, coin_type, price_type, price, amount, fee_rate):
        account = repo.accounts.find(account_id)
        order = klass(id, account_id, coin_type, price_type, price, amount, fee_rate)
        balance_diff = order.build_balance_diff_for_create(account)
        return cls(repo.revision + 1, order, balance_diff)

    def apply(self, repo):
        account = repo.accounts.find(self.order.account_id)
        exchange = repo.exchanges.find(self.order.exchange_id)
        if repo.orders.get(self.order.id):
            raise ConflictedError("Order %s already created" % self.order.id)
        order = deepcopy(self.order)
        account.adjust(self.balance_diff)
        repo.orders.add(order)
        exchange.enqueue(order)

class OrderCanceled(Event):
    def __init__(self, revision, order_id, balance_diff):
        self.revision = revision
        self.order_id = order_id
        self.balance_diff = balance_diff

    @classmethod
    def build(cls, repo, order_id):
        order = repo.orders.find(order_id)
        account = repo.accounts.find(order.account_id)
        balance_diff = order.build_balance_diff_for_close(account)
        return cls(repo.revision + 1, order_id, balance_diff)

    def apply(self, repo):
        order = repo.orders.find(self.order_id)
        exchange = repo.exchanges.find(order.exchange_id)
        account = repo.accounts.find(order.account_id)
        account.adjust(self.balance_diff)
        repo.orders.remove(order.id)
        exchange.dequeue(order)

class OrderDealed(Event):
    def __init__(self, revision, deal, balance_diffs):
        pass

    def build(self, repo, ask_order_id, bid_order_id):
        pass
