# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    tax_name = fields.Char(
        string="Tax Name",
        help="Name as shown on tax invoice (ใบกำกับภาษี). "
        "If empty, the partner name is used.",
    )
    branch_code = fields.Char(
        string="Branch Code",
        help="5-digit branch code for Thai tax branch reporting. "
        "Use '00000' for head office.",
    )
    name_en = fields.Char(
        string="English Name",
        help="Partner name in English (for international correspondence).",
    )
    address_en = fields.Text(
        string="English Address",
        help="Partner address in English (for international shipping).",
    )
    fax = fields.Char(string="Fax")
    od19_amphoe = fields.Char(
        string="Amphoe / District",
        help="District (อำเภอ) or Khet (เขต) of the Thai address.",
    )
    od19_subdistrict = fields.Char(
        string="Subdistrict / Tambon",
        help="Sub-district (ตำบล) or Khwaeng (แขวง) of the Thai address.",
    )

    @api.constrains("branch_code")
    def _check_branch_code(self):
        for partner in self:
            code = (partner.branch_code or "").strip()
            if code and (len(code) != 5 or not code.isdigit()):
                raise ValidationError(
                    _(
                        "Branch Code must be exactly 5 digits "
                        "(use '00000' for the head office), got '%(code)s'.",
                        code=partner.branch_code,
                    )
                )

    @api.depends("is_company", "country_code", "branch_code", "company_registry")
    def _compute_l10n_th_branch_name(self):
        """Drive the Thai branch label from ``branch_code`` when it is set.

        Core l10n_th only fills ``l10n_th_branch_name`` for companies whose
        country is Thailand, deriving it from ``company_registry``. Thai
        partners here often have no country set, so the core value stays empty
        even when ``branch_code`` is filled in. Keep the core result as a
        fallback, then override it with the 5-digit branch code
        (``00000`` = head office).
        """
        super()._compute_l10n_th_branch_name()
        for partner in self:
            code = (partner.branch_code or "").strip()
            if partner.is_company and code:
                partner.l10n_th_branch_name = (
                    self.env._("Headquarter")
                    if code == "00000"
                    else self.env._("Branch %(code)s", code=code)
                )


class ResCompany(models.Model):
    _inherit = "res.company"

    tax_name = fields.Char(
        related="partner_id.tax_name",
        readonly=False,
        string="Tax Name",
    )
    branch_code = fields.Char(
        related="partner_id.branch_code",
        readonly=False,
        string="Branch Code",
    )
    name_en = fields.Char(
        related="partner_id.name_en",
        readonly=False,
        string="English Name",
    )
    address_en = fields.Text(
        related="partner_id.address_en",
        readonly=False,
        string="English Address",
    )
    fax = fields.Char(
        related="partner_id.fax",
        readonly=False,
        string="Fax",
    )
    od19_amphoe = fields.Char(
        related="partner_id.od19_amphoe",
        readonly=False,
        string="Amphoe / District",
    )
    od19_subdistrict = fields.Char(
        related="partner_id.od19_subdistrict",
        readonly=False,
        string="Subdistrict / Tambon",
    )
