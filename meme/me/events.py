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
    def __init__(self, revision, id, account_id, coin_type, balance_revision):
        self.id = id
        self.revision = revision
        self.account_id = account_id
        self.coin_type = coin_type
        self.balance_revision = balance_revision

    @classmethod
    def build(cls, repo, id, account_id, coin_type, amount):
        account = repo.accounts.find(account_id)
        balance = account.find_balance(coin_type)
        balance_revision = balance.build_next(active_diff=amount)
        return cls(repo.revision + 1, id, account_id, coin_type, balance_revision)

    def apply(self, repo):
        if not validate_id(self.id):
            raise ValidationError("Invalid credit id format %s" % self.id)
        if self.id in repo.credits_bloom:
            raise ConflictedError("Credit id %s is already occupied" % self.id)
        account = repo.accounts.find(self.account_id)
        account.adjust(self.balance_revision)
        repo.credits_bloom.add(self.id)

class AccountDebited(Event):
    def __init__(self, revision, id, account_id, coin_type, balance_revision):
        self.id = id
        self.revision = revision
        self.account_id = account_id
        self.coin_type = coin_type
        self.balance_revision = balance_revision

    @classmethod
    def build(cls, repo, id, account_id, coin_type, amount):
        account = repo.accounts.find(account_id)
        balance = account.find_balance(coin_type)
        balance_revision = balance.build_next(active_diff=0-amount)
        return cls(repo.revision + 1, id, account_id, coin_type, balance_revision)

    def apply(self, repo):
        if not validate_id(self.id):
            raise ValidationError("Invalid debit id format %s" % self.id)
        if self.id in repo.debits_bloom:
            raise ConflictedError("Debit id %s is already occupied" % self.id)
        account = repo.accounts.find(self.account_id)
        account.adjust(self.balance_revision)
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
    def __init__(self, revision, order, balance_revision):
        self.revision = revision
        self.order = deepcopy(order)
        self.balance_revision = balance_revision

    @classmethod
    def build(cls, repo, id, klass, account_id, coin_type, price_type, price, amount, fee_rate, timestamp=None):
        account = repo.accounts.find(account_id)
        order = klass(id, account_id, coin_type, price_type, price, amount, fee_rate, timestamp)
        balance_revision = cls.build_balance_revision(account, order)
        return cls(repo.revision + 1, order, balance_revision)

    @classmethod
    def build_balance_revision(self, account, order):
        freeze_amount = order.freeze_amount
        balance = account.find_balance(order.outcome_type)
        return balance.build_next(
                active_diff = 0 - freeze_amount,
                frozen_diff = freeze_amount)

    def apply(self, repo):
        account = repo.accounts.find(self.order.account_id)
        exchange = repo.exchanges.find(self.order.exchange_id)
        if self.order.id in repo.orders_bloom:
            raise ConflictedError("Order %s already created" % self.order.id)
        order = deepcopy(self.order)
        account.adjust(self.balance_revision)
        repo.orders_bloom.add(order.id)
        repo.orders.add(order)
        exchange.enqueue(order)

class OrderCanceled(Event):
    def __init__(self, revision, order_id, balance_revision):
        self.revision = revision
        self.order_id = order_id
        self.balance_revision = balance_revision

    @classmethod
    def build(cls, repo, order_id):
        order = repo.orders.find(order_id)
        account = repo.accounts.find(order.account_id)
        balance_revision = cls.build_balance_revision(account, order)
        return cls(repo.revision + 1, order_id, balance_revision)

    @classmethod
    def build_balance_revision(self, account, order):
        rest_freeze_amount = order.rest_freeze_amount
        balance = account.find_balance(order.outcome_type)
        return balance.build_next(
                active_diff = rest_freeze_amount,
                frozen_diff = 0 - rest_freeze_amount)

    def apply(self, repo):
        order = repo.orders.find(self.order_id)
        exchange = repo.exchanges.find(order.exchange_id)
        account = repo.accounts.find(order.account_id)
        account.adjust(self.balance_revision)
        repo.orders.remove(order.id)
        exchange.dequeue(order)

class OrderDealt(Event):
    def __init__(self, revision, bid_deal, ask_deal, bid_balance_revisions, ask_balance_revisions):
        self.revision = revision
        self.bid_deal = bid_deal
        self.ask_deal = ask_deal
        self.bid_balance_revisions = bid_balance_revisions
        self.ask_balance_revisions = ask_balance_revisions

    @classmethod
    def build_balance_revisions(cls, income_balance, outcome_balance, deal):
        income_revision = income_balance.build_next(
                active_diff = deal.income)
        unfreeze_amount = deal.rest_freeze_amount if deal.rest_amount == 0 else 0
        outcome_revision = outcome_balance.build_next(
                active_diff = unfreeze_amount,
                frozen_diff = 0 - deal.outcome - unfreeze_amount)
        return (income_revision, outcome_revision)

    @classmethod
    def build(cls, repo, bid_deal, ask_deal):
        bid_order = repo.orders.find(bid_deal.order_id)
        ask_order = repo.orders.find(ask_deal.order_id)
        bid_account = repo.accounts.find(bid_order.account_id)
        ask_account = repo.accounts.find(ask_order.account_id)
        bid_income_balance = bid_account.find_balance(bid_order.income_type)
        bid_outcome_balance = bid_account.find_balance(bid_order.outcome_type)
        bid_income_revision, bid_outcome_revision = cls.build_balance_revisions(bid_income_balance, bid_outcome_balance, bid_deal)
        if bid_account.id == ask_account.id:
            ask_income_revision, ask_outcome_revision = cls.build_balance_revisions(bid_outcome_revision, bid_income_revision, ask_deal)
        else:
            ask_income_balance = ask_account.find_balance(ask_order.income_type)
            ask_outcome_balance = ask_account.find_balance(ask_order.outcome_type)
            ask_income_revision, ask_outcome_revision = cls.build_balance_revisions(ask_income_balance, ask_outcome_balance, ask_deal)
        return cls(repo.revision + 1, bid_deal, ask_deal, (bid_income_revision, bid_outcome_revision), (ask_income_revision, ask_outcome_revision))

    def apply(self, repo):
        # 打 cProfile 显示这里的 deepcopy 挺慢的...
        bid_order = deepcopy(repo.orders.find(self.bid_deal.order_id))
        ask_order = deepcopy(repo.orders.find(self.ask_deal.order_id))
        bid_account = deepcopy(repo.accounts.find(bid_order.account_id))
        ask_account = deepcopy(repo.accounts.find(ask_order.account_id))
        exchange = repo.exchanges.find(bid_order.exchange_id)
        bid_order.append_deal(self.bid_deal)
        ask_order.append_deal(self.ask_deal)
        [bid_account.adjust(revision) for revision in self.bid_balance_revisions]
        [ask_account.adjust(revision) for revision in self.ask_balance_revisions]
        [exchange.dequeue_if_completed(order) for order in [bid_order, ask_order]]
        [repo.orders.add(order) for order in [bid_order, ask_order]]
        [repo.accounts.add(account) for account in [bid_account, ask_account]]
