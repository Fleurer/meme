from collections import namedtuple
from decimal import Decimal
from operator import attrgetter
from .errors import BalanceError

Deal = namedtuple('Deal', [
    'order_id',
    'pair_id',
    'price',
    'amount',
    'rest_amount',
    'rest_freeze_amount',
    'income',
    'outcome',
    'fee',
    'timestamp'
])

class BalanceRevision(object):
    account_id = property(attrgetter("_account_id"))
    coin_type = property(attrgetter("_coin_type"))
    old_active = property(attrgetter("_old_active"))
    old_frozen = property(attrgetter("_old_frozen"))
    new_active = property(attrgetter("_new_active"))
    new_frozen = property(attrgetter("_new_frozen"))
    active = property(attrgetter("_new_active"))
    frozen = property(attrgetter("_new_frozen"))

    def __init__(self, account_id, coin_type, old_active, old_frozen, new_active, new_frozen):
        self._account_id = account_id
        self._coin_type = coin_type
        self._old_active = Decimal(old_active)
        self._old_frozen = Decimal(old_frozen)
        self._new_active = Decimal(new_active)
        self._new_frozen = Decimal(new_frozen)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "BalanceRevision(account_id=%s, coin_type=%s, old_active=%s, old_frozen=%s, new_active=%s, new_frozen=%s)" % (self.account_id, self.coin_type, self.old_active, self.old_frozen, self.new_active, self.new_frozen)

    @property
    def active_diff(self):
        return self.new_active - self.old_active

    @property
    def frozen_diff(self):
        return self.new_frozen - self.old_frozen

    @classmethod
    def build(cls, account_id, coin_type, active=0, frozen=0):
        return cls(account_id, coin_type, 0, 0, active, frozen)

    def build_next(self, active_diff=0, frozen_diff=0):
        new_active = self.new_active + active_diff
        new_frozen = self.new_frozen + frozen_diff
        if new_active < 0 or new_frozen < 0:
            raise BalanceError("Invalid new balance for %s active: %s frozen: %s" % (self.coin_type, new_active, new_frozen))
        return BalanceRevision(
                self.account_id,
                self.coin_type,
                old_active = self.new_active,
                old_frozen = self.new_frozen,
                new_active = new_active,
                new_frozen = new_frozen)
