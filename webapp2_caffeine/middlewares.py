# -*- coding: utf-8 -*-
"""Middlewares for Google App Engine Python instances.

Usage:
  Create a file `appengine_config.py` with:

    ```
    def webapp_add_wsgi_middleware(app):
      app = clear_event_queue(app)
      app = DisableNdbCaching(app)
      return app
    ```
"""
from google.appengine.ext import ndb


class DisableNdbCaching(object):
    """Disable ndb cache.

    The NDB cache is stored in the _State’s context, which means it is a
    thread-local cache, not shared between threads.

    These caches are only cleared when the next request comes in (in
    `tasklets.get_context`). This means for the duration *inbetween* calls, the
    thread will hold on to the cache. Given that the threadpool balancer
    appears to be doing a great job of loadbalancing between threads (each
    request gets its own thread-local variables)... this means each thread
    (with 600+ threads per instance in production) will accumulate it’s own
    cache of NDB objects to sit in memory un-used between requests.

    You can fix this part by disabling NDB cache entirely.
    """

    def __init__(self, application):
        """Set application."""
        self.application = application

    def __call__(self, environ, start_response):
        """Disable cache in ndb context."""
        ctx = ndb.get_context()
        ctx.set_cache_policy(False)

        response = self.application(environ, start_response)

        ctx.clear_cache()
        return response


def clear_event_queue(app):
    """Clear ndb event queue.

    Some Futures complete and get their job done, triggering completion
    callbacks to be stuck in the event queue. However, since we just writing
    regular NDB code (not tasklets), there is no guarantee that the event queue
    will be emptied when the request finishes. This leaves Futures stuck in the
    thread-local cache, in each thread, uselessly between requests.

    There is no way to disable this like with an NDB cache.

    However, You can solve this by wrapping *any* code that uses NDB objects
    with `@ndb.toplevel`. The documentation mentions this only in the context
    of being useful for tasklet code this should be run for *ALL* code that
    uses NDB libraries. In fact, given the nature of what it does, can be done
    in a wrapper around the wsgi library in the appengine runtime, similar to
    what is done with the threadlocal variables in `appengine.runtime`’s
    management of `request_environment.current_request`.
    """
    return ndb.toplevel(app)
