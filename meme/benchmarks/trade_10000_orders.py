import sys, os
import time
sys.path.append(os.path.realpath(os.path.join(__file__, '../../..')))
from meme.me.entities import Repository, EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.events import AccountCredited, AccountDebited, AccountCreated, AccountCanceled, ExchangeCreated, OrderCreated, OrderCanceled, OrderDealt

# PYENV_VERSION=pypy-2.3.1 python meme/benchmarks/trade_10000_orders.py

def benchmark(repeat):
    timestamp_start = float(time.time())
    repo = Repository()
    repo.commit(ExchangeCreated.build(repo, 'ltc', 'btc'))
    repo.commit(AccountCreated.build(repo, 'account1'))
    repo.commit(AccountCreated.build(repo, 'account2'))
    repo.commit(AccountCredited.build(repo, 'credit1', 'account1', 'btc', 100))
    repo.commit(AccountCredited.build(repo, 'credit2', 'account1', 'ltc', 100))
    repo.commit(AccountCredited.build(repo, 'credit3', 'account2', 'btc', 100))
    repo.commit(AccountCredited.build(repo, 'credit4', 'account2', 'ltc', 100))
    exchange = repo.exchanges.find('ltc-btc')
    for i in range(repeat):
        repo.commit(OrderCreated.build(repo, 'ask%8d'%i, AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
    for i in range(repeat):
        repo.commit(OrderCreated.build(repo, 'bid%8d'%i, BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
    timestamp_start = float(time.time())
    for i in range(repeat):
        bid_deal, ask_deal = exchange.match_and_compute_deals(repo)
        repo.commit(OrderDealt.build(repo, bid_deal, ask_deal))
    seconds = float(time.time()) - timestamp_start
    return seconds

if __name__ == '__main__':
    print benchmark(10000)
