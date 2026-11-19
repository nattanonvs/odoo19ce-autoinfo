import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 OCA Accounting Reports Tour
 *
 * Walks the user through the financial reporting suite provided by the OCA
 * `account_financial_report` module, reachable from
 * Accounting > Reporting > OCA accounting reports:
 *
 *  - General Ledger      - all journal items per account
 *  - Journal Ledger      - all journal items per journal
 *  - Trial Balance       - debit/credit balance per account
 *  - Open Items          - still-open receivables / payables
 *  - Aged Partner Balance- open items bucketed by age
 *  - VAT Report          - tax summary by period
 *
 * Every report is an `ir.actions.act_window` with `target = new`, so picking a
 * menu entry opens its parameter wizard as a dialog. The tour opens each wizard,
 * points at its filters and closes it again without printing.
 */
const OCAR_GROUP = ".dropdown-menu .dropdown-header:text('OCA accounting reports')";

// `Taxes Balance` (OCA `account_tax_balance`) sits directly under Reporting,
// next to the "OCA accounting reports" group rather than inside it.
const openReportingItem = (label, description) => [
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
            "Set the <b>period</b> and the filters, then use <b>Open Taxes</b> / <b>Print</b> to render it."
        )),
        run: "click",
        timeout: 20000,
    },
    {
        trigger: ".o_dialog .modal-header .btn-close",
        content: markup(_t("Close the dialog.")),
        tooltipPosition: "left",
        run: "click",
    },
];

const openOcaReport = (label, description) => [
    {
        trigger: navSection("Reporting"),
        content: markup(_t("Open the <b>Reporting</b> menu.")),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: OCAR_GROUP,
        content: markup(_t("Open the <b>OCA accounting reports</b> group.")),
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
        // The wizard opens asynchronously as a dialog (`target = new`).
        trigger: ".o_dialog .o_form_view",
        content: markup(_t(
            "Set the <b>period</b> and the filters, then use <b>Print</b> to render the report."
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

registry.category("web_tour.tours").add("od19_accounting_oca_reports_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the <b>OCA accounting reports</b>: the statutory financial " +
                "reports shipped with the OCA reporting suite."
            ))
        ),

        ...openOcaReport(
            "General Ledger",
            markup(_t(
                "Open the <b>General Ledger</b>: every journal item grouped by account, " +
                "with opening/closing balances."
            ))
        ),
        ...openOcaReport(
            "Journal Ledger",
            markup(_t(
                "Open the <b>Journal Ledger</b>: the same detail grouped by <b>journal</b>."
            ))
        ),
        ...openOcaReport(
            "Trial Balance",
            markup(_t(
                "Open the <b>Trial Balance</b>: the debit/credit balance of each account for " +
                "the period."
            ))
        ),
        ...openOcaReport(
            "Open Items",
            markup(_t(
                "Open <b>Open Items</b>: receivables and payables that are still unsettled."
            ))
        ),
        ...openOcaReport(
            "Aged Partner Balance",
            markup(_t(
                "Open the <b>Aged Partner Balance</b>: open items bucketed by age (0-30, " +
                "30-60, 60-90, 90+ days)."
            ))
        ),
        ...openOcaReport(
            "VAT Report",
            markup(_t(
                "Open the <b>VAT Report</b>: the tax summary by period for VAT returns."
            ))
        ),
        ...openReportingItem(
            "Taxes Balance",
            markup(_t(
                "Open <b>Taxes Balance</b>: the balance of each tax account, per period, " +
                "as a drill-down on the tax entries."
            ))
        ),

        {
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "OCA accounting reports complete! These cover <b>General Ledger</b>, " +
                "<b>Journal Ledger</b>, <b>Trial Balance</b>, <b>Open Items</b>, " +
                "<b>Aged Partner Balance</b>, <b>VAT Report</b> and <b>Taxes Balance</b>."
            )),
            run: "click",
        },
    ],
});
