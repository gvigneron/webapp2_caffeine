# -*- coding: utf-8 -*-
"""Utilities for in memory cache."""
import logging
import time


# Instance data cache `{key: (value, expiration)}`
CACHE = {}


def flush():
    """Reset the cache of the current instance, not all the instances."""
    global CACHE
    CACHE = {}


class CacheContainer(object):
    """Generic cache container for "per instance" data.

    Attribute:
        key (str) -- Object key in cache.
        validity (int) -- Cache validity in seconds.
    """

    key = None
    validity = 21600  # 6 hours

    @property
    def value(self):
        """Return value from cache."""
        value = self.get()
        if value:
            return value
        value = self.update()
        return value

    def get(self):
        """Get the data associated to the key or a None."""
        global CACHE
        if self.key not in CACHE:
            return None
        value, expiration = CACHE[self.key]
        now = time.time()
        if expiration is None or now < expiration:
            return value
        else:
            self.delete()
            return None

    def set(self, value, expiration=None):
        """Set data in cache."""
        if self.key is None:
            raise ValueError('CacheContainer.key must be set.')
        global CACHE
        if expiration is None:
            expiration = time.time() + self.validity
        msg = 'Set cache for {}'.format(self.key)
        logging.info(msg)
        CACHE[self.key] = (value, expiration)
        return (value, expiration)

    def delete(self):
        """Delete data from cache."""
        global CACHE
        CACHE.pop(self.key, None)

    def update(self):
        """Update cache."""
        value = self.fresh_value
        self.set(value)
        return value

    @property
    def fresh_value(self):
        """Return an updated value to set in cache."""
        raise NotImplementedError()
