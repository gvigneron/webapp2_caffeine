# -*- coding: utf-8 -*-
import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb

from webapp2_caffeine.pagination import Pager
from webapp2_caffeine.test_case import BaseTestCase


class DummyModel(ndb.Model):
    value = ndb.IntegerProperty()


class PagerTest(BaseTestCase, unittest.TestCase):

    def setUp(self):
        super(PagerTest, self).setUp()
        [DummyModel(value=x).put() for x in range(100)]
        self.query = DummyModel.query().order(DummyModel.value)

    def test_init(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        self.assertEqual(pager.query, self.query)
        self.assertEqual(pager.lifetime, 3600)
        self.assertEqual(pager.page, 1)
        pager = Pager(self.query, page=10, lifetime=3600)
        self.assertEqual(pager.page, 10)
        pager = Pager(self.query, page=0, lifetime=3600)
        self.assertEqual(pager.page, 1)

    def test_next_page(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        self.assertEqual(pager.next_page, 1)
        pager.has_next = True
        self.assertEqual(pager.next_page, 2)

    def test_prev_page(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        self.assertEqual(pager.prev_page, 1)
        pager = Pager(self.query, page=10, lifetime=3600)
        self.assertEqual(pager.prev_page, 9)

    def test_paginate_page1(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].value, 0)
        self.assertTrue(more)

    def test_paginate_page_size(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=200)
        self.assertEqual(len(results), 100)
        self.assertFalse(more)

    def test_paginate_pages(self):
        # Firts.
        pager = Pager(self.query, page=1, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].value, 0)
        self.assertTrue(more)
        # Second.
        pager = Pager(self.query, page=2, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].value, 10)
        self.assertTrue(more)
        # Third.
        pager = Pager(self.query, page=3, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].value, 20)
        self.assertTrue(more)
        # Last.
        pager = Pager(self.query, page=10, lifetime=3600)
        results, cursor, more = pager.paginate(page_size=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].value, 90)
        self.assertFalse(more)
        # All.
        for page in xrange(1, 10):
            pager = Pager(self.query, page=page, lifetime=3600)
            results, cursor, more = pager.paginate(page_size=10)
            self.assertEqual(len(results), 10)

    def test_set_cursor_to_cache(self):
        dummy, cursor, more = self.query.fetch_page(10)
        pager = Pager(self.query, page=1, lifetime=3600)
        pager._set_cursor_to_cache(cursor, 2, page_size=10)
        cursor_key = pager._get_memcache_key(page=2)
        result = memcache.get(cursor_key)
        self.assertEqual(result, cursor.to_bytes())

    def test_get_cursor_from_cache(self):
        dummy, cursor, more = self.query.fetch_page(10)
        pager = Pager(self.query, page=1, lifetime=3600)
        pager._set_cursor_to_cache(cursor, 2, page_size=10)
        result = pager._get_cursor_from_cache(page=2, page_size=10)
        self.assertEqual(result, cursor)

    def test_query_id(self):
        query = DummyModel.query().filter(DummyModel.value > 10)
        pager1 = Pager(query, page=1, lifetime=3600)
        query = DummyModel.query().filter(DummyModel.value < 10)
        pager2 = Pager(query, page=1, lifetime=3600)
        self.assertNotEqual(pager1._query_id, pager2._query_id)

    def test_get_memcache_key(self):
        pager = Pager(self.query, page=1, lifetime=3600)
        key = pager._get_memcache_key(page=3)
        self.assertIn('Pager-', key)
        self.assertIn('-3', key)
