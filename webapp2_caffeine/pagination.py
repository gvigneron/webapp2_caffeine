# -*- coding: utf-8 -*-
"""Pager for ndb request."""
import hashlib

from google.appengine.api import memcache
from google.appengine.datastore.datastore_query import Cursor


class Pager(object):
    """NDB pager."""

    has_next = False  # Next page exists.
    __query_id = ''  # Quary hash.

    def __init__(self, query, page=0, lifetime=3600):
        """Set pager attributes."""
        self.query = query
        self.lifetime = lifetime
        try:
            self.page = int(page)
        except ValueError:
            self.page = 1
        if self.page < 1:
            self.page = 1

    def paginate(self, page_size=20, **q_options):
        """Fetch page and return results.

        Args:
            page_size (int)
            q_options (obj) -- Query options.

        Return:
            (results, cursor, more)

        """
        cursor = self._get_cursor(self.page, page_size, **q_options)
        results, cursor, more = self.query.fetch_page(page_size,
                                                      start_cursor=cursor,
                                                      **q_options)
        self.has_next = more
        return results, cursor, more

    def _get_cursor(self, page, page_size=20, **q_options):
        """Return the cursor for the given page."""
        # Check if cursor already exists.
        curs = self._get_cursor_from_cache(page, page_size=20, **q_options)
        if curs:
            return curs
        # Compute new cursor.
        if self.page > 1:
            # Get cursor.
            for page in xrange(1, 10000 / page_size):
                if page == self.page:
                    break
                dummy, curs, more = self.query.fetch_page(page_size,
                                                          start_cursor=curs,
                                                          keys_only=True,
                                                          **q_options)
                self._set_cursor_to_cache(curs, page, page_size, **q_options)
                if not more:
                    break
        return curs

    def _get_cursor_from_cache(self, page, page_size=20, **q_options):
        cursor_key = self._get_memcache_key(page=page)
        value = memcache.get(cursor_key)
        if value:
            return Cursor.from_bytes(value)
        else:
            return None

    def _set_cursor_to_cache(self, cursor, page, page_size=20, **q_options):
        """Set Cursor to memcahe."""
        cursor_key = self._get_memcache_key(page=page)
        memcache.add(cursor_key, cursor.to_bytes(), time=self.lifetime)

    @property
    def _query_id(self):
        if not hasattr(self, '__query_id'):
            hsh = hashlib.sha1()
            hsh.update(repr(self.query))
            self.__query_id = hsh.hexdigest()
        return self.__query_id

    def _get_memcache_key(self, page):
        """Return a unique key for query and Cursor."""
        return '{}-{}-{}'.format(self.__class__.__name__, self._query_id, page)

    @property
    def has_prev(self):
        """Previous page exists."""
        return self.page > 1

    @property
    def prev_page(self):
        """Return previous page."""
        if self.has_prev:
            return self.page - 1
        else:
            return self.page

    @property
    def next_page(self):
        """Return next page."""
        if self.has_next:
            return self.page + 1
        else:
            return self.page

    def __nonzero__(self):
        """Return True if previous page or next page, else False."""
        return self.has_prev or self.has_next
