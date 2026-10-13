from odoo import _, api, fields, models


class MoneyInReportBuilder(models.AbstractModel):
    _name = "od19.money.in.report.builder"
    _description = "OD19 Money In Report Builder"

    def _build_run_name(self, wizard):
        wizard.ensure_one()
        return _("Money In %s to %s") % (wizard.date_from, wizard.date_to)

    def _prepare_run_vals_from_wizard(self, wizard):
        wizard.ensure_one()
        return {
            "name": self._build_run_name(wizard),
            "company_id": wizard.company_id.id,
            "date_from": wizard.date_from,
            "date_to": wizard.date_to,
            "phase": wizard.phase,
            "generated_by": self.env.user.id,
            "generated_at": fields.Datetime.now(),
            "partner_ids": [(6, 0, wizard.partner_ids.ids)],
            "salesperson_ids": [(6, 0, wizard.salesperson_ids.ids)],
            "project_ids": [(6, 0, wizard.project_ids.ids)],
            "product_categ_ids": [(6, 0, wizard.product_categ_ids.ids)],
            "job_type_values": wizard.job_type_values,
            "notes": _("Generated from wizard filters."),
        }

    def _get_optional_value(self, record, field_name):
        if not record:
            return False
        try:
            return getattr(record, field_name)
        except AttributeError:
            return False

    def _get_invoice_domain(self, wizard):
        wizard.ensure_one()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", wizard.date_from),
            ("invoice_date", "<=", wizard.date_to),
            ("company_id", "=", wizard.company_id.id),
        ]
        if wizard.partner_ids:
            domain.append(("partner_id", "in", wizard.partner_ids.ids))
        return domain

    def _get_phase2_invoice_domain(self, wizard):
        wizard.ensure_one()
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", wizard.company_id.id),
        ]
        if wizard.partner_ids:
            domain.append(("partner_id", "in", wizard.partner_ids.ids))
        return domain

    def _get_sale_order_data(self, invoice, invoice_line):
        sale_order_line = invoice_line.sale_line_ids[:1]
        if sale_order_line:
            return sale_order_line.order_id, sale_order_line
        return self.env["sale.order"], self.env["sale.order.line"]

    def _resolve_project(self, invoice, sale_order):
        for record, field_name in (
            (invoice, "project_id"),
            (invoice, "customer_project_from_sale"),
            (sale_order, "customer_project"),
        ):
            value = self._get_optional_value(record, field_name)
            if value:
                return value
        return self.env["project.project"]

    def _resolve_salesperson(self, invoice, sale_order):
        return (
            self._get_optional_value(invoice, "invoice_user_id")
            or self._get_optional_value(sale_order, "user_id")
            or self.env["res.users"]
        )

    def _resolve_project_type_name(self, project):
        project_type = self._get_optional_value(project, "type_id")
        if project_type:
            return project_type.display_name or project_type.name
        return False

    def _is_cost_reliable(self, product):
        return bool(product and product.standard_price > 0)

    def _convert_amount_to_company_currency(self, report_run, invoice, amount):
        company = report_run.company_id
        source_currency = invoice.currency_id or company.currency_id
        conversion_date = invoice.invoice_date or fields.Date.context_today(self)
        return source_currency._convert(
            amount,
            company.currency_id,
            company,
            conversion_date,
        )

    def _convert_sale_order_amount_to_company_currency(self, report_run, sale_order):
        if not sale_order:
            return False
        company = report_run.company_id
        source_currency = sale_order.currency_id or company.currency_id
        conversion_date = (
            fields.Date.to_date(sale_order.date_order)
            if sale_order.date_order
            else fields.Date.context_today(self)
        )
        return source_currency._convert(
            sale_order.amount_total,
            company.currency_id,
            company,
            conversion_date,
        )

    def _get_customer_reference(self, sale_order):
        return (
            self._get_optional_value(sale_order, "customer_reference")
            or self._get_optional_value(sale_order, "client_order_ref")
            or False
        )

    def _get_company_currency_cost(self, report_run, product, quantity):
        standard_price = product.with_company(report_run.company_id).standard_price
        return standard_price * quantity

    def _line_matches_wizard_filters(self, wizard, invoice_line, project, salesperson):
        if wizard.salesperson_ids and (
            not salesperson or salesperson not in wizard.salesperson_ids
        ):
            return False
        if wizard.project_ids and (not project or project not in wizard.project_ids):
            return False
        if wizard.product_categ_ids and (
            not invoice_line.product_id.categ_id
            or invoice_line.product_id.categ_id not in wizard.product_categ_ids
        ):
            return False
        if wizard.job_type_values:
            job_type = self._get_optional_value(project, "job_type") or "unknown"
            if job_type != wizard.job_type_values:
                return False
        return True

    def _build_line_values(
        self,
        report_run,
        invoice,
        invoice_line,
        sale_order_line,
        sale_order,
        project,
        salesperson,
    ):
        stamp_date = self._get_optional_value(sale_order, "stamp_date") or False
        customer_reference = self._get_customer_reference(sale_order)
        sale_order_amount = self._convert_sale_order_amount_to_company_currency(
            report_run, sale_order
        )
        cycle_start_date = stamp_date or invoice.invoice_date
        project_type_name = self._resolve_project_type_name(project)
        product = invoice_line.product_id
        recognized_cost = False
        cost_preliminary_available = self._is_cost_reliable(
            product.with_company(report_run.company_id)
        )
        if cost_preliminary_available:
            recognized_cost = self._get_company_currency_cost(
                report_run, product, invoice_line.quantity
            )
        return {
            "run_id": report_run.id,
            "company_id": report_run.company_id.id,
            "partner_id": invoice.partner_id.id,
            "salesperson_id": salesperson.id if salesperson else False,
            "project_id": project.id if project else False,
            "project_job_type": self._get_optional_value(project, "job_type")
            or "unknown",
            "project_type_name": project_type_name,
            "product_id": product.id,
            "product_categ_id": product.categ_id.id,
            "invoice_id": invoice.id,
            "invoice_line_id": invoice_line.id,
            "invoice_date": invoice.invoice_date,
            "stamp_date": stamp_date,
            "customer_reference": customer_reference,
            "sale_order_id": sale_order.id if sale_order else False,
            "sale_order_line_id": sale_order_line.id if sale_order_line else False,
            "sale_order_amount": sale_order_amount,
            "recognized_amount": self._convert_amount_to_company_currency(
                report_run,
                invoice,
                invoice_line.price_subtotal,
            ),
            "recognized_cost": recognized_cost,
            "cost_preliminary_available": cost_preliminary_available,
            "cycle_start_date": cycle_start_date,
            "cycle_end_date": invoice.invoice_date,
            "recognition_mode": "invoice_proxy",
            "phase": report_run.phase,
            "is_preliminary_profit": True,
        }

    def _get_invoice_product_lines(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.product_id and line.display_type in (False, "", "product")
        )

    def _get_phase2_bridge_row(self, wizard, invoice):
        for invoice_line in self._get_invoice_product_lines(invoice):
            sale_order, sale_order_line = self._get_sale_order_data(invoice, invoice_line)
            project = self._resolve_project(invoice, sale_order)
            salesperson = self._resolve_salesperson(invoice, sale_order)
            if self._line_matches_wizard_filters(
                wizard, invoice_line, project, salesperson
            ):
                return (
                    invoice_line,
                    sale_order_line,
                    sale_order,
                    project,
                    salesperson,
                )
        return False

    def _get_phase2_profit_snapshot(self, report_run, invoice):
        invoice_lines = self._get_invoice_product_lines(invoice)
        recognized_amount = self._convert_amount_to_company_currency(
            report_run,
            invoice,
            sum(invoice_lines.mapped("price_subtotal")),
        )
        cost_preliminary_available = bool(invoice_lines) and all(
            self._is_cost_reliable(
                line.product_id.with_company(report_run.company_id)
            )
            for line in invoice_lines
        )
        recognized_cost = False
        if cost_preliminary_available:
            recognized_cost = sum(
                self._get_company_currency_cost(
                    report_run, line.product_id, line.quantity
                )
                for line in invoice_lines
            )
        return recognized_amount, recognized_cost, cost_preliminary_available

    def _get_phase2_event_date(self, partial, counterpart_move):
        payment = counterpart_move.origin_payment_id
        if payment and payment.date:
            return payment.date
        if counterpart_move.date:
            return counterpart_move.date
        return partial.max_date

    def _get_phase2_event_amount(self, invoice_line, partial):
        if partial.debit_move_id == invoice_line:
            return partial.debit_amount_currency or partial.amount
        return partial.credit_amount_currency or partial.amount

    def _get_phase2_cash_events(self, wizard, invoice):
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        )
        sale_types = set(self.env["account.move"].get_sale_types(include_receipts=True))
        events = []
        seen_keys = set()
        for invoice_line in receivable_lines:
            partials = invoice_line.matched_debit_ids | invoice_line.matched_credit_ids
            for partial in partials:
                counterpart_line = (
                    partial.credit_move_id
                    if partial.debit_move_id == invoice_line
                    else partial.debit_move_id
                )
                counterpart_move = counterpart_line.move_id
                if counterpart_move == invoice:
                    continue
                event_date = self._get_phase2_event_date(partial, counterpart_move)
                if (
                    not event_date
                    or event_date < wizard.date_from
                    or event_date > wizard.date_to
                ):
                    continue
                event_key = (
                    partial.id,
                    counterpart_line.id,
                )
                if event_key in seen_keys:
                    continue
                seen_keys.add(event_key)
                amount = abs(self._get_phase2_event_amount(invoice_line, partial))
                is_refund = counterpart_move.move_type in sale_types and (
                    counterpart_move.move_type != "out_invoice"
                )
                events.append(
                    {
                        "partial": partial,
                        "counterpart_line": counterpart_line,
                        "counterpart_move": counterpart_move,
                        "payment_date": event_date,
                        "reconcile_date": partial.max_date,
                        "paid_amount": 0.0 if is_refund else amount,
                        "refund_amount": amount if is_refund else 0.0,
                    }
                )
        events.sort(key=lambda event: (event["payment_date"], event["partial"].id))
        return events

    def _build_phase2_line_values(
        self,
        wizard,
        report_run,
        invoice,
        invoice_line,
        sale_order_line,
        sale_order,
        project,
        salesperson,
        event,
    ):
        stamp_date = self._get_optional_value(sale_order, "stamp_date") or False
        project_type_name = self._resolve_project_type_name(project)
        product = invoice_line.product_id
        recognized_amount, recognized_cost, cost_preliminary_available = (
            self._get_phase2_profit_snapshot(report_run, invoice)
        )
        return {
            "run_id": report_run.id,
            "company_id": report_run.company_id.id,
            "partner_id": invoice.partner_id.id,
            "salesperson_id": salesperson.id if salesperson else False,
            "project_id": project.id if project else False,
            "project_job_type": self._get_optional_value(project, "job_type")
            or "unknown",
            "project_type_name": project_type_name,
            "product_id": product.id if product else False,
            "product_categ_id": product.categ_id.id
            if product and product.categ_id
            else False,
            "invoice_id": invoice.id,
            "invoice_line_id": invoice_line.id if invoice_line else False,
            "invoice_date": invoice.invoice_date,
            "stamp_date": stamp_date,
            "customer_reference": self._get_customer_reference(sale_order),
            "sale_order_id": sale_order.id if sale_order else False,
            "sale_order_line_id": sale_order_line.id if sale_order_line else False,
            "sale_order_amount": self._convert_sale_order_amount_to_company_currency(
                report_run, sale_order
            ),
            "recognized_amount": recognized_amount,
            "recognized_cost": recognized_cost,
            "cost_preliminary_available": cost_preliminary_available,
            "cycle_start_date": stamp_date or invoice.invoice_date,
            "cycle_end_date": event["payment_date"],
            "payment_date": event["payment_date"],
            "reconcile_date": event["reconcile_date"],
            "paid_amount": event["paid_amount"],
            "refund_amount": event["refund_amount"],
            "recognition_mode": "cash_based",
            "phase": report_run.phase,
            "is_preliminary_profit": True,
            "is_invoice_bridged_dimension": True,
        }

    def _get_phase2_matching_rows(self, wizard):
        wizard.ensure_one()
        invoices = self.env["account.move"].search(self._get_phase2_invoice_domain(wizard))
        candidate_invoice_ids = set()
        matching_rows = []
        for invoice in invoices:
            events = self._get_phase2_cash_events(wizard, invoice)
            if events:
                candidate_invoice_ids.add(invoice.id)
            bridge_row = self._get_phase2_bridge_row(wizard, invoice)
            if not bridge_row:
                continue
            (
                invoice_line,
                sale_order_line,
                sale_order,
                project,
                salesperson,
            ) = bridge_row
            for event in events:
                matching_rows.append(
                    (
                        invoice,
                        invoice_line,
                        sale_order_line,
                        sale_order,
                        project,
                        salesperson,
                        event,
                    )
                )
        return invoices, candidate_invoice_ids, matching_rows

    def _get_matching_rows(self, wizard):
        wizard.ensure_one()
        invoices = self.env["account.move"].search(self._get_invoice_domain(wizard))
        matching_rows = []
        for invoice in invoices:
            invoice_lines = invoice.invoice_line_ids.filtered(
                lambda line: line.product_id and line.display_type in (False, "", "product")
            )
            for invoice_line in invoice_lines:
                sale_order, sale_order_line = self._get_sale_order_data(
                    invoice, invoice_line
                )
                project = self._resolve_project(invoice, sale_order)
                salesperson = self._resolve_salesperson(invoice, sale_order)
                if not self._line_matches_wizard_filters(
                    wizard, invoice_line, project, salesperson
                ):
                    continue
                matching_rows.append(
                    (
                        invoice,
                        invoice_line,
                        sale_order_line,
                        sale_order,
                        project,
                        salesperson,
                    )
                )
        return invoices, matching_rows

    @api.model
    def get_preview_counts(self, wizard):
        wizard.ensure_one()
        if wizard.phase == "phase2_cash_invoice_based":
            _invoices, candidate_invoice_ids, matching_rows = (
                self._get_phase2_matching_rows(wizard)
            )
            matching_invoice_ids = {row[0].id for row in matching_rows}
            return {
                "invoice_candidate_count": len(candidate_invoice_ids),
                "matching_invoice_count": len(matching_invoice_ids),
                "matching_line_count": len(matching_rows),
            }
        invoices, matching_rows = self._get_matching_rows(wizard)
        matching_invoice_ids = {row[0].id for row in matching_rows}
        return {
            "invoice_candidate_count": len(invoices),
            "matching_invoice_count": len(matching_invoice_ids),
            "matching_line_count": len(matching_rows),
        }

    @api.model
    def create_run_from_wizard(self, wizard):
        wizard.ensure_one()
        report_run = self.env["od19.money.in.report.run"].create(
            self._prepare_run_vals_from_wizard(wizard)
        )

        line_values = []
        if wizard.phase == "phase2_cash_invoice_based":
            _invoices, _candidate_invoice_ids, matching_rows = (
                self._get_phase2_matching_rows(wizard)
            )
            for (
                invoice,
                invoice_line,
                sale_order_line,
                sale_order,
                project,
                salesperson,
                event,
            ) in matching_rows:
                line_values.append(
                    self._build_phase2_line_values(
                        wizard,
                        report_run,
                        invoice,
                        invoice_line,
                        sale_order_line,
                        sale_order,
                        project,
                        salesperson,
                        event,
                    )
                )
        else:
            _invoices, matching_rows = self._get_matching_rows(wizard)
            for (
                invoice,
                invoice_line,
                sale_order_line,
                sale_order,
                project,
                salesperson,
            ) in matching_rows:
                line_values.append(
                    self._build_line_values(
                        report_run,
                        invoice,
                        invoice_line,
                        sale_order_line,
                        sale_order,
                        project,
                        salesperson,
                    )
                )

        if line_values:
            self.env["od19.money.in.report.line"].create(line_values)
        report_run.status = "done"
        return report_run
