import unittest
from decimal import Decimal
from collections import namedtuple, deque
from meme.me.entities import Repository, EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.events import AccountCredited, AccountDebited, AccountCreated, AccountCanceled
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
        self.assertEqual(self.repo.accounts.get('123').active_balances['btc'], 100)
        self.assertEqual(self.repo.accounts.get('123').active_balances['ltc'], 200)

    def test_create_credit_then_create(self):
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        self.repo.accounts.find('123')
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', '123', 'btc', 100))
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        self.assertEqual(self.repo.accounts.get('123').active_balances['btc'], 100)

    def test_create_credit_then_debit(self):
        self.repo.commit(AccountCreated.build(self.repo, '123'))
        account = self.repo.accounts.find('123')
        self.repo.commit(AccountCredited.build(self.repo, 'credit1', '123', 'btc', 100))
        self.repo.commit(AccountDebited.build(self.repo, 'debit1', '123', 'btc', 90))
        self.assertEqual(self.repo.accounts.get('123').active_balances['btc'], 10)
        with self.assertRaises(BalanceError):
            self.repo.commit(AccountDebited.build(self.repo, 'debit2', '123', 'btc', 20))
        self.assertEqual(self.repo.accounts.get('123').active_balances['btc'], 10)
        self.repo.commit(AccountDebited.build(self.repo, 'debit3', '123', 'btc', 10))
        self.assertTrue(account.is_empty())
