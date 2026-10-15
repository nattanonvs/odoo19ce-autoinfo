import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Stock FIFO Tour
 *
 * Walks the user through:
 *  1. Reviewing FIFO valuation records
 *  2. Valuing stock on a specific date (As-Of)
 *  3. Adjusting the brought-forward (BF) value
 */
registry.category("web_tour.tours").add("od19_stock_fifo_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's review <b>FIFO stock valuation</b> and the valuation reports."))
        ),

        // --- FIFO Valuation Records ---
        {
            trigger: ".o_menu_sections a:contains('FIFO Valuation /')",
            content: markup(_t("Open the <b>FIFO Valuation</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('FIFO Valuation Records')",
            content: markup(_t(
                "Open <b>FIFO Valuation Records</b>. Each line stores the date, product, " +
                "quantity, unit cost and total value at the moment of the move."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "This list is the FIFO valuation ledger: <b>quantity × unit cost = total value</b>, " +
                "used as the basis for stock accounting."
            )),
        },

        // --- FIFO As-Of ---
        {
            trigger: ".o_menu_sections a:contains('FIFO As-Of')",
            content: markup(_t(
                "Open <b>FIFO As-Of</b> to value the whole stock at a chosen date."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_as_of_date'] input",
            content: markup(_t("Pick the <b>As-Of Date</b> and optionally the products to value.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_product_ids'] input",
            content: markup(_t("Leave the products empty to compute FIFO for all products.")),
            run: "click",
        },
        {
            trigger: "footer button[name='action_compute_fifo']",
            content: markup(_t(
                "Click <b>Compute FIFO Valuation</b> to generate the valuation result lines."
            )),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The result shows quantity, unit cost and total value per product as of the chosen date."
            )),
        },

        // --- BF Revaluation ---
        {
            trigger: ".o_menu_sections a:contains('BF Revaluation')",
            content: markup(_t(
                "Open <b>BF Revaluation / ปรับมูลค่ายกมา</b> to adjust the brought-forward stock value."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_product_id'] input",
            content: markup(_t("Select the product whose opening value must be adjusted.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_new_value'] input",
            content: markup(_t(
                "Enter the <b>New Value</b>. The <b>difference</b> from the current value is computed " +
                "and highlighted; a valuation layer and journal entry are created on apply."
            )),
            run: "edit 50000",
        },
        {
            trigger: "footer button[name='action_apply_revaluation']",
            content: markup(_t("Click <b>Apply Revaluation</b> to post the adjustment.")),
            tooltipPosition: "top",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Stock FIFO complete! Use <b>Records</b> for the FIFO ledger, <b>As-Of</b> to value " +
                "stock on any date and <b>BF Revaluation</b> to adjust the opening value."
            )),
        },
    ],
});
