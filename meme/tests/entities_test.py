import unittest
from decimal import Decimal
from collections import namedtuple, deque
from meme.me.entities import EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.values import BalanceRevision
from meme.me.errors import NotFoundError

class TestEntitiesSet(unittest.TestCase):
    def setUp(self):
        pass

    def test_add_and_find(self):
        SampleEntity = namedtuple('SampleEntity', ['id', 'title'])
        entities_set = EntitiesSet('Test')
        entities_set.add(SampleEntity(1, 'hello'))
        entities_set.add(SampleEntity(2, 'world'))
        self.assertEqual('hello', entities_set.find(1).title)
        self.assertEqual('world', entities_set.find(2).title)
        with self.assertRaises(NotFoundError):
            entities_set.find(3)
        entities_set.remove(2)
        with self.assertRaises(NotFoundError):
            entities_set.find(2)
        entities_set.remove(5)

    def test_add_an_order(self):
        ask1 = AskOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        entities_set = EntitiesSet('Order')
        entities_set.add(ask1)
        entities_set.add(ask1)
        entities_set.find(2)

class TestExchange(unittest.TestCase):
    def setUp(self):
        self.exchange = Exchange('ltc', 'btc')

    def test_exchange_id(self):
        self.assertEqual(self.exchange.id, 'ltc-btc')

    def test_enqueue_and_dequeue1(self):
        ask1 = AskOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        ask0 = AskOrder(1, 1, 'ltc', 'btc', price=0.1, amount=1)
        self.exchange.enqueue(ask0)
        self.exchange.enqueue(ask1)
        self.assertEqual(self.exchange.asks.keys(), [Decimal('0.1')])
        self.assertEqual(self.exchange.asks.values(), [deque([1, 2])])
        self.exchange.dequeue(ask0)
        self.assertEqual(self.exchange.asks.keys(), [Decimal('0.1')])
        self.assertEqual(self.exchange.asks.values(), [deque([2])])
        self.exchange.dequeue(ask1)
        self.assertEqual(self.exchange.asks.keys(), [])

    def test_enqueue_and_dequeue2(self):
        bid0 = BidOrder(1, 1, 'ltc', 'btc', price=0.1, amount=1)
        bid1 = BidOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        self.exchange.enqueue(bid0)
        self.exchange.enqueue(bid1)
        self.assertEqual(map(float, self.exchange.bids.keys()), [0.1])
        self.assertEqual(self.exchange.bids.values(), [deque([1, 2])])
        self.exchange.dequeue(bid0)
        self.assertEqual(map(float, self.exchange.bids.keys()), [0.1])
        self.assertEqual(self.exchange.bids.values(), [deque([2])])
        self.exchange.dequeue(bid1)
        self.assertEqual(self.exchange.bids.keys(), [])

    def test_enqueue1(self):
        ask0 = AskOrder(1, 1, 'ltc', 'btc', price=0.1, amount=1)
        ask1 = AskOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        ask2 = AskOrder(3, 1, 'ltc', 'btc', price=0.2, amount=1)
        self.exchange.enqueue(ask0)
        self.exchange.enqueue(ask1)
        self.exchange.enqueue(ask2)
        self.assertEqual(sorted(map(float, self.exchange.asks.keys())), [0.1, 0.2])
        self.assertEqual(sorted(self.exchange.asks.values()), [deque([1, 2]), deque([3])])

    def test_enqueue2(self):
        bid0 = BidOrder(1, 1, 'ltc', 'btc', price=0.1, amount=1)
        bid1 = BidOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        bid2 = BidOrder(3, 1, 'ltc', 'btc', price=0.2, amount=1)
        self.exchange.enqueue(bid0)
        self.exchange.enqueue(bid1)
        self.exchange.enqueue(bid2)
        self.assertEqual(sorted(map(float, self.exchange.bids.keys())), [0.1, 0.2])
        self.assertEqual(sorted(self.exchange.bids.values()), [deque([1, 2]), deque([3])])

    def test_match(self):
        self.exchange.enqueue(BidOrder(1, 1, 'ltc', 'btc', price=0.2, amount=1))
        self.exchange.enqueue(BidOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1))
        self.exchange.enqueue(BidOrder(3, 1, 'ltc', 'btc', price=0.3, amount=4))
        self.exchange.enqueue(BidOrder(4, 1, 'ltc', 'btc', price=0.3, amount=1))
        self.exchange.enqueue(AskOrder(5, 1, 'ltc', 'btc', price=0.2, amount=1))
        self.exchange.enqueue(AskOrder(6, 1, 'ltc', 'btc', price=0.3, amount=1))
        self.exchange.enqueue(AskOrder(7, 1, 'ltc', 'btc', price=0.3, amount=1))
        self.assertEqual(self.exchange.match(pop=True), (3, 5))
        self.assertEqual(self.exchange.match(pop=True), (4, 6))
        self.assertEqual(self.exchange.match(pop=True), (None, None))

