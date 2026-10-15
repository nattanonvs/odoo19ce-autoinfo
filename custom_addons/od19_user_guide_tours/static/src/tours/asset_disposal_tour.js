import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Asset Disposal Tour
 *
 * Walks the user through:
 *  1. Creating and validating a fixed asset
 *  2. Disposing the asset (generates a disposal journal entry)
 *  3. Recording disposal reason and linked documents
 *  4. Reverting a disposal
 */
registry.category("web_tour.tours").add("od19_asset_disposal_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's learn how to <b>dispose</b> a fixed asset and generate the disposal entry."))
        ),
        {
            trigger: ".o_menu_sections :contains('Assets'), .dropdown-item:contains('Assets')",
            content: markup(_t("Open the <b>Assets</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Assets'), .dropdown-item:contains('Assets')",
            content: markup(_t("Open the <b>Assets</b> list.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Create and validate an asset ---
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new fixed asset."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the asset name (e.g. Machine A)."),
            run: "edit Machine A",
        },
        {
            trigger: ".o_field_widget[name='value'] input",
            content: _t("Enter the purchase value."),
            run: "edit 120000",
        },
        {
            trigger: ".o_field_widget[name='salvage_value'] input",
            content: _t("Enter the salvage (residual) value."),
            run: "edit 12000",
        },
        {
            trigger: ".o_field_widget[name='method_number'] input",
            content: _t("Set the number of depreciation periods (e.g. 60 months)."),
            run: "edit 60",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='validate']",
            content: markup(_t(
                "Click <b>Confirm Asset</b> to activate the asset. Its state becomes <b>Running</b>."
            )),
            tooltipPosition: "left",
            run: "click",
        },

        // --- Disposal ---
        {
            trigger: "button[name='action_dispose']",
            content: markup(_t(
                "Click <b>Dispose</b> to dispose the asset. The system cancels draft depreciation " +
                "entries and creates a <b>disposal journal entry</b> automatically."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "The disposal journal entry is opened. Return to the asset to review the disposal details."
            )),
        },
        {
            trigger: "a.nav-link:contains('Disposal')",
            content: markup(_t(
                "Open the <b>Disposal</b> tab: it shows the <b>disposal date</b>, the generated " +
                "<b>disposal journal entry</b> and the linked documents."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_disposal_reason'] textarea",
            content: markup(_t("Record the <b>Disposal Reason</b> for the audit trail.")),
            run: "edit Sold to third party",
        },
        {
            trigger: ".o_field_widget[name='od19_additional_bill_ids']",
            content: markup(_t(
                "Attach <b>Additional Documents</b> and <b>Supporting Documents</b> (bills / moves) " +
                "related to the disposal."
            )),
        },
        ...stepUtils.saveForm(),

        // --- Revert disposal ---
        {
            trigger: "button[name='action_revert_disposal']",
            content: markup(_t(
                "If the disposal was a mistake, click <b>Revert Disposal</b>. The disposal entry is " +
                "reversed and the asset goes back to <b>Running</b>."
            )),
            tooltipPosition: "left",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Asset Disposal complete! The lifecycle is <b>Draft → Running → Disposed</b>, " +
                "with the option to revert. Disposed assets appear in red in the list."
            )),
        },
    ],
});
