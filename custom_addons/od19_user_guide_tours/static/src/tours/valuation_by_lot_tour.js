import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Inventory Execution Control - Stock Valuation by Lot Tour
 *
 * Walks the user through viewing and analyzing stock valuation
 * broken down by lot/serial number, product, and location.
 */
registry.category("web_tour.tours").add("od19_valuation_by_lot_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's review <b>Stock Valuation by Lot</b> for accurate cost tracking."))
        ),

        {
            trigger: navSection('Products'),
            content: markup(_t("Open the <b>Inventory Control</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Valuation by Lot'),
            content: markup(_t(
                "Open <b>Valuation by Lot</b> to see stock value broken down by lot/serial number."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            content: markup(_t(
                "Use the <b>search bar</b> to filter by product, lot, or location."
            )),
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            content: markup(_t(
                "Use <b>Group By</b> to aggregate the valuation by Product, Lot, Location, or Cost Method. " +
                "This helps identify which lots have the highest value."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Review the columns: <b>Quantity</b>, <b>Unit Cost</b>, and <b>Total Value</b>. " +
                "Negative total values are highlighted in red and may indicate valuation issues."
            )),
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Stock Valuation by Lot complete! Use this view to track inventory value " +
                "at the lot level, identify slow-moving or high-value lots, and reconcile " +
                "with the general ledger."
            )),
            run: "click",
        },
    ],
});
