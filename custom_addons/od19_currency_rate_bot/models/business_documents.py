# Copyright 2026 Auto-Info
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime

import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

_AUTOINFO_MINI_BAR_PARAM = "od19_currency_rate_bot.enable_mini_bar"
_AUTOINFO_MINI_BAR_GROUP = "od19_currency_rate_bot.group_currency_rate_bar_viewer"

# Model -> stored field holding the rate "company currency -> document currency"
# (Odoo 19 semantics). account.payment has no such field, its rate is always
# resolved from the related accounting documents.
_AUTOINFO_RATE_FIELDS = {
    "account.move": "invoice_currency_rate",
    "sale.order": "currency_rate",
    "purchase.order": "currency_rate",
}


def _autoinfo_cutoff_date(date_value):
    date_value = fields.Date.to_date(date_value)
    if not date_value:
        return None
    now_local = datetime.datetime.now(pytz.timezone("Asia/Bangkok"))
    if date_value == now_local.date() and now_local.time() < datetime.time(18, 0, 0):
        return date_value - datetime.timedelta(days=1)
    return date_value


def _autoinfo_mini_bar_enabled(env):
    value = env["ir.config_parameter"].sudo().get_param(_AUTOINFO_MINI_BAR_PARAM, "True")
    return str(value).lower() in ("1", "true", "yes", "on")


def _autoinfo_user_has_bar_access(env):
    return env.user.has_group(_AUTOINFO_MINI_BAR_GROUP)


def _autoinfo_assert_bar_access(env):
    if not _autoinfo_user_has_bar_access(env):
        raise AccessError(
            env._("You are not allowed to view or refresh the currency rate mini bar.")
        )
    if not _autoinfo_mini_bar_enabled(env):
        raise AccessError(
            env._("The currency rate mini bar is disabled by the administrator.")
        )


def _autoinfo_pick_foreign_currency(currencies, company_currency):
    currencies = currencies.filtered(lambda c: c and c != company_currency)
    return currencies[:1]


def _autoinfo_record_currency(record):
    return "currency_id" in record._fields and record.currency_id or False


def _autoinfo_record_exchange_rate(record):
    """Company currency per 1 unit of the record currency.

    Odoo 19 stores ``currency_rate`` / ``invoice_currency_rate`` as
    "company currency -> document currency", so it is inverted here to keep a
    single, human readable "1 <foreign> = X <company>" convention.
    """
    field_name = _AUTOINFO_RATE_FIELDS.get(record._name)
    if not field_name or field_name not in record._fields:
        return 0.0
    rate = record[field_name]
    if not rate:
        return 0.0
    return 1.0 / rate


def _autoinfo_has_exchange_rate(record):
    return bool(_autoinfo_record_exchange_rate(record))


def _autoinfo_exchange_rate_is_meaningful(record, currency):
    if not _autoinfo_has_exchange_rate(record):
        return False
    company_currency = (
        record.company_id.currency_id if record.company_id else record.env.company.currency_id
    )
    record_currency = _autoinfo_record_currency(record)
    if (
        currency
        and currency != company_currency
        and record_currency == company_currency
        and abs(_autoinfo_record_exchange_rate(record) - 1.0) < 1e-9
    ):
        return False
    return True


def _autoinfo_record_date(record):
    if record._name == "account.move":
        return _autoinfo_cutoff_date(
            record.invoice_date or record.date or fields.Date.context_today(record)
        )
    if record._name == "account.payment":
        return _autoinfo_cutoff_date(record.date or fields.Date.context_today(record))
    if record._name in ("sale.order", "purchase.order"):
        date_value = fields.Datetime.to_datetime(record.date_order)
        return _autoinfo_cutoff_date(
            date_value.date() if date_value else fields.Date.context_today(record)
        )
    return _autoinfo_cutoff_date(fields.Date.context_today(record))


