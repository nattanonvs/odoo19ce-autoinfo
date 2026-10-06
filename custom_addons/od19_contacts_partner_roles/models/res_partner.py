from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Odoo 19 base partner in this workspace has no `mobile` field, but Task 1
    # requires accepting mobile as a valid contact channel.
    mobile = fields.Char(string="Mobile")
    od19_is_commercial_customer = fields.Boolean(string="Commercial Customer")
    od19_is_project_owner = fields.Boolean(string="Project Owner")
    od19_is_contractor = fields.Boolean(string="Contractor")

    @api.constrains(
        "od19_is_commercial_customer",
        "od19_is_project_owner",
        "od19_is_contractor",
        "email",
        "phone",
        "mobile",
        "is_company",
    )
    def _check_od19_partner_roles(self):
        for partner in self:
            if partner.od19_is_commercial_customer and not (
                partner.email or partner.phone or partner.mobile
            ):
                raise ValidationError(
                    "Commercial customers must have at least one contact channel."
                )

            if partner.od19_is_project_owner and not partner.is_company:
                raise ValidationError("Project owners must be companies.")

            if partner.od19_is_contractor and not partner.is_company:
                raise ValidationError("Contractors must be companies.")
