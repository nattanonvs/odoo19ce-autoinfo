# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Flag the labels of custom (``od19_``) fields while Developer Mode is on.

Every field added by the ``od19_*`` modules carries the ``od19_`` prefix so
that customisations can be told apart from the standard Odoo fields.  That
prefix must not show up in the production user interface, but while Developer
Mode is enabled it is handy to see at a glance which labels are custom.

``BaseModel.fields_get`` is the single place every view type (form, list,
search, pivot, export, ...) reads its labels from, so the label of an
``od19_`` field is prefixed there.  The hook does nothing outside Developer
Mode, which keeps the production labels clean.
"""

import functools

from odoo import api, models
from odoo.http import request

FIELD_PREFIX = "od19_"
MARKER = "[od19] "

_original_fields_get = models.BaseModel.fields_get


def mark_custom_field_labels(fields_description):
    """Prefix the label of every ``od19_`` field in a ``fields_get`` result."""
    for fname, description in fields_description.items():
        label = description.get("string")
        if not fname.startswith(FIELD_PREFIX) or not label:
            continue
        if not label.startswith(MARKER):
            description["string"] = MARKER + label
    return fields_description


@functools.wraps(_original_fields_get)
def _fields_get_with_marker(self, allfields=None, attributes=None):
    result = _original_fields_get(self, allfields, attributes)
    # ``request`` is unbound outside of an HTTP request (cron, shell, RPC
    # without a session) and is then falsy, exactly like in Odoo core.
    if not (request and request.session.debug):
        return result
    return mark_custom_field_labels(result)


models.BaseModel.fields_get = api.model(_fields_get_with_marker)
