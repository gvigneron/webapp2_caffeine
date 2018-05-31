# -*- coding: utf-8 -*-
"""Generic form fields."""
from datetime import datetime
import decimal
import json

from google.appengine.ext import ndb

from wtforms import validators
from wtforms.compat import string_types
from wtforms.fields import SelectField
from wtforms.fields import TextAreaField
from wtforms.fields.html5 import DateField as CoreDateField
from wtforms.fields.html5 import DateTimeField as CoreDateTimeField
from wtforms.fields.html5 import DecimalField as CoreDecimalField
from wtforms.fields.html5 import IntegerField as CoreIntegerField
from wtforms.widgets import Input
from wtforms.widgets import Select
from wtforms_appengine.fields import IntegerListPropertyField
from wtforms_appengine.fields import KeyPropertyField as CoreKeyPropertyField
from wtforms_appengine.ndb import ModelConverter


class DateTimeInput(Input):
    """Render an input with type "datetime"."""

    input_type = 'datetime-local'


class ReadOnlyWidgetProxy(object):
    """Proxy to create read-only widget."""

    def __init__(self, widget):
        """Set widget."""
        self.widget = widget

    def __getattr__(self, name):
        """Get widget attribute."""
        return getattr(self.widget, name)

    def __call__(self, field, **kwargs):
        """Set widget defaults."""
        kwargs.setdefault('readonly', True)
        # Some html elements also need disabled attribute to achieve the
        # expected UI behaviour.
        kwargs.setdefault('disabled', True)
        return self.widget(field, **kwargs)


def do_nothing(*args, **kwargs):
    """Do nothing function."""
    pass


def read_only(field):
    """Set a field as read-only."""
    field.widget = ReadOnlyWidgetProxy(field.widget)
    field.process = do_nothing
    field.populate_obj = do_nothing
    return field


class DecimalField(CoreDecimalField):
    """Customized decimal field."""

    def populate_obj(self, obj, name):
        """Populate `obj.<name>` with the field's data.

        Note:
            This is a destructive operation. If `obj.<name>` already exists, it
            will be overridden. Use with caution.
        """
        setattr(obj, name, float(self.data))

    def process_formdata(self, valuelist):
        """Parse decimal data."""
        if valuelist and valuelist[0]:
            try:
                if self.use_locale:
                    self.data = self._parse_decimal(valuelist[0])
                else:
                    self.data = decimal.Decimal(valuelist[0])
            except (decimal.InvalidOperation, ValueError):
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value'))


class IntegerField(CoreIntegerField):
    """Allow empty value."""

    def process_formdata(self, valuelist):
        """Parse integer data."""
        if valuelist and valuelist[0]:
            try:
                self.data = int(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid integer value'))


class DateField(CoreDateField):
    """Allow empty value."""

    def process_formdata(self, valuelist):
        """Parse date data."""
        if valuelist and valuelist[0]:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))


class DateTimeField(CoreDateTimeField):
    """Allow empty value."""

    widget = DateTimeInput()

    def __init__(self, label=None, validators=None,
                 format='%Y-%m-%dT%H:%M:%S', **kwargs):
        """Set defaults."""
        super(DateTimeField, self).__init__(
            label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        """Parse datetime data."""
        if valuelist and valuelist[0]:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.strptime(
                    date_str, self.format)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))


class JsonField(TextAreaField):
    """JSON data field."""

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return json.dumps(self.data)
        else:
            return ''

    def pre_validate(self, form):
        """Pre-validate JSON data."""
        try:
            json.loads(self.data)
        except ValueError:
            message = self.gettext('Not a valid JSON.')
            raise ValueError(message)

    def populate_obj(self, obj, name):
        """Populate `obj.<name>` with the field's data.

        Note:
            This is a destructive operation. If `obj.<name>` already exists, it
            will be overridden. Use with caution.
        """
        setattr(obj, name, json.loads(self.data))


class KeyPropertyField(CoreKeyPropertyField):
    """Customized `KeyPropertyField`."""

    def iter_choices(self):
        """Iterate on field choices.

        Yield:
            (Key, str, bool) -- Entity key, label, field data exists
        """
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.query:
            key = str(obj.key.id())
            label = self.get_label(obj)
            yield (key, label, (self.data == obj.key) if self.data else False)

    def pre_validate(self, form):
        """Pre-validate key data."""
        if self.data is not None:
            for obj in self.query:
                if hasattr(self.data, 'key') and self.data.key == obj.key:
                    break
                elif self.data == obj.key:
                    break
            else:
                raise ValueError(self.gettext('Not a valid choice'))
        elif not self.allow_blank:
            raise ValueError(self.gettext('Not a valid choice'))

    def populate_obj(self, obj, name):
        """Populate `obj.<name>` with the field's data.

        Note:
            This is a destructive operation. If `obj.<name>` already exists, it
            will be overridden. Use with caution.
        """
        try:
            setattr(obj, name, self.data.key)
        except AttributeError:
            setattr(obj, name, self.data)


