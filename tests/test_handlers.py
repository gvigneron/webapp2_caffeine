# -*- coding: utf-8 -*-
import unittest

from jinja2.exceptions import TemplateNotFound
from webapp2 import Request, Response, WSGIApplication

from webapp2_caffeine.handlers import BaseRequestHandler
from webapp2_caffeine.handlers import ImproperlyConfigured
from webapp2_caffeine.handlers import TemplateRequestHandler
from webapp2_caffeine.test_case import BaseTestCase, wsgi_config


class BaseHandler(BaseRequestHandler):

    def get(self, *args, **kwargs):
        self.response.write('Hello World ! {}')


class BaseRequestHandlerTest(BaseTestCase, unittest.TestCase):

    application = WSGIApplication([('/', BaseHandler)],
                                  config=wsgi_config, debug=True)

    def setUp(self):
        super(BaseRequestHandlerTest, self).setUp()
        self.request = Request.blank('/', environ={
            'CONTENT_TYPE': 'text/html; charset=ISO-8859-4',
        })
        self.response = Response()
        self.testapp.app.set_globals(
            app=self.testapp.app, request=self.request)

    def test_init(self):
        handler = BaseRequestHandler(self.request, self.response)
        self.assertEqual(handler.LANGUAGE, 'en')
        self.assertEqual(handler.request, self.request)
        self.assertEqual(handler.response, self.response)

    def test_auth(self):
        handler = BaseRequestHandler(self.request, self.response)
        # Ducktype auth object.
        self.assertEqual(handler.auth.request, self.request)


class TemplateHandler(TemplateRequestHandler):

    template_name = 'test_template.html'


class TemplateRequestHandlerTest(BaseTestCase, unittest.TestCase):

    application = WSGIApplication([('/', TemplateHandler)],
                                  config=wsgi_config, debug=True)

    def setUp(self):
        super(TemplateRequestHandlerTest, self).setUp()
        self.request = Request.blank('/', environ={
            'CONTENT_TYPE': 'text/html; charset=ISO-8859-4',
        })
        self.response = Response()
        self.testapp.app.set_globals(
            app=self.testapp.app, request=self.request)

    def test_get(self):
        handler = TemplateRequestHandler(self.request, self.response)
        handler.template_name = 'test_template.html'
        with self.assertRaises(TemplateNotFound):
            self.testapp.get('/')

    def test_get_template_name(self):
        handler = TemplateRequestHandler(self.request, self.response)
        with self.assertRaises(ImproperlyConfigured):
            handler.get_template_name()
        handler.template_name = 'test_template.html'
        self.assertEqual(handler.get_template_name(), 'test_template.html')

    def test_get_context_data(self):
        handler = TemplateRequestHandler(self.request, self.response)
        self.assertIn('view', handler.get_context_data())
        self.assertIn('test', handler.get_context_data(test=123))
