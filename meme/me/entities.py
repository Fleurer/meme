# coding: utf-8
import time
import collections
from decimal import Decimal, ROUND_DOWN
import rbtree
from pybloom import ScalableBloomFilter
from .errors import NotFoundError, BalanceError, DealError
from .values import Deal, BalanceRevision
from .consts import PRECISION_EXP

class Repository(object):
    def __init__(self, revision=0, accounts=None, orders=None, exchanges=None, debits_bloom=None, credits_bloom=None, orders_bloom=None):
        self.revision = revision
        self.accounts = EntitiesSet(accounts)
        self.orders = EntitiesSet(orders)
        self.exchanges = EntitiesSet(exchanges)
        # self.events = events or EventsBuffer()
        self.debits_bloom = debits_bloom or ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)
        self.credits_bloom = credits_bloom or ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)
        self.orders_bloom = orders_bloom or ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)

    @classmethod
    def load_snapshot(self, snapshot):
        pass

    def sync(self):
        pass

    def commit(self, event):
        if event.revision != self.revision + 1:
            raise ValueError("Invalid revision")
        event.apply(self)

    def flush(self):
        pass

class EntitiesSet(object):
    def __init__(self, name, entities=None):
        self.entities = entities or {}
        self.name = name

    def __eq__(self, other):
        return self.entities.__eq__(other.entities)

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

    def get(self, id, default=None):
        return self.entities.get(id, default)

class Entity(object):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class Account(Entity):
    def __init__(self, id, balances=None):
        self.id = id
        self.balances = balances or {}

    @classmethod
    def build(cls, id, balances_map=None):
        account = cls(id)
        for coin_type, balance_tuple in balances_map.items():
            active, frozen = balance_tuple
            balance = account.find_balance(coin_type)
            revision = balance.build_next(active, frozen)
            account.adjust(revision)
        return account

    def find_balance(self, coin_type):
        zero_balance = BalanceRevision.build(self.id, coin_type)
        return self.balances.get(coin_type, zero_balance)

    def find_balances(self, coin_types):
        return [self.find_balance(coin_type) for coin_type in coin_types]

    def adjust(self, revision):
        coin_type = revision.coin_type
        balance = self.find_balance(coin_type)
        if balance.active != revision.old_active:
            raise BalanceError("BalanceRevision old_active mismatch, expected %s, but got %s" % (balance.active, revision.old_active))
        if balance.frozen != revision.old_frozen:
            raise BalanceError("BalanceRevision old_frozen mismatch: expected %s, but got %s" % (balance.frozen, revision.old_frozen))
        if revision.active < 0 or revision.frozen < 0:
            raise BalanceError("invalid BalanceRevision %s" % balance_revision)
        self.balances[coin_type] = revision

    def is_empty(self):
        for b in self.balances.values():
            if b.active > 0 or b.frozen > 0:
                return False
        return True

class Order(Entity):
    def __init__(self, id, account_id, coin_type, price_type, price, amount, fee_rate=0.001, timestamp=None, deals=None):
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
        return (self.amount - sum([d.amount for d in self.deals])).quantize(PRECISION_EXP)

    @property
    def rest_freeze_amount(self):
        return (self.freeze_amount - sum([d.outcome for d in self.deals])).quantize(PRECISION_EXP)

    def is_completed(self):
        return self.rest_amount == 0

    def append_deal(self, deal):
        if self.rest_amount != deal.rest_amount + deal.amount:
            raise DealError("Deal rest_amount %s mismatch" % (deal, ))
        if self.rest_freeze_amount != deal.rest_freeze_amount + deal.outcome:
            raise DealError("Deal rest_freeze_amount %s mismatch" % (deal, ))
        self.deals.append(deal)

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

class Exchange(Entity):
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

    def dequeue_if_completed(self, order):
        if order.is_completed():
            self.dequeue(order)

    def is_empty(self):
        return self.bids == rbtree.rbtree() and self.asks == rbtree.rbtree()

    # 最高买价大于等于最低卖价
    def match(self, pop=False):
        bid_price = self.bids.max()
        ask_price = self.asks.min()
        if not bid_price or not ask_price:
            return (None, None)
        if bid_price >= ask_price:
            bids_queue = self.bids[bid_price]
            asks_queue = self.asks[ask_price]
            bid_id = bids_queue[0]
            ask_id = asks_queue[0]
            if pop:
                self._discard(self.bids, bid_price, bid_id)
                self._discard(self.asks, ask_price, ask_id)
            return (bid_id, ask_id)
        return (None, None)

    @classmethod
    def compute_deals(cls, bid, ask):
        assert type(bid) is BidOrder
        assert type(ask) is AskOrder
        assert bid.price >= ask.price
        assert bid.rest_amount > 0
        assert ask.rest_amount > 0
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
        # 记录订单未结清的额度
        bid_rest_amount = bid.rest_amount - deal_amount
        ask_rest_amount = ask.rest_amount - deal_amount
        bid_rest_freeze_amount = bid.rest_freeze_amount - bid_outcome
        ask_rest_freeze_amount = ask.rest_freeze_amount - ask_outcome
        bid_deal = Deal(bid.id, ask.id, deal_price, deal_amount, bid_rest_amount, bid_rest_freeze_amount, bid_income, bid_outcome, bid_fee, timestamp)
        ask_deal = Deal(ask.id, bid.id, deal_price, deal_amount, ask_rest_amount, ask_rest_freeze_amount, ask_income, ask_outcome, ask_fee, timestamp)
        return (bid_deal, ask_deal)

    def match_and_compute_deals(self, repo):
        bid_id, ask_id = self.match()
        if not bid_id or not ask_id:
            return (None, None)
        bid = repo.orders.find(bid_id)
        ask = repo.orders.find(ask_id)
        return Exchange.compute_deals(bid, ask)

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
