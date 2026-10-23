# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Central contract for the "pull source document lines" mechanism.

Destination documents (account.move, purchase.order, ...) inherit this
abstract model and implement the contract methods below. The shared
helpers here only deal with guards and with opening the wizards, so the
mechanism stays in one place (Lean & Maintainable).
"""

from odoo import _, models
from odoo.exceptions import UserError


class Od19DocumentPullMixin(models.AbstractModel):
    _name = "od19.document.pull.mixin"
    _description = "OD19 Document Pull Mixin"

    # ------------------------------------------------------------------
    # Contract — override in the destination model
    # ------------------------------------------------------------------

    def _od19_pull_editable_states(self):
        """Return the states in which the document may be modified."""
        return ("draft",)

    def _od19_pull_source_specs(self):
        """Return the allowed source documents for this record.

        Each spec is a dict:
            {
                "model": str,     # e.g. "purchase.order"
                "label": str,     # bilingual label shown in the wizard
                "domain": list,   # extra domain (already scoped to self)
            }
        """
        self.ensure_one()
        return []

    def _od19_pull_spec(self, model_name):
        """Return the spec for a given source model, or None."""
        self.ensure_one()
        for spec in self._od19_pull_source_specs():
            if spec["model"] == model_name:
                return spec
        return None

    def _od19_pull_candidate_lines(self, source):
        """Return the source lines that can still be pulled from source."""
        raise NotImplementedError

    def _od19_pull_line_info(self, source, line):
        """Return a dict feeding one od19.document.pull.wizard.line."""
        raise NotImplementedError

    def _od19_pull_apply(self, source, lines):
        """Create destination lines from lines of source. Return count."""
        raise NotImplementedError

    def _od19_pull_remove(self, source):
        """Delete destination lines linked to source. Return count removed."""
        raise NotImplementedError

    def _od19_pull_bound_sources(self):
        """Return [(source_record, line_count)] currently bound to self."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _od19_pull_check_editable(self):
        """Raise when the document may not be modified anymore."""
        self.ensure_one()
        if self.state not in self._od19_pull_editable_states():
            raise UserError(
                _(
                    "Source document lines can only be managed on a draft "
                    "document (current state: %(state)s).",
                    state=self.state,
                )
            )
        return True

    def _od19_pull_check_source(self, source):
        """Validate that source is one of the allowed source documents."""
        self.ensure_one()
        if not source:
            raise UserError(_("Please select a source document."))
        spec = self._od19_pull_spec(source._name)
        if not spec:
            raise UserError(
                _(
                    "%(source)s is not a valid source document for this "
                    "document.",
                    source=source._name,
                )
            )
        if (
            self.env[source._name].search_count(
                spec["domain"] + [("id", "=", source.id)]
            )
            == 0
        ):
            raise UserError(
                _(
                    "The selected source document does not match this "
                    "document (check the partner or the state)."
                )
            )
        return True

    def _od19_pull_action_open_pull_wizard(self):
        """Open the pull wizard for the current document."""
        self.ensure_one()
        self._od19_pull_check_editable()
        return {
            "name": _("Pull Lines from Source / ดึงรายการจากเอกสารต้นทาง"),
            "type": "ir.actions.act_window",
            "res_model": "od19.document.pull.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }

    def _od19_pull_action_open_remove_wizard(self):
        """Open the remove-with-confirmation wizard for the document."""
        self.ensure_one()
        self._od19_pull_check_editable()
        return {
            "name": _("Manage/Remove Source / จัดการ/ลบเอกสารต้นทาง"),
            "type": "ir.actions.act_window",
            "res_model": "od19.document.pull.remove.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }
