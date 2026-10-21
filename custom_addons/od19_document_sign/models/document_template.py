from odoo import fields, models


class Od19DocumentTemplate(models.Model):
    _name = "od19.document.template"
    _description = "Document Signing Template"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    body_html = fields.Html(string="Document Content", sanitize=True)
    role_ids = fields.One2many(
        comodel_name="od19.document.template.role",
        inverse_name="template_id",
        string="Signer Roles",
        copy=True,
    )
    role_count = fields.Integer(string="Roles", compute="_compute_role_count")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    def _compute_role_count(self):
        for template in self:
            template.role_count = len(template.role_ids)


class Od19DocumentTemplateRole(models.Model):
    _name = "od19.document.template.role"
    _description = "Document Signing Template Role"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="od19.document.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Role", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Default Signer",
        help="Contact pre-filled on the signing request created from this role.",
    )
