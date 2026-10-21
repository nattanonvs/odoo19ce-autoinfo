from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19Document(models.Model):
    _name = "od19.document"
    _description = "Document to Sign"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "id desc"

    name = fields.Char(string="Number", default="/", readonly=True, copy=False)
    template_id = fields.Many2one(
        comodel_name="od19.document.template",
        string="Template",
        required=True,
        tracking=True,
    )
    reference = fields.Char(string="Reference", tracking=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Main Contact",
        tracking=True,
    )
    body_html = fields.Html(string="Document Content", sanitize=True)
    date_deadline = fields.Datetime(string="Signing Deadline", tracking=True)
    signer_ids = fields.One2many(
        comodel_name="od19.document.signer",
        inverse_name="document_id",
        string="Signers",
        copy=True,
    )
    signer_count = fields.Integer(string="Signer Count", compute="_compute_signer_counts")
    signed_signer_count = fields.Integer(
        string="Signed", compute="_compute_signer_counts"
    )
    current_signer_id = fields.Many2one(
        comodel_name="od19.document.signer",
        string="Next Signer",
        compute="_compute_current_signer",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("refused", "Refused"),
            ("expired", "Expired"),
        ],
        string="Status",
        default="draft",
        tracking=True,
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
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # Compute / onchange
    # ------------------------------------------------------------------
    def _compute_access_url(self):
        for document in self:
            document.access_url = "/my/documents/%s" % document.id

    @api.depends("signer_ids.state")
    def _compute_signer_counts(self):
        for document in self:
            document.signer_count = len(document.signer_ids)
            document.signed_signer_count = len(
                document.signer_ids.filtered(lambda s: s.state == "signed")
            )

    @api.depends("signer_ids.state", "signer_ids.sequence")
    def _compute_current_signer(self):
        for document in self:
            pending = document.signer_ids.filtered(
                lambda s: s.state in ("draft", "sent")
            ).sorted("sequence")
            document.current_signer_id = pending[:1]

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        if not self.body_html:
            self.body_html = self.template_id.body_html
        if not self.signer_ids:
            self.signer_ids = [Command.clear()] + [
                Command.create(self._prepare_signer_vals(role))
                for role in self.template_id.role_ids
            ]

    # ------------------------------------------------------------------
    # Create / helpers
    # ------------------------------------------------------------------
    def _prepare_signer_vals(self, role):
        return {
            "role_name": role.name,
            "partner_id": role.partner_id.id,
            "sequence": role.sequence,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.document") or "/"
                )
            template = self.env["od19.document.template"].browse(
                vals.get("template_id")
            )
            if template:
                if not vals.get("body_html"):
                    vals["body_html"] = template.body_html
                if not vals.get("signer_ids"):
                    vals["signer_ids"] = [
                        Command.create(self._prepare_signer_vals(role))
                        for role in template.role_ids
                    ]
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_send(self):
        self._check_signers_ready()
        for document in self:
            if document.state != "draft":
                continue
            document.signer_ids._prepare_for_signing()
            document.state = "sent"
            document.message_post(
                body=_(
                    "Document sent for signature to %(signers)s.",
                    signers=", ".join(document.signer_ids.mapped("partner_id.name")),
                )
            )
            document._send_signer_emails()
        return True

    def action_resend(self):
        """Re-send the request to every signer that has not signed yet.

        Signers may be added or corrected while the request is in the ``sent``
        state; this action pushes the notification again.
        """
        self._check_signers_ready()
        for document in self:
            if document.state != "sent":
                continue
            document.signer_ids.filtered(
                lambda s: s.state != "signed"
            )._prepare_for_signing()
            document._send_signer_emails()
            document.message_post(body=_("Signature request re-sent."))
        return True

    def action_reset_draft(self):
        self.write({
            "state": "draft",
            "signature": False,
            "signed_by": False,
            "signed_on": False,
            "refusal_reason": False,
        })
        self.signer_ids.write({
            "state": "draft",
            "signature": False,
            "signed_by": False,
            "signed_on": False,
            "refusal_reason": False,
        })
        return True

    def action_expire(self):
        self.filtered(lambda d: d.state == "sent").write({"state": "expired"})
        return True

    def _check_signers_ready(self):
        for document in self:
            if not document.signer_ids:
                raise UserError(
                    _("Please add at least one signer before sending the document.")
                )
            if document.signer_ids.filtered(lambda s: not s.partner_id):
                raise UserError(
                    _("Every signer must have a contact defined.")
                )
            if document.signer_ids.filtered(lambda s: not s.partner_id.email):
                raise UserError(
                    _("Every signer must have an email address defined.")
                )

    def _send_signer_emails(self):
        template = self.env.ref(
            "od19_document_sign.mail_template_document_sign_request",
            raise_if_not_found=False,
        )
        if not template:
            return
        for document in self:
            for signer in document.signer_ids.filtered(lambda s: s.state != "signed"):
                signer._ensure_token()
                template.with_context(
                    lang=signer.partner_id.lang or self.env.user.lang
                ).send_mail(signer.id, force_send=True)

    def _update_state_after_signing(self):
        for document in self:
            if document.state != "sent":
                continue
            signers = document.signer_ids
            if signers.filtered(lambda s: s.state == "refused"):
                document.state = "refused"
                document.refusal_reason = signers.filtered(
                    lambda s: s.state == "refused"
                )[:1].refusal_reason
            elif signers and all(s.state == "signed" for s in signers):
                last = signers.sorted("signed_on")[-1:]
                document.write({
                    "state": "signed",
                    "signature": last.signature,
                    "signed_by": last.signed_by,
                    "signed_on": last.signed_on,
                })

    @api.model
    def _cron_expire_documents(self):
        now = fields.Datetime.now()
        documents = self.search([
            ("state", "=", "sent"),
            ("date_deadline", "!=", False),
            ("date_deadline", "<", now),
        ])
        documents.write({"state": "expired"})
        return True
