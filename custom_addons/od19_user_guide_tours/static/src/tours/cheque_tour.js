import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Cheque Management Tour
 *
 * Walks the user through:
 *  1. Creating a cheque (receivable or payable)
 *  2. Confirming the cheque
 *  3. Depositing / clearing / marking paid
 *  4. Bouncing a cheque
 *  5. Printing the cheque
 */
registry.category("web_tour.tours").add("od19_cheque_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's manage <b>Cheques</b> from creation to clearance."))
        ),

        {
            trigger: ".o_menu_sections a:contains('Cheques')",
            content: markup(_t("Open the <b>Cheques</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new cheque."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the cheque number."),
            run: "edit CHQ-000123",
        },
        {
            trigger: ".o_field_widget[name='cheque_type'] select",
            content: markup(_t("Choose the <b>cheque type</b> (receivable or payable).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the payer or payee."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='bank_id'] input",
            content: _t("Select the bank."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: _t("Enter the cheque amount."),
            run: "edit 50000",
        },
        {
            trigger: ".o_field_widget[name='cheque_date'] input",
            content: _t("Set the cheque date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='due_date'] input",
            content: _t("Set the due date."),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("<b>Confirm</b> the cheque.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_deposit']",
            content: markup(_t(
                "For receivable cheques, click <b>Deposit</b> when the cheque is deposited at the bank."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_clear']",
            content: markup(_t(
                "Click <b>Clear</b> when the cheque is cleared (funds received). " +
                "If the cheque bounces, use <b>Bounce</b>."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_print_cheque']",
            content: markup(_t(
                "Use the <b>Print Cheque</b> button to print the cheque. " +
                "A single QWeb template supports all banks."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Cheque workflow complete: <b>Draft → Confirm → Deposit → Clear</b> (or <b>Paid</b> for payables). " +
                "Use <b>Bounce</b> for returned cheques."
            )),
        },
    ],
});
