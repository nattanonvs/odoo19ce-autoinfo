# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Signing certificates backing the XAdES signature (ขมธอ.14-2560).

The certificate is stored as PEM so the exact material issued by the CA is
kept verbatim.  Only the private key can carry a passphrase; the public
certificate and its chain are re-emitted unchanged during signing so the
``ds:X509Certificate`` element matches what the CA published.
"""

import logging

from cryptography import x509
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Od19EtaxCertificate(models.Model):
    _name = "od19.etax.certificate"
    _description = "e-Tax Invoice Signing Certificate"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
        help="Label identifying this certificate, for example the CA name.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)

    private_key = fields.Text(
        string="Private Key (PEM)",
        groups="base.group_system",
        copy=False,
        help="PKCS#8 / PKCS#1 PEM private key matching the certificate.",
    )
    certificate = fields.Text(
        string="Certificate (PEM)",
        copy=False,
        help="X.509 signing certificate in PEM format.",
    )
    chain = fields.Text(
        string="Intermediate Chain (PEM)",
        copy=False,
        help="Optional intermediate and root certificates, PEM, leaf excluded.",
    )
    passphrase = fields.Char(
        string="Key Passphrase",
        groups="base.group_system",
        copy=False,
    )

    subject = fields.Char(readonly=True, copy=False)
    issuer = fields.Char(readonly=True, copy=False)
    serial_number = fields.Char(readonly=True, copy=False)
    valid_from = fields.Datetime(readonly=True, copy=False)
    valid_to = fields.Datetime(readonly=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "Not Verified"),
            ("active", "Valid"),
            ("expired", "Expired"),
            ("invalid", "Invalid"),
        ],
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Certificate material
    # ------------------------------------------------------------------
    def _get_certificates(self):
        """Return the PEM chain as a list of ``x509.Certificate``, leaf first."""
        self.ensure_one()
        if not self.certificate:
            raise UserError(
                self.env._("Certificate %s has no X.509 certificate.", self.name)
            )
        pem = self.certificate.encode()
        if self.chain:
            pem += b"\n" + self.chain.encode()
        try:
            return x509.load_pem_x509_certificates(pem)
        except ValueError as error:
            raise UserError(
                self.env._("Cannot read the certificate of %(name)s: %(error)s",
                           name=self.name, error=error)
            )

    def _get_private_key(self):
        """Return the decoded private key object."""
        self.ensure_one()
        if not self.private_key:
            raise UserError(
                self.env._("Certificate %s has no private key.", self.name)
            )
        password = self.passphrase.encode() if self.passphrase else None
        try:
            return load_pem_private_key(self.private_key.encode(), password=password)
        except (ValueError, TypeError) as error:
            raise UserError(
                self.env._("Cannot read the private key of %(name)s: %(error)s",
                           name=self.name, error=error)
            )

    def _get_signing_key_pem(self):
        """Return the private key as an unencrypted PKCS#8 PEM ``bytes``."""
        self.ensure_one()
        key = self._get_private_key()
        return key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )

    def _get_signing_cert_pem(self):
        """Return the certificate chain as a single PEM ``bytes`` blob."""
        self.ensure_one()
        return b"".join(
            certificate.public_bytes(Encoding.PEM)
            for certificate in self._get_certificates()
        )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def action_verify(self):
        """Parse the material and record the certificate metadata."""
        for record in self:
            certificates = record._get_certificates()
            record._get_private_key()
            leaf = certificates[0]
            valid_from = leaf.not_valid_before_utc.replace(tzinfo=None)
            valid_to = leaf.not_valid_after_utc.replace(tzinfo=None)
            now = fields.Datetime.now()
            if valid_to < now:
                state = "expired"
            elif valid_from > now:
                state = "invalid"
            else:
                state = "active"
            record.write({
                "subject": leaf.subject.rfc4514_string(),
                "issuer": leaf.issuer.rfc4514_string(),
                "serial_number": "%X" % leaf.serial_number,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "state": state,
            })
        return True

    def _check_usable(self):
        """Raise when the certificate cannot be used for signing right now."""
        self.ensure_one()
        if self.state == "draft":
            self.action_verify()
        if self.state != "active":
            raise UserError(
                self.env._(
                    "Certificate %(name)s is not valid (%(state)s). "
                    "Verify it before signing.",
                    name=self.name,
                    state=dict(self._fields["state"].selection).get(self.state),
                )
            )
        return True
