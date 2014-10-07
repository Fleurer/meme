import sys, os
import time
sys.path.append(os.path.realpath(os.path.join(__file__, '../../..')))
from meme.me.entities import Repository, EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.events import AccountCredited, AccountDebited, AccountCreated, AccountCanceled, ExchangeCreated, OrderCreated, OrderCanceled, OrderDealt
from meme.me.errors import ConflictedError

# PYENV_VERSION=pypy-2.3.1 python meme/benchmarks/trade_10000_orders.py

def benchmark(repeat):
    timestamp_start = float(time.time())
    repo = Repository()
    repo.commit(ExchangeCreated.build(repo, 'ltc', 'btc'))
    repo.commit(AccountCreated.build(repo, 'account1'))
    repo.commit(AccountCreated.build(repo, 'account2'))
    repo.commit(AccountCredited.build(repo, 'credit1', 'account1', 'btc', 100000))
    repo.commit(AccountCredited.build(repo, 'credit2', 'account1', 'ltc', 100000))
    repo.commit(AccountCredited.build(repo, 'credit3', 'account2', 'btc', 100000))
    repo.commit(AccountCredited.build(repo, 'credit4', 'account2', 'ltc', 100000))
    exchange = repo.exchanges.find('ltc-btc')
    for i in xrange(repeat):
        j = 0
        while True:
            try:
                repo.commit(OrderCreated.build(repo, 'ask%d%d'%(i,j), AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
                repo.commit(OrderCreated.build(repo, 'bid%d%d'%(i,j), BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
                break
            except ConflictedError:
                j += 1
                continue
    timestamp_start = float(time.time())
    for i in range(repeat):
        bid_deal, ask_deal = exchange.match_and_compute_deals(repo)
        repo.commit(OrderDealt.build(repo, bid_deal, ask_deal))
    seconds = float(time.time()) - timestamp_start
    return (seconds, float(repeat * 2) / seconds)

if __name__ == '__main__':
    print "trade 200 orders in %s seconds, %s orders per second" % benchmark(100)
    print "trade 2000 orders in %s seconds, %s orders per second" % benchmark(1000)
    print "trade 20000 orders in %s seconds, %s orders per second" % benchmark(10000)
    print "trade 200000 orders in %s seconds, %s orders per second" % benchmark(100000)
