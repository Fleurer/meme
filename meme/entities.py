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

def EntitiesSet(object):
    def __init__(self, name, entities=None):
        self.entities = entities or {}
        self.name = name

    def add(self, entity):
        self.entities[entity.id] = entity

    def remove(self, entity):
        del self.entities[entity.id]

    def find(self, id):
        entity = self.entities.get(id)
        if not entity:
            raise NotFoundError("%s#%d not found" % (self.name, id))
        return entity

def Account(object):
    def __init__(self, id, active_balances=None, frozen_balances=None):
        self.id = id
        self.active_balances = active_balances or {}
        self.frozen_balances = frozen_balances or {}

class Order(object):
    def __init__(self, id, account_id, price, amount, rest_amount):
        self.id = id
        self.account_id = account_id
        self.price = price
        self.amount = amount
        self.rest_amount = amount

class Exchange(object):
    def __init__(self, id, bids={}, asks={}):
        self.bids = rbtree.rbtree(bids)
        self.asks = rbtree.rbtree(asks)

    def match(self):
        pass
