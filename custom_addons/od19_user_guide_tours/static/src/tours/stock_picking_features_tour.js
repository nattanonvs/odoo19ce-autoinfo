import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Stock Picking Features Tour
 *
 * Walks the user through:
 *  1. Signature chain fields (salesperson + department manager) on a transfer
 *  2. Additional print lines on a transfer document
 */
registry.category("web_tour.tours").add("od19_stock_picking_features_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's learn the extra <b>Transfer</b> features: signature chain and additional lines."))
        ),

        {
            trigger: ".o_menu_sections a:contains('Operations')",
            content: markup(_t("Open the <b>Operations</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Transfers')",
            content: markup(_t("Open <b>Transfers</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first",
            content: markup(_t("Open a transfer to see the extra fields and tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_sale_user_id']",
            content: markup(_t(
                "The <b>Salesperson</b> (od19_sale_user_id) and the <b>Department Manager</b> " +
                "(od19_dept_manager_id) form the signature chain printed on the transfer document. " +
                "They are locked once the transfer is done or cancelled."
            )),
        },
        {
            trigger: "a.nav-link:contains('Additional Lines')",
            content: markup(_t(
                "Open the <b>Additional Lines / บรรทัดเพิ่มเติม</b> tab to add free-text print lines " +
                "(name, quantity, unit) that appear on the printed document."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_additional_line_ids'] .o_field_x2many_list_row_add",
            content: markup(_t("Click <b>Add a Line</b> to insert an additional print line.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the free-text description for the printed line."),
            run: "edit Delivered in 2 batches",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Stock Picking Features complete! Transfers now carry a <b>signature chain</b> and " +
                "optional <b>additional print lines</b>."
            )),
        },
    ],
});
