from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_customer_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Customer Invoice Bring Forward",
        copy=False,
    )
    od19_vendor_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Vendor Bill Bring Forward",
        copy=False,
    )
    od19_customer_cn_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Customer Credit Note Bring Forward",
        copy=False,
    )
    od19_customer_dn_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Customer Debit Note Bring Forward",
        copy=False,
    )
    od19_vendor_cn_bf_id = fields.Many2one(
        "od19.bring.forward",
        string="Vendor Credit Note Bring Forward",
        copy=False,
    )
