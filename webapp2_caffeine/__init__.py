# -*- coding: utf-8 -*-
"""Extra utilities for webapp2 on Google App Engine.

    - class-based views for models, lists, forms, templates, redirection...
    - a pager for ndb requests
    - support of `webapp2_extras.i18n` translations in WTForms
    - customized fields for decimal, interger, date, datetime, json, ndb.Key...
    - automatic conversion from `ndb.Model` to WTForms
    - image model with Google Cloud Storage and Google Image CDN support
    - a lightweight cache container

Status:
    Copyright 2011 Grégoire Vigneron.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
