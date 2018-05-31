# -*- coding: utf-8 -*-
"""Generic models."""
import os
import time

import cloudstorage as gcs
from google.appengine.api import app_identity
from google.appengine.api.images import delete_serving_url
from google.appengine.api.images import get_serving_url
from google.appengine.api.images import Image
from google.appengine.api.images import NotImageError
from google.appengine.api.images import TransformationError
from google.appengine.ext import ndb
from google.appengine.ext import blobstore


class FormImage(object):
    """Object to emulate images in form data."""

    type = None
    value = None


class BaseImage(ndb.Model):
    """Generic image representation with Google Image service.

    `_bucket` and `_get_kind` methods must be overrided.
    `_pre_transform` can be overrided if you need to appli transformation
        to image before saving it.

    Attributes:
        filename (str) -- Cloud Storage resource filename.
        resource (str) -- Cloud Storage resource (`<bucket><path><filename>`).
        blobkey (str) -- Image blobkey.
        url (str) -- Image serving URL.
        width (str) -- Image width.
        height (str) -- Image height.
        original (str) -- Cloud Storage original image.

    """

    filename = ndb.StringProperty(indexed=False)
    resource = ndb.StringProperty(indexed=False)
    blobkey = ndb.StringProperty(indexed=False)
    url = ndb.StringProperty(indexed=False)
    width = ndb.IntegerProperty(indexed=False)
    height = ndb.IntegerProperty(indexed=False)
    original = ndb.StringProperty(indexed=False)

    _content_types = {'JPEG': 'image/jpeg',
                      'GIF': 'image/gif',
                      'PNG': 'image/png', }

    @property
    def _bucket(self):
        """Return the default bucket (hack for cycle in imports)."""
        bucket = os.environ.get('BUCKET_NAME',
                                app_identity.get_default_gcs_bucket_name())
        return '/{}/images/'.format(bucket)

    @property
    def ratio(self):
        """Return image ratio."""
        if self.width > self.height:
            return 'landscape'
        elif self.height > self.width:
            return 'portrait'
        else:
            return 'square'

    def __init__(self, *args, **kwargs):
        """Add `bucket` argument."""
        if kwargs.get('bucket'):
            self._bucket = kwargs.pop('bucket')
        super(BaseImage, self).__init__(*args, **kwargs)

    def _delete_blob(self):
        """Delete blob images and resources."""
        blob_info = blobstore.BlobInfo.get(self.blobkey)
        if blob_info:
            delete_serving_url(blob_info.key())
            blobstore.delete(blob_info.key())
            blob_info.delete()
        if self.resource:
            try:
                gcs.delete(self.resource)
            except gcs.NotFoundError:
                pass
        if self.original:
            try:
                gcs.delete(self.original)
            except gcs.NotFoundError:
                pass
        self.blobkey = None
        self.url = None
        self.width = None
        self.height = None

    def delete(self):
        """Delete entity."""
        if self.blobkey:
            self._delete_blob()
        if self.key:
            self.key.delete()

    def _pre_transform(self, image_data):
        """Apply image pre-transformation.

        Attributes:
            image_data (str) -- Original image content.

        Return:
            (image width, image height, transformed image content,
            content type).

        """
        img = Image(image_data=image_data)
        return img.width, img.height, None, None

    def set_image(self, image, filename, path=None, force_filename=False):
        """Set or update image data.

        Args:
            image (bytes) -- Form data.
            filename (str) -- Image filename.
            path (str) -- Image sub-directory, in format `path/to/image/`.
            force_filename (bool) -- Don't override filename.
        """
        if not hasattr(image, 'value'):
            return
        # Delete old image.
        if self.blobkey:
            self._delete_blob()
        # Set path and filename.
        base_path = '{}{}/'.format(self._bucket,
                                   path) if path else self._bucket
        if not force_filename:
            filename = '{}-{}'.format(filename, int(time.time() * 100000))
        self.resource = '{}transformed/{}'.format(base_path, filename)
        self.original = '{}{}'.format(base_path, filename)
        # Save original file.
        with gcs.open(self.original, 'w', content_type=image.type) as img:
            img.write(image.value)
        # Format image and extract meta data.
        try:
            self.width, self.height, _content, _type = self._pre_transform(
                image.value)
        except (TransformationError, NotImageError, IOError):
            return
        if _content:
            with gcs.open(self.resource, 'w', content_type=_type) as img:
                img.write(_content)
        else:
            self.resource = self.original
        # Set new image data, height and width attributes.
        blobstore_filename = '/gs' + self.resource
        self.blobkey = blobstore.create_gs_key(blobstore_filename)
        try:
            self.url = get_serving_url(self.blobkey, secure_url=True)
            if not os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'):
                self.url = self.url.replace('http:', 'https:')
        except (TransformationError, NotImageError):
            blob_info = blobstore.BlobInfo.get(self.blobkey)
            blobstore.delete(blob_info.key())
            blob_info.delete()
            self.blobkey = None
            self.url = None
            return

        return

    def get_width_url(self, width):
        """Return serving URL for the image width the given width.

        Args:
            width (int) -- Width.
        Return:
            (str) Serving URL.
        """
        if self.width >= self.height:
            return '{}=s{}'.format(self.url, width)
        ratio = float(width) / float(self.width)
        height = self.height * ratio
        return '{}=s{}'.format(self.url, int(height))

    def get_height_url(self, height):
        """Return serving URL for the image width the given height.

        Args:
            height (int) -- Height.
        Return:
            (str) Serving URL.
        """
        if self.height >= self.width:
            return '{}=s{}'.format(self.url, height)
        ratio = float(height) / float(self.height)
        width = self.width * ratio
        return '{}=s{}'.format(self.url, int(width))

    def get_croped_url(self, size):
        """Return serving URL for the croped image width the given size.

        Args:
            size (int) -- Height / Width.
        Return:
            (str) Serving URL.
        """
        return '{}=s{}-c'.format(self.url, int(size))
