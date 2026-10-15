import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 HR Expense Enhanced Tour
 *
 * Walks the user through:
 *  1. Cash advance lifecycle (Not Received → Received → Used → Returned)
 *  2. Returning unspent cash through a wizard
 *  3. Delegating the approval to another approver
 *  4. Exporting expenses to XLSX from the list view
 */
registry.category("web_tour.tours").add("od19_hr_expense_enhanced_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("Let's learn the enhanced <b>Cash Advance</b> and <b>Delegation</b> features."))
        ),

        // --- Create an expense ---
        {
            trigger: ".o_menu_sections :contains('My Expenses'), .dropdown-item:contains('My Expenses')",
            content: markup(_t("Open <b>My Expenses</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new expense."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the expense description."),
            run: "edit Cash Advance - Site Visit",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the expense category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='total_amount'] input",
            content: _t("Enter the amount."),
            run: "edit 3000",
        },
        {
            trigger: ".o_field_widget[name='od19_first_approver_id'] input",
            content: markup(_t(
                "The <b>First Approver (Dept Head)</b> is auto-filled from the department manager, " +
                "but can be changed manually."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_cash_state']",
            content: markup(_t(
                "The <b>Cash State</b> badge tracks the cash advance: " +
                "<b>Not Received → Received → Used → Returned</b>."
            )),
        },
        ...stepUtils.saveForm(),

        // --- Cash lifecycle ---
        {
            trigger: "button[name='action_receive_cash']",
            content: markup(_t("Click <b>Receive Cash</b> once the employee receives the advance.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_use_cash']",
            content: markup(_t("Click <b>Use Cash</b> when the advance has been spent.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_open_return_cash_wizard']",
            content: markup(_t(
                "Click <b>Return Cash</b> to open the return wizard for any unspent amount."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: markup(_t(
                "The unspent amount is pre-filled. Choose the <b>return date</b>, <b>journal</b> " +
                "and whether to create the accounting entry."
            )),
            run: "click",
        },
        {
            trigger: "footer button[name='action_return_cash']",
            content: markup(_t("<b>Return Cash</b> records the return and closes the cash advance.")),
        },
        {
            trigger: "footer button[special='cancel']",
            content: _t("Cancel here to keep the demo data unchanged."),
            run: "click",
        },

        // --- Delegation ---
        {
            trigger: "button[name='action_delegate_approval']",
            content: markup(_t(
                "Use <b>Delegate Approval</b> to hand the approval over to another approver while away."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='delegate_approver_id'] input",
            content: markup(_t("Choose the <b>Delegate Approver</b> who will approve on your behalf.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='reason'] textarea",
            content: _t("Record the reason for the delegation."),
            run: "edit Annual leave",
        },
        {
            trigger: "footer button[name='action_delegate']",
            content: markup(_t(
                "Confirm with <b>Delegate</b>. The delegate then sees <b>Approve (Delegate)</b> " +
                "and <b>Refuse (Delegate)</b> buttons."
            )),
        },
        {
            trigger: "footer button[special='cancel']",
            content: _t("Cancel here to keep the demo data unchanged."),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- XLSX export ---
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "From the expense list use the <b>Export XLSX</b> button to export the filtered " +
                "expenses (by date, state, employee, department and cash state)."
            )),
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "HR Expense Enhanced complete! Cash advances follow " +
                "<b>Not Received → Received → Used → Returned</b>, approvals can be delegated, " +
                "and data can be exported to XLSX."
            )),
        },
    ],
});
