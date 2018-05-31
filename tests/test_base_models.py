# -*- coding: utf-8 -*-
"""luther.generic.models.tests.test_images"""
from StringIO import StringIO
import unittest

from google.appengine.ext import ndb
from PIL import Image

from webapp2_caffeine.base_models import BaseImage
from webapp2_caffeine.test_case import ModelTestCase


class FakeFile(object):
    value = 'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'.decode(
        'base64')
    type = 'image/gif'


class ImageTest(ModelTestCase, unittest.TestCase):

    model_class = BaseImage
    properties = {'filename': ndb.StringProperty,
                  'original': ndb.StringProperty,
                  'resource': ndb.StringProperty,
                  'blobkey': ndb.StringProperty,
                  'url': ndb.StringProperty,
                  'width': ndb.IntegerProperty,
                  'height': ndb.IntegerProperty, }

    def test_set_image(self):
        entity = BaseImage()
        image = FakeFile()
        entity.set_image(image, 'image.gif')
        self.assertTrue(entity.resource)
        self.assertTrue(entity.blobkey)
        self.assertTrue(entity.url)
        self.assertEqual(entity.width, 1)
        self.assertEqual(entity.height, 1)

    def test_delete_blob(self):
        entity = BaseImage()
        image = FakeFile()
        entity.set_image(image, 'image.gif')
        entity._delete_blob()
        self.assertFalse(entity.url)

    def test_get_width_url(self):
        entity = BaseImage(width=50, height=50)
        url = entity.get_width_url(200)
        self.assertTrue(url.endswith('=s200'))
        entity = BaseImage(width=100, height=50)
        url = entity.get_width_url(200)
        self.assertTrue(url.endswith('=s200'))
        entity = BaseImage(width=50, height=100)
        url = entity.get_width_url(200)
        self.assertTrue(url.endswith('=s400'))

    def test_get_height_url(self):
        entity = BaseImage(width=50, height=50)
        url = entity.get_height_url(200)
        self.assertTrue(url.endswith('=s200'))
        entity = BaseImage(width=50, height=100)
        url = entity.get_height_url(200)
        self.assertTrue(url.endswith('=s200'))
        entity = BaseImage(width=100, height=50)
        url = entity.get_height_url(200)
        self.assertTrue(url.endswith('=s400'))

    def test_pre_transform(self):

        class TestImage(BaseImage):

            def _pre_transform(self, image_data):
                image = Image.open(StringIO(image_data))
                image = image.resize((2, 2))
                output = StringIO()
                image.save(output, format='GIF')
                content = output.getvalue()
                output.close()
                return 2, 2, content, 'image/gif'

        entity = TestImage()
        image = FakeFile()
        entity.set_image(image, 'image.gif')
        self.assertTrue(entity.resource)
        self.assertTrue(entity.blobkey)
        self.assertTrue(entity.url)
        self.assertEqual(entity.width, 2)
        self.assertEqual(entity.height, 2)
        self.assertTrue(entity.original)
