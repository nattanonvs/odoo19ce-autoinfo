from odoo import api, fields, models, _


class SaleOrderRevisionWizard(models.TransientModel):
    _name = "sale.order.revision.wizard"
    _description = "Sale Order Revision Wizard"

    name = fields.Char(string="Message", readonly=True)
    cancel_original = fields.Boolean(
        string="Cancel Original Quotation",
        default=False,
        help="If checked, the original quotation will be cancelled after creating the revision.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_id = self.env.context.get("sale_id")
        if sale_id:
            quotation = self.env["sale.order"].browse(sale_id)
            res["name"] = _(
                "Do you want to create a new revision of quotation %s?"
            ) % quotation.name
        return res

    def confirm(self):
        sale_id = self.env.context.get("sale_id")
        if not sale_id:
            return {"type": "ir.actions.act_window_close"}
        quotation = self.env["sale.order"].browse(sale_id)
        new_quotation = self._create_revision(quotation)
        if self.cancel_original:
            quotation.action_cancel()
        return {
            "name": new_quotation.name,
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "sale.order",
            "res_id": new_quotation.id,
            "target": "current",
        }

    def _create_revision(self, quotation):
        """Create a new revision of the quotation.

        The new quotation name gets /R01, /R02, ... appended.
        All parent revisions are linked to the new quotation.
        """
        revision_number = len(quotation.parent_ids) + 1
        new_name = quotation._generate_revision_name(
            quotation.name, revision_number
        )
        default = {"name": new_name}
        new_quotation = quotation.copy(default)

        # Link all existing parent revisions to the new quotation
        for item in quotation.parent_ids:
            self.env["quotation.revision.parent"].create(
                {
                    "sale_order_id": new_quotation.id,
                    "parent_id": item.parent_id.id,
                }
            )

        # Link the original quotation as a parent of the new revision
        self.env["quotation.revision.parent"].create(
            {
                "sale_order_id": new_quotation.id,
                "parent_id": quotation.id,
            }
        )
        return new_quotation
