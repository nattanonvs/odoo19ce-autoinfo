from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    od19_initials = fields.Char(
        string="Initials",
        size=10,
        help="Salesperson initials used in project job number (e.g. NV for Nattanai "
             "Vinyangkoon). Leave empty to derive them from the user name: first "
             "letter of the first name + first letter of the last name.",
    )
    project_sale_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sale Project Job No. Sequence",
        check_company=True,
        help="Sequence that supplies the running counter for Sales-type project job "
             "numbers (Project Type = Sales). The job number itself is built as "
             "S + initials + YY + running number, e.g. SNV26-0001, so the sequence "
             "prefix is ignored.",
    )

    def _od19_derive_initials(self):
        """Return initials taken from the user name, e.g. NV for Nattanai Vinyangkoon."""
        self.ensure_one()
        parts = (self.name or "").split()
        if not parts:
            return ""
        initials = parts[0][0]
        if len(parts) > 1:
            initials += parts[-1][0]
        return initials.upper()

    def _od19_job_no_initials(self):
        """Return the initials used in job numbers: manual value wins when set."""
        self.ensure_one()
        manual = (self.od19_initials or "").strip().upper()
        return manual or self._od19_derive_initials()
