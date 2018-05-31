# -*- coding: utf-8 -*-
import base64
import unittest

from webapp2_caffeine.security import generate_oauthstatetoken
from webapp2_caffeine.security import generate_token
from webapp2_caffeine.security import is_safe_url
from webapp2_caffeine.security import safe_oauthstatetoken_validation
from webapp2_caffeine.security import safe_string_equals


class GenerateTokenTest(unittest.TestCase):

    def runTest(self):
        a = generate_token(10)
        b = generate_token(10)
        self.assertEqual(len(a), 10)
        self.assertNotEqual(a, b)


class GenerateOauthStateTokenTest(unittest.TestCase):

    def runTest(self):
        a = generate_oauthstatetoken(_time=1234567890)
        el = base64.urlsafe_b64decode(a).split(':')
        self.assertEqual(el[1], '1234567890')
        self.assertEqual(len(el[0]), 30)


class SafeEtringEqualsTest(unittest.TestCase):

    def runTest(self):
        a = generate_token(10)
        b = generate_token(10)
        self.assertTrue(safe_string_equals(a, a))
        self.assertFalse(safe_string_equals(a, b))


class SafeOauthStateTokenValidationTest(unittest.TestCase):

    def runTest(self):
        a = generate_oauthstatetoken()
        b = generate_oauthstatetoken()
        self.assertTrue(safe_oauthstatetoken_validation(a, a))
        self.assertFalse(safe_oauthstatetoken_validation(a, b))


class IsSafeUrlTest(unittest.TestCase):

    def runTest(self):
        self.assertTrue(is_safe_url('http://test.com', 'test.com'))
        self.assertFalse(is_safe_url('http://dummy.com', 'test.com'))
        self.assertFalse(is_safe_url('ftp://test.com', 'test.com'))
