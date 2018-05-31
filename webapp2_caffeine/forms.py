# -*- coding: utf-8 -*-
"""WTForms forms with `webapp2_extras.i18n` translation support."""
import datetime

from webapp2_extras.i18n import ngettext, gettext
from wtforms import Form


class MyTranslations(object):
    """`webapp2_extras.i18n` translation support."""

    def gettext(self, string):
        """Gettext handler."""
        return gettext(string)

    def ngettext(self, singular, plural, num):
        """Ngettext handler."""
        return ngettext(singular, plural, num)


class BaseForm(Form):
    """Base form with `webapp2_extras.i18n` translation support."""

    def _get_translations(self):
        """Return translation class."""
        return MyTranslations()

    @classmethod
    def convert_date_string(cls, field):
        """Convert field into date."""
        return datetime.datetime.strptime(field.data, field.format).date()
