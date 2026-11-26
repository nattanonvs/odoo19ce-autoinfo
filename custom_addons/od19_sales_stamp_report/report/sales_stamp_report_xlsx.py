import base64
import io

from odoo import models

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:  # pragma: no cover - openpyxl ships with Odoo
    openpyxl = None


class SalesStampReportXlsx(models.AbstractModel):
    """Build the multi-sheet XLSX workbook of the stamp date report."""

    _name = "report.od19_sales_stamp_report.sales_stamp_report_xlsx"
    _description = "Sales Stamp Date Report (XLSX)"

    def create_xlsx_report(self, docids, data):
        """Return the workbook as a base64-encoded string."""
        if openpyxl is None:
            raise RuntimeError("openpyxl is not installed")

        data = data or {}
        report_data = self.env["od19.sales.stamp.report.analysis"].build_report_data(
            data.get("filters")
        )

        workbook = openpyxl.Workbook()

        # ---- Summary by period -------------------------------------
        summary = workbook.active
        summary.title = "Summary by Period"
        headers = [
            "Period",
            "Orders",
            "Untaxed Amount",
            "Total Amount",
            "Share %",
            "Previous Year (Untaxed)",
            "YoY %",
            "Previous Period (Untaxed)",
            "MoM %",
        ]
        rows = [
            [
                row["label"],
                row["orders"],
                row["amount_untaxed"],
                row["amount_total"],
                self._pct(row["share_pct"]),
                row["prev_year_untaxed"],
                self._pct(row["yoy_pct"]),
                row["prev_period_untaxed"],
                self._pct(row["mom_pct"]),
            ]
            for row in report_data["period_rows"]
        ]
        totals = report_data["totals"]
        rows.append(
            [
                "Total",
                totals["orders"],
                totals["amount_untaxed"],
                totals["amount_total"],
                100.0,
                "",
                "",
                "",
                "",
            ]
        )
        self._write_sheet(summary, headers, rows)

        # ---- One sheet per dimension -------------------------------
        for table in report_data["dimension_tables"]:
            sheet = workbook.create_sheet(title=table["label"][:31])
            headers = [
                table["label"],
                "Orders",
                "Untaxed Amount",
                "Total Amount",
                "Share %",
                "Previous Year (Untaxed)",
                "YoY %",
            ]
            rows = [
                [
                    row["label"],
                    row["orders"],
                    row["amount_untaxed"],
                    row["amount_total"],
                    self._pct(row["share_pct"]),
                    row["prev_year_untaxed"],
                    self._pct(row["yoy_pct"]),
                ]
                for row in table["rows"]
            ]
            self._write_sheet(sheet, headers, rows)

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return base64.b64encode(buffer.read())

    @staticmethod
    def _pct(value):
        if value in (None, False):
            return ""
        return round(value, 2)

    def _write_sheet(self, sheet, headers, rows):
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="4F81BD", end_color="4F81BD", fill_type="solid"
        )
        header_alignment = Alignment(horizontal="center", vertical="center")

        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        for row_idx, row in enumerate(rows, start=2):
            for col_idx, value in enumerate(row, start=1):
                sheet.cell(row=row_idx, column=col_idx, value=value)

        for col_idx in range(1, len(headers) + 1):
            max_length = len(str(headers[col_idx - 1]))
            for row_idx in range(2, len(rows) + 2):
                cell_value = sheet.cell(row=row_idx, column=col_idx).value
                if cell_value is not None:
                    max_length = max(max_length, len(str(cell_value)))
            sheet.column_dimensions[
                openpyxl.utils.get_column_letter(col_idx)
            ].width = min(max_length + 2, 40)