def _autoinfo_move_source_currency(move):
    company_currency = move.company_id.currency_id
    sale_currency = _autoinfo_pick_foreign_currency(
        move.line_ids.mapped("sale_line_ids.order_id.currency_id"),
        company_currency,
    )
    if sale_currency:
        return sale_currency
    purchase_currency = _autoinfo_pick_foreign_currency(
        move.line_ids.mapped("purchase_line_id.order_id.currency_id"),
        company_currency,
    )
    if purchase_currency:
        return purchase_currency
    return _autoinfo_pick_foreign_currency(move.currency_id, company_currency)


def _autoinfo_payment_source_currency(payment):
    company_currency = payment.company_id.currency_id
    invoices = payment.reconciled_invoice_ids | payment.reconciled_bill_ids
    sale_currency = _autoinfo_pick_foreign_currency(
        invoices.mapped("line_ids.sale_line_ids.order_id.currency_id"),
        company_currency,
    )
    if sale_currency:
        return sale_currency
    purchase_currency = _autoinfo_pick_foreign_currency(
        invoices.mapped("line_ids.purchase_line_id.order_id.currency_id"),
        company_currency,
    )
    if purchase_currency:
        return purchase_currency
    invoice_currency = _autoinfo_pick_foreign_currency(
        invoices.mapped("currency_id"), company_currency
    )
    if invoice_currency:
        return invoice_currency
    return _autoinfo_pick_foreign_currency(payment.currency_id, company_currency)


def _autoinfo_related_source_moves(env, moves):
    if not moves:
        return env["account.move"]
    sale_orders = moves.mapped("line_ids.sale_line_ids.order_id")
    purchase_orders = moves.mapped("line_ids.purchase_line_id.order_id")
    return moves | sale_orders.invoice_ids | purchase_orders.invoice_ids


def _autoinfo_related_payments(env, moves):
    if not moves:
        return env["account.payment"]
    partials = env["account.partial.reconcile"].search(
        [
            "|",
            ("debit_move_id.move_id", "in", moves.ids),
            ("credit_move_id.move_id", "in", moves.ids),
        ]
    )
    counterpart_moves = (partials.debit_move_id.move_id | partials.credit_move_id.move_id) - moves
    if not counterpart_moves:
        return env["account.payment"]
    return env["account.payment"].search([("move_id", "in", counterpart_moves.ids)])


def _autoinfo_latest_accounting_rate(candidates, currency_getter):
    latest = False
    for record in candidates:
        currency = currency_getter(record)
        if not currency or not _autoinfo_exchange_rate_is_meaningful(record, currency):
            continue
        write_dt = (
            fields.Datetime.to_datetime(record.write_date or record.create_date)
            or fields.Datetime.now()
        )
        candidate = (
            write_dt,
            record.id,
            {
                "currency": currency,
                "rate": _autoinfo_record_exchange_rate(record),
                "rate_date": _autoinfo_record_date(record),
            },
        )
        if not latest or candidate[:2] > latest[:2]:
            latest = candidate
    return latest and latest[2] or False


def _autoinfo_fallback_rate(record, currency):
    if not currency:
        return False
    rate_date = _autoinfo_record_date(record)
    if not rate_date:
        return False
    if _autoinfo_exchange_rate_is_meaningful(record, currency):
        return {
            "currency": currency,
            "rate": _autoinfo_record_exchange_rate(record),
            "rate_date": rate_date,
        }
    company = record.company_id or record.env.company
    return {
        "currency": currency,
        "rate": record.env["res.currency"]._get_conversion_rate(
            currency, company.currency_id, company, rate_date
        ),
        "rate_date": rate_date,
    }


def _autoinfo_apply_currency_bar(records, accounting_resolver, fallback_currency_getter):
    enabled = _autoinfo_mini_bar_enabled(records.env) and _autoinfo_user_has_bar_access(
        records.env
    )
    for rec in records:
        resolved = accounting_resolver(rec) or _autoinfo_fallback_rate(
            rec, fallback_currency_getter(rec)
        )
        if not enabled or not resolved:
            rec.autoinfo_currency_bar_show = False
            rec.autoinfo_currency_bar_currency_id = False
            rec.autoinfo_currency_bar_rate_date = False
            rec.autoinfo_currency_bar_rate = 0.0
            continue
        rec.autoinfo_currency_bar_show = True
        rec.autoinfo_currency_bar_currency_id = resolved["currency"]
        rec.autoinfo_currency_bar_rate_date = resolved["rate_date"]
        rec.autoinfo_currency_bar_rate = resolved["rate"]


