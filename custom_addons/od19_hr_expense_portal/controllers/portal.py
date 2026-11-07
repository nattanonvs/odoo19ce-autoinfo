# -*- coding: utf-8 -*-
"""Employee-facing portal routes for HR expense claims (``/my/expenses``).

The controller runs with the portal user's environment; ``.sudo()`` is used
only at the ORM level and every query is further restricted by the owner
domain ``[('employee_id.user_id', '=', request.env.user.id)]`` so a user can
never reach an expense belonging to somebody else.
"""

import logging

import requests

from odoo import _, fields, http
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)

_logger = logging.getLogger(__name__)

_MAP_PROVIDER_PARAM = 'od19_hr_expense_portal.map_provider'
_MAP_API_KEY_PARAM = 'od19_hr_expense_portal.map_api_key'
_ORS_GEOCODE_URL = 'https://api.openrouteservice.org/geocode/search'
_ORS_DIRECTIONS_URL = 'https://api.openrouteservice.org/v2/directions/driving-car'
_MAP_REQUEST_TIMEOUT = 10


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
            'map_enabled': self._map_config()[2],
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
    # Map distance (optional, disabled unless configured)
    # ------------------------------------------------------------
    def _map_config(self):
        """Read the map provider configuration from system parameters.

        Returns ``(provider, api_key, enabled)``. The feature stays off until
        an operator sets both a provider and an API key, so the button never
        appears out of the box (see spec K7).
        """
        params = request.env['ir.config_parameter'].sudo()
        provider = (params.get_param(_MAP_PROVIDER_PARAM) or 'none').strip().lower()
        api_key = params.get_param(_MAP_API_KEY_PARAM) or ''
        return provider, api_key, bool(provider != 'none' and api_key)

    def _compute_distance_km(self, provider, api_key, origin, destination):
        """Return the driving distance (km) between two free-text places."""
        if provider == 'ors':
            return self._distance_ors(api_key, origin, destination)
        raise UserError(_("Unsupported map provider: %s") % provider)

    def _distance_ors(self, api_key, origin, destination):
        """Distance via OpenRouteService (geocoding + driving-car route)."""

        def _geocode(text):
            response = requests.get(
                _ORS_GEOCODE_URL,
                params={'api_key': api_key, 'text': text, 'size': 1},
                timeout=_MAP_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            features = response.json().get('features') or []
            return features[0]['geometry']['coordinates'] if features else None

        start = _geocode(origin)
        end = _geocode(destination)
        if not start or not end:
            return 0.0
        response = requests.get(
            _ORS_DIRECTIONS_URL,
            params={
                'api_key': api_key,
                'start': '%s,%s' % (start[0], start[1]),
                'end': '%s,%s' % (end[0], end[1]),
            },
            timeout=_MAP_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        features = response.json().get('features') or []
        if not features:
            return 0.0
        return features[0]['properties']['summary']['distance'] / 1000.0

    @http.route(
        '/my/expenses/distance', type='http', auth='user', website=True,
        methods=['POST'],
    )
    def portal_my_expense_distance(self, **post):
        """Return the driving distance (km) as JSON for the map button.

        The API key never reaches the browser: the lookup runs server-side and
        the endpoint fails softly (JSON ``error``) so a network problem never
        blocks the portal (see spec §6.5).
        """
        provider, api_key, enabled = self._map_config()
        if not enabled:
            return request.make_json_response(
                {'error': _("Map distance is not configured.")}, status=400)
        origin = (post.get('origin') or '').strip()
        destination = (post.get('destination') or '').strip()
        if not origin or not destination:
            return request.make_json_response(
                {'error': _("Please fill in both origin and destination.")},
                status=400)
        try:
            distance_km = self._compute_distance_km(
                provider, api_key, origin, destination)
        except Exception as exc:  # noqa: BLE001 - never break the portal
            _logger.warning("Map distance lookup failed: %s", exc)
            return request.make_json_response(
                {'error': _("Could not calculate the distance.")}, status=502)
        return request.make_json_response({'distance_km': round(distance_km, 1)})

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
