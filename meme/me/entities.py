# coding: utf-8
import time
import collections
from decimal import Decimal, ROUND_DOWN
import rbtree
from .errors import NotFoundError
from .values import Deal, BalanceDiff
from .consts import PRECISION_EXP

class Repository(object):
    def __init__(self, events=None, accounts=None, orders=None, exchanges=None):
        self.revision = revision
        self.accounts = EntitiesSet(accounts)
        self.orders = EntitiesSet(orders)
        self.exchanges = EntitiesSet(exchanges)
        self.events = events or EventsBuffer()
        self.debit_ids_set = debit_ids_set or bloomfilter.bloomfilter()
        self.credit_ids_set = credit_ids_set or bloomfilter.bloomfilter()

    @classmethod
    def load_snapshot(self, snapshot):
        pass

    def sync(self):
        pass

    def commit(self, event):
        pass

    def flush(self):
        pass

class EntitiesSet(object):
    def __init__(self, name, entities=None):
        self.entities = entities or {}
        self.name = name

    def add(self, entity):
        assert hasattr(entity, 'id')
        self.entities[entity.id] = entity

    def remove(self, id):
        self.entities.pop(id, None)

    def find(self, id):
        entity = self.entities.get(id)
        if not entity:
            raise NotFoundError("%s#%d not found" % (self.name, id))
        return entity

class Account(object):
    def __init__(self, id, active_balances=None, frozen_balances=None):
        self.id = id
        self.active_balances = active_balances or {}
        self.frozen_balances = frozen_balances or {}

    def build_balance_diff(self, coin_type, active_diff=0, frozen_diff=0):
        old_active = self.active_balances.get(coin_type, Decimal('0'))
        old_frozen = self.frozen_balances.get(coin_type, Decimal('0'))
        new_active = old_active + active_diff
        new_frozen = old_frozen + frozen_diff
        assert new_active >= 0
        assert new_frozen >= 0
        return BalanceDiff(self.id, coin_type, old_active, old_frozen, new_active, new_frozen)

class Order(object):
    def __init__(self, id, account_id, coin_type, price_type, price, amount, fee_rate=0.001, deals=None, timestamp=None):
        self.id = id
        self.account_id = account_id
        self.coin_type = coin_type
        self.price_type = price_type
        self.price = Decimal(price).quantize(PRECISION_EXP)
        self.amount = Decimal(amount).quantize(PRECISION_EXP, ROUND_DOWN)
        self.fee_rate = Decimal(fee_rate)
        self.deals = deals or []
        self.timestamp = timestamp or int(time.time())

    @property
    def exchange_id(self):
        return "%s-%s" % (self.coin_type, self.price_type)

    @property
    def rest_amount(self):
        return self.amount - sum([d.amount for d in self.deals])

    @property
    def rest_freeze_amount(self):
        return self.freeze_amount - sum([d.outcome for d in self.deals])

    def append_deal(self, deal):
        self.deals.append(deal)

    def build_balance_diff_for_create(self, account):
        freeze_amount = self.freeze_amount
        balance_diff = account.build_balance_diff(
                self.outcome_type,
                active_diff = 0 - freeze_amount,
                frozen_diff = freeze_amount)
        return balance_diff

    def build_balance_diffs_for_deal(self, account, deal):
        return [
            account.build_balance_diff(self.income_type,  active_diff = deal.income_amount),
            account.build_balance_diff(self.outcome_type, frozen_diff = 0 - deal.outcome_amount),
        ]

    def build_balance_diff_for_close(self, account):
        rest_freeze_amount = self.rest_freeze_amount
        balance_diff = account.build_balance_diff(
                self.outcome_type,
                active_diff = rest_freeze_amount,
                frozen_diff = 0 - rest_freeze_amount)
        return balance_diff

class BidOrder(Order):
    @property
    def income_type(self):
        return self.coin_type

    @property
    def outcome_type(self):
        return self.price_type

    @property
    def freeze_amount(self):
        net_total = ((self.amount * self.price) * (1 + self.fee_rate)).quantize(PRECISION_EXP)
        return net_total