def _autoinfo_move_accounting_rate(move):
    related_moves = _autoinfo_related_source_moves(move.env, move)
    payments = _autoinfo_related_payments(move.env, related_moves)
    return _autoinfo_latest_accounting_rate(
        list(related_moves) + list(payments),
        lambda rec: (
            _autoinfo_move_source_currency(rec)
            if rec._name == "account.move"
            else _autoinfo_payment_source_currency(rec)
        ),
    )


def _autoinfo_payment_accounting_rate(payment):
    invoices = payment.reconciled_invoice_ids | payment.reconciled_bill_ids
    related_moves = _autoinfo_related_source_moves(payment.env, invoices)
    payments = _autoinfo_related_payments(payment.env, related_moves)
    candidates = [payment] + list(related_moves) + list(payments)
    return _autoinfo_latest_accounting_rate(
        candidates,
        lambda rec: (
            _autoinfo_move_source_currency(rec)
            if rec._name == "account.move"
            else _autoinfo_payment_source_currency(rec)
        ),
    )


def _autoinfo_document_accounting_rate(order):
    related_moves = _autoinfo_related_source_moves(order.env, order.invoice_ids)
    payments = _autoinfo_related_payments(order.env, related_moves)
    return _autoinfo_latest_accounting_rate(
        list(related_moves) + list(payments),
        lambda rec: (
            _autoinfo_move_source_currency(rec)
            if rec._name == "account.move"
            else _autoinfo_payment_source_currency(rec)
        ),
    )


def _autoinfo_update_company_rates(companies, force=False):
    """Trigger a BOT refresh through the OCA provider and stamp the company."""
    provider = companies.env["res.currency.rate.provider"]
    providers = provider.search(
        [
            ("company_id", "in", companies.ids),
            ("service", "=", "BOT"),
            ("active", "=", True),
        ]
    )
    if not providers:
        raise UserError(
            companies.env._(
                "No active Bank of Thailand currency rate provider is configured "
                "for this company."
            )
        )
    if not any(company.bot_token for company in companies):
        raise UserError(
            companies.env._("No bot.or.th credentials specified!")
        )
    today = fields.Date.context_today(companies)
    date_from = today - datetime.timedelta(days=7)
    providers._update(date_from, today, newest_only=True)
    for company in companies:
        newest = companies.env["res.currency.rate"].search(
            [("company_id", "=", company.id)], order="name desc", limit=1
        )
        company.sudo().write(
            {
                "autoinfo_currency_rate_last_update": fields.Datetime.now(),
                "autoinfo_currency_rate_last_rate_date": newest.name or False,
            }
        )


