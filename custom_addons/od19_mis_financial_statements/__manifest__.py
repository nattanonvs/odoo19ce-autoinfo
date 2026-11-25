{
    "name": "OD19 MIS Financial Statements (Header Level)",
    "version": "19.0.1.2.0",
    "summary": "งบแสดงฐานะทางการเงิน งบกำไรขาดทุน งบกระแสเงินสด และงบประมาณเทียบผลจริง ระดับหัวข้อบัญชี (แบบ ค) บน OCA MIS Builder",
    "author": "TRAE",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "depends": [
        "mis_builder",
        "mis_builder_budget",
        "account",
    ],
    "data": [
        "data/mis_report_style.xml",
        "data/mis_report_balance_sheet.xml",
        "data/mis_report_profit_loss.xml",
        "data/mis_report_cash_flow.xml",
        "data/mis_report_instance.xml",
        "data/mis_report_instance_cash_flow.xml",
        "data/mis_report_budget.xml",
    ],
    "installable": True,
    "application": False,
}
