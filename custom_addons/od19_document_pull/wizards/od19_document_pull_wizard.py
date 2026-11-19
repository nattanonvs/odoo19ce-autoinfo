# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19DocumentPullWizard(models.TransientModel):
    _name = "od19.document.pull.wizard"
    _description = "OD19 Document Pull Wizard"

    res_model = fields.Char(
        string="Destination Model / โมเดลปลายทาง", required=True
    )
    res_id = fields.Integer(
        string="Destination ID / รหัสเอกสารปลายทาง", required=True
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner / คู่ค้า",
        compute="_compute_partner_id",
    )
    source_ids = fields.One2many(
        comodel_name="od19.document.pull.source",
        inverse_name="wizard_id",
        string="Source Documents / เอกสารต้นทาง",
    )
    mode = fields.Selection(
        selection=[
            ("all_order", "All lines (document order) / ทั้งหมดตามลำดับเอกสาร"),
            ("select", "Select lines / เลือกรายบรรทัด"),
        ],
        string="Pull Mode / โหมดการดึง",
        default="all_order",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="od19.document.pull.wizard.line",
        inverse_name="wizard_id",
        string="Lines / รายการ",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.depends("res_model", "res_id")
    def _compute_partner_id(self):
        for wizard in self:
            target = (
                wizard._od19_get_target()
                if wizard.res_model and wizard.res_id
                else False
            )
            wizard.partner_id = (
                getattr(target, "partner_id", False) if target else False
            )

    @api.model
    def _od19_source_commands(self, res_model, res_id):
        """Build the selectable source rows for a destination document.

        A source document is offered only when it matches the destination's
        source specification (partner, state, ...) and still has lines left to
        pull, so the wizard never shows an irrelevant or exhausted source.
        """
        target = self.env[res_model].browse(res_id).exists()
        if not target:
            return []
        commands = [Command.clear()]
        sequence = 10
        for spec in target._od19_pull_source_specs():
            for source in self.env[spec["model"]].search(spec["domain"]):
                remaining = len(target._od19_pull_candidate_lines(source))
                if not remaining:
                    continue
                commands.append(
                    Command.create(
                        {
                            "sequence": sequence,
                            "source_model": source._name,
                            "source_id": source.id,
                            "source_type": spec["label"],
                            "name": source.display_name,
                            "partner_id": (
                                source.partner_id.id
                                if "partner_id" in source._fields
                                else False
                            ),
                            "remaining": remaining,
                        }
                    )
                )
                sequence += 10
        return commands

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_model = res.get("res_model") or self.env.context.get("active_model")
        res_id = res.get("res_id") or self.env.context.get("active_id")
        if res_model and res_id:
            res["res_model"] = res_model
            res["res_id"] = res_id
            res["source_ids"] = self._od19_source_commands(res_model, res_id)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            if not wizard.source_ids:
                wizard.source_ids = wizard._od19_source_commands(
                    wizard.res_model, wizard.res_id
                )
        return wizards

    def _od19_selected_source(self):
        """Return the single source document ticked on the wizard."""
        self.ensure_one()
        selected = self.source_ids.filtered("selected")
        if len(selected) > 1:
            raise UserError(_("Please select only one source document."))
        return selected._od19_get_source() if selected else False

    @api.onchange("source_ids")
    def _onchange_source_ids(self):
        """Rebuild the candidate lines from the selected source document."""
        self.line_ids = [Command.clear()]
        self._od19_build_lines()

    def _od19_build_lines(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        source = self._od19_selected_source()
        if not source:
            return
        target = self._od19_get_target()
        commands = [
            Command.create(target._od19_pull_line_info(source, line))
            for line in target._od19_pull_candidate_lines(source)
        ]
        self.line_ids = commands

    def _od19_selected_source_lines(self):
        """Return the recordset of selected source lines."""
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        if not selected:
            return False
        models = set(selected.mapped("res_model"))
        if len(models) != 1:
            raise UserError(
                _("Selected lines must come from a single source document.")
            )
        model_name = models.pop()
        return self.env[model_name].browse(selected.mapped("res_id"))

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_pull(self):
        self.ensure_one()
        target = (
            self._od19_get_target()
            if self.res_model and self.res_id
            else False
        )
        if not target or not target.exists():
            raise UserError(_("The destination document no longer exists."))
        target._od19_pull_check_editable()
        source = self._od19_selected_source()
        target._od19_pull_check_source(source)

        if self.mode == "all_order":
            lines = target._od19_pull_candidate_lines(source)
        else:
            lines = self._od19_selected_source_lines()

        count = target._od19_pull_apply(source, lines) if lines else 0
        if not count:
            raise UserError(_("There is no line to pull from this document."))
        return {"type": "ir.actions.act_window_close"}