class AccountMove(models.Model):
    _inherit = "account.move"

    autoinfo_currency_bar_show = fields.Boolean(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_currency_id = fields.Many2one(
        "res.currency", compute="_compute_autoinfo_currency_bar"
    )
    autoinfo_currency_bar_rate_date = fields.Date(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_rate = fields.Float(
        compute="_compute_autoinfo_currency_bar", digits=(16, 6)
    )
    autoinfo_currency_bar_last_update = fields.Datetime(
        related="company_id.autoinfo_currency_rate_last_update"
    )

    def action_refresh_currency_rates(self):
        _autoinfo_assert_bar_access(self.env)
        _autoinfo_update_company_rates(self.company_id, force=True)
        return True

    @api.depends(
        "currency_id",
        "company_id",
        "date",
        "invoice_date",
        "invoice_currency_rate",
        "write_date",
        "line_ids.sale_line_ids",
        "line_ids.sale_line_ids.order_id.currency_id",
        "line_ids.sale_line_ids.order_id.invoice_ids.invoice_currency_rate",
        "line_ids.sale_line_ids.order_id.invoice_ids.write_date",
        "line_ids.purchase_line_id",
        "line_ids.purchase_line_id.order_id.currency_id",
        "line_ids.purchase_line_id.order_id.invoice_ids.invoice_currency_rate",
        "line_ids.purchase_line_id.order_id.invoice_ids.write_date",
    )
    def _compute_autoinfo_currency_bar(self):
        _autoinfo_apply_currency_bar(
            self,
            _autoinfo_move_accounting_rate,
            _autoinfo_move_source_currency,
        )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    autoinfo_currency_bar_show = fields.Boolean(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_currency_id = fields.Many2one(
        "res.currency", compute="_compute_autoinfo_currency_bar"
    )
    autoinfo_currency_bar_rate_date = fields.Date(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_rate = fields.Float(
        compute="_compute_autoinfo_currency_bar", digits=(16, 6)
    )
    autoinfo_currency_bar_last_update = fields.Datetime(
        related="company_id.autoinfo_currency_rate_last_update"
    )

    def action_refresh_currency_rates(self):
        _autoinfo_assert_bar_access(self.env)
        _autoinfo_update_company_rates(self.company_id, force=True)
        return True

    @api.depends(
        "currency_id",
        "company_id",
        "date",
        "state",
        "write_date",
        "invoice_ids",
        "invoice_ids.invoice_currency_rate",
        "invoice_ids.write_date",
        "invoice_ids.line_ids.sale_line_ids",
        "invoice_ids.line_ids.sale_line_ids.order_id.currency_id",
        "invoice_ids.line_ids.purchase_line_id.order_id.currency_id",
    )
    def _compute_autoinfo_currency_bar(self):
        _autoinfo_apply_currency_bar(
            self,
            _autoinfo_payment_accounting_rate,
            _autoinfo_payment_source_currency,
        )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    autoinfo_currency_bar_show = fields.Boolean(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_currency_id = fields.Many2one(
        "res.currency", compute="_compute_autoinfo_currency_bar"
    )
    autoinfo_currency_bar_rate_date = fields.Date(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_rate = fields.Float(
        compute="_compute_autoinfo_currency_bar", digits=(16, 6)
    )
    autoinfo_currency_bar_last_update = fields.Datetime(
        related="company_id.autoinfo_currency_rate_last_update"
    )

    def action_refresh_currency_rates(self):
        _autoinfo_assert_bar_access(self.env)
        _autoinfo_update_company_rates(self.company_id, force=True)
        return True

    @api.depends(
        "currency_id",
        "company_id",
        "date_order",
        "currency_rate",
        "invoice_ids",
        "invoice_ids.invoice_currency_rate",
        "invoice_ids.write_date",
    )
    def _compute_autoinfo_currency_bar(self):
        _autoinfo_apply_currency_bar(
            self,
            _autoinfo_document_accounting_rate,
            lambda rec: _autoinfo_pick_foreign_currency(
                rec.currency_id, rec.company_id.currency_id
            ),
        )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    autoinfo_currency_bar_show = fields.Boolean(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_currency_id = fields.Many2one(
        "res.currency", compute="_compute_autoinfo_currency_bar"
    )
    autoinfo_currency_bar_rate_date = fields.Date(compute="_compute_autoinfo_currency_bar")
    autoinfo_currency_bar_rate = fields.Float(
        compute="_compute_autoinfo_currency_bar", digits=(16, 6)
    )
    autoinfo_currency_bar_last_update = fields.Datetime(
        related="company_id.autoinfo_currency_rate_last_update"
    )

    def action_refresh_currency_rates(self):
        _autoinfo_assert_bar_access(self.env)
        _autoinfo_update_company_rates(self.company_id, force=True)
        return True

    @api.depends(
        "currency_id",
        "company_id",
        "date_order",
        "currency_rate",
        "invoice_ids",
        "invoice_ids.invoice_currency_rate",
        "invoice_ids.write_date",
    )
    def _compute_autoinfo_currency_bar(self):
        _autoinfo_apply_currency_bar(
            self,
            _autoinfo_document_accounting_rate,
            lambda rec: _autoinfo_pick_foreign_currency(
                rec.currency_id, rec.company_id.currency_id
            ),
        )
