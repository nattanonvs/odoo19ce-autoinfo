from odoo import fields, models, tools


class ReportAfterSalesProductReturn(models.Model):
    _name = "od19.report.after.sales.product.return"
    _description = "After-Sales Product Return KPI"
    _auto = False

    reason = fields.Selection(
        selection=[
            ("defective", "Defective"),
            ("wrong_product", "Wrong Product"),
            ("damaged", "Damaged in Transit"),
            ("not_as_described", "Not as Described"),
            ("warranty", "Warranty Claim"),
            ("other", "Other"),
        ],
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("approved", "Approved"),
            ("returned", "Returned"),
            ("refunded", "Refunded"),
            ("rejected", "Rejected"),
        ],
        readonly=True,
    )
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    return_count = fields.Integer(readonly=True)
    total_quantity = fields.Float(readonly=True)
    total_refund_amount = fields.Monetary(
        currency_field="currency_id", readonly=True
    )

    def search(self, domain, offset=0, limit=None, order=None):
        self.env["od19.product.return"].flush_model(
            ["reason", "state", "quantity", "refund_amount", "company_id"]
        )
        return super().search(domain, offset=offset, limit=limit, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(ret.id) AS id,
                    ret.reason AS reason,
                    ret.state AS state,
                    ret.company_id AS company_id,
                    company.currency_id AS currency_id,
                    COUNT(*) AS return_count,
                    COALESCE(SUM(ret.quantity), 0.0) AS total_quantity,
                    COALESCE(SUM(ret.refund_amount), 0.0) AS total_refund_amount
                FROM od19_product_return ret
                LEFT JOIN res_company company ON company.id = ret.company_id
                GROUP BY
                    ret.reason,
                    ret.state,
                    ret.company_id,
                    company.currency_id
            )
            """
        )
