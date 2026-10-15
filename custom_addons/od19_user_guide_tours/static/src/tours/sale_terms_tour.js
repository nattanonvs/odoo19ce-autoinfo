import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sale Terms Tour
 *
 * Walks the user through:
 *  1. Creating reusable sales term templates
 *  2. Applying terms on a quotation (OD19 Terms tab)
 */
registry.category("web_tour.tours").add("od19_sale_terms_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's set up reusable <b>Sale Term Templates</b> and apply them on quotations."))
        ),

        // --- Term templates ---
        {
            trigger: ".o_menu_sections :contains('Configuration'), .dropdown-item:contains('Configuration')",
            content: markup(_t("Open the Sales <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Sale Term Templates'), .dropdown-item:contains('Sale Term Templates')",
            content: markup(_t("Open <b>Sale Term Templates</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new term template."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the template name (e.g. Standard Warranty 1 Year)."),
            run: "edit Standard Warranty 1 Year",
        },
        {
            trigger: ".o_field_widget[name='term_type'] select",
            content: markup(_t(
                "Choose the <b>Term Type</b> (price, delivery, payment, validity, warranty, credit)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='content'] textarea",
            content: _t("Type the standard wording shown on quotations."),
            run: "edit รับประกันสินค้า 1 ปี นับจากวันที่ส่งมอบ",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Apply on a quotation ---
        {
            trigger: ".o_menu_sections :contains('Orders'), .dropdown-item:contains('Orders')",
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Quotations'), .dropdown-item:contains('Quotations')",
            content: markup(_t("Open <b>Quotations</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "On any quotation open the <b>OD19 Terms</b> tab and pick the templates for " +
                "<b>Price</b>, <b>Delivery</b>, <b>Payment (Product / Engineering)</b>, " +
                "<b>Validity</b>, <b>Warranty</b> and <b>Credit</b>."
            )),
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The combined term text is generated automatically into the <b>Terms &amp; Conditions</b> " +
                "and printed on the quotation."
            )),
        },
    ],
});
