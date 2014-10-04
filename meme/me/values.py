from collections import namedtuple

BalanceDiff = namedtuple('BalanceDiff', [
    'account_id',
    'coin_type',
    'old_active',
    'old_frozen',
    'new_active',
    'new_frozen'
])

Deal = namedtuple('Deal', [
    'pair_id',
    'price',
    'amount',
    'income',
    'outcome',
    'fee',
    'timestamp'
])