class AskOrder(Order):
    @property
    def income_type(self):
        return self.price_type

    @property
    def outcome_type(self):
        return self.coin_type

    @property
    def freeze_amount(self):
        return self.amount

class Exchange(object):
    def __init__(self, coin_type, price_type, bids=None, asks=None):
        self.coin_type = coin_type
        self.price_type = price_type
        self.bids = rbtree.rbtree(bids or {})
        self.asks = rbtree.rbtree(asks or {})

    @property
    def id(self):
        return "%s-%s" % (self.coin_type, self.price_type)

    def enqueue(self, order):
        rbtree = self._find_rbtree(order)
        queue = rbtree.setdefault(order.price, collections.deque())
        queue.append(order.id)
        rbtree[order.price] = queue

    def dequeue(self, order):
        rbtree = self._find_rbtree(order)
        self._discard(rbtree, order.price, order.id)

    # 最高买价大于等于最低卖价
    def match(self, pop=False):
        bid_price = self.bids.max()
        ask_price = self.asks.min()
        if bid_price >= ask_price:
            bids_queue = self.bids[bid_price]
            asks_queue = self.asks[ask_price]
            bid_id = bids_queue[0]
            ask_id = asks_queue[0]
            if pop:
                self._discard(self.bids, bid_price, bid_id)
                self._discard(self.asks, ask_price, ask_id)
            return (bid_id, ask_id)
        return None

    @classmethod
    def compute_deals(cls, bid, ask):
        assert type(bid) is BidOrder
        assert type(ask) is AskOrder
        assert bid.price >= ask.price
        timestamp = int(time.time())
        # 卖出申报价格低于即时揭示的最高买入申报价格时，以即时揭示的最高买入申报价格为成交价。
        # 买入申报价格高于即时揭示的最低卖出申报价格时，以即时揭示的最低卖出申报价格为成交价。
        if bid.timestamp > ask.timestamp:
            deal_price = ask.price
        else:
            deal_price = bid.price
        # 这里需要 round(:down)，不然会导致成交额大于委托额
        deal_amount = min(bid.rest_amount, ask.rest_amount).quantize(PRECISION_EXP, ROUND_DOWN)
        ask_outcome = deal_amount
        bid_outcome_origin = (ask_outcome * deal_price).quantize(PRECISION_EXP, ROUND_DOWN)
        # 买单手续费 = 买单支出部分 * 买单手续费率，加在买单支出上
        # 卖单手续费 = 卖单收入部分 * 卖单手续费率，扣在卖单收入里
        bid_fee = (bid_outcome_origin * bid.fee_rate).quantize(PRECISION_EXP, ROUND_DOWN)
        ask_fee = (bid_outcome_origin * ask.fee_rate).quantize(PRECISION_EXP, ROUND_DOWN)
        bid_outcome = bid_outcome_origin + bid_fee
        # 买单收入 = 卖单支出
        # 卖单收入 = 买单支出 - 卖单手续费
        bid_income = ask_outcome
        ask_income = bid_outcome_origin - ask_fee
        bid_deal = Deal(ask.id, deal_price, deal_amount, bid_income, bid_outcome, bid_fee, timestamp)
        ask_deal = Deal(bid.id, deal_price, deal_amount, ask_income, ask_outcome, ask_fee, timestamp)
        return (bid_deal, ask_deal)

    def _find_rbtree(self, order):
        if order.exchange_id != self.id:
            raise ValueError("Order#exchange_id<%s> mismatch with Exchange<%s>" % (order.exchange_id, self.id))
        if type(order) is BidOrder:
            return self.bids
        elif type(order) is AskOrder:
            return self.asks
        else:
            raise ValueError("argument is not an Order")

    # 当同价格的队列为空时，删除红黑树中的键
    def _discard(self, rbtree, price, order_id):
        queue = rbtree.get(price)
        if not queue or not order_id in queue:
            return
        queue.remove(order_id)
        if queue == collections.deque():
            del rbtree[price]
