import unittest
import time
from copy import deepcopy
from decimal import Decimal
from collections import namedtuple, deque
from meme.me.entities import Repository, EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.events import AccountCredited, AccountDebited, AccountCreated, AccountCanceled, ExchangeCreated, OrderCreated, OrderCanceled, OrderDealt
from meme.me.errors import NotFoundError, CancelError, BalanceError

class TestAccountEvents(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def test_create_and_cancel1(self):
        event = AccountCreated.build(self.repo, '123')
        self.repo.commit(event)
        self.repo.accounts.find('123')
        event = AccountCanceled.build(self.repo, '123')
        self.repo.commit(event)
        self.assertFalse(self.repo.accounts.get('123'))

    def test_create_credit_then_cancel(self):
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        self.repo.accounts.find('123')
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', '123', 'btc', 100))
        self.repo.commit(AccountCredited.build(self.repo, 'credit2', '123', 'ltc', 200))
        with self.assertRaises(CancelError):
            self.repo.commit(AccountCanceled.build(self.repo, '123'))
        self.assertEqual(float(self.repo.accounts.get('123').find_balance('btc').active), 100)
        self.assertEqual(float(self.repo.accounts.get('123').find_balance('ltc').active), 200)

    def test_create_credit_then_create(self):
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        self.repo.accounts.find('123')
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', '123', 'btc', 100))
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        self.assertEqual(self.repo.accounts.get('123').find_balance('btc').active, 100)

    def test_create_credit_then_debit(self):
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        account = self.repo.accounts.find('123')
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', '123', 'btc', 100))
        self.repo.commit(AccountDebited.build(self.repo, 'debit1', '123', 'btc', 90))
        self.assertEqual(self.repo.accounts.get('123').find_balance('btc').active, 10)
        with self.assertRaises(BalanceError):
            self.repo.commit(AccountDebited.build(self.repo, 'debit2', '123', 'btc', 20))
        self.assertEqual(self.repo.accounts.get('123').find_balance('btc').active, 10)
        self.repo.commit(AccountDebited.build(self.repo, 'debit3', '123', 'btc', 10))
        self.assertTrue(account.is_empty())

class TestOrderEvents(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.repo.commit(ExchangeCreated.build(self.repo, 'ltc', 'btc'))
        self.repo.commit(AccountCreated.build(self.repo, 'account1'))
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', 'account1', 'btc', 100))
        self.repo.commit(AccountCredited.build(self.repo, 'credit2', 'account1', 'ltc', 100))

    def test_create_order(self):
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', 1, 10, 0.01))
        self.assertTrue(self.repo.orders.get('bid1'))
        self.assertEqual(float(self.repo.accounts.find('account1').find_balance('btc').active), 89.9)
        self.assertEqual(float(self.repo.accounts.find('account1').find_balance('btc').frozen), 10.1)
        self.repo.commit(OrderCanceled.build(self.repo, 'bid1'))
        self.assertEqual(float(self.repo.accounts.find('account1').find_balance('btc').active), 100)
        self.assertEqual(float(self.repo.accounts.find('account1').find_balance('btc').frozen), 0)

    def test_create_a_bigger_order_than_balance(self):
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', 1, 50, 0.01))
        repo_bak = deepcopy(self.repo)
        with self.assertRaises(BalanceError):
            self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', 1, 50, 0.01))
        self.assertEqual(repo_bak.orders, self.repo.orders)
        self.assertEqual(repo_bak.accounts, self.repo.accounts)
        # self.assertEqual(repo_bak.exchanges, self.repo.exchanges)

    def test_compute_balance_revision_for_create(self):
        account = Account.build('account1', {'btc': (10, 0), 'ltc': (10, 0) })
        bid = BidOrder('bid1', 'account1', 'ltc', 'btc', price=0.3, amount=1, fee_rate=0.001, timestamp = 2)
        balance_revision = OrderCreated.build_balance_revision(account, bid)
        account.adjust(balance_revision)
        self.assertEqual(float(balance_revision.old_active), 10)
        self.assertEqual(float(balance_revision.new_active), 9.6997)
        self.assertEqual(float(balance_revision.new_frozen), 0.3003)
        self.assertEqual(balance_revision.active_diff, 0-bid.freeze_amount)
        self.assertEqual(balance_revision.frozen_diff, bid.freeze_amount)
        balance_revision = OrderCanceled.build_balance_revision(account, bid)
        account.adjust(balance_revision)
        self.assertEqual(float(balance_revision.old_active), 9.6997)
        self.assertEqual(float(balance_revision.new_active), 10)
        self.assertEqual(float(balance_revision.new_frozen), 0)
        self.assertEqual(balance_revision.active_diff, bid.freeze_amount)
        self.assertEqual(balance_revision.frozen_diff, 0 - bid.freeze_amount)

class TestOrderDealt(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.repo.commit(ExchangeCreated.build(self.repo, 'ltc', 'btc'))
        self.repo.commit(AccountCreated.build(self.repo, 'account1'))
        self.repo.commit(AccountCreated.build(self.repo, 'account2'))
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', 'account1', 'btc', 100))
        self.repo.commit(AccountCredited.build(self.repo, 'credit2', 'account1', 'ltc', 100))
        self.repo.commit(AccountCredited.build(self.repo, 'credit3', 'account2', 'btc', 100))
        self.repo.commit(AccountCredited.build(self.repo, 'credit4', 'account2', 'ltc', 100))
        self.exchange = self.repo.exchanges.find('ltc-btc')

    def test_deal_from_different_account1(self):
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=1, fee_rate=0.01, timestamp=1))
        self.repo.commit(OrderCreated.build(self.repo, 'ask1', AskOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=2))
        self.repo.commit(OrderCreated.build(self.repo, 'ask2', AskOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=3))
        self.repo.commit(OrderCreated.build(self.repo, 'ask3', AskOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=4))
        self.assertEqual(self.exchange.match(), ('bid1', 'ask1'))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        self.assertEqual(float(bid_deal.amount), 0.4)
        self.assertEqual(float(bid_deal.rest_amount), 0.6)
        self.assertEqual(float(bid_deal.rest_freeze_amount), 0.0606)
        self.assertEqual(float(ask_deal.amount), 0.4)
        self.assertEqual(float(ask_deal.rest_amount), 0)
        self.assertEqual(float(ask_deal.rest_freeze_amount), 0)
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        self.assertEqual(float(bid_deal.rest_amount), 0.2)
        self.assertEqual(float(ask_deal.rest_amount), 0.0)
        self.assertEqual(float(bid_deal.rest_freeze_amount), 0.0202)
        self.assertEqual(float(ask_deal.rest_freeze_amount), 0.0)
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        event = OrderDealt.build(self.repo, bid_deal, ask_deal)
        self.repo.commit(event)
        self.assertEqual(float(bid_deal.rest_amount), 0.0)
        self.assertEqual(float(ask_deal.rest_amount), 0.2)
        self.assertEqual(float(bid_deal.rest_freeze_amount), 0.0)
        self.assertEqual(float(ask_deal.rest_freeze_amount), 0.2)
        account1 = self.repo.accounts.find('account1')
        account2 = self.repo.accounts.find('account2')
        btcbalance1, ltcbalance1 = account1.find_balances(['btc', 'ltc'])
        btcbalance2, ltcbalance2 = account2.find_balances(['btc', 'ltc'])
        self.assertEqual(float(btcbalance1.active), 99.899)
        self.assertEqual(float(btcbalance2.active), 100.099)
        self.assertEqual(float(btcbalance1.frozen), 0)
        self.assertEqual(float(btcbalance2.frozen), 0)
        self.assertEqual(float(ltcbalance1.active), 101)
        self.assertEqual(float(ltcbalance2.active), 98.8)
        self.assertEqual(float(ltcbalance2.frozen), 0.2)
        self.assertEqual(float(200-btcbalance2.active-btcbalance1.active), 0.002)
        ask3 = self.repo.orders.find('ask3')
        self.assertEqual(float(ask3.rest_freeze_amount), 0.2)

    def test_deal_from_different_account2(self):
        self.repo.commit(OrderCreated.build(self.repo, 'ask1', AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=1, fee_rate=0.01, timestamp=1))
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=2))
        self.repo.commit(OrderCreated.build(self.repo, 'bid2', BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=3))
        self.repo.commit(OrderCreated.build(self.repo, 'bid3', BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=4))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.assertFalse(bid_deal and ask_deal)
        account1 = self.repo.accounts.find('account1')
        account2 = self.repo.accounts.find('account2')
        btcbalance1, ltcbalance1 = account1.find_balances(['btc', 'ltc'])
        btcbalance2, ltcbalance2 = account2.find_balances(['btc', 'ltc'])
        self.assertEqual(float(200 - btcbalance1.active - btcbalance2.active), 0.0222)
        self.assertEqual(float(200 - ltcbalance1.active - ltcbalance2.active), 0)
        self.assertEqual(float(ltcbalance2.frozen), 0)
        self.assertEqual(float(btcbalance2.frozen), 0.0202)

    def test_deal_from_different_account_with_benchmark1(self):
        timestamp_start = float(time.time())
        for i in range(100):
            self.repo.commit(OrderCreated.build(self.repo, 'ask%d'%i, AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
        for i in range(100):
            self.repo.commit(OrderCreated.build(self.repo, 'bid%d'%i, BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
        seconds = float(time.time()) - timestamp_start
        timestamp_start = float(time.time())
        for i in range(100):
            bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
            self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        seconds = float(time.time()) - timestamp_start
        self.assertTrue(seconds < 0.2)
        exchange = self.repo.exchanges.find('ltc-btc')
        self.assertTrue(exchange.is_empty())
        account1 = self.repo.accounts.find('account1')
        account2 = self.repo.accounts.find('account2')
        btcbalance1, ltcbalance1 = account1.find_balances(['btc', 'ltc'])
        btcbalance2, ltcbalance2 = account2.find_balances(['btc', 'ltc'])
        self.assertEqual((float(btcbalance1.frozen), float(btcbalance2.frozen)), (0, 0))
        self.assertEqual((float(ltcbalance1.frozen), float(ltcbalance2.frozen)), (0, 0))
        self.assertEqual((float(ltcbalance1.active + ltcbalance2.active - 200)), 0)
        self.assertEqual((float(btcbalance1.active + btcbalance2.active - 200)), -0.002)

    @unittest.skip
    def test_deal_from_different_account_with_benchmark2(self):
        timestamp_start = float(time.time())
        for i in range(10000):
            self.repo.commit(OrderCreated.build(self.repo, 'ask%d'%i, AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
        for i in range(10000):
            self.repo.commit(OrderCreated.build(self.repo, 'bid%d'%i, BidOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.01, fee_rate=0.01, timestamp=i))
        seconds = float(time.time()) - timestamp_start
        timestamp_start = float(time.time())
        for i in range(10000):
            bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
            self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        seconds = float(time.time()) - timestamp_start
        print seconds

    def test_deal_from_same_account1(self):
        self.repo.commit(OrderCreated.build(self.repo, 'ask1', AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=1, fee_rate=0.01, timestamp=1))
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=2))
        self.repo.commit(OrderCreated.build(self.repo, 'bid2', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=3))
        self.repo.commit(OrderCreated.build(self.repo, 'bid3', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=4))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.assertFalse(bid_deal and ask_deal)
        account1 = self.repo.accounts.find('account1')
        btcbalance1, ltcbalance1 = account1.find_balances(['btc', 'ltc'])
        self.assertEqual(float(btcbalance1.active), 99.9778)
        self.assertEqual(float(btcbalance1.frozen), 0.0202)
        self.assertEqual(float(ltcbalance1.active), 100)
        self.assertEqual(float(ltcbalance1.frozen), 0)

    def test_deal_from_same_account1(self):
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=1, fee_rate=0.01, timestamp=1))
        self.repo.commit(OrderCreated.build(self.repo, 'ask1', AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=2))
        self.repo.commit(OrderCreated.build(self.repo, 'ask2', AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=3))
        self.repo.commit(OrderCreated.build(self.repo, 'ask3', AskOrder, 'account1', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01, timestamp=4))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.assertFalse(bid_deal and ask_deal)
        account1 = self.repo.accounts.find('account1')
        btcbalance1, ltcbalance1 = account1.find_balances(['btc', 'ltc'])
        self.assertEqual(float(btcbalance1.active), 99.998)
        self.assertEqual(float(btcbalance1.frozen), 0)
        self.assertEqual(float(ltcbalance1.active), 99.8)
        self.assertEqual(float(ltcbalance1.frozen), 0.2)


if __name__ == '__main__':
    unittest.main()
