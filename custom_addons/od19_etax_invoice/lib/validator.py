# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""XSD validation of the generated ขมธอ.3-2560 e-Tax Invoice XML.

Each document family ships its own ``*_CrossIndustryInvoice_2p0.xsd`` entry
point; the ``xsd:import`` statements inside those files reference the shared
UnqualifiedDataType / QualifiedDataType / code list schemas with relative
paths, so we always parse the entry point from disk (which preserves its
``base_url`` and lets lxml resolve the whole import graph).

Compiled schemas are cached per document type because the ETDA import graph is
large and compilation is expensive.
"""

import logging
from pathlib import Path

from lxml import etree

from . import namespaces

_logger = logging.getLogger(__name__)

#: ``<module>/data/schema/ETDA/data/standard``.
_SCHEMA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "schema"
    / "ETDA"
    / "data"
    / "standard"
)

_schema_cache = {}


class ValidationError(Exception):
    """Raised when the document does not conform to the ETDA XSD."""


def schema_path(document_type):
    """Return the entry point ``.xsd`` path for a document type key."""
    try:
        class_name = namespaces.DOCUMENT_TYPES[document_type]["class"]
    except KeyError:
        raise ValidationError("Unsupported document type: %s" % document_type)
    return _SCHEMA_DIR / ("%s_CrossIndustryInvoice_2p0.xsd" % class_name)


def get_schema(document_type):
    """Return (and cache) the compiled ``lxml.etree.XMLSchema``."""
    if document_type not in _schema_cache:
        path = schema_path(document_type)
        if not path.exists():
            raise ValidationError(
                "Missing ETDA schema file for %s: %s" % (document_type, path)
            )
        try:
            document = etree.parse(str(path))
            _schema_cache[document_type] = etree.XMLSchema(document)
        except etree.XMLSchemaParseError as error:
            raise ValidationError(
                "Cannot compile the ETDA schema for %s: %s" % (document_type, error)
            )
    return _schema_cache[document_type]


def validate(element, document_type):
    """Validate ``element`` and return the list of schema errors.

    An empty list means the document conforms to the profile.
    """
    schema = get_schema(document_type)
    if schema.validate(element):
        return []
    return [str(entry) for entry in schema.error_log]


def is_valid(element, document_type):
    """Return whether ``element`` conforms to the ETDA XSD."""
    return not validate(element, document_type)


def assert_valid(element, document_type):
    """Raise :class:`ValidationError` when ``element`` is not conformant."""
    errors = validate(element, document_type)
    if errors:
        _logger.warning("e-Tax XML validation failed: %s", "; ".join(errors))
        raise ValidationError("\n".join(errors))
    return True
