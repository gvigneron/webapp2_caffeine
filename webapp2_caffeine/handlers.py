# -*- coding: utf-8 -*-
"""Generic requests handlers."""
import datetime
from operator import itemgetter

from google.appengine.ext import ndb
from jinja2 import FileSystemLoader
from webapp2 import cached_property
from webapp2 import RequestHandler
from webapp2 import uri_for
from webapp2_extras import auth
from webapp2_extras import i18n
from webapp2_extras import jinja2
from webapp2_extras import sessions
from webapp2_extras import sessions_memcache


try:
    from appengine_config import template_loaders
except ImportError:
    template_loaders = FileSystemLoader('')


try:
    from appengine_config import available_languages
except ImportError:
    available_languages = {
        'en': 'en_US',
        'fr': 'fr_FR'
    }

try:
    from appengine_config import language_code
except ImportError:
    language_code = 'en_US'


EXTENSIONS = ['jinja2.ext.autoescape', 'jinja2.ext.with_', 'jinja2.ext.i18n']


def jinja2_factory(app, loaders=None):
    """Set configuration environment for Jinja2.

    Args:
        app -- (WSGIApplication)
        loaders -- (list) Jinja2 template loaders

    Return:
        (Jinja2) A Jinja2 instance.
    """
    if loaders is None:
        loaders = template_loaders
    config = {'environment_args': {'extensions': EXTENSIONS,
                                   'loader': loaders},
              'globals': {'uri_for': uri_for, 'datetime': datetime},
              'filters': {}}
    j = jinja2.Jinja2(app, config=config)
    return j


class BaseRequestHandler(RequestHandler):
    """Base request handler with session support and Jinja2 templates."""

    session_store = None

    @cached_property
    def auth(self):
        """Shortcut to access the auth instance as a property."""
        return auth.get_auth()

    @cached_property
    def user_info(self):
        """Shortcut to access a subset of the user attributes.

        That subset is stored in session.
        The list of attributes to store in the session is specified in
        config['webapp2_extras.auth']['user_attributes'].

        Returns:
            A dictionary with most user information

        """
        return self.auth.get_user_by_session()

    @cached_property
    def user(self):
        """Shortcut to access the current logged in user.

        Unlike user_info, it fetches information from the persistence layer and
        returns an instance of the underlying model.

        Returns:
            The instance of the user model associated to the logged in user.

        """
        usr = self.user_info
        return self.user_model.get_by_id(usr['user_id'], namespace='') \
            if usr else None

    @cached_property
    def user_model(self):
        """Return the implementation of the user model.

        If set, it's consistent with
            config['webapp2_extras.auth']['user_model']

        """
        return self.auth.store.user_model

    @cached_property
    def session(self):
        """Shortcut to access the current session."""
        factory = sessions_memcache.MemcacheSessionFactory
        return self.session_store.get_session(factory=factory)

    @cached_property
    def jinja2(self):
        """Return a Jinja2 renderer cached in the app registry."""
        return jinja2.get_jinja2(factory=jinja2_factory, app=self.app)

    def render_html(self, _template, **context):
        """Render a template and writes the result to the response."""
        context.update({'user': self.user_info})
        resp = self.jinja2.render_template(_template, **context)
        self.response.write(resp)

    @classmethod
    def _extract_locale_from_header(cls, locale_header):
        """Extract locale from HTTP Accept-Language header.

        We only support langage, not locale for now.
        Header with en-GB will be set as en_US, etc.

        Args:
            locale_header (str): HTTP Accept-Language header.

        Returns:
            (str) Locale.

        """
        if locale_header is None:
            return language_code
        parts = (part.split(';q=')
                 for part in locale_header.replace(' ', '').split(','))
        languages = ((part[0].split('-')[0].lower(),
                      float(part[1]) if len(part) > 1 else 1.0)
                     for part in parts)
        languages = [language for language in languages
                     if language[0].lower() in available_languages]
        languages.sort(key=itemgetter(1), reverse=True)
        locale = available_languages[languages[0][0]] if len(
            languages) > 0 else language_code
        return locale

    def request_language(self):
        """Return primary language from request."""
        locale_header = self.request.headers.get('Accept-Language')
        if locale_header is None:
            return None
        parts = (part.split(';q=')
                 for part in locale_header.replace(' ', '').split(','))
        languages = [(part[0].split('-')[0].lower(),
                      float(part[1]) if len(part) > 1 else 1.0)
                     for part in parts]
        languages.sort(key=itemgetter(1), reverse=True)
        try:
            return languages[0][0]
        except IndexError:
            return None

    def __init__(self, request, response):
        """Override the initialiser in order to set the language."""
        self.initialize(request, response)
        # Set language.
        locale_header = self.request.headers.get('Accept-Language')
        locale = self._extract_locale_from_header(locale_header)
        i18n.get_i18n().set_locale(locale)
        self.LANGUAGE = i18n.get_i18n().locale[0:2]

    def dispatch(self):
        """Override the dispatcher in order to set session."""
        # Get a session store for this request.
        self.session_store = sessions.get_store()
        try:
            super(BaseRequestHandler, self).dispatch()
        finally:
            self.session_store.save_sessions(self.response)

    def get_geodata(self):
        """Return `Request` geo data dict."""
        geopt = ndb.GeoPt(self.request.headers.get('X-AppEngine-CityLatLong'))\
            if self.request.headers.get('X-AppEngine-CityLatLong') else None
        return {'language': self.request_language(),
                'country': self.request.headers.get('X-AppEngine-Country'),
                'region': self.request.headers.get('X-AppEngine-Region'),
                'city': self.request.headers.get('X-AppEngine-City'),
                'geopt': geopt}


