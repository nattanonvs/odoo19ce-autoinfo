import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Stock Valuation Adjustment Tour
 *
 * Walks the user through:
 *  1. Creating a stock valuation adjustment
 *  2. Setting the adjustment type and new value
 *  3. Confirming and approving the adjustment
 *  4. Reviewing the audit trail
 */
registry.category("web_tour.tours").add("od19_stock_valuation_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's adjust <b>Stock Valuation</b> when costs change or need correction."))
        ),

        {
            trigger: ".o_menu_sections :contains('Inventory Control'), .dropdown-item:contains('Inventory Control')",
            content: markup(_t("Open the <b>Inventory Control</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Valuation Adjustments'), .dropdown-item:contains('Valuation Adjustments')",
            content: markup(_t("Open <b>Valuation Adjustments</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new valuation adjustment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='adjustment_type'] select",
            content: markup(_t(
                "Choose the <b>adjustment type</b>: increase or decrease the stock value."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the product to adjust."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='quantity'] input",
            content: _t("Enter the quantity affected."),
            run: "edit 10",
        },
        {
            trigger: ".o_field_widget[name='new_value'] input",
            content: markup(_t(
                "Set the <b>new value</b> per unit. The current value is shown for reference; " +
                "the total adjustment is calculated automatically."
            )),
            run: "edit 1200",
        },
        {
            trigger: ".o_field_widget[name='reason'] textarea",
            content: markup(_t("Enter the <b>reason</b> for the adjustment (required for audit).")),
            run: "edit Market price adjustment",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("<b>Confirm</b> the adjustment.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_approve']",
            content: markup(_t(
                "A manager must <b>Approve</b> the adjustment before it takes effect."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Stock Valuation Adjustment complete: <b>Draft → Confirm → Approve → Done</b>. " +
                "The <b>Audit Trail</b> tab records all changes for compliance."
            )),
        },
    ],
});
