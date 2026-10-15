# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Wizard to manually trigger a runtime guard snapshot.

This wizard is intentionally simple: it creates a new ``od19.runtime.guard``
record, collects the runtime information and opens the created record so the
administrator can review the snapshot.

Access is restricted to administrators (see ``security/ir.model.access.csv``
and the ``_check_admin`` guard).
"""

from odoo import _, fields, models
from odoo.exceptions import AccessError


class Od19RuntimeGuardWizard(models.TransientModel):
    _name = "od19.runtime.guard.wizard"
    _description = "OD19 Runtime Guard Wizard"

    note = fields.Text(
        string="Note",
        default=lambda self: _(
            "Click 'Run Check' to collect runtime information. "
            "This action is manual and does not run as a scheduled job."
        ),
    )

    def _check_admin(self):
        if not self.env.is_admin():
            raise AccessError(
                _("Only administrators can run the runtime guard check.")
            )

    def action_run_check(self):
        """Collect runtime info, persist it and open the snapshot record.

        :returns: an action window opening the created snapshot
        """
        self.ensure_one()
        self._check_admin()

        guard = self.env["od19.runtime.guard"].create({})
        guard.action_collect()

        return {
            "type": "ir.actions.act_window",
            "name": _("Runtime Guard Snapshot"),
            "res_model": "od19.runtime.guard",
            "view_mode": "form",
            "res_id": guard.id,
            "target": "current",
        }
