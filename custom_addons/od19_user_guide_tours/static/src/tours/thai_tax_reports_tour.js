import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
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
            trigger: ".o_menu_sections :contains('Reporting'), .dropdown-item:contains('Reporting')",
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Thai Tax Reports'), .dropdown-item:contains('Thai Tax Reports')",
            content: markup(_t("Open the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- VAT Sales Register ---
        {
            trigger: ".o_menu_sections :contains('VAT Sales Register'), .dropdown-item:contains('VAT Sales Register')",
            content: markup(_t(
                "Open <b>VAT Sales Register (สมุดรายการภาษีขาย)</b> for output VAT."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_from'] input, .o_field_widget[name='start_date'] input, .modal .o_datepicker input",
            content: _t("Set the start date of the reporting period."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_to'] input, .o_field_widget[name='end_date'] input",
            content: _t("Set the end date of the reporting period."),
            run: "click",
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Click <b>Print/Generate</b> to produce the VAT Sales Register.")),
            tooltipPosition: "left",
            run: "click",
        },

        // --- VAT Purchase Register ---
        {
            trigger: ".o_menu_sections :contains('Thai Tax Reports'), .dropdown-item:contains('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('VAT Purchase Register'), .dropdown-item:contains('VAT Purchase Register')",
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

        // --- WHT Register ---
        {
            trigger: ".o_menu_sections :contains('Thai Tax Reports'), .dropdown-item:contains('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('WHT Register'), .dropdown-item:contains('WHT Register')",
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
