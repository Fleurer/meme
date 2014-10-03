import unittest
from collections import namedtuple
from meme.me.entities import EntitiesSet
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

if __name__ == '__main__':
    unittest.main()
