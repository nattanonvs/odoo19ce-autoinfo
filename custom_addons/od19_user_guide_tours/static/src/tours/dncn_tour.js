import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Debit Note / Credit Note (DN/CN) Tour
 *
 * Walks the user through:
 *  1. Creating a Debit Note (ใบเพิ่มหนี้) from a posted invoice
 *  2. Creating a Credit Note (ใบลดหนี้) — copies the original lines,
 *     reverses the accounting entries and links the original invoice
 *  3. Remastering an invoice (cancel + recreate)
 *  4. Setting DN/CN reasons
 *
 * Credit-note behaviour after the fix:
 *  - Odoo's native "Credit Note" button (action_reverse) is hidden, so the
 *    custom button is the only one left;
 *  - the custom button copies the original lines, auto-reverses the journal
 *    entries through `_reverse_moves()`, links `parent_id` /
 *    `reversed_entry_id` back to the original invoice and reconciles with it
 *    once posted (full or partial);
 *  - it works for both customer (out_refund) and vendor (in_refund) documents.
 */
registry.category("web_tour.tours").add("od19_dncn_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's learn how to create <b>Debit Notes</b> (ใบเพิ่มหนี้), " +
                "<b>Credit Notes</b> (ใบลดหนี้) and <b>Remaster</b> invoices " +
                "(Odoo 19 has no built-in DN)."
            ))
        ),

        // --- DN/CN Reasons ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("DN/CN Reasons"),
            content: markup(_t(
                "Open <b>DN/CN Reasons</b> to define why a debit or credit note is issued."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("DN/CN Reasons"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new DN/CN reason."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the reason name (e.g. Price Adjustment)."),
            run: "edit Price Adjustment",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Open a posted invoice ---
        {
            trigger: navSection("Customers"),
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Invoices"),
            content: markup(_t("Open <b>Invoices</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_data_row:first",
            content: markup(_t(
                "Open a <b>posted invoice</b>. DN/CN and Remaster can only be created " +
                "from a posted invoice."
            )),
            run: "click",
        },

        // --- Debit Note ---
        {
            trigger: "button[name='action_create_debit_note']",
            content: markup(_t(
                "Click <b>Debit Note</b> (ใบเพิ่มหนี้) to increase the invoice amount " +
                "(e.g. additional charges). The lines are copied with a <b>zero price</b> " +
                "so you can enter the extra charge yourself."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Credit Note ---
        {
            trigger: ".o_data_row:first",
            content: markup(_t("Open the same posted invoice again.")),
            run: "click",
        },
        {
            trigger: "button[name='action_create_credit_note']",
            content: markup(_t(
                "Click <b>Credit Note</b> (ใบลดหนี้). Odoo's own Credit Note button is " +
                "hidden, so this is the <b>only</b> Credit Note button left. It copies the " +
                "original lines, <b>reverses the accounting entries</b> and links back to the " +
                "original invoice — for both customer and vendor documents."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "The draft credit note is linked to its original invoice: the " +
                "<b>Parent Invoice</b> stat button and the <b>Source Document</b> field show " +
                "the original number (not the note's own number). Edit the amount for a " +
                "<b>partial</b> credit, pick a <b>Reason</b>, then <b>Post</b> — the note is " +
                "then reconciled with the original invoice automatically."
            )),
            tooltipPosition: "left",
        },
        ...stepUtils.discardForm(),

        // --- Remaster ---
        {
            trigger: ".o_data_row:first",
            content: markup(_t("Open the same posted invoice again.")),
            run: "click",
        },
        {
            trigger: "button[name='action_remaster_invoice']",
            content: markup(_t(
                "Click <b>Remaster</b> to cancel and recreate the invoice with corrections " +
                "(keeps the audit trail)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "DN/CN workflow complete! Use <b>Debit Note</b> to add charges, " +
                "<b>Credit Note</b> to reduce/refund (it reverses the entries and reconciles " +
                "with the original invoice), and <b>Remaster</b> to cancel and recreate an " +
                "invoice. Always set the <b>Reason</b> and add a <b>Remark</b> for audit purposes."
            )),
            run: "click",
        },
    ],
});
