# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Value formatters for the ETDA 3-2560 XML profile.

The profile inherits very strict numeric facets from ``QualifiedDataType_1p0``:

* ``qdt:Amount``          fractionDigits=5,  totalDigits=18, minInclusive=0
* ``qdt:PercentageRate``  fractionDigits=10, totalDigits=11
* ``qdt:Quantity``        fractionDigits=17, totalDigits=18

The XSD only caps the number of fraction digits, so trailing zeros are
optional (the ETDA sample files ship both ``63050`` and ``4413.50``).  We
normalise on write and strip insignificant trailing zeros so the produced
document stays compact and deterministic.
"""

import decimal
import re

import pytz
from odoo import fields

_AMOUNT_PLACES = 5
_RATE_PLACES = 10
_QUANTITY_PLACES = 17

_PHONE_RE = re.compile(r"\+[0-9]{1,3}-[0-9()+\-]{1,30}$")


def _quantize(value, places):
    """Return ``value`` rounded half-up to ``places`` decimal digits."""
    try:
        number = decimal.Decimal(str(value if value is not None else 0.0))
    except (decimal.InvalidOperation, ValueError):
        number = decimal.Decimal(0)
    quantum = decimal.Decimal(1).scaleb(-places)
    return number.quantize(quantum, rounding=decimal.ROUND_HALF_UP)


def _clean(number, places):
    text = format(_quantize(number, places), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_amount(value, places=_AMOUNT_PLACES):
    """Format an amount for ``qdt:Amount`` (non negative, <= 5 decimals)."""
    number = _quantize(value, places)
    if number < 0:
        raise ValueError("Amount cannot be negative in the ETDA 3-2560 profile.")
    return _clean(number, places)


def format_rate(value, places=_RATE_PLACES):
    """Format a percentage rate for ``qdt:PercentageRate``."""
    return _clean(value, places)


def format_quantity(value, places=_QUANTITY_PLACES):
    """Format a quantity for ``qdt:Quantity``."""
    return _clean(value, places)


def _localize(value, tz_name):
    """Convert a naive UTC Odoo datetime to the company timezone."""
    if not value:
        return value
    tzinfo = pytz.timezone(tz_name) if tz_name else pytz.utc
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    return value.astimezone(tzinfo)


def format_datetime(value, tz_name=None):
    """Format a datetime as ``qdt:ISODateTime`` (``YYYY-MM-DDTHH:MM:SS.0``).

    The ETDA sample files always end the value with a fractional second and
    carry no timezone offset, so we mirror that representation.
    """
    if not value:
        value = fields.Datetime.now()
    if isinstance(value, str):
        value = fields.Datetime.to_datetime(value)
    value = _localize(value, tz_name)
    return "%s.%s" % (value.strftime("%Y-%m-%dT%H:%M:%S"), value.microsecond // 100000)


def format_date_only(value):
    """Format a date as ``YYYY-MM-DD`` (``qdt:DateMandatoryDateTimeType``)."""
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_phone(value):
    """Format a phone number for ``qdt:PhoneNumber``.

    The facet requires ``+<cc>-<number>``; anything that does not match is
    dropped by returning an empty string so the caller can omit the element
    instead of producing an invalid document.
    """
    if not value:
        return ""
    digits = re.sub(r"[^\d+]", "", str(value))
    if not digits.startswith("+"):
        digits = "+" + digits.lstrip("+")
    if "-" not in digits:
        # Assume a Thai national number when no country code separator exists.
        if digits.startswith("+0"):
            digits = "+66-" + digits[3:]
        elif digits.startswith("+66"):
            digits = "+66-" + digits[3:]
        else:
            digits = digits[:3] + "-" + digits[3:]
    return digits if _PHONE_RE.match(digits) else ""


def unit_code(uom):
    """Return the UN/ECE Rec. 20 code for an ``uom.uom`` record."""
    from . import namespaces

    if not uom:
        return namespaces.DEFAULT_UNIT_CODE
    for candidate in (uom.name or "", uom.name):
        key = candidate.strip().lower()
        if key in namespaces.UNIT_CODES:
            return namespaces.UNIT_CODES[key]
    return namespaces.DEFAULT_UNIT_CODE
