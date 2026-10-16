import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Tour
 *
 * Walks the user through:
 *  1. Petty Cash Fund setup and transactions
 *  2. WHT (Withholding Tax) on payments
 *  3. Fixed Assets and depreciation
 *  4. Fiscal Year management and year-end closing
 */
registry.category("web_tour.tours").add("od19_accounting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's explore the <b>Accounting</b> module: Petty Cash, WHT, Fixed Assets, and Fiscal Year."))
        ),

        // --- Petty Cash Fund ---
        {
            trigger: ".o_menu_sections :contains('Petty Cash'), .dropdown-item:contains('Petty Cash')",
            content: markup(_t("Open the <b>Petty Cash</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Funds'), .dropdown-item:contains('Funds')",
            content: markup(_t("Open <b>Funds</b> to manage small cash funds.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new petty cash fund."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the fund name (e.g. Office Petty Cash)."),
            run: "edit Office Petty Cash",
        },
        {
            trigger: ".o_field_widget[name='account_id'] input",
            content: _t("Select the cash GL account."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: markup(_t("Set the <b>fund amount</b>. The balance is updated automatically by transactions.")),
            run: "edit 5000",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "a.nav-link:contains('Transactions')",
            content: markup(_t(
                "Open the <b>Transactions</b> page to record petty cash inflows and outflows. " +
                "Each transaction updates the fund balance."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- WHT on Payment ---
        {
            trigger: ".o_menu_sections :contains('Payments'), .dropdown-item:contains('Payments')",
            content: markup(_t(
                "Open <b>Payments</b> to record vendor/customer payments with <b>Withholding Tax (WHT)</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new payment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the vendor or customer."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the payment amount."),
            run: "edit 10000",
        },
        {
            trigger: ".o_field_widget[name='wht_type_id'] input",
            content: markup(_t(
                "Select the <b>WHT Type</b>. The system calculates the WHT base, WHT amount, " +
                "and net amount automatically."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Fixed Assets ---
        {
            trigger: ".o_menu_sections :contains('Fixed Assets'), .dropdown-item:contains('Fixed Assets')",
            content: markup(_t("Open <b>Fixed Assets</b> to manage assets and depreciation.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fixed asset."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the asset name (e.g. Company Vehicle)."),
            run: "edit Company Vehicle",
        },
        {
            trigger: ".o_field_widget[name='value'] input",
            content: _t("Enter the purchase value."),
            run: "edit 500000",
        },
        {
            trigger: ".o_field_widget[name='salvage_value'] input",
            content: _t("Enter the salvage (residual) value."),
            run: "edit 50000",
        },
        {
            trigger: ".o_field_widget[name='method_number'] input",
            content: _t("Set the number of depreciation periods (e.g. 60 months)."),
            run: "edit 60",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='validate']",
            content: markup(_t(
                "Click <b>Validate</b> to activate the asset. The depreciation schedule is generated automatically."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Depreciation Schedule')",
            content: markup(_t(
                "Open the <b>Depreciation Schedule</b> page. Each line shows a depreciation entry; " +
                "click <b>Create Entry</b> to post it."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Fiscal Year ---
        {
            trigger: ".o_menu_sections :contains('Configuration'), .dropdown-item:contains('Configuration')",
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Fiscal Years'), .dropdown-item:contains('Fiscal Years')",
            content: markup(_t("Open <b>Fiscal Years</b> to define accounting periods.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fiscal year."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the fiscal year name (e.g. FY 2026)."),
            run: "edit FY 2026",
        },
        {
            trigger: ".o_field_widget[name='date_from'] input",
            content: _t("Set the start date of the fiscal year."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_to'] input",
            content: _t("Set the end date of the fiscal year."),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_open']",
            content: markup(_t("Click <b>Open</b> to activate the fiscal year.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_menu_sections :contains('Year-End Closing'), .dropdown-item:contains('Year-End Closing')",
            content: markup(_t(
                "At the end of the year, use <b>Year-End Closing</b> to close the fiscal year " +
                "and carry forward balances."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Accounting tour complete! You've learned <b>petty cash</b> fund management, " +
                "<b>WHT</b> on payments, <b>fixed asset</b> depreciation, and <b>fiscal year</b> " +
                "management with year-end closing."
            )),
            run: "click",
        },
    ],
});
