import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 HR Expense Enhanced Tour
 *
 * Walks the user through:
 *  1. Cash advance lifecycle (Not Received → Received → Used → Returned)
 *  2. Returning unspent cash through a wizard
 *  3. Delegating the approval to another approver
 *  4. Claiming a mileage reimbursement with the odometer auto-fill
 *  5. Exporting expenses to XLSX from the list view
 */
registry.category("web_tour.tours").add("od19_hr_expense_enhanced_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("Let's learn the enhanced <b>Cash Advance</b> and <b>Delegation</b> features."))
        ),

        // --- Create an expense ---
        // The per-expense "My Expenses" menu of the core app is hidden (the
        // expense claim is the only entry point). The hr.expense record itself
        // — which hosts the cash-advance lifecycle and the XLSX export — is
        // reachable from Reporting > Expenses Analysis.
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Expenses Analysis"),
            content: markup(_t("Open <b>Expenses Analysis</b> to work with expense records.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Expenses Analysis"),
        {
            trigger: ".o_switch_view.o_list",
            content: _t("Switch to the list view."),
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
            trigger: ".o_field_widget[name='product_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the first available expense category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='quantity'] input",
            content: markup(_t("Set the <b>quantity</b>; the total amount is computed automatically.")),
            run: "edit 1",
        },
        {
            trigger: ".o_field_widget[name='total_amount']",
            content: markup(_t(
                "The <b>total amount</b> is computed from quantity × unit price."
            )),
        },
        {
            trigger: ".o_field_widget[name='first_approver_id'] input",
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
            run: "click",
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
            run: "click",
        },
        // Recording the cash return raises an "Invalid Operation" dialog when
        // no journal is configured. It opens asynchronously right after the
        // click above, so wait for either outcome first (a wait step is never
        // blocked by a modal), then close the dialog only if it appeared.
        {
            trigger: ".o_error_dialog, .o_dialog .modal-footer .btn-secondary",
        },
        {
            isActive: [".o_error_dialog"],
            trigger: ".o_error_dialog .modal-footer .o-default-button",
            content: markup(_t("Close the warning dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "footer button[special='cancel']",
            content: _t("Cancel here to keep the demo data unchanged."),
            run: "click",
        },
        {
            trigger: ".o_form_view:not(:has(.modal))",
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
            trigger: ".o_field_widget[name='reason'] input",
            content: _t("Record the reason for the delegation."),
            run: "edit Annual leave",
        },
        {
            trigger: "footer button[name='action_delegate']",
            content: markup(_t(
                "Confirm with <b>Delegate</b>. The delegate then sees <b>Approve (Delegate)</b> " +
                "and <b>Refuse (Delegate)</b> buttons."
            )),
            run: "click",
        },
        {
            trigger: "footer button[special='cancel']",
            content: _t("Cancel here to keep the demo data unchanged."),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Mileage reimbursement with odometer auto-fill ---
        {
            trigger: ".o_list_button_add",
            content: markup(_t(
                "Now let's claim a <b>mileage reimbursement</b> for a trip made with your own car."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Name the trip."),
            run: "edit Mileage - Client Visit",
        },
        {
            trigger: ".o_field_widget[name='od19_is_mileage'] input",
            content: markup(_t(
                "Tick <b>Mileage / ค่าเดินทางตามระยะทาง</b>. The mileage fields appear and your " +
                "vehicle is looked up automatically."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_vehicle_id'] input",
            content: markup(_t(
                "Your <b>vehicle</b> is pre-selected from your vehicle book; you can change it."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_odometer_start'] input",
            content: markup(_t(
                "The <b>start odometer</b> is pre-filled with the vehicle's last recorded reading, " +
                "so you do not have to note the number before leaving."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_odometer_end'] input",
            content: markup(_t(
                "Enter the <b>end odometer</b> reading when the trip is over."
            )),
            run: "edit 12500",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_distance_km'] input",
            content: markup(_t(
                "The <b>distance (km)</b> is computed automatically as end − start."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_rate']",
            content: markup(_t(
                "The reimbursement amount is the distance × the company <b>rate per km</b>."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_mileage_odometer_image']",
            content: markup(_t(
                "Attach a <b>photo of the odometer</b> here as evidence of the reading."
            )),
            tooltipPosition: "left",
        },
        ...stepUtils.discardForm(),

        // --- XLSX export ---
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "From the expense list use the <b>Export XLSX</b> button to export the filtered " +
                "expenses (by date, state, employee, department and cash state)."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "HR Expense Enhanced complete! Cash advances follow " +
                "<b>Not Received → Received → Used → Returned</b>, approvals can be delegated, " +
                "and data can be exported to XLSX."
            )),
            run: "click",
        },
    ],
});
