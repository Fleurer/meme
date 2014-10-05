from collections import namedtuple
from decimal import Decimal
from operator import attrgetter
from .errors import BalanceError

Deal = namedtuple('Deal', [
    'order_id',
    'pair_id',
    'price',
    'amount',
    'income',
    'outcome',
    'fee',
    'timestamp'
])

class Balance(object):
    active = property(attrgetter("_active"))
    frozen = property(attrgetter("_frozen"))
    revision = property(attrgetter("_revision"))

    def __init__(self, active=0, frozen=0, revision=0):
        self._active = Decimal(active)
        self._frozen = Decimal(frozen)
        self._revision = revision

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "Balance(active=%s, frozen=%s, revision=%s)" % (self.active, self.frozen, self.revision)

class BalanceDiff(object):
    account_id = property(attrgetter("_account_id"))
    coin_type = property(attrgetter("_coin_type"))
    old_active = property(attrgetter("_old_active"))
    old_frozen = property(attrgetter("_old_frozen"))
    new_active = property(attrgetter("_new_active"))
    new_frozen = property(attrgetter("_new_frozen"))

    def __init__(self, account_id, coin_type, old_active, old_frozen, new_active, new_frozen):
        self._account_id = account_id
        self._coin_type = coin_type
        self._old_active = Decimal(old_active)
        self._old_frozen = Decimal(old_frozen)
        self._new_active = Decimal(new_active)
        self._new_frozen = Decimal(new_frozen)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def active_diff(self):
        return self.new_active - self.old_active

    @property
    def frozen_diff(self):
        return self.new_frozen - self.old_frozen

    def build_next(self, active_diff=0, frozen_diff=0):
        new_active = self.new_active + active_diff
        new_frozen = self.new_frozen + frozen_diff
        if new_active < 0 or new_frozen < 0:
            raise BalanceError("Invalid new balance for %s active: %s frozen: %s" % (self.coin_type, new_active, new_frozen))
        return BalanceDiff(
                self.account_id,
                self.coin_type,
                old_active = self.new_active,
                old_frozen = self.new_frozen,
                new_active = new_active,
                new_frozen = new_frozen)
