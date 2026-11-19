import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Jasper Financial Reports Tour
 *
 * Walks the user through the financial statement wizards generated on top of
 * JasperReports (module `od19_reporting_jasper`). They all live directly under
 * Accounting > Reporting and their labels share the "(J-Report OD15)" prefix.
 *
 *  - (J-Report OD15) General Ledger
 *  - (J-Report OD15) Trial Balance
 *  - (J-Report OD15) Profit and Loss
 *  - (J-Report OD15) Balance Sheet
 *  - (J-Report OD15) AR/AP Aging
 *  - (J-Report OD15) Tax Invoice Report
 *  - (J-Report OD15) Sales Tax Report
 *  - (J-Report OD15) Purchase Tax Report
 *
 * Each entry is an `ir.actions.act_window` with `target = new`: the tour opens
 * its parameter wizard as a dialog, points at the filters and closes it again.
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
        // The wizard opens asynchronously as a dialog (`target = new`).
        trigger: ".o_dialog .o_form_view",
        content: markup(_t(
            "Set the <b>date range</b> and the other filters, then use <b>Print</b> to render " +
            "the Jasper report."
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

registry.category("web_tour.tours").add("od19_accounting_jasper_finance_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the <b>Jasper financial reports</b> under Accounting > Reporting."
            ))
        ),

        ...openJasperReport(
            "(J-Report OD15) General Ledger",
            markup(_t("Open the Jasper <b>General Ledger</b> (รายงานบัญชีแยกประเภท)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Trial Balance",
            markup(_t("Open the Jasper <b>Trial Balance</b> (งบทดลอง)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Profit and Loss",
            markup(_t("Open the Jasper <b>Profit and Loss</b> statement (งบกำไรขาดทุน)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Balance Sheet",
            markup(_t("Open the Jasper <b>Balance Sheet</b> (งบแสดงฐานะการเงิน)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) AR/AP Aging",
            markup(_t(
                "Open the Jasper <b>AR/AP Aging</b>: outstanding receivables and payables " +
                "bucketed by age."
            ))
        ),
        ...openJasperReport(
            "(J-Report OD15) Tax Invoice Report",
            markup(_t("Open the Jasper <b>Tax Invoice Report</b> (รายงานใบกำกับภาษี)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Sales Tax Report",
            markup(_t("Open the Jasper <b>Sales Tax Report</b> (รายงานภาษีขาย)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Purchase Tax Report",
            markup(_t("Open the Jasper <b>Purchase Tax Report</b> (รายงานภาษีซื้อ)."))
        ),

        {
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "Jasper financial reports complete! Every <b>(J-Report OD15)</b> entry under " +
                "Reporting opens a parameter wizard that streams a JasperReport PDF."
            )),
            run: "click",
        },
    ],
});
