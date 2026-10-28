import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Asset Loan Tour
 *
 * Walks the user through:
 *  1. Creating an Asset Loan record
 *  2. Adding equipment lines
 *  3. Confirming the loan
 *  4. Returning the equipment
 *  5. Marking equipment as lost (if applicable)
 */
registry.category("web_tour.tours").add("od19_asset_loan_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "maintenance.menu_maintenance_title",
            markup(_t("Let's manage <b>Asset Loans</b> for equipment borrowing and returns."))
        ),

        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Asset Loan')",
            content: markup(_t("Open <b>Asset Loan</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Loans"),
            content: markup(_t("Open <b>Loans</b> to view and create asset loans.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new asset loan."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='borrower_id'] input",
            content: _t("Select the borrower (employee or partner)."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='loan_date'] .o_input",
            content: _t("Open the date picker to set the loan date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='loan_date'] input.o_input",
            content: _t("Set the loan date."),
            run: "edit 2026-01-15",
        },
        {
            trigger: ".o_field_widget[name='expected_return_date'] .o_input",
            content: _t("Set the expected return date."),
            run: "edit 2026-02-15",
        },
        {
            trigger: "a.nav-link:contains('Equipment')",
            content: markup(_t(
                "Open the <b>Equipment</b> page to add the items being loaned."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: _t("Add an equipment line."),
            run: "click",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='equipment_id'] input",
            content: _t("Select the equipment to loan."),
            run: "edit ",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:first",
            run: "click",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='quantity'] input",
            content: _t("Set the quantity to loan."),
            run: "edit 1",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t(
                "Click <b>Confirm</b> to mark the equipment as borrowed."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_return']",
            content: markup(_t(
                "When the equipment is returned, click <b>Return</b>. " +
                "The returned quantity is updated on each line."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_lost']",
            content: markup(_t(
                "If equipment is not returned, click <b>Mark Lost</b> to record the loss."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Asset Loan workflow complete: <b>Create → Confirm → Return</b> (or <b>Mark Lost</b>). " +
                "Use the <b>Overdue</b> filter to find loans past their expected return date."
            )),
            run: "click",
        },
    ],
});
