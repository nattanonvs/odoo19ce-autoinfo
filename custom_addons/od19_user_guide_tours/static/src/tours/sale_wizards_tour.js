import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sale Wizards Tour
 *
 * Walks the user through:
 *  1. Changing the delivery date on a quotation
 *  2. Pulling sale lines into a draft customer invoice (Get Sale Lines)
 *  3. Downpayment origin / source tracking on invoices
 */
registry.category("web_tour.tours").add("od19_sale_wizards_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's learn the <b>Sale Wizards</b>: delivery date and sale-line picking."))
        ),

        // --- Change delivery date ---
        {
            trigger: ".o_menu_sections a:contains('Orders')",
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Quotations')",
            content: markup(_t("Open <b>Quotations</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer."),
            run: "click",
        },
        {
            trigger: "button[name='action_open_change_delivery_date']",
            content: markup(_t(
                "On a <b>draft / sent</b> quotation, click <b>Change Delivery Date</b> to shift the " +
                "delivery date of all lines in one step."
            )),
            tooltipPosition: "left",
        },
        {
            trigger: ".o_field_widget[name='commitment_date'] input",
            content: markup(_t(
                "Pick the new <b>delivery date</b> in the wizard and confirm to update the quotation."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Get Sale Lines on invoice (Invoicing app) ---
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Now switch to <b>Invoicing</b> to see the invoice wizards."))
        ),
        {
            trigger: ".o_menu_sections a:contains('Customers')",
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Invoices')",
            content: markup(_t("Open <b>Invoices</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "On a <b>draft customer invoice</b>, use <b>Get Sale Lines</b> to pull the order lines " +
                "(or downpayment lines) into the invoice automatically."
            )),
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The invoice also shows the <b>Downpayment Info</b> group with the <b>origin</b> and " +
                "<b>source</b> of the downpayment, plus the linked source purchase order."
            )),
        },
    ],
});
