import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Fleet Accounting Tour
 *
 * Walks the user through:
 *  1. Setting up vehicle expense categories
 *  2. Recording vehicle service/expense logs
 *  3. Linking expenses to analytic accounts and departments
 *  4. Tracking vehicle costs by project / department
 */
registry.category("web_tour.tours").add("od19_fleet_accounting_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "fleet.menu_root",
            markup(_t("Let's manage <b>Fleet Accounting</b>: vehicle expenses and cost tracking."))
        ),

        // --- Expense Categories ---
        {
            trigger: ".o_menu_sections :contains('Fleet Accounting'), .dropdown-item:contains('Fleet Accounting')",
            content: markup(_t("Open the <b>Fleet Accounting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Expense Categories'), .dropdown-item:contains('Expense Categories')",
            content: markup(_t(
                "Open <b>Expense Categories</b> to classify vehicle costs (fuel, maintenance, etc.)."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new expense category."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the category name (e.g. Fuel)."),
            run: "edit Fuel",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Vehicle Service Log ---
        {
            trigger: ".o_menu_sections :contains('Vehicles'), .dropdown-item:contains('Vehicles')",
            content: markup(_t("Go back to <b>Vehicles</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first",
            content: markup(_t("Open a vehicle to log a service expense.")),
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Costs')",
            content: markup(_t(
                "Open the <b>Costs</b> tab to record fuel, maintenance, and other vehicle expenses."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='log_services'] .o_field_x2many_list_row_add",
            content: _t("Add a new service/expense log."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='expense_category_id'] input",
            content: markup(_t(
                "Set the <b>Expense Category</b> for proper cost classification."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id'] input",
            content: markup(_t(
                "Set the <b>Department</b> to allocate the cost to the right team."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='analytic_account_id'] input",
            content: markup(_t(
                "Set the <b>Analytic Account</b> (Job Number) to track vehicle costs by project."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Fleet Accounting complete! Vehicle expenses are now classified by <b>category</b>, " +
                "<b>department</b>, and <b>analytic account</b> (project), enabling accurate P&amp;L tracking."
            )),
            run: "click",
        },
    ],
});
