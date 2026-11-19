import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Jasper asset & operations Tour
 *
 * Covers the remaining Jasper `(J-Report OD15)` reports under
 * Accounting > Reporting:
 *
 *  - Asset cards (ทะเบียนทรัพย์สิน / ฟอร์ม / บาร์โค้ด / QR)
 *  - Depreciation (ค่าเสื่อมราคา / รายบรรทัด) and book value (มูลค่าตามบัญชี)
 *  - Financial statements by level (งบการเงิน ระดับ 3 / ระดับ 4)
 *  - Petty cash (request / payment)
 *  - Advance (request form / clear / condition / at date)
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

registry.category("web_tour.tours").add("od19_accounting_jasper_asset_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore the <b>Jasper asset & operations reports</b> under " +
                "Accounting > Reporting."
            ))
        ),
        ...openJasperReport(
            "(J-Report OD15) ทะเบียนทรัพย์สิน",
            markup(_t("Open the <b>Fixed Asset Register</b> (ทะเบียนทรัพย์สิน)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) ทะเบียนทรัพย์สิน (ฟอร์ม)",
            markup(_t("Open the <b>Asset Register (Form)</b> (ทะเบียนทรัพย์สิน ฟอร์ม)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) ทะเบียนทรัพย์สิน (บาร์โค้ด)",
            markup(_t("Open the <b>Asset Register (Barcode)</b> (ทะเบียนทรัพย์สิน บาร์โค้ด)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) ทะเบียนทรัพย์สิน (QR)",
            markup(_t("Open the <b>Asset Register (QR)</b> (ทะเบียนทรัพย์สิน QR)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) ค่าเสื่อมราคา",
            markup(_t("Open the <b>Depreciation</b> report (ค่าเสื่อมราคา)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) ค่าเสื่อมราคา (รายบรรทัด)",
            markup(_t("Open the <b>Depreciation by line</b> report (ค่าเสื่อมราคา รายบรรทัด)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) มูลค่าตามบัญชี",
            markup(_t("Open the <b>Book Value</b> report (มูลค่าตามบัญชี)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) งบการเงิน (ระดับ 3)",
            markup(_t("Open the <b>Financial Statements (level 3)</b> (งบการเงิน ระดับ 3)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) งบการเงิน (ระดับ 4)",
            markup(_t("Open the <b>Financial Statements (level 4)</b> (งบการเงิน ระดับ 4)."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Petty Cash Request Report",
            markup(_t("Open the <b>Petty Cash Request Report</b>: petty-cash requests for the period."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Petty Cash Payment Report",
            markup(_t("Open the <b>Petty Cash Payment Report</b>: petty-cash payments for the period."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Advance Request Form",
            markup(_t("Open the <b>Advance Request Form</b>: the advance request documents."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Advance Clear Form",
            markup(_t("Open the <b>Advance Clear Form</b>: the cleared advance documents."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Advance Request Condition",
            markup(_t("Open <b>Advance Request Condition</b>: advances grouped by their condition."))
        ),
        ...openJasperReport(
            "(J-Report OD15) Advance Request At Date",
            markup(_t("Open <b>Advance Request At Date</b>: the advance position on a given date."))
        ),
        {
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "Jasper asset & operations reports complete! Every <b>(J-Report OD15)</b> entry " +
                "under Reporting opens a parameter wizard that streams a JasperReport PDF."
            )),
            run: "click",
        },
    ],
});
