# -*- coding: utf-8 -*-
"""Main FIFO model.

Provides the monthly stock report cron job, XLSX report generation and
email sending. Inherits the FIFO valuation service so the computation
logic is centralized.
"""
import base64
import io
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    _logger.warning("openpyxl is not installed. Monthly stock report will not generate XLSX.")
    Workbook = None


class StockFifo(models.Model):
    _name = 'od19.stock.fifo'
    _inherit = 'od19.stock.fifo.service'
    _description = 'FIFO Stock Valuation'
    _order = 'od19_date desc, id desc'

    od19_product_id = fields.Many2one(
        'product.product',
        string='Product / สินค้า',
        required=True,
        ondelete='cascade',
        index=True,
    )
    od19_date = fields.Date(
        string='Valuation Date / วันที่ประเมิน',
        required=True,
        index=True,
    )
    od19_quantity = fields.Float(
        string='Quantity / จำนวน',
        digits='Product Unit of Measure',
    )
    od19_total_value = fields.Float(
        string='Total Value / มูลค่ารวม',
        digits='Account',
    )
    od19_unit_cost = fields.Float(
        string='Unit Cost / ต้นทุนต่อหน่วย',
        digits='Account',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company / บริษัท',
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # Cron: Monthly Stock Report Email
    # ------------------------------------------------------------------
    @api.model
    def _send_monthly_stock_report(self):
        """Cron action: compute FIFO valuation as of last day of previous
        month, generate an XLSX report and email it to the inventory
        manager / accounting.
        """
        today = fields.Date.today()
        # Last day of the previous month
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)

        return self.send_monthly_stock_report(as_of_date=last_of_prev_month)

    @api.model
    def send_monthly_stock_report(self, as_of_date=None):
        """Compute, generate and email the monthly FIFO stock report.

        :param as_of_date: date string or object. Defaults to last day of
                           the previous month.
        :return: True on success.
        """
        if as_of_date is None:
            today = fields.Date.today()
            first_of_this_month = today.replace(day=1)
            as_of_date = first_of_this_month - timedelta(days=1)

        if isinstance(as_of_date, str):
            as_of_date = fields.Date.from_string(as_of_date)

        _logger.info("Generating monthly FIFO stock report as of %s", as_of_date)

        # Get all storable products that have stock moves (to keep the report relevant)
        products = self.env['product.product'].search([
            ('type', '=', 'consu'),
            ('is_storable', '=', True),
        ])

        rows = []
        total_qty = 0.0
        total_value = 0.0
        for product in products:
            valuation = self.compute_fifo_valuation(product.id, as_of_date)
            qty = valuation['quantity_on_hand']
            value = valuation['total_value']
            unit_cost = valuation['unit_cost']
            rows.append({
                'product_id': product.id,
                'product_name': product.display_name,
                'default_code': product.default_code or '',
                'quantity': qty,
                'total_value': value,
                'unit_cost': unit_cost,
            })
            total_qty += qty
            total_value += value

        # Generate XLSX attachment
        xlsx_data = self._generate_xlsx_report(rows, as_of_date, total_qty, total_value)

        # Send email
        self._send_report_email(as_of_date, xlsx_data, total_qty, total_value, len(rows))

        _logger.info(
            "Monthly FIFO stock report sent for %s. Products: %d, Total Qty: %.2f, Total Value: %.2f",
            as_of_date, len(rows), total_qty, total_value,
        )
        return True

    # ------------------------------------------------------------------
    # XLSX report generation
    # ------------------------------------------------------------------
    @api.model
    def _generate_xlsx_report(self, rows, as_of_date, total_qty, total_value):
        """Build an XLSX workbook and return its base64-encoded content."""
        if Workbook is None:
            raise UserError(_(
                "openpyxl is not installed. Please install it to generate "
                "the monthly stock report (pip install openpyxl)."
            ))

        wb = Workbook()
        ws = wb.active
        ws.title = _("Stock Valuation")

        # Title
        ws.merge_cells('A1:F1')
        title_cell = ws['A1']
        title_cell.value = _("Monthly FIFO Stock Valuation Report / รายงานมูลค่าสินค้า FIFO ประจำเดือน")
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal='center', vertical='center')

        ws.merge_cells('A2:F2')
        ws['A2'].value = _("As of / ณ วันที่: %s") % (as_of_date.strftime('%Y-%m-%d'),)
        ws['A2'].alignment = Alignment(horizontal='center')

        # Headers
        headers = [
            _("Product Code / รหัสสินค้า"),
            _("Product Name / ชื่อสินค้า"),
            _("Quantity / จำนวน"),
            _("Unit Cost / ต้นทุนต่อหน่วย"),
            _("Total Value / มูลค่ารวม"),
            _("Company / บริษัท"),
        ]
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        header_row = 4
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # Data rows
        data_start = header_row + 1
        company_name = self.env.company.name
        for row_idx, row in enumerate(rows, start=data_start):
            ws.cell(row=row_idx, column=1, value=row['default_code'])
            ws.cell(row=row_idx, column=2, value=row['product_name'])
            ws.cell(row=row_idx, column=3, value=row['quantity'])
            ws.cell(row=row_idx, column=4, value=row['unit_cost'])
            ws.cell(row=row_idx, column=5, value=row['total_value'])
            ws.cell(row=row_idx, column=6, value=company_name)

        # Summary totals
        total_row = data_start + len(rows) + 1
        ws.cell(row=total_row, column=2, value=_("Total / รวมทั้งหมด")).font = Font(bold=True)
        ws.cell(row=total_row, column=3, value=total_qty).font = Font(bold=True)
        ws.cell(row=total_row, column=5, value=total_value).font = Font(bold=True)

        # Column widths
        widths = [18, 40, 14, 18, 18, 20]
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width

        # Number formats
        for row in ws.iter_rows(min_row=data_start, max_row=total_row, min_col=3, max_col=5):
            for cell in row:
                cell.number_format = '#,##0.00'

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return base64.b64encode(output.read())

    # ------------------------------------------------------------------
    # Email sending
    # ------------------------------------------------------------------
    @api.model
    def _send_report_email(self, as_of_date, xlsx_data, total_qty, total_value, product_count):
        """Send the stock report email with the XLSX attachment."""
        template = self.env.ref('od19_stock_fifo.mail_template_monthly_stock_report', raise_if_not_found=False)
        if not template:
            _logger.warning("Monthly stock report email template not found.")
            return False

        # Determine recipients: inventory manager + accounting
        recipient_emails = self._get_report_recipients()
        if not recipient_emails:
            _logger.warning("No recipients configured for monthly stock report.")
            return False

        # Compose context for the template
        ctx = dict(self.env.context)
        ctx.update({
            'as_of_date': as_of_date.strftime('%Y-%m-%d'),
            'total_qty': total_qty,
            'total_value': total_value,
            'product_count': product_count,
            'company_name': self.env.company.name,
        })

        # Build attachment
        attachment_name = _("Stock_Valuation_Report_%s.xlsx") % (as_of_date.strftime('%Y%m%d'),)
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'datas': xlsx_data,
            'type': 'binary',
            'res_model': 'od19.stock.fifo',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Send email
        mail_values = {
            'subject': _('Monthly FIFO Stock Valuation Report - %s') % (as_of_date.strftime('%Y-%m-%d'),),
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': ','.join(recipient_emails),
            'attachment_ids': [(6, 0, [attachment.id])],
        }

        template.with_context(**ctx).send_mail(
            self.env.company.id,
            email_values=mail_values,
            force_send=True,
            raise_exception=False,
        )
        return True

    @api.model
    def _get_report_recipients(self):
        """Return a list of email addresses to send the report to.

        Looks for the inventory manager (group_stock_manager) and
        accounting users (group_account_invoice). Falls back to the
        company email.
        """
        recipients = set()

        # Inventory managers
        inv_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if inv_group:
            for user in inv_group.users:
                if user.email:
                    recipients.add(user.email)

        # Accountants
        acc_group = self.env.ref('account.group_account_invoice', raise_if_not_found=False)
        if acc_group:
            for user in acc_group.users:
                if user.email:
                    recipients.add(user.email)

        if not recipients and self.env.company.email:
            recipients.add(self.env.company.email)

        return list(recipients)


class ResCompany(models.Model):
    _inherit = 'res.company'

    od19_stock_revaluation_account_id = fields.Many2one(
        'account.account',
        string='Stock Revaluation Account / บัญชีปรับมูลค่าสินค้า',
        company_dependent=True,
        help='Account used for the counter-side of BF (ยกมา) stock revaluations.',
    )
