# -*- coding: utf-8 -*-
"""Extensions for unittest.TestCase."""
import os
import warnings

from google.appengine.api import apiproxy_stub
from google.appengine.api import namespace_manager
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import ndb
from google.appengine.ext import testbed
import webapp2
import webtest

try:
    from appengine_config import wsgi_config
except ImportError:
    wsgi_config = {'webapp2_extras.auth':
                   {'user_model': 'webapp2_extras.appengine.auth.models.User',
                    'token_max_age': 3600,
                    'user_attributes': ['auth_ids']},
                   'webapp2_extras.sessions':
                   {'secret_key': '1234567890',
                    'cookie_name': '_session',
                    'session_max_age': 3600,
                    'cookie_args': {'max_age': 3600}}}


class FetchServiceStub(apiproxy_stub.APIProxyStub):
    def __init__(self, service_name='urlfetch'):
        super(FetchServiceStub, self).__init__(service_name)

    def set_return_values(self, **kwargs):
        self.return_values = kwargs

    def _Dynamic_Fetch(self, request, response):
        rv = self.return_values
        response.set_content(rv.get('content', ''))
        response.set_statuscode(rv.get('status_code', 500))
        for header_key, header_value in rv.get('headers', {}):
            new_header = response.add_header()  # prototype for a header
            new_header.set_key(header_key)
            new_header.set_value(header_value)
        response.set_finalurl(rv.get('final_url', request.url))
        response.set_contentwastruncated(
            rv.get('content_was_truncated', False))

        # allow to query the object after it is used
        self.request = request
        self.response = response


class BaseTestCase(object):
    """Test case with GAE testbed stubs activated.

    Example :

        class MyTest(BaseTestCase, unittest.TestCase):

    """

    application = webapp2.WSGIApplication([], config=wsgi_config, debug=True)

    def setUp(self):
        """Activate GAE testbed."""
        # Show warnings.
        warnings.simplefilter('default')
        # Clear thread-local variables.
        self.clear_globals()
        # Get current and root path.
        start = os.path.dirname(__file__)
        self.rel_root_path = os.path.join(start, '../../../')
        self.abs_root_path = os.path.realpath(self.rel_root_path)
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Set environment variables.
        self.testbed.setup_env(HTTP_HOST='localhost')
        self.testbed.setup_env(SERVER_SOFTWARE='Development')
        # Next, declare which service stubs you want to use.
        self.testbed.init_app_identity_stub()
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=1)
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        ndb.get_context().clear_cache()
        self.testbed.init_blobstore_stub()
        self.testbed.init_urlfetch_stub()
        self.testbed.init_user_stub()
        self.testbed.init_taskqueue_stub(root_path=self.abs_root_path)
        self.testbed.init_images_stub()
        # Set stubs access.
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)
        # URLFetch stub.
        self.testbed._disable_stub('urlfetch')
        self.fetch_stub = FetchServiceStub()
        self.testbed._register_stub('urlfetch', self.fetch_stub)
        # Reset namespace.
        namespace_manager.set_namespace('')
        # Update application config to force template absolute import.
        rel_templates_path = os.path.join(start, '../templates')
        abs_templates_path = os.path.realpath(rel_templates_path)
        self.application.config.update(
            {'templates_path': abs_templates_path})
        # Wrap the app with WebTest’s TestApp.
        self.testapp = webtest.TestApp(self.application)

    def tearDown(self):
        """Deasctivate testbed."""
        self.testbed.deactivate()

    def clear_globals(self):
        webapp2._local.__release_local__()

    def login_admin(self):
        """Log in the current user as admin."""
        self.testbed.setup_env(user_is_admin='1')

    def logout_admin(self):
        """Log out the current user as admin."""
        self.testbed.setup_env(user_is_admin='0')

    def assertRouteUrl(self, route_name, url, args=None, kwargs=None):
        """Test that given route name match the URL.

        Args:
            route_name -- (str) webapp2 route name.
            url -- (str) Expected URL.
            args -- (iter) Route args.
            kwargs -- (dict) Route kwargs.
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        # Set a dummy request just to be able to use uri_for().
        req = webapp2.Request.blank('/')
        req.app = self._application
        self._application.set_globals(app=self._application, request=req)

        route_url = webapp2.uri_for(
            route_name, *args, **kwargs)
        message = 'Route `{}` URL is not `{}` but `{}`'
        self.assertEqual(route_url, url, message.format(
            route_name, url, route_url))

    def uri_for(self, _name, *args, **kwargs):
        """Return a URI for a named :class:`Route`."""
        # Set a dummy request just to be able to use uri_for().
        req = webapp2.Request.blank('/')
        req.app = self._application
        self._application.set_globals(app=self._application, request=req)

        return webapp2.uri_for(_name, *args, **kwargs)


class ModelTestCase(BaseTestCase):
    """Test case with test method for model properties.

    Test the type of the fields listed in `properties` for the model
    `model_class`.

    Example :

        class MyModelTest(ModelTestCase, unittest.TestCase):
            model_class = YourModelToTest
            properties = {'your_field_name': FieldType,}

    """

    model_class = None
    properties = {}

    def test_properties(self):
        """Test the type listed in `properties`."""
        for _property, _type in self.properties.iteritems():
            msg = 'Missing property `{}` in model `{}`'
            self.assertTrue(hasattr(self.model_class, _property),
                            msg.format(_property, self.model_class))
            msg = 'Invalid property type for `{}` in model `{}`'
            self.assertTrue(isinstance(getattr(self.model_class, _property),
                                       _type),
                            msg.format(_property, self.model_class))


class FormTestCase(BaseTestCase):
    """Test case with test methods for forms."""

    form_class = None
    fields_type = None
    fields_validators = None

    def assertFieldsCount(self, form_class, count):
        """Test fields count."""
        self.assertEqual(len(form_class()._fields), count)

    def assertFieldsType(self, form_class, fields_type):
        """Test fields type."""
        for _property, _type in fields_type.iteritems():
            self.assertTrue(hasattr(form_class, _property))
            self.assertEqual(getattr(form_class, _property).field_class, _type)

    def assertWidgets(self, form_class, widgets):
        """Test widgets."""
        for _property, _widget in widgets.iteritems():
            res = getattr(self.form_class, _property).kwargs.get(
                'widget').__class__
            self.assertEqual(res, _widget)

    def assertValidators(self, form_class, fields_validators):
        """Test fields validators."""
        for _field, _validators in fields_validators.iteritems():
            _field_validators = getattr(form_class, _field).kwargs.get(
                'validators')
            _field_validators = [
                validator.__class__ for validator in _field_validators]
            for _validator in _validators:
                self.assertIn(_validator, _field_validators)

    def assertExcluded(self, form_class, fields_exluded):
        """Test fields exclusions."""
        msg = 'Field {} not excluded from {}'
        for field in fields_exluded:
            self.assertFalse(hasattr(form_class, field),
                             msg.format(field, form_class))
