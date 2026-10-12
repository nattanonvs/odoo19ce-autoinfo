from datetime import date

from odoo.tests.common import TransactionCase


class MoneyInReportCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.sale_journal:
            cls.sale_journal = cls.env["account.journal"].create(
                {
                    "name": "Money In Sale",
                    "code": "MISR",
                    "type": "sale",
                    "company_id": cls.company.id,
                }
            )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create(
                {
                    "name": "Money In Bank",
                    "code": "MIBK",
                    "type": "bank",
                    "company_id": cls.company.id,
                }
            )

        cls.receivable_account = cls.env["account.account"].create(
            {
                "name": "Money In Receivable",
                "code": "MIR100",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Money In Income",
                "code": "MIR200",
                "account_type": "income",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Money In Customer",
                "property_account_receivable_id": cls.receivable_account.id,
            }
        )
        cls.salesperson = cls.env["res.users"].search(
            [("id", "!=", cls.env.ref("base.user_admin").id)], limit=1
        )
        if not cls.salesperson:
            cls.salesperson = cls.env["res.users"].create(
                {"name": "Money In Salesperson", "login": "moneyin_sp"}
            )
        cls.project = cls.env["project.project"].create({"name": "Project A"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Money In Product",
                "type": "service",
                "invoice_policy": "order",
                "standard_price": 40.0,
                "list_price": 100.0,
                "property_account_income_id": cls.income_account.id,
            }
        )
        cls.product_category_2 = cls.env["product.category"].create(
            {"name": "Money In Category 2"}
        )
        cls.product_2 = cls.env["product.product"].create(
            {
                "name": "Money In Product 2",
                "type": "service",
                "invoice_policy": "order",
                "standard_price": 30.0,
                "list_price": 150.0,
                "categ_id": cls.product_category_2.id,
                "property_account_income_id": cls.income_account.id,
            }
        )

    @classmethod
    def _create_invoice(cls, partner=None, product=None, qty=1.0, price=100.0, invoice_date=None, salesperson=None):
        partner = partner or cls.partner
        product = product or cls.product
        invoice_date = invoice_date or date(2026, 10, 1)
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "journal_id": cls.sale_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": qty,
                            "price_unit": price,
                            "name": product.name,
                        },
                    )
                ],
            }
        )
        if salesperson:
            invoice.invoice_user_id = salesperson
        result = invoice.action_post()
        if result:
            # action_post returned a wizard action, force post via _post
            invoice._post(soft=False)
        return invoice

    @classmethod
    def _create_wizard(cls, phase="phase1_invoice_based", date_from=None, date_to=None, **kwargs):
        date_from = date_from or date(2026, 10, 1)
        date_to = date_to or date(2026, 10, 31)
        vals = {
            "date_from": date_from,
            "date_to": date_to,
            "phase": phase,
            "company_id": cls.company.id,
        }
        vals.update(kwargs)
        return cls.env["od19.money.in.report.wizard"].create(vals)
