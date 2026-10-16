import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

# Matches "<base>/R<digits>" at the end of a document reference.
REVISION_SUFFIX_RE = re.compile(r"^(?P<base>.+)/R(?P<no>\d+)$")


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_revision_of_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Revised From",
        index=True,
        ondelete="restrict",
        copy=False,
    )
    od19_revision_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="od19_revision_of_id",
        string="Revision History",
        copy=False,
    )
    od19_base_name = fields.Char(
        string="Base Reference",
        compute="_compute_od19_revision_naming",
        store=True,
        index=True,
        copy=False,
    )
    od19_revision_no = fields.Integer(
        string="Revision No.",
        compute="_compute_od19_revision_naming",
        store=True,
        copy=False,
    )
    od19_is_revision = fields.Boolean(
        string="Is Revision",
        compute="_compute_od19_is_revision",
        store=True,
        copy=False,
    )
    od19_revision_status = fields.Selection(
        selection=[
            ("current", "Current"),
            ("superseded", "Superseded"),
        ],
        string="Revision Status",
        default="current",
        required=True,
        copy=False,
        tracking=True,
    )
    od19_revision_count = fields.Integer(
        string="Revisions",
        compute="_compute_od19_revision_count",
    )

    # Write keys that stay writable on a superseded document (mail/activity
    # technical fields and the revision status itself).
    _OD19_SUPERSEDED_SAFE_FIELDS = frozenset({"od19_revision_status"})
    _OD19_SUPERSEDED_SAFE_PREFIXES = ("message_", "activity_")

    @api.depends("name")
    def _compute_od19_revision_naming(self):
        for order in self:
            match = REVISION_SUFFIX_RE.match(order.name or "")
            if match:
                order.od19_base_name = match.group("base")
                order.od19_revision_no = int(match.group("no"))
            else:
                order.od19_base_name = order.name or ""
                order.od19_revision_no = -1

    @api.depends("od19_revision_of_id")
    def _compute_od19_is_revision(self):
        for order in self:
            order.od19_is_revision = bool(order.od19_revision_of_id)

    @api.depends("od19_base_name")
    def _compute_od19_revision_count(self):
        for order in self:
            if not order.od19_base_name:
                order.od19_revision_count = 0
                continue
            order.od19_revision_count = self.search_count(
                [
                    ("od19_base_name", "=", order.od19_base_name),
                    ("id", "!=", order.id),
                ]
            )

    def _od19_check_revision_access(self):
        if not self.env.user.has_group(
            "od19_purchase_procurement_core.group_purchase_director"
        ):
            raise AccessError(
                _("Only members of the Purchase Director group can create "
                  "purchase order revisions.")
            )

    def action_create_revision(self):
        """Create a new revision of this purchase order."""
        self.ensure_one()
        self._od19_check_revision_access()
        if self.od19_revision_status == "superseded":
            raise UserError(
                _("This document has already been superseded. "
                  "Please use the latest revision.")
            )
        if self.state != "purchase":
            raise UserError(
                _("Only confirmed purchase orders can be revised.")
            )

        base_name = self.od19_base_name or self.name
        chain = self.search([("od19_base_name", "=", base_name)])
        next_no = max(chain.mapped("od19_revision_no") or [-1]) + 1
        new_name = "%s/R%02d" % (base_name, next_no)

        new_order = self.copy(
            {
                "name": new_name,
                "od19_revision_of_id": self.id,
                "od19_revision_status": "current",
                "date_approve": False,
            }
        )
        self.od19_revision_status = "superseded"

        self.message_post(
            body=_("Revision %(new)s created from this document.",
                   new=new_order.name)
        )
        new_order.message_post(
            body=_("Created as revision %(new)s of %(old)s.",
                   new=new_order.name, old=self.name)
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order"),
            "res_model": "purchase.order",
            "res_id": new_order.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_view_revisions(self):
        """Open the list of every document in the same revision chain."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Revisions"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("od19_base_name", "=", self.od19_base_name)],
            "target": "current",
        }

    def write(self, vals):
        if not self.env.context.get("od19_allow_superseded_write"):
            blocked = {
                key
                for key in vals
                if key not in self._OD19_SUPERSEDED_SAFE_FIELDS
                and not key.startswith(self._OD19_SUPERSEDED_SAFE_PREFIXES)
            }
            if blocked:
                superseded = self.filtered(
                    lambda order: order.od19_revision_status == "superseded"
                )
                if superseded:
                    raise UserError(
                        _("Document %s has been superseded and can no longer "
                          "be modified. Please use the latest revision.",
                          ", ".join(superseded.mapped("name")))
                    )
        return super().write(vals)
