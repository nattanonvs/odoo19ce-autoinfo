# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Submission gateway to the Revenue Department e-Tax service.

The RD API contract (service provider identifier, authentication, request and
response schemas) is not published yet, so the module ships a mockable
adapter:

* :class:`MockRdGateway` answers locally and is the default, so the whole
  submission flow — state, reference, response code, retries, audit trail —
  can be exercised without a live endpoint.
* :class:`LiveRdGateway` is the single place to implement the real protocol
  once the RD specification is available.

:func:`get_gateway` resolves the adapter from the company configuration.
"""

import hashlib
import logging

_logger = logging.getLogger(__name__)


class RdGatewayError(Exception):
    """Raised when a submission cannot be delivered to the RD service."""


class BaseRdGateway:
    """Common contract of an RD submission adapter."""

    mode = None

    def __init__(self, company):
        self.company = company

    def _check_configuration(self):
        """Raise when the endpoint or the provider identifier is missing."""
        if not self.company.od19_etax_rd_endpoint:
            raise RdGatewayError(
                "ยังไม่ได้ตั้งค่า RD Submission Endpoint ของบริษัท %s"
                % self.company.display_name
            )
        if not self.company.od19_etax_rd_provider_id:
            raise RdGatewayError(
                "ยังไม่ได้ตั้งค่า RD Service Provider ID ของบริษัท %s"
                % self.company.display_name
            )

    def _signed_payload(self, document):
        """Return the signed XML of ``document`` or raise."""
        if not document.signed_xml_file:
            raise RdGatewayError(
                "เอกสาร %s ยังไม่มีการลงนาม (signed XML) จึงนำส่งไม่ได้"
                % document.name
            )
        return document.signed_xml_file

    def submit(self, document):
        """Send ``document`` to the RD service and return its response.

        The response is a ``dict`` carrying ``ref``, ``response_code`` and
        ``response_message``. A ``response_code`` of ``0`` means the document
        was accepted.
        """
        raise NotImplementedError


class MockRdGateway(BaseRdGateway):
    """Local adapter used until the RD API contract is published."""

    mode = "mock"

    def submit(self, document):
        payload = self._signed_payload(document)
        self._check_configuration()
        reference = "MOCK-%s-%s" % (
            document.name,
            hashlib.sha1(payload).hexdigest()[:8].upper(),
        )
        _logger.info("Mock RD submission of %s accepted as %s", document.name, reference)
        return {
            "ref": reference,
            "response_code": "0",
            "response_message": "MOCK: รับข้อมูลเรียบร้อย (ยังไม่ได้เชื่อมต่อ RD จริง)",
        }


class LiveRdGateway(BaseRdGateway):
    """Production adapter — to be implemented against the official RD API."""

    mode = "live"

    def submit(self, document):
        self._signed_payload(document)
        self._check_configuration()
        raise RdGatewayError(
            "ยังไม่รองรับการนำส่งไปยัง RD จริง (รอ API specification จากผู้ให้บริการ) "
            "กรุณาสลับช่องทางเป็นโหมดทดสอบ (Mock) ก่อน"
        )


def get_gateway(company):
    """Return the submission adapter configured on ``company``."""
    if company.od19_etax_rd_mode == "live":
        return LiveRdGateway(company)
    return MockRdGateway(company)
