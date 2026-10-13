import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Fixed Assets Tour
 *
 * Walks the user through:
 *  1. Creating a fixed asset
 *  2. Setting depreciation method and accounts
 *  3. Validating the asset (starts depreciation)
 *  4. Creating depreciation entries
 *  5. Closing the asset
 */
registry.category("web_tour.tours").add("od19_fixed_assets_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's manage <b>Fixed Assets</b> from creation to depreciation and closure."))
        ),

        {
            trigger: ".o_menu_sections a:contains('Fixed Assets')",
            content: markup(_t("Open the <b>Fixed Assets</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fixed asset."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the asset name."),
            run: "edit Office Printer",
        },
        {
            trigger: ".o_field_widget[name='asset_account_id'] input",
            content: markup(_t("Set the <b>asset account</b> (balance sheet account).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='journal_id'] input",
            content: _t("Set the depreciation journal."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date'] input",
            content: _t("Set the asset acquisition date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='value'] input",
            content: markup(_t("Enter the <b>original value</b> of the asset.")),
            run: "edit 50000",
        },
        {
            trigger: ".o_field_widget[name='salvage_value'] input",
            content: markup(_t("Enter the <b>salvage value</b> (residual value at end of life).")),
            run: "edit 5000",
        },

        // --- Depreciation Setup ---
        {
            trigger: ".o_field_widget[name='method'] select",
            content: markup(_t(
                "Set the <b>depreciation method</b>: " +
                "Straight Line, Declining, or Accelerated."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='method_number'] input",
            content: markup(_t(
                "Set the <b>number of depreciations</b> (useful life in periods)."
            )),
            run: "edit 60",
        },
        {
            trigger: ".o_field_widget[name='method_period'] select",
            content: markup(_t("Set the <b>period length</b> (Month or Year).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='depreciation_account_id'] input",
            content: markup(_t("Set the <b>accumulated depreciation account</b>.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='expense_account_id'] input",
            content: markup(_t("Set the <b>depreciation expense account</b>.")),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Asset Workflow ---
        {
            trigger: "button[name='validate']",
            content: markup(_t(
                "Click <b>Validate</b> to confirm the asset. " +
                "This generates the depreciation schedule automatically."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Depreciation Schedule')",
            content: markup(_t(
                "Open the <b>Depreciation Schedule</b> tab to see the computed depreciation lines."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='depreciation_line_ids'] button[name='create_move']",
            content: markup(_t(
                "Click <b>Create Entry</b> on a depreciation line to post the depreciation journal entry."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Fixed Assets complete! Workflow: " +
                "<b>Draft → Validate (Open) → Create Depreciation Entries → Close</b>. " +
                "The depreciation schedule is auto-computed based on method, value, and useful life."
            )),
        },
    ],
});
