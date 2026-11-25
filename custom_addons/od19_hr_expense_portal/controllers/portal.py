# -*- coding: utf-8 -*-
"""Employee-facing portal routes for HR expense claims (``/my/expenses``).

The controller runs with the portal user's environment; ``.sudo()`` is used
only at the ORM level and every query is further restricted by the owner
domain ``[('employee_id.user_id', '=', request.env.user.id)]`` so a user can
never reach an expense belonging to somebody else.
"""

import base64
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
_ADVANCE_ACCOUNT_PARAM = 'od19_hr_expense_portal.advance_account_id'
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
        """Return the claim if it belongs to the current user, else raise."""
        claim = request.env['od19.expense.claim'].sudo().search(
            self._expense_domain() + [('id', '=', expense_id)], limit=1)
        if not claim:
            raise MissingError(
                _("The expense does not exist or you do not have access to it."))
        return claim

    def _prepare_expense_form_values(self):
        """Values needed to render the submission form."""
        employee = request.env.user.employee_id
        Vehicle = request.env['od19.employee.vehicle'].sudo()
        return {
            'employee': employee,
            'categories': request.env['product.product'].sudo().search(
                [('can_be_expensed', '=', True)], order='name'),
            'analytics': request.env['account.analytic.account'].sudo().search(
                [], order='name'),
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
            'analytic_account_id': _int(post.get('analytic_account_id')),
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
        Claim = request.env['od19.expense.claim'].sudo()
        domain = self._expense_domain()

        pager = portal_pager(
            url='/my/expenses',
            url_args={},
            total=Claim.search_count(domain),
            page=page,
            step=self._items_per_page,
        )
        expenses = Claim.search(
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
        '/my/expenses/help', type='http', auth='user', website=True,
    )
    def portal_my_expense_help(self, **kw):
        """Static in-portal user guide for filing an expense claim (Phase 4d)."""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'expense',
            'map_enabled': self._map_config()[2],
        })
        return request.render(
            'od19_hr_expense_portal.portal_my_expense_help', values)

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
        upload = request.httprequest.files.get('attachment')
        if upload and upload.filename:
            vals['attachment'] = base64.b64encode(upload.read())
            vals['attachment_filename'] = upload.filename
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
            claim = self._expense_check_access(expense_id)
        except MissingError:
            return request.not_found()
        values = self._prepare_portal_layout_values()
        values.update({
            'expense': claim,
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
            claim = self._expense_check_access(expense_id)
        except MissingError:
            return request.not_found()
        if claim.state == 'draft':
            claim.action_submit()
        return request.redirect('/my/expenses/%s' % expense_id)

    @http.route(
        '/my/expenses/<int:expense_id>/print', type='http', auth='user',
        website=True,
    )
    def portal_my_expense_print(self, expense_id, **kw):
        """Return the printable expense-claim document (PDF) for its owner.

        The claim is fetched through ``_expense_check_access`` (owner-only),
        then rendered in sudo so the portal user does not need back-office
        access to the analytic accounts referenced by the report.
        """
        try:
            claim = self._expense_check_access(expense_id)
        except MissingError:
            return request.not_found()
        pdf_content, _report_type = request.env[
            'ir.actions.report'
        ].sudo()._render_qweb_pdf(
            'od19_hr_expense_claim.od19_expense_claim_document', claim.ids)
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition',
                 'inline; filename="ExpenseClaim-%s.pdf"'
                 % (claim.name or claim.id)),
            ],
        )

    # ------------------------------------------------------------
    # My Advances (P3 — employee-facing cash-advance requests)
    # ------------------------------------------------------------
    def _advance_domain(self):
        """Restrict advances to the current user's own cash-advance claims."""
        return [
            ('employee_id.user_id', '=', request.env.user.id),
            ('claim_type', '=', 'advance'),
        ]

    def _advance_check_access(self, advance_id):
        """Return the advance if it belongs to the current user, else raise."""
        advance = request.env['od19.expense.claim'].sudo().search(
            self._advance_domain() + [('id', '=', advance_id)], limit=1)
        if not advance:
            raise MissingError(
                _("The advance does not exist or you do not have access to it."))
        return advance

    def _od19_default_advance_account(self, employee):
        """Resolve the employee-advance account used for portal requests.

        The employee never picks an accounting account: an operator may set
        ``od19_hr_expense_portal.advance_account_id`` (system parameter);
        otherwise the employee contact's payable account is used.
        """
        param = request.env['ir.config_parameter'].sudo().get_param(
            _ADVANCE_ACCOUNT_PARAM)
        Account = request.env['account.account'].sudo()
        if param:
            try:
                account = Account.browse(int(param)).exists()
            except (TypeError, ValueError):
                account = Account.browse()
            if account:
                return account
        partner = employee.work_contact_id or employee.user_id.partner_id
        return partner.property_account_payable_id

    def _prepare_advance_form_values(self):
        """Values needed to render the cash-advance request form."""
        return {
            'employee': request.env.user.employee_id,
            'today': fields.Date.context_today(request.env.user),
            'form': {},
        }

    @http.route(
        ['/my/advances', '/my/advances/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_advances(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Claim = request.env['od19.expense.claim'].sudo()
        domain = self._advance_domain()

        pager = portal_pager(
            url='/my/advances',
            url_args={},
            total=Claim.search_count(domain),
            page=page,
            step=self._items_per_page,
        )
        advances = Claim.search(
            domain, order='date desc, id desc',
            limit=self._items_per_page, offset=pager['offset'],
        )
        values.update({
            'advances': advances,
            'page_name': 'advance',
            'pager': pager,
            'default_url': '/my/advances',
        })
        return request.render(
            'od19_hr_expense_portal.portal_my_advances', values)

    @http.route(
        '/my/advances/new', type='http', auth='user', website=True,
        methods=['GET'],
    )
    def portal_my_advance_new(self, **kw):
        if not request.env.user.employee_id:
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_advance_form_values())
        values['page_name'] = 'advance'
        return request.render(
            'od19_hr_expense_portal.portal_my_advance_new', values)

    @http.route(
        '/my/advances/new', type='http', auth='user', website=True,
        methods=['POST'],
    )
    def portal_my_advance_new_post(self, **post):
        if not request.env.user.employee_id:
            return request.redirect('/my')
        employee = request.env.user.employee_id

        def _float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        vals = {
            'advance_date': post.get('advance_date')
            or fields.Date.context_today(request.env.user),
            'amount': _float(post.get('amount')),
            'purpose': (post.get('purpose') or '').strip(),
            'submit_now': bool(post.get('submit_now')),
        }
        error = None
        account = self._od19_default_advance_account(employee)
        if not account:
            error = _(
                "ยังไม่ได้ตั้งค่าบัญชีเงินทดรอง/ลูกหนี้พนักงาน "
                "กรุณาติดต่อฝ่ายบัญชี")
        claim = None
        if not error:
            try:
                claim = request.env['od19.expense.claim'].sudo().create({
                    'employee_id': employee.id,
                    'company_id': request.env.company.id,
                    'claim_type': 'advance',
                    'claim_source': 'self_service',
                    'payment_mode': 'company_account',
                    'date': vals['advance_date'],
                    'amount': vals['amount'],
                    'purpose': vals['purpose'],
                    'advance_account_id': account.id,
                })
                if vals['submit_now']:
                    claim.action_submit()
            except (UserError, ValidationError) as exc:
                _logger.info("Portal advance submission rejected: %s", exc)
                error = exc.args[0] if exc.args else _(
                    "Unable to create the advance request.")
        if error:
            values = self._prepare_portal_layout_values()
            values.update(self._prepare_advance_form_values())
            values.update({
                'page_name': 'advance',
                'error': error,
                'form': vals,
            })
            return request.render(
                'od19_hr_expense_portal.portal_my_advance_new', values)
        return request.redirect('/my/advances/%s' % claim.id)

    @http.route(
        '/my/advances/<int:advance_id>', type='http', auth='user',
        website=True,
    )
    def portal_my_advance_detail(self, advance_id, **kw):
        try:
            advance = self._advance_check_access(advance_id)
        except MissingError:
            return request.not_found()
        values = self._prepare_portal_layout_values()
        values.update({
            'advance': advance,
            'page_name': 'advance',
        })
        return request.render(
            'od19_hr_expense_portal.portal_my_advance_detail', values)

    @http.route(
        '/my/advances/<int:advance_id>/submit', type='http', auth='user',
        website=True, methods=['POST'],
    )
    def portal_my_advance_submit(self, advance_id, **post):
        try:
            advance = self._advance_check_access(advance_id)
        except MissingError:
            return request.not_found()
        if advance.state == 'draft':
            advance.action_submit()
        return request.redirect('/my/advances/%s' % advance_id)
