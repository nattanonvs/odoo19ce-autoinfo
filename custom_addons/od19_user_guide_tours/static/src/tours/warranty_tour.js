import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Service Warranty Tour
 *
 * Walks the user through:
 *  1. Creating a Warranty Claim
 *  2. Checking warranty coverage
 *  3. Confirming and starting the claim
 *  4. Creating a linked Repair Order
 *  5. Completing the claim with resolution
 */
registry.category("web_tour.tours").add("od19_warranty_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "repair.menu_repair_order",
            markup(_t("Let's manage a <b>Warranty Claim</b> from creation to resolution."))
        ),

        {
            trigger: navSection("Warranty Claims"),
            content: markup(_t("Open <b>Warranty Claims</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new warranty claim."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='claim_date'] .o_input",
            content: _t("Set the claim date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            content: _t("Pick the customer from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='claim_type'] .o_select_menu_toggler",
            content: _t("Select the claim type (warranty, out-of-warranty, etc.)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the product with warranty."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='lot_id'] input",
            content: markup(_t(
                "Select the <b>Serial/Lot</b> to check warranty coverage automatically."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='under_warranty']",
            content: markup(_t(
                "The <b>Under Warranty</b> flag is computed automatically based on the product and serial."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='description'] textarea",
            content: markup(_t("Describe the <b>problem</b> reported by the customer.")),
            run: "edit Product not working as expected",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("<b>Confirm</b> the claim to start processing.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>Start</b> to begin the repair/evaluation process.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_create_repair_order']",
            content: markup(_t(
                "Click <b>Create Repair Order</b> to generate a linked repair order for servicing."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_back_button:visible",
            content: markup(_t("Go back to the warranty claim to complete it.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[name='action_done']",
            content: markup(_t(
                "Once resolved, click <b>Done</b> and fill in the <b>Resolution</b> notes."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Warranty workflow complete: <b>Create → Confirm → Start → (Repair Order) → Done</b>. " +
                "Warranty coverage is checked automatically from the product and serial number."
            )),
            run: "click",
        },
    ],
});
