import rbtree
from .errors import NotFoundError

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

class Order(object):
    def __init__(self, id, account_id, coin_type, price_type, price, amount, rest_amount=None, fee_rate=0.001):
        self.id = id
        self.account_id = account_id
        self.coin_type = coin_type
        self.price_type = price_type
        self.price = price
        self.amount = amount
        self.rest_amount = rest_amount or amount
        self.fee_rate = fee_rate

    @property
    def exchange_id(self):
        return "%s-%s" % (self.coin_type, self.price_type)

class BidOrder(Order):
    @property
    def income_type(self):
        return self.coin_type

    @property
    def outcome_type(self):
        return self.price_type

class AskOrder(Order):
    @property
    def income_type(self):
        return self.price_type

    @property
    def outcome_type(self):
        return self.coin_type

class Exchange(object):
    def __init__(self, coin_type, price_type, bids_queue=None, asks_queue=None):
        self.coin_type = coin_type
        self.price_type = price_type
        self.bids_queue = rbtree.rbtree(bids_queue or {})
        self.asks_queue = rbtree.rbtree(asks_queue or {})

    @property
    def id(self):
        return "%s-%s" % (self.coin_type, self.price_type)

    def enqueue(self, order):
        if order.exchange_id != self.id:
            raise ValueError("Order#exchange_id<%s> mismatch with Exchange<%s>" % (order.exchange_id, self.id))
        if type(order) is BidOrder:
            queue = self.bids_queue
        elif type(order) is AskOrder:
            queue = self.asks_queue
        else:
            raise ValueError("argument is not an Order")
        bucket = queue.get(order.price, [])
        bucket.append(order.id)

    def dequeue(self, order):
        pass

    def match(self):
        pass
