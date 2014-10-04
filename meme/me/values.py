from collections import namedtuple

_BalanceDiff = namedtuple('BalanceDiff', [
    'account_id',
    'coin_type',
    'old_active',
    'old_frozen',
    'new_active',
    'new_frozen'
])

class BalanceDiff(_BalanceDiff):
    @property
    def active_diff(self):
        return self.new_active - self.old_active

    @property
    def frozen_diff(self):
        return self.new_frozen - self.old_frozen

Deal = namedtuple('Deal', [
    'pair_id',
    'price',
    'amount',
    'income',
    'outcome',
    'fee',
    'timestamp'
])