class KeyPropertyMultiField(KeyPropertyField):
    """Multi choice `KeyPropertyField`."""

    widget = Select(multiple=True)
    reference_class = None

    def __init__(self, *args, **kwargs):
        """Set reference_class."""
        super(KeyPropertyMultiField, self).__init__(*args, **kwargs)
        self.reference_class = kwargs.get('reference_class')

    def iter_choices(self):
        """Iterate on field choices.

        Yield:
            (Key, str, bool) -- Entity key, label, field data exists
        """
        for obj in self.query:
            key = str(obj.key.id())
            label = self.get_label(obj)
            yield (key, label, (obj.key in self.data) if self.data else False)

    def pre_validate(self, form):
        """Pre-validate keys data."""
        if self.data is not None:
            choices = [entity.key for entity in self.query]
            for value in self.data:
                if hasattr(value, 'key') and value.key in choices:
                    pass
                elif value in choices:
                    pass
                else:
                    raise ValueError(self.gettext('Not a valid choice'))
        elif not self.allow_blank:
            raise ValueError(self.gettext('Not a valid choice'))

    def populate_obj(self, obj, name):
        """Populate `obj.<name>` with the field's data.

        Note:
            This is a destructive operation. If `obj.<name>` already exists, it
            will be overridden. Use with caution.
        """
        if self.data is not None:
            values = self.data if hasattr(
                self.data, '__iter__') else [self.data]
        else:
            values = []
        try:
            setattr(obj, name, [value.key for value in values])
        except AttributeError:
            setattr(obj, name, values)

    def process_formdata(self, valuelist):
        """Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        Args:
            valuelist -- (list) A list of strings to process.
        """
        if valuelist:
            self._data = None
            self._formdata = valuelist

    def _get_data(self):
        if self._formdata is not None:
            try:
                data = [ndb.Key(self.reference_class, int(key_id))
                        for key_id in self._formdata]
            except (TypeError, ValueError):
                data = [ndb.Key(self.reference_class, key_id)
                        for key_id in self._formdata]
            self._set_data(data)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)


class HTML5Converter(ModelConverter):
    """Convert properties from a `ndb.Model` class to HTML5 form fields."""

    def convert(self, model, prop, field_args):
        """Return a form field for a single model property.

        Args:
            model -- The ``db.Model`` class that contains the property.
            prop -- The model property: a ``db.Property`` instance.
            field_args -- Optional keyword arguments to construct the field.
        """
        prop_type_name = type(prop).__name__

        # check for generic property
        if prop_type_name == "GenericProperty":
            # try to get type from field args
            generic_type = field_args.get("type")
            if generic_type:
                prop_type_name = field_args.get("type")
            # if no type is found, the generic property uses string set in
            # convert_GenericProperty
        kwargs = {
            'label': prop._code_name.replace('_', ' ').title(),
            'default': prop._default,
            'validators': [],
        }
        if field_args:
            kwargs.update(field_args)

        if prop._required and prop_type_name not in self.NO_AUTO_REQUIRED:
            kwargs['validators'].append(validators.required())

        if kwargs.get('choices', None):
            # Use choices in a select field.
            kwargs['choices'] = [(k, v) for k, v in kwargs.get('choices')]
            return SelectField(**kwargs)

        if prop._choices:
            # Use choices in a select field.
            kwargs['choices'] = [(v, v)
                                 for v in prop._choices]
            return SelectField(**kwargs)
        else:
            converter = self.converters.get(prop_type_name, None)
            if converter is not None:
                return converter(model, prop, kwargs)
            else:
                return self.fallback_converter(model, prop, kwargs)

    def convert_IntegerProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.IntegerProperty``."""
        if prop._repeated:
            return IntegerListPropertyField(**kwargs)
        return IntegerField(**kwargs)

    def convert_FloatProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.FloatProperty``."""
        return DecimalField(**kwargs)

    def convert_DateProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.DateProperty``."""
        if prop._auto_now or prop._auto_now_add:
            return None
        return DateField(**kwargs)

    def convert_DateTimeProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.DateTimeProperty``."""
        if prop._auto_now or prop._auto_now_add:
            return None
        return DateTimeField(**kwargs)

    def convert_JsonProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.JsonProperty``."""
        return JsonField(**kwargs)

    def convert_KeyProperty(self, model, prop, kwargs):
        """Return a form field for a ``ndb.KeyProperty``."""
        if 'reference_class' not in kwargs:
            try:
                reference_class = prop._kind
            except AttributeError:
                reference_class = prop._reference_class

            if isinstance(reference_class, string_types):
                # reference_class is a string,
                # try to retrieve the model object.
                mod = __import__(model.__module__, None,
                                 None, [reference_class], 0)
                reference_class = getattr(mod, reference_class)
            kwargs['reference_class'] = reference_class
        kwargs.setdefault(
            'allow_blank', not prop._required)
        if prop._repeated:
            return KeyPropertyMultiField(**kwargs)
        return KeyPropertyField(**kwargs)

    def convert__ClassKeyProperty(self, model, prop, kwargs):
        """Ignore Polymodel _ClassKeyProperty."""
        return None
