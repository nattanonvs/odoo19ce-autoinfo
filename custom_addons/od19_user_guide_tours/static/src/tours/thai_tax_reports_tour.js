import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Thai Tax Reports Tour
 *
 * Walks the user through generating Thai statutory tax reports:
 *  - VAT Sales Register (สมุดรายการภาษีขาย)
 *  - VAT Purchase Register (สมุดรายการภาษีซื้อ)
 *  - WHT Register (สมุดภาษีหัก ณ ที่จ่าย)
 */
registry.category("web_tour.tours").add("od19_thai_tax_reports_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's generate <b>Thai Tax Reports</b> (VAT and WHT registers)."))
        ),

        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Open the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- VAT Sales Register ---
        {
            trigger: navItem("VAT Sales Register (สมุดรายการภาษีขาย)"),
            content: markup(_t(
                "Open <b>VAT Sales Register (สมุดรายการภาษีขาย)</b> for output VAT."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_from'] .o_input, .o_field_widget[name='start_date'] .o_input, .modal .o_datepicker .o_input",
            content: _t("Set the start date of the reporting period."),
        },
        {
            trigger: ".o_field_widget[name='date_to'] .o_input, .o_field_widget[name='end_date'] .o_input",
            content: _t("Set the end date of the reporting period."),
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Click <b>Print/Generate</b> to produce the VAT Sales Register.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing may leave an error dialog and/or the "Configure your
        // document layout" configurator open, which blocks the navbar. Close
        // whichever appears (gated so the happy path is not affected).
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog button:contains('Close'), .o_error_dialog .btn-close, .o_error_dialog .btn-primary",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: [".o_dialog:has(.o_document_layout)"],
            trigger: ".o_dialog .modal-header .btn-close, .o_dialog footer button[special='cancel'], .o_dialog .o_form_button_cancel",
            content: markup(_t("Close the document layout configurator without saving.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_form_view:not(:has(.modal)), .o_list_view:not(:has(.modal))",
        },

        // --- VAT Purchase Register ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("VAT Purchase Register (สมุดรายการภาษีซื้อ)"),
            content: markup(_t(
                "Open <b>VAT Purchase Register (สมุดรายการภาษีซื้อ)</b> for input VAT."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Set the period and click <b>Print/Generate</b>.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing may leave an error dialog and/or the "Configure your
        // document layout" configurator open, which blocks the navbar. Close
        // whichever appears (gated so the happy path is not affected).
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog button:contains('Close'), .o_error_dialog .btn-close, .o_error_dialog .btn-primary",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: [".o_dialog:has(.o_document_layout)"],
            trigger: ".o_dialog .modal-header .btn-close, .o_dialog footer button[special='cancel'], .o_dialog .o_form_button_cancel",
            content: markup(_t("Close the document layout configurator without saving.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_form_view:not(:has(.modal)), .o_list_view:not(:has(.modal))",
        },

        // --- WHT Register ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("WHT Register (สมุดภาษีหัก ณ ที่จ่าย)"),
            content: markup(_t(
                "Open <b>WHT Register (สมุดภาษีหัก ณ ที่จ่าย)</b> for withholding tax records."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Set the period and click <b>Print/Generate</b>.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing may leave an error dialog and/or the "Configure your
        // document layout" configurator open, which blocks the navbar. Close
        // whichever appears (gated so the happy path is not affected).
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog button:contains('Close'), .o_error_dialog .btn-close, .o_error_dialog .btn-primary",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: [".o_dialog:has(.o_document_layout)"],
            trigger: ".o_dialog .modal-header .btn-close, .o_dialog footer button[special='cancel'], .o_dialog .o_form_button_cancel",
            content: markup(_t("Close the document layout configurator without saving.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_form_view:not(:has(.modal)), .o_list_view:not(:has(.modal))",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Thai Tax Reports complete! Generate <b>VAT Sales Register</b>, " +
                "<b>VAT Purchase Register</b>, and <b>WHT Register</b> for statutory compliance. " +
                "These reports are required for monthly/quarterly tax filings with the Revenue Department."
            )),
            run: "click",
        },
    ],
});
