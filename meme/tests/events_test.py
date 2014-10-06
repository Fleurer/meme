import unittest
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
        self.assertEqual(repo_bak.exchanges, self.repo.exchanges)

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
        self.account1 = self.repo.accounts.find('account1')
        self.account2 = self.repo.accounts.find('account2')
        self.exchange = self.repo.exchanges.find('ltc-btc')

    def test_deal_from_different_account(self):
        self.repo.commit(OrderCreated.build(self.repo, 'bid1', BidOrder, 'account1', 'ltc', 'btc', price=0.1, amount=1, fee_rate=0.01))
        self.repo.commit(OrderCreated.build(self.repo, 'ask1', AskOrder, 'account2', 'ltc', 'btc', price=0.1, amount=0.4, fee_rate=0.01))
        self.assertEqual(self.exchange.match(), ('bid1', 'ask1'))
        bid_deal, ask_deal = self.exchange.match_and_compute_deals(self.repo)
        self.assertEqual(float(bid_deal.amount), 0.4)
        self.assertEqual(float(bid_deal.rest_amount), 0.6)
        self.assertEqual(float(bid_deal.rest_freeze_amount), 0.0606)
        self.assertEqual(float(ask_deal.amount), 0.4)
        self.assertEqual(float(ask_deal.rest_amount), 0)
        self.assertEqual(float(ask_deal.rest_freeze_amount), 0)
        self.repo.commit(OrderDealt.build(self.repo, bid_deal, ask_deal))

if __name__ == '__main__':
    unittest.main()
