import ast
import re

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )
    # NOTE (OD19 <-> OCA revision integration):
    # The custom revision tracking fields (parent_ids, child_ids, revision_count,
    # child_count) are kept for backward compatibility with existing views and
    # reports, but the *primary* revision mechanism is now OCA's
    # ``sale_order_revision`` (which provides ``current_revision_id``,
    # ``old_revision_ids``, ``revision_number`` and the ``create_revision``
    # method).  When OCA is installed, ``action_create_revision`` delegates to
    # OCA's ``create_revision`` so that both systems stay consistent and there
    # is a single source of truth for the revision chain.
    parent_ids = fields.One2many(
        "quotation.revision.parent",
        "sale_order_id",
        string="Revision History",
    )
    revision_count = fields.Integer(
        string="# of Revision",
        compute="_compute_revision_count",
        readonly=True,
    )
    child_ids = fields.One2many(
        "quotation.revision.parent",
        "parent_id",
        string="Child Revisions",
    )
    child_count = fields.Integer(
        string="# of Child",
        compute="_compute_child_count",
        readonly=True,
    )

    @api.depends("parent_ids")
    def _compute_revision_count(self):
        for order in self:
            order.revision_count = len(order.parent_ids)

    @api.depends("child_ids")
    def _compute_child_count(self):
        for order in self:
            order.child_count = len(order.child_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "department_id" not in res or not res.get("department_id"):
            user = self.env["res.users"].browse(self.env.uid)
            if user.employee_id and user.employee_id.department_id:
                res["department_id"] = user.employee_id.department_id.id
        return res

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                department_id = vals.get("department_id")
                if department_id:
                    department = self.env["hr.department"].browse(department_id)
                    if department and department.quotation_sequence_id:
                        seq_date = None
                        if vals.get("date_order"):
                            seq_date = fields.Datetime.context_timestamp(
                                self, fields.Datetime.to_datetime(vals["date_order"])
                            )
                        vals["name"] = (
                            department.quotation_sequence_id.next_by_id(
                                sequence_date=seq_date
                            )
                            or "/"
                        )
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "department_id" in vals:
            for rec in self:
                if rec.name in (_("New"), "/") and rec.department_id:
                    if rec.department_id.quotation_sequence_id:
                        seq_date = (
                            fields.Datetime.context_timestamp(rec, rec.date_order)
                            if rec.date_order
                            else None
                        )
                        rec.name = (
                            rec.department_id.quotation_sequence_id.next_by_id(
                                sequence_date=seq_date
                            )
                            or "/"
                        )
        return res

    def _od19_oca_revision_available(self):
        """Return True if OCA sale_order_revision is installed.

        Detected by the presence of ``current_revision_id`` (provided by OCA)
        and the ``create_revision`` method on the sale order model.
        """
        return (
            "current_revision_id" in self._fields
            and hasattr(type(self), "create_revision")
        )

    def action_create_revision(self):
        """Create a new revision of the quotation.

        When OCA ``sale_order_revision`` is installed, delegate the revision
        creation to OCA's ``create_revision`` method so the revision chain is
        managed by OCA (the single source of truth).  The custom
        ``quotation.revision.parent`` records are still kept in sync for
        backward-compatible reporting.

        When OCA is not installed, fall back to the legacy wizard flow.
        """
        self.ensure_one()
        if self._od19_oca_revision_available():
            # Delegate to OCA's create_revision which handles the full
            # revision chain (current_revision_id, old_revision_ids,
            # revision_number, unrevisioned_name).
            result = self.create_revision()
            # Keep the custom quotation.revision.parent table in sync so
            # existing views/reports that rely on parent_ids still work.
            new_revision_ids = result.get("domain", [])
            self._od19_sync_custom_revision_links(new_revision_ids)
            return result
        # Legacy fallback: open the custom revision wizard.
        return {
            "name": _("Quotation Revision Confirmation"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "sale.order.revision.wizard",
            "target": "new",
            "context": {"sale_id": self.id},
        }

    def _od19_sync_custom_revision_links(self, new_revision_domain):
        """Sync custom quotation.revision.parent records after OCA revision.

        OCA manages the canonical revision chain.  This helper mirrors the
        relationship into the custom ``quotation.revision.parent`` table so
        that views relying on ``parent_ids``/``child_ids`` keep working.

        ``new_revision_domain`` may be a list (e.g. ``[('id', 'in', [1, 2])]``)
        or a string representation of such a list (OCA's ``create_revision``
        returns the domain as a string).
        """
        if not new_revision_domain:
            return
        # OCA returns the domain as a string; parse it into a list if needed.
        if isinstance(new_revision_domain, str):
            try:
                new_revision_domain = ast.literal_eval(new_revision_domain)
            except (ValueError, SyntaxError):
                return
        new_orders = self.env["sale.order"].search(new_revision_domain)
        for new_order in new_orders:
            # Link the original as parent of the new revision
            existing = self.env["quotation.revision.parent"].search(
                [
                    ("sale_order_id", "=", new_order.id),
                    ("parent_id", "=", self.id),
                ]
            )
            if not existing:
                self.env["quotation.revision.parent"].create(
                    {
                        "sale_order_id": new_order.id,
                        "parent_id": self.id,
                    }
                )

    def action_view_revisions(self):
        """View parent revisions of this quotation."""
        self.ensure_one()
        if self._od19_oca_revision_available():
            # Delegate to OCA's action_view_revisions which shows the full
            # revision chain including inactive records.
            return super(SaleOrder, self).action_view_revisions()
        action = self.env.ref("sale.action_quotations_with_onboarding")
        return {
            "name": action.name,
            "type": action.type,
            "view_mode": action.view_mode,
            "res_model": action.res_model,
            "target": action.target,
            "help": action.help,
            "domain": [
                ("id", "in", self.parent_ids.mapped("parent_id").mapped("id"))
            ],
        }

    def action_view_child_revisions(self):
        """View child revisions of this quotation."""
        self.ensure_one()
        action = self.env.ref("sale.action_quotations_with_onboarding")
        return {
            "name": action.name,
            "type": action.type,
            "view_mode": action.view_mode,
            "res_model": action.res_model,
            "target": action.target,
            "help": action.help,
            "domain": [
                ("id", "in", self.child_ids.mapped("sale_order_id").mapped("id"))
            ],
        }

    @api.model
    def _generate_revision_name(self, base_name, revision_number):
        """Generate a revision name by appending /R01, /R02, etc.

        If the name already ends with /RNN, increment it.
        Otherwise append /R01.

        NOTE: This helper is retained for backward compatibility but is no
        longer the primary naming mechanism.  OCA's ``base_revision`` uses
        ``unrevisioned_name`` + ``revision_number`` (formatted as
        ``{name}-{rev:02d}``).  When OCA is installed, OCA's naming takes
        precedence.
        """
        match = re.search(r"/R(\d+)$", base_name)
        if match:
            base = base_name[: match.start()]
        else:
            base = base_name
        return f"{base}/R{revision_number:02d}"
