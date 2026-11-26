# -*- coding: utf-8 -*-
{
    "name": "OD19 Sales Stamp Report",
    "version": "19.0.1.0.0",
    "category": "Sales/Reporting",
    "summary": "Sales analysis by Stamp Date (year / quarter / month / department and more)",
    "description": """
OD19 Sales Stamp Report
=======================
An analytical report on confirmed sale orders (quotations) driven by the
``stamp_date`` captured on confirmation by ``od19_sales_confirm_stamp``.

Features
--------
* Live Pivot / Graph / List analysis, sliceable by year, quarter, month,
  week and day plus department, sale mode, project, customer, salesperson,
  sales team and who confirmed the order.
* Search filters with period presets (today / this month / this quarter /
  this year / last year).
* A wizard that prints a PDF summary and downloads a multi-sheet XLSX
  workbook (summary by period with YoY / MoM / share %, and breakdowns by
  department, customer, salesperson, sale mode and project).
* A curated data source so dashboard tiles can be built on the report.
    """,
    "author": "OD19 Custom",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "hr",
        "od19_sales_confirm_stamp",
        "od19_quotation_document_sequence",
        "od19_sales_project_context",
        "od19_dashboard",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/sales_stamp_report_security.xml",
        "data/dashboard_source_data.xml",
        "views/sales_stamp_report_views.xml",
        "views/sales_stamp_report_wizard_views.xml",
        "report/sales_stamp_report_reports.xml",
        "report/sales_stamp_report_pdf.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_sales_stamp_report/static/description/icon.svg",
}
