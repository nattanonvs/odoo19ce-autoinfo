# -*- coding: utf-8 -*-
"""FIFO stock valuation service.

This module provides the FIFO (First-In, First-Out) stock valuation logic
for Odoo 19.  In Odoo 19 the ``stock.valuation.layer`` model was removed;
valuation is now derived directly from ``stock.move`` records using the
``is_in`` / ``is_out`` flags and the move ``value`` field.

The service processes stock moves in chronological order, matching
incoming moves (receipts) against outgoing moves (deliveries) to compute
the remaining quantity and value of stock as of a given date.
"""
from datetime import datetime, time

from odoo import api, models
from odoo.tools import float_is_zero, float_round


class StockFifoService(models.AbstractModel):
    _name = 'od19.stock.fifo.service'
    _description = 'FIFO Stock Valuation Service'

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def compute_fifo_valuation(self, product_id, as_of_date):
        """Compute FIFO valuation for a product as of ``as_of_date``.

        :param product_id: id of a ``product.product`` record.
        :param as_of_date: date or datetime string (or datetime/date object)
                           up to which the valuation is computed.
        :return: dict with keys ``quantity_on_hand``, ``total_value`` and
                 ``unit_cost``.
        """
        as_of_dt = self._as_datetime(as_of_date)
        moves = self._get_valuation_moves(product_id, as_of_dt)
        fifo_layers = self._consume_moves_fifo(moves)

        total_qty = sum(layer['qty'] for layer in fifo_layers)
        total_value = sum(layer['value'] for layer in fifo_layers)

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        total_qty = float_round(total_qty, precision_digits=precision)

        if float_is_zero(total_qty, precision_digits=precision):
            unit_cost = 0.0
            total_value = 0.0
        else:
            unit_cost = total_value / total_qty

        value_precision = self.env['decimal.precision'].precision_get('Account')
        total_value = float_round(total_value, precision_digits=value_precision)
        unit_cost = float_round(unit_cost, precision_digits=value_precision)

        return {
            'quantity_on_hand': total_qty,
            'total_value': total_value,
            'unit_cost': unit_cost,
        }

    @api.model
    def compute_fifo_valuation_multi(self, product_ids, as_of_date):
        """Compute FIFO valuation for a list of products.

        :param product_ids: list of ``product.product`` ids.
        :param as_of_date: date or datetime string (or object).
        :return: dict mapping product id -> valuation dict.
        """
        result = {}
        for product_id in product_ids:
            result[product_id] = self.compute_fifo_valuation(product_id, as_of_date)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @api.model
    def _as_datetime(self, as_of_date):
        """Normalize ``as_of_date`` into a naive UTC datetime.

        Stock move dates are stored in UTC in the database, so the returned
        value must also be in UTC for correct comparison.

        * ``date`` objects and date-only strings are expanded to the end of
          that day (23:59:59) in the user's timezone, then converted to UTC.
        * ``datetime`` objects are used as-is (assumed to be UTC already).
        """
        if isinstance(as_of_date, datetime):
            return as_of_date

        user_tz = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        try:
            import pytz
            tz = pytz.timezone(user_tz)
        except Exception:
            tz = None

        if isinstance(as_of_date, str):
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(as_of_date, fmt)
                    is_date_only = (len(as_of_date) <= 10)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("Unrecognized as_of_date format: %r" % (as_of_date,))
        else:
            # date object
            dt = datetime.combine(as_of_date, time(0, 0, 0))
            is_date_only = True

        if is_date_only:
            dt = dt.replace(hour=23, minute=59, second=59)

        if tz is not None:
            try:
                localized = tz.localize(dt, is_dst=None)
                dt = localized.astimezone(pytz.utc).replace(tzinfo=None)
            except Exception:
                pass
        return dt

    @api.model
    def _get_valuation_moves(self, product_id, as_of_dt):
        """Return done stock moves for ``product_id`` up to ``as_of_dt``.

        Only moves that affect stock valuation (incoming or outgoing to/from
        valued internal locations) are returned, ordered by date then id.
        """
        domain = [
            ('product_id', '=', product_id),
            ('state', '=', 'done'),
            ('date', '<=', as_of_dt),
            '|', ('is_in', '=', True), ('is_out', '=', True),
        ]
        company = self.env.company
        if company:
            domain.append(('company_id', 'in', [company.id, False]))
        return self.env['stock.move'].search(domain, order='date, id')

    @api.model
    def _consume_moves_fifo(self, moves):
        """Process moves in order and return the remaining FIFO layers.

        Incoming moves (``is_in``) are appended to the FIFO queue.
        Outgoing moves (``is_out``) consume the oldest incoming layers
        first, proportionally reducing their remaining value.
        """
        fifo_layers = []  # list of dicts: {'qty': float, 'value': float}

        for move in moves:
            qty = move.quantity
            value = move.value or 0.0

            if move.is_in and qty > 0:
                # Incoming move - add to the back of the FIFO queue
                fifo_layers.append({'qty': qty, 'value': value})
            elif move.is_out and qty > 0:
                # Outgoing move - consume from the front of the queue
                to_consume = qty
                while to_consume > 0 and fifo_layers:
                    oldest = fifo_layers[0]
                    if oldest['qty'] <= to_consume:
                        to_consume -= oldest['qty']
                        fifo_layers.pop(0)
                    else:
                        # Partial consumption of the oldest layer
                        ratio = to_consume / oldest['qty']
                        oldest['qty'] -= to_consume
                        oldest['value'] -= ratio * oldest['value']
                        to_consume = 0.0

        return fifo_layers
