# -*- coding: utf-8 -*-
"""Base security functions."""
import base64
import random
import time
import urlparse


UNICODE_ASCII_CHARACTER_SET = ('abcdefghijklmnopqrstuvwxyz'
                               'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                               '0123456789')

ALWAYS_SAFE = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')

CLIENT_ID_CHARACTER_SET = (r' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMN'
                           'OPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}')


def generate_token(length=255, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generate a non-guessable string.

    Can be used for OAuth token.
    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.

    Can be used for OAuth client_id and client_secret.
    OAuth 2 specify the format of client_id in
    http://tools.ietf.org/html/rfc6749#appendix-A.
    """
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for dummy in range(length))


def generate_oauthstatetoken(_time=None):
    """Create a new random token that can be safely used as a URL param.

    Token would normally be stored in a user session and passed as 'state'
    parameter during OAuth 2.0 authorization step.
    """
    now = str(_time or long(time.time()))
    secret = generate_token(30, chars=ALWAYS_SAFE)
    token = ':'.join([secret, now])
    return base64.urlsafe_b64encode(token)


def safe_string_equals(string_a, string_b):
    """Near-constant time string comparison.

    Used in order to avoid timing attacks on sensitive information such
    as secret keys during request verification.
    """
    if len(string_a) != len(string_b):
        return False

    result = 0
    for string_x, string_y in zip(string_a, string_b):
        result |= ord(string_x) ^ ord(string_y)
    return result == 0


def safe_oauthstatetoken_validation(expected, actual):
    """Validate expected token against the actual.

    Args:
        expected (str) -- Existing token. Normally stored in a user session.
        actual (str) -- Token provided (via 'state' param in oauth2).
    """
    if not safe_string_equals(expected, actual):
        return False

    try:
        decoded = base64.urlsafe_b64decode(expected.encode('ascii'))
        token_key, token_time = decoded.rsplit(':', 1)
        if not token_key:
            return False
        token_time = long(token_time)
    except (TypeError, ValueError, UnicodeDecodeError):
        return False
    now = long(time.time())
    timeout = now - token_time > 3600
    return not timeout


def is_safe_url(url, host=None):
    """Check URL 'safety'.

    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).

    Always returns ``False`` on an empty url.

    Returns:
        (bool)

    """
    if not url:
        return False
    url_info = urlparse.urlparse(url)
    return (not url_info.netloc or url_info.netloc == host) and \
        (not url_info.scheme or url_info.scheme in ['http', 'https'])
