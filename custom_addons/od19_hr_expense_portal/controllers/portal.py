# -*- coding: utf-8 -*-
"""Employee-facing portal routes for HR expense claims (``/my/expenses``).

The controller runs with the portal user's environment; ``.sudo()`` is used
only at the ORM level and every query is further restricted by the owner
domain ``[('employee_id.user_id', '=', request.env.user.id)]`` so a user can
never reach an expense belonging to somebody else.
"""

import logging

from odoo import _, fields, http
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)

_logger = logging.getLogger(__name__)


class Od19HrExpensePortal(CustomerPortal):

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _expense_domain(self):
        """Restrict expenses to the ones owned by the current portal user."""
        return [('employee_id.user_id', '=', request.env.user.id)]

    def _expense_check_access(self, expense_id):
        """Return the expense if it belongs to the current user, else raise."""
        expense = request.env['hr.expense'].sudo().search(
            self._expense_domain() + [('id', '=', expense_id)], limit=1)
        if not expense:
            raise MissingError(
                _("The expense does not exist or you do not have access to it."))
        return expense

    def _prepare_expense_form_values(self):
        """Values needed to render the submission form."""
        employee = request.env.user.employee_id
        Vehicle = request.env['od19.employee.vehicle'].sudo()
        return {
            'employee': employee,
            'categories': request.env['product.product'].sudo().search(
                [('can_be_expensed', '=', True)], order='name'),
            'vehicles': Vehicle.search([('employee_id', '=', employee.id)])
            if employee else Vehicle.browse(),
            'today': fields.Date.context_today(request.env.user),
            'form': {},
        }

    def _expense_form_to_wizard_vals(self, post):
        """Translate the posted form into ``od19.expense.quick.create`` vals.

        ``employee_id`` is always forced to the current user's employee so the
        posted form cannot be used to file a claim on behalf of someone else.
        """
        def _int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return False

        def _float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        return {
            'employee_id': request.env.user.employee_id.id,
            'expense_category_id': _int(post.get('expense_category_id')),
            'expense_date': post.get('expense_date')
            or fields.Date.context_today(request.env.user),
            'description': post.get('description'),
            'amount': _float(post.get('amount')),
            'distance_km': _float(post.get('distance_km')),
            'vehicle_id': _int(post.get('vehicle_id')),
            'origin': post.get('origin'),
            'destination': post.get('destination'),
            'submit_now': bool(post.get('submit_now')),
        }

    # ------------------------------------------------------------
    # My Expenses
    # ------------------------------------------------------------
    @http.route(
        ['/my/expenses', '/my/expenses/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_expenses(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Expense = request.env['hr.expense'].sudo()
        domain = self._expense_domain()

        pager = portal_pager(
            url='/my/expenses',
            url_args={},
            total=Expense.search_count(domain),
            page=page,
            step=self._items_per_page,
        )
        expenses = Expense.search(
            domain, order='date desc, id desc',
            limit=self._items_per_page, offset=pager['offset'],
        )
        values.update({
            'expenses': expenses,
            'page_name': 'expense',
            'pager': pager,
            'default_url': '/my/expenses',
        })
        return request.render(
            'od19_hr_expense_portal.portal_my_expenses', values)

    @http.route(
        '/my/expenses/new', type='http', auth='user', website=True,
        methods=['GET'],
    )
    def portal_my_expense_new(self, **kw):
        if not request.env.user.employee_id:
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_expense_form_values())
        values['page_name'] = 'expense'
        return request.render(
            'od19_hr_expense_portal.portal_my_expense_new', values)

    @http.route(
        '/my/expenses/new', type='http', auth='user', website=True,
        methods=['POST'],
    )
    def portal_my_expense_new_post(self, **post):
        if not request.env.user.employee_id:
            return request.redirect('/my')

        vals = self._expense_form_to_wizard_vals(post)
        try:
            wizard = request.env['od19.expense.quick.create'].sudo().create(vals)
            action = wizard.action_create_expense()
        except (UserError, ValidationError) as exc:
            _logger.info("Portal expense submission rejected: %s", exc)
            values = self._prepare_portal_layout_values()
            values.update(self._prepare_expense_form_values())
            values.update({
                'page_name': 'expense',
                'error': exc.args[0] if exc.args else _(
                    "Unable to create the expense."),
                'form': vals,
            })
            return request.render(
                'od19_hr_expense_portal.portal_my_expense_new', values)
        return request.redirect('/my/expenses/%s' % action['res_id'])

    @http.route(
        '/my/expenses/<int:expense_id>', type='http', auth='user',
        website=True,
    )
    def portal_my_expense_detail(self, expense_id, **kw):
        try:
            expense = self._expense_check_access(expense_id)
        except MissingError:
            return request.not_found()
        values = self._prepare_portal_layout_values()
        values.update({
            'expense': expense,
            'page_name': 'expense',
        })
        return request.render(
            'od19_hr_expense_portal.portal_my_expense_detail', values)

    @http.route(
        '/my/expenses/<int:expense_id>/submit', type='http', auth='user',
        website=True, methods=['POST'],
    )
    def portal_my_expense_submit(self, expense_id, **post):
        try:
            expense = self._expense_check_access(expense_id)
        except MissingError:
            return request.not_found()
        if expense.state == 'draft':
            expense.action_submit()
        return request.redirect('/my/expenses/%s' % expense_id)
