from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    is_loanable = fields.Boolean(
        string="Loanable",
        default=True,
        help="Indicates whether this equipment can be borrowed internally.",
        index=True,
    )
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Accounting Asset",
        help="Link to the fixed asset record for depreciation tracking.",
    )
    loan_line_ids = fields.One2many(
        comodel_name="asset.loan.line",
        inverse_name="equipment_id",
        string="Loan Lines",
    )
    loan_count = fields.Integer(
        string="Loan Count",
        compute="_compute_loan_count",
    )
    current_loan_line_id = fields.Many2one(
        comodel_name="asset.loan.line",
        string="Current Loan",
        compute="_compute_current_loan",
    )
    calibration_date = fields.Date(
        string="Next Calibration Date",
        index=True,
        help="Date when the next calibration is due.",
    )

    @api.depends("loan_line_ids")
    def _compute_loan_count(self):
        for record in self:
            record.loan_count = len(record.loan_line_ids)

    @api.depends("loan_line_ids", "loan_line_ids.state")
    def _compute_current_loan(self):
        for record in self:
            current = record.loan_line_ids.filtered(
                lambda l: l.state in ("draft", "borrowed")
            )[:1]
            record.current_loan_line_id = current

    def action_view_loans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Loans"),
            "res_model": "asset.loan",
            "view_mode": "list,form",
            "domain": [("line_ids.equipment_id", "=", self.id)],
            "context": {"default_line_ids": [(0, 0, {"equipment_id": self.id})]},
        }

    # ------------------------------------------------------------------
    # Calibration notifications
    # ------------------------------------------------------------------
    def _notify_calibration_due(self):
        self.ensure_one()
        responsible = self.technician_user_id or self.category_id.technician_user_id
        partners = responsible.partner_id if responsible else self.env["res.partner"]
        if not partners:
            return
        message = _(
            "Reminder: Equipment %(name)s requires calibration on %(date)s.",
            name=self.display_name,
            date=self.calibration_date,
        )
        self.env["notification.service"].notify(
            partners,
            message,
            event="asset_calibration_due",
            subject=_("Equipment Calibration Due"),
        )

    @api.model
    def _cron_send_calibration_reminders(self, days=7):
        """Send reminders for equipment requiring calibration within ``days``."""
        today = fields.Date.context_today(self)
        due_date = today + relativedelta(days=days)
        equipments = self.search(
            [
                ("calibration_date", "!=", False),
                ("calibration_date", "<=", due_date),
                ("calibration_date", ">=", today),
            ]
        )
        for equipment in equipments:
            equipment._notify_calibration_due()
