import unittest
from collections import namedtuple
from meme.me.entities import EntitiesSet, AskOrder, Exchange
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

class TestExchange(unittest.TestCase):
    def setUp(self):
        self.exchange = Exchange('ltc', 'btc')

    def test_exchange_id(self):
        self.assertEqual(self.exchange.id, 'ltc-btc')

    def test_enqueue(self):
        ask0 = AskOrder(1, 1, 'ltc', 'btc', price=0.1, amount=1)
        ask1 = AskOrder(2, 1, 'ltc', 'btc', price=0.1, amount=1)
        self.exchange.enqueue(ask0)
        self.exchange.enqueue(ask1)
        self.assertEqual(self.exchange.asks_queue.values(), [[1, 2]])

if __name__ == '__main__':
    unittest.main()
