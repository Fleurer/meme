import unittest
from decimal import Decimal
from collections import namedtuple, deque
from meme.me.entities import Repository, EntitiesSet, AskOrder, BidOrder, Exchange, Account
from meme.me.events import AccountCredited, AccountCreated, AccountCanceled
from meme.me.errors import NotFoundError, InvalidAccountCancel

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
        self.repo.commit(AccountCredited.build(self.repo, '123', 'btc', 100))
        with self.assertRaises(InvalidAccountCancel):
            self.repo.commit(AccountCanceled.build(self.repo, '123'))
        self.assertEqual(self.repo.accounts.get('123').active_balances['btc'], 100)
