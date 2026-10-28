# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Submission gateway to the e-Withholding Tax service of the bank.

Thai e-Withholding Tax (e-WHT) — the payer hands the withholding records over
to its bank, which files them with the Revenue Department on the payer's
behalf. The bank API contract is not published in a stable form, so the module
ships a mockable adapter:

* :class:`MockEwhtGateway` answers locally and is the default, so the whole
  submission flow — state, reference, response code, retries, audit trail —
  can be exercised without a live endpoint.
* :class:`LiveEwhtGateway` is the single place to implement the real protocol
  once the bank specification is available.

:func:`get_gateway` resolves the adapter from the company configuration.
"""

import hashlib
import logging

_logger = logging.getLogger(__name__)


class EwhtGatewayError(Exception):
    """Raised when a withholding record cannot be delivered to the bank."""


class BaseEwhtGateway:
    """Common contract of an e-Withholding Tax submission adapter."""

    mode = None

    def __init__(self, company):
        self.company = company

    def _check_configuration(self):
        """Raise when the endpoint or the provider identifier is missing."""
        if not self.company.od19_ewht_endpoint:
            raise EwhtGatewayError(
                "ยังไม่ได้ตั้งค่า e-WHT Bank Endpoint ของบริษัท %s"
                % self.company.display_name
            )
        if not self.company.od19_ewht_provider_id:
            raise EwhtGatewayError(
                "ยังไม่ได้ตั้งค่า e-WHT Service Provider ID ของบริษัท %s"
                % self.company.display_name
            )

    def _payload(self, wht_move):
        """Return the canonical payload string of ``wht_move`` or raise."""
        if not wht_move.partner_id:
            raise EwhtGatewayError(
                "รายการหัก ณ ที่จ่าย %s ไม่มีคู่ค้า (Vendor) จึงนำส่งไม่ได้"
                % wht_move.id
            )
        return "|".join(
            [
                wht_move.partner_id.vat or "",
                wht_move.partner_id.name or "",
                str(wht_move.date or ""),
                "%.2f" % (wht_move.amount_income or 0.0),
                "%.2f" % (wht_move.amount_wht or 0.0),
                wht_move.wht_tax_id.name or "",
            ]
        )

    def submit(self, wht_move):
        """Send ``wht_move`` to the bank and return its response.

        The response is a ``dict`` carrying ``ref``, ``response_code`` and
        ``response_message``. A ``response_code`` of ``0`` means the record
        was accepted.
        """
        raise NotImplementedError


class MockEwhtGateway(BaseEwhtGateway):
    """Local adapter used until the bank API contract is published."""

    mode = "mock"

    def submit(self, wht_move):
        payload = self._payload(wht_move)
        self._check_configuration()
        reference = "MOCK-EWHT-%s-%s" % (
            wht_move.id,
            hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8].upper(),
        )
        _logger.info(
            "Mock e-WHT submission of withholding move %s accepted as %s",
            wht_move.id,
            reference,
        )
        return {
            "ref": reference,
            "response_code": "0",
            "response_message": "MOCK: รับข้อมูลเรียบร้อย (ยังไม่ได้เชื่อมต่อธนาคารจริง)",
        }


class LiveEwhtGateway(BaseEwhtGateway):
    """Production adapter — to be implemented against the official bank API."""

    mode = "live"

    def submit(self, wht_move):
        self._payload(wht_move)
        self._check_configuration()
        raise EwhtGatewayError(
            "ยังไม่รองรับการนำส่ง e-Withholding ไปยังธนาคารจริง "
            "(รอ API specification จากธนาคาร) "
            "กรุณาสลับช่องทางเป็นโหมดทดสอบ (Mock) ก่อน"
        )


def get_gateway(company):
    """Return the e-Withholding submission adapter configured on ``company``."""
    if company.od19_ewht_mode == "live":
        return LiveEwhtGateway(company)
    return MockEwhtGateway(company)
