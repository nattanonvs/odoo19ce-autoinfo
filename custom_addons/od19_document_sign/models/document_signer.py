import uuid

from odoo import _, fields, models
from odoo.exceptions import UserError


class Od19DocumentSigner(models.Model):
    _name = "od19.document.signer"
    _description = "Document Signer"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="od19.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    role_name = fields.Char(string="Role")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Signer")
    email = fields.Char(related="partner_id.email")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("refused", "Refused"),
        ],
        string="Status",
        default="draft",
        copy=False,
    )
    signature = fields.Image(
        string="Signature",
        max_width=1024,
        max_height=1024,
        copy=False,
    )
    signed_by = fields.Char(string="Signed By", copy=False)
    signed_on = fields.Datetime(string="Signed On", copy=False)
    refusal_reason = fields.Text(string="Refusal Reason", copy=False)
    access_token = fields.Char(string="Security Token", copy=False)
    access_url = fields.Char(string="Signing URL", compute="_compute_access_url")
    document_state = fields.Selection(
        related="document_id.state",
        string="Document Status",
    )

    def _compute_access_url(self):
        for signer in self:
            signer.access_url = "/my/documents/sign/%s" % signer.id

    def _ensure_token(self):
        """Return the signer token, generating one on first use."""
        self.ensure_one()
        if not self.access_token:
            self.sudo().write({"access_token": str(uuid.uuid4())})
        return self.access_token

    def _prepare_for_signing(self):
        """Give every signer a security token and open the request for them."""
        for signer in self:
            signer._ensure_token()
            if signer.state == "draft":
                signer.state = "sent"

    def _sign(self, name=None, signature=None):
        """Record the signature of this signer and refresh the parent status."""
        self.ensure_one()
        if self.state == "signed":
            raise UserError(_("This document was already signed."))
        if self.document_id.state != "sent":
            raise UserError(_("This document is not open for signature."))
        self.write({
            "signature": signature,
            "signed_by": name or self.partner_id.name,
            "signed_on": fields.Datetime.now(),
            "state": "signed",
        })
        self.document_id._update_state_after_signing()

    def _refuse(self, reason=None):
        for signer in self:
            if signer.document_id.state != "sent":
                raise UserError(_("This document is not open for signature."))
            signer.write({
                "state": "refused",
                "refusal_reason": reason or "",
            })
            signer.document_id._update_state_after_signing()
