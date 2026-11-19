# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Confirmation wizard: the user always confirms before lines are removed."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class Od19DocumentPullRemoveWizard(models.TransientModel):
    _name = "od19.document.pull.remove.wizard"
    _description = "OD19 Document Pull Remove Wizard"

    res_model = fields.Char(
        string="Destination Model / โมเดลปลายทาง", required=True
    )
    res_id = fields.Integer(
        string="Destination ID / รหัสเอกสารปลายทาง", required=True
    )
    state = fields.Selection(
        selection=[
            ("choose", "Choose the source / เลือกเอกสารต้นทาง"),
            ("confirm", "Confirm the removal / ยืนยันการลบ"),
        ],
        string="Step / ขั้นตอน",
        default="choose",
        required=True,
    )
    source_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.source",
        inverse_name="wizard_id",
        string="Source Documents / เอกสารต้นทาง",
    )
    source_type_filter = fields.Selection(
        selection="_od19_source_type_selection",
        string="Pull Type / ประเภทการดึง",
        default="all",
    )
    source_line_ids = fields.One2many(
        comodel_name="od19.document.pull.remove.line",
        inverse_name="wizard_id",
        string="Lines to remove / รายการที่จะลบ",
    )
    remove_summary = fields.Char(
        string="Summary / สรุป",
        compute="_compute_remove_summary",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _od19_get_target(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.model
    def _od19_source_type_selection(self):
        """Delegate to the shared mixin list (keeps one source of truth)."""
        return self.env["od19.document.pull.mixin"]._od19_pull_type_selection()

    def _od19_selected_source(self):
        """Return the source document ticked on the wizard."""
        self.ensure_one()
        selected = self.source_ids.filtered("selected")
        if len(selected) > 1:
            raise UserError(_("Please select only one source document."))
        return selected._od19_get_source() if selected else False

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._od19_build_bound_sources()
        return wizards

    @api.onchange("res_model", "res_id")
    def _onchange_target(self):
        self._od19_build_bound_sources()

    @api.onchange("source_type_filter")
    def _onchange_source_type_filter(self):
        """Rebuild the bound-source rows when the pull type filter changes."""
        self.source_line_ids = [Command.clear()]
        self._od19_build_bound_sources()

    def _od19_build_bound_sources(self):
        self.ensure_one()
        type_filter = self.source_type_filter
        commands = []
        if self.res_model and self.res_id:
            target = self._od19_get_target().exists()
            if target:
                commands = [
                    Command.create(
                        {
                            "source_ref": "%s,%s" % (source._name, source.id),
                            "name": "%s (%s)" % (source.display_name, count),
                        }
                    )
                    for source, count in target._od19_pull_bound_sources()
                    if type_filter in (None, False, "all")
                    or source._name == type_filter
                ]
        self.source_ids = [Command.clear()] + commands

    @api.depends("source_line_ids", "source_ids.selected")
    def _compute_remove_summary(self):
        for wizard in self:
            count = len(wizard.source_line_ids)
            source = wizard.source_ids.filtered("selected")[:1]
            if source and count:
                wizard.remove_summary = _(
                    "Document %(name)s will have %(count)s line(s) removed.",
                    name=source.name,
                    count=count,
                )
            else:
                wizard.remove_summary = False

    def _od19_push_preview_lines(self, target, source):
        self.ensure_one()
        commands = [
            Command.create(dict(vals, wizard_id=self.id))
            for vals in target._od19_pull_preview_lines(source)
        ]
        self.source_line_ids = [Command.clear()] + commands
        return self.source_line_ids

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_select_source(self):
        """Move to the confirmation step and preview the lines to remove."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        source = self._od19_selected_source()
        if not source:
            raise UserError(_("Please select the source document to remove."))
        target._od19_pull_check_source(source)
        lines = self._od19_push_preview_lines(target, source)
        if not lines:
            raise UserError(
                _(
                    "There is no line linked to %(name)s in this document.",
                    name=source.display_name,
                )
            )
        self.state = "confirm"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_back(self):
        self.ensure_one()
        self.state = "choose"
        self.source_line_ids = [Command.clear()]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_remove(self):
        """Remove the lines after the user confirmed."""
        self.ensure_one()
        target = self._od19_get_target()
        target._od19_pull_check_editable()
        source = self._od19_selected_source()
        if not source:
            raise UserError(_("No source document selected."))
        target._od19_pull_remove(source)
        return {"type": "ir.actions.act_window_close"}
