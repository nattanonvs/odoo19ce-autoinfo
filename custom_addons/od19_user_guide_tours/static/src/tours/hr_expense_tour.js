import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 HR Expense Tour
 *
 * The expense claim (od19.expense.claim) is the single entry point for
 * filing an expense. This tour walks the user through:
 *  1. Creating an expense claim (header + expense lines)
 *  2. Filling the mandatory analytic account on every line
 *  3. Submitting the claim
 *  4. Tier validation (Dept Manager -> Accounting -> CEO)
 *  5. Posting the journal entries once approved
 */
registry.category("web_tour.tours").add("od19_hr_expense_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("Let's learn the <b>Expense Claim</b> workflow with 3-level tier approval."))
        ),

        // --- Single entry point: the expense claim ---
        {
            trigger: navSection("ใบเบิกของฉัน"),
            content: markup(_t(
                "Open <b>ใบเบิกของฉัน</b> — the single place to file and follow an expense claim."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ใบเบิกของฉัน"),
        {
            trigger: ".o-kanban-button-new",
            content: _t("Create a new expense claim."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='employee_id'] input",
            content: _t("Set the employee the claim belongs to."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='employee_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the employee."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='payment_mode'] .o_radio_input[data-value='own_account']",
            content: markup(_t(
                "Choose <b>Paid By</b>: employee (to reimburse) or company. " +
                "All lines of a claim must share the same mode."
            )),
            run: "click",
        },

        // --- Add an expense line ---
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: _t("Add an expense line to the claim (a claim groups several expenses)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_widget[name='name'] input",
            content: _t("Enter the expense description."),
            run: "edit Client Visit - Transportation",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_widget[name='product_id'] input",
            content: _t("Select the expense product/category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the first available expense category."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_widget[name='quantity'] input",
            content: markup(_t(
                "Set the <b>quantity</b> (and unit price); the line <b>total</b> is " +
                "computed from both."
            )),
            run: "edit 1",
        },

        // --- Analytic distribution (mandatory on every line) ---
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_widget[name='analytic_distribution'] .o_input_dropdown",
            content: markup(_t(
                "Every line must carry an <b>Analytic Account</b>. Open the analytic distribution."
            )),
            run: "click",
        },
        // Opening the widget already appends the first distribution line
        // (analytic_distribution.js: openAnalyticEditor() -> addLine()), so the
        // popup never starts empty — no extra "Add a Line" click is needed.
        {
            trigger: ".analytic_distribution_popup .o_field_widget[name='account_id'] input",
            content: _t("Pick the analytic account to charge."),
            run: "click",
        },
        {
            trigger: ".analytic_distribution_popup .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Select the analytic account."),
            run: "click",
        },
        {
            trigger: ".analytic_distribution_popup .popupButtons .btn",
            content: _t("Close the analytic distribution popup."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='total_amount']",
            content: markup(_t("The claim <b>Total</b> sums every expense line.")),
        },
        ...stepUtils.saveForm(),

        // --- Submit ---
        ...stepUtils.statusbarButtonsSteps(
            "Submit",
            markup(_t("Click <b>Submit</b> to send the claim for approval.")),
            ".o_form_view"
        ),

        // --- Tier Validation ---
        // อนุมัติ 3 ชั้นที่หัวใบ: หัวหน้าแผนก → บัญชี → CEO
        {
            isActive: ["button[name='validate_tier']"],
            trigger: "button[name='validate_tier']",
            content: markup(_t(
                "Each approver clicks <b>Validate</b> in their turn: " +
                "Department Manager → Accounting → CEO. Approval follows the sequence."
            )),
            tooltipPosition: "left",
            run: "click",
        },

        // --- Post the journal entries once fully approved ---
        {
            isActive: ["button[name='action_post']"],
            trigger: "button[name='action_post']",
            content: markup(_t(
                "Once approved, click <b>Post Journal Entries</b> to account the expense lines."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        // Posting can raise a "Confirmation" dialog. Acknowledge it first,
        // otherwise the back/discard buttons below are blocked by the modal.
        {
            isActive: [".modal-footer .btn-primary"],
            trigger: ".modal-footer .btn-primary",
            content: _t("Acknowledge the confirmation dialog."),
            tooltipPosition: "top",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_kanban_view, .o_list_renderer",
            content: markup(_t(
                "Expense Claim workflow complete! The process is: <b>Create → Submit → " +
                "Validate ×3 → Approved → Post</b>. Every line carries an analytic account " +
                "so costs are allocated to the right project or department."
            )),
            run: "click",
        },
    ],
});