class TestAccount(unittest.TestCase):
    def test_is_empty(self):
        account = Account.build('account1', {'btc': (10, 0), 'ltc': (0, 0)})
        self.assertTrue(not account.is_empty())
        account = Account.build('account1', {'btc': (0, 0), 'ltc': (0, 0) })
        self.assertTrue(account.is_empty())
        account = Account('account2')
        self.assertTrue(account.is_empty())

class TestOrder(unittest.TestCase):
    def test_rest_freeze_amount(self):
        bid = BidOrder(1, 1, 'ltc', 'btc', price=3, amount=1, fee_rate=0.01, timestamp = 2)
        self.assertEqual(float(bid.rest_freeze_amount), 3.03)
        ask = AskOrder(1, 1, 'ltc', 'btc', price=3, amount=1, fee_rate=0.01, timestamp = 2)
        self.assertEqual(float(ask.rest_freeze_amount), 1)

    def test_compute_deals1(self):
        bid = BidOrder(1, 1, 'ltc', 'btc', price=0.3, amount=1.1, fee_rate=0.001, timestamp = 2)
        ask = AskOrder(2, 1, 'ltc', 'btc', price=0.2, amount=1, fee_rate=0.001, timestamp = 1)
        bid_deal, ask_deal = Exchange.compute_deals(bid, ask)
        self.assertEqual(float(bid_deal.price), 0.2)
        self.assertEqual(float(bid_deal.income), 1)
        self.assertEqual(float(bid_deal.outcome), 0.2002)
        self.assertEqual(float(bid_deal.fee), 0.0002)
        self.assertEqual(float(ask_deal.price), 0.2)
        self.assertEqual(float(ask_deal.income), 0.1998)
        self.assertEqual(float(ask_deal.outcome), 1)
        self.assertEqual(float(ask_deal.fee), 0.0002)
        bid.append_deal(bid_deal)
        ask.append_deal(ask_deal)
        self.assertEqual(float(bid.rest_amount), 0.1)
        self.assertEqual(float(bid.rest_freeze_amount), 0.13013)
        ask = AskOrder(3, 1, 'ltc', 'btc', price=0.2, amount=1, fee_rate=0.001, timestamp = 3)
        bid_deal, ask_deal = Exchange.compute_deals(bid, ask)
        self.assertEqual(float(bid_deal.price), 0.3)
        self.assertEqual(float(bid_deal.income), 0.1)
        self.assertEqual(float(bid_deal.outcome), 0.03003)
        self.assertEqual(float(bid_deal.fee), 0.00003)
        bid.append_deal(bid_deal)
        ask.append_deal(ask_deal)
        self.assertEqual(float(ask.rest_amount), 0.9)
        self.assertEqual(float(bid.rest_amount), 0.0)
        self.assertEqual(float(ask.rest_freeze_amount), 0.9)
        self.assertEqual(float(bid.rest_freeze_amount), 0.1001)

if __name__ == '__main__':
    unittest.main()
