import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Jasper accounting documents Tour
 *
 * Covers the Jasper `(J-Report OD15)` document-style reports that live directly
 * under Accounting > Reporting (alongside the financial statements covered by
 * `accounting_jasper_finance_tour.js`):
 *
 *  - AR/AP Card, Invoice Condition, Invoice Actual Due Date, Credit/Debit Note
 *  - Billing Condition, Prepayment Condition
 *  - Payment Down Payment, Payment Inbound, Payment Outbound
 *  - Receipt Report, Cheque Balance Report
 *
 * Each menu entry is an `ir.actions.act_window` with `target = new`, so opening
 * it shows the parameter wizard as a dialog. The tour opens each wizard, points
 * at its filters and closes it again without printing.
 */
const openJasperReport = (label, description) => [
    {
        trigger: navSection("Reporting"),
        content: markup(_t("Open the <b>Reporting</b> menu.")),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: navItem(label),
        content: description,
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: ".o_dialog .o_form_view",
        content: markup(_t(
            "Set the <b>date range</b> and the other filters, then use <b>Print</b> to render the Jasper report."
        )),
        run: "click",
        timeout: 20000,
    },
    {
        trigger: ".o_dialog .modal-header .btn-close",
        content: markup(_t("Close the wizard.")),
        tooltipPosition: "left",
        run: "click",
    },
];

registry.category("web_tour.tours").add("od19_accounting_jasper_docs_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the <b>Jasper document reports</b> under Accounting > Reporting " +
                "(AR/AP cards, invoices and payments)."
            ))
        ),
        ...openJasperReport(
            "(J-Report OD15) AR/AP Card",
            markup(_t("Open the <b>AR/AP Card</b>: the statement of a partner's receivables and payables."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Invoice Condition",
            markup(_t("Open <b>Invoice Condition</b>: invoices grouped by their payment condition."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Invoice Actual Due Date",
            markup(_t("Open <b>Invoice Actual Due Date</b>: the real due date of each invoice."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Credit/Debit Note Report",
            markup(_t("Open the <b>Credit/Debit Note Report</b>: credit notes and debit notes for the period."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Billing Condition",
            markup(_t("Open <b>Billing Condition</b>: the billing schedule driven by the payment terms."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Prepayment Condition",
            markup(_t("Open <b>Prepayment Condition</b>: the down payments and prepayments on hand."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Payment Down Payment",
            markup(_t("Open <b>Payment Down Payment</b>: down payments received / paid."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Payment Inbound",
            markup(_t("Open <b>Payment Inbound</b>: incoming customer payments."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Payment Outbound",
            markup(_t("Open <b>Payment Outbound</b>: outgoing vendor payments."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Receipt Report",
            markup(_t("Open the <b>Receipt Report</b>: the payment receipts issued for the period."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Cheque Balance Report",
            markup(_t("Open the <b>Cheque Balance Report</b>: cheques received / issued and still uncleared."))
        ),
        {
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "Jasper document reports complete! Every <b>(J-Report OD15)</b> entry under " +
                "Reporting opens a parameter wizard that streams a JasperReport PDF."
            )),
            run: "click",
        },
    ],
});