class RedirectHandler(BaseRequestHandler):
    """Redirect handler."""

    redirect_url = None

    def get(self, *args, **kwargs):
        """Return redirection."""
        self.redirect(self.get_redirect_url())

    def get_redirect_url(self):
        """Return success URL."""
        return self.uri_for(self.redirect_url)


class ImproperlyConfigured(Exception):
    """App is somehow improperly configured."""


class TemplateRequestHandler(BaseRequestHandler):
    """Generic handler for template view."""

    template_name = None

    def get(self, *args, **kwargs):
        """Render template."""
        context = self.get_context_data(**kwargs)
        template = self.get_template_name()
        self.render_html(template, **context)

    def get_template_name(self):
        """Return a template name to be used for the request."""
        if self.template_name is None:
            raise ImproperlyConfigured(
                "TemplateRequestHandler requires either a definition of "
                "'template_name' or an implementation of "
                "'get_template_names()'")
        else:
            return self.template_name

    def get_context_data(self, **kwargs):
        """Return kwargs as template context."""
        if 'view' not in kwargs:
            kwargs['view'] = self
        return kwargs


class ModelRequestHandler(TemplateRequestHandler):
    """To render an entity."""

    model = None
    _entity = None

    def get(self, *args, **kwargs):
        """Render template with entity in context."""
        if kwargs.get('object_id'):
            self._set_entity(kwargs.get('object_id'))
            if not self._entity:
                return self.response.set_status(404)
        super(ModelRequestHandler, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add model entity to context."""
        kwargs = super(ModelRequestHandler, self).get_context_data(**kwargs)
        if self._entity:
            kwargs['object'] = self._entity
        return kwargs

    def _set_entity(self, object_id):
        """Set model entity."""
        try:
            object_id = int(object_id)
        except ValueError:
            pass
        if self.request.route_kwargs.get('parent_id'):
            parent_id = self.request.route_kwargs.get('parent_id')
            try:
                parent_id = int(parent_id)
            except ValueError:
                pass
            key = ndb.Key(self.model.parent_class, parent_id,
                          self.model, object_id)
            self._entity = key.get()
        else:
            self._entity = self.model.get_by_id(object_id)


class ChildsRequestHandler(TemplateRequestHandler):
    """To render list of an entity childrens."""

    child_model = None
    parent_id_key = 'parent_id'
    limit = 20

    def get_context_data(self, **kwargs):
        """Add list items to context."""
        kwargs = super(ChildsRequestHandler, self).get_context_data(**kwargs)
        ancestor = ndb.Key(self.child_model.parent_class,
                           kwargs[self.parent_id_key])
        items = self.queryset(ancestor).fetch_async(self.limit)
        parent = ancestor.get_async()
        kwargs['parent'] = parent.get_result()
        kwargs['items'] = items.get_result()
        return kwargs

    def queryset(self, ancestor):
        """Return child query."""
        return self.child_model.query(ancestor=ancestor)


class FormRequestHandler(TemplateRequestHandler):
    """Render a form on GET and processes it on POST."""

    form_class = None
    form_prefix = ''
    success_url = None
    template_name = None

    def get(self, *args, **kwargs):
        """Instantiate a blank version of the form."""
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(form=form)
        template = self.get_template_name()
        self.render_html(template, **context)

    def post(self, *args, **kwargs):
        """Check POT variables for validity and call response method."""
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.validate():
            self.form_valid(form)
        else:
            self.form_invalid(form)

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        self.redirect(self.get_succes_url())

    def get_succes_url(self):
        """Return success URL."""
        return self.uri_for(self.success_url)

    def form_invalid(self, form):
        """If the form is invalid.

        Re-render the context data with the data-filled form and errors.
        """
        context = self.get_context_data(form=form)
        template = self.get_template_name()
        self.render_html(template, **context)

    def get_form_class(self):
        """Return the form class to use in this view."""
        return self.form_class

    def get_form(self, form_class):
        """Return an instance of the form to be used in this view."""
        return form_class(self.get_form_kwargs(), prefix=self.form_prefix)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        method_name = self.request.method.upper().replace('-', '_')
        if method_name == 'POST':
            return self.request.POST
        else:
            return self.request.GET


class ModelFormRequestHandler(FormRequestHandler):
    """Render a model form on GET and processes it on POST."""

    model = None
    form_prefix = ''
    _entity = None

    def get(self, *args, **kwargs):
        """Instantiate a blank version of the form."""
        if kwargs.get('object_id'):
            self._set_entity(kwargs.get('object_id'))
            if not self._entity:
                return self.response.set_status(404)
        super(ModelFormRequestHandler, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):  # pylint: disable=W0613
        """Check POT variables for validity and call response method."""
        if kwargs.get('object_id'):
            self._set_entity(kwargs.get('object_id'))
            if not self._entity:
                return self.response.set_status(404)
        super(ModelFormRequestHandler, self).post(*args, **kwargs)

    def _set_entity(self, object_id):
        """Set model entity."""
        try:
            object_id = int(object_id)
        except ValueError:
            pass
        if self.request.route_kwargs.get('parent_id'):
            parent_id = self.request.route_kwargs.get('parent_id')
            try:
                parent_id = int(parent_id)
            except ValueError:
                pass
            key = ndb.Key(self.model.parent_class, parent_id,
                          self.model, object_id)
            self._entity = key.get()
        else:
            self._entity = self.model.get_by_id(object_id)

    def form_valid(self, form):
        """Create entity and redirect."""
        # Create entity
        entity = self._entity or self.model()
        form.populate_obj(entity)
        entity.put()
        # Redirect
        super(ModelFormRequestHandler, self).form_valid(form)

    def get_form(self, form_class):
        """Return an instance of the form to be used in this view."""
        return form_class(self.get_form_kwargs(),
                          obj=self._entity,
                          data=self.request.route_kwargs,
                          prefix=self.form_prefix)

    def get_context_data(self, **kwargs):
        """Return kwargs as template context."""
        kwargs = super(ModelFormRequestHandler,
                       self).get_context_data(**kwargs)
        if self._entity:
            kwargs['object'] = self._entity
        return kwargs
