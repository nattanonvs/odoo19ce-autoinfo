import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Money In Analysis Report Tour
 *
 * Walks the user through:
 *  1. Generating a Money In report with filters
 *  2. Understanding the two phases (invoice-based vs cash-based)
 *  3. Reviewing report runs and analysis lines
 */
registry.category("web_tour.tours").add("od19_money_in_report_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's generate a <b>Money In Analysis</b> report."))
        ),

        {
            trigger: ".o_menu_sections :contains('Reporting'), .dropdown-item:contains('Reporting')",
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Money In Analysis'), .dropdown-item:contains('Money In Analysis')",
            content: markup(_t("Open <b>Money In Analysis</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Generate Report'), .dropdown-item:contains('Generate Report')",
            content: markup(_t("Click <b>Generate Report</b> to open the report wizard.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_from'] input",
            content: _t("Set the start date of the analysis period."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_to'] input",
            content: _t("Set the end date of the analysis period."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='phase'] select",
            content: markup(_t(
                "Choose the <b>phase</b>:<br/>" +
                "<b>Phase 1</b> (Invoice-based): recognizes revenue when invoices are posted.<br/>" +
                "<b>Phase 2</b> (Cash &amp; Invoice-based): recognizes revenue when cash is actually received."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='job_type_values'] input",
            content: markup(_t("Filter by <b>job type</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_ids'] input",
            content: markup(_t("Filter by specific <b>customers</b> (leave blank for all).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='salesperson_ids'] input",
            content: markup(_t("Filter by <b>salespersons</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='project_ids'] input",
            content: markup(_t("Filter by <b>projects</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_categ_ids'] input",
            content: markup(_t("Filter by <b>product categories</b> (optional).")),
            run: "click",
        },
        {
            trigger: "button[name='action_generate_report']",
            content: markup(_t("Click <b>Generate Report</b> to run the analysis.")),
            tooltipPosition: "left",
            run: "click",
        },

        // --- Review Report Runs ---
        {
            trigger: ".o_menu_sections :contains('Report Runs'), .dropdown-item:contains('Report Runs')",
            content: markup(_t("Open <b>Report Runs</b> to see all generated reports.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first",
            content: markup(_t("Open a report run to review the results.")),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Analysis Lines ---
        {
            trigger: ".o_menu_sections :contains('Analysis Lines'), .dropdown-item:contains('Analysis Lines')",
            content: markup(_t(
                "Open <b>Analysis Lines</b> to see the detailed breakdown of revenue " +
                "by customer, salesperson, project, and product category."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Money In Analysis complete! Use <b>Phase 1</b> for invoice-based revenue " +
                "recognition and <b>Phase 2</b> for cash-based. Review <b>Report Runs</b> for " +
                "summary results and <b>Analysis Lines</b> for detailed breakdowns."
            )),
        },
    ],
});
