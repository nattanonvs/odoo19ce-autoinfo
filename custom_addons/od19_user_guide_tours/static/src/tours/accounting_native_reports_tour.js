import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Management Reports Tour
 *
 * Walks the user through the built-in analysis reports that live under
 * Accounting > Reporting > Management:
 *
 *  - Invoice Analysis - turnover analysed by customer / product / period
 *  - Analytic Report  - costs and revenues per analytic account
 *
 * Both are `ir.actions.act_window` analysis views (graph / pivot), so no modal
 * is involved: the tour simply opens each report and waits for its container.
 */
registry.category("web_tour.tours").add("od19_accounting_native_reports_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's explore the built-in <b>Management</b> analysis reports."))
        ),

        // --- Invoice Analysis ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Management')",
            content: markup(_t("Open the <b>Management</b> group.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Invoice Analysis"),
            content: markup(_t(
                "Open <b>Invoice Analysis</b>: turnover broken down by customer and period."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Invoices Analysis"),
        {
            trigger: ".o_graph_view, .o_pivot_view",
            content: markup(_t(
                "Switch between the <b>Graph</b> and <b>Pivot</b> views, and use <b>Measures</b> " +
                "and <b>Group By</b> in the search bar to slice the revenue by product, " +
                "salesperson or month."
            )),
            run: "click",
        },

        // --- Analytic Report ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Re-open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Management')",
            content: markup(_t("Open the <b>Management</b> group.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Analytic Report"),
            content: markup(_t(
                "Open <b>Analytic Report</b>: revenues and costs grouped by <b>analytic account</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Analytic Reporting"),
        {
            trigger: ".o_pivot_view, .o_graph_view, .o_list_renderer",
            content: markup(_t(
                "Analytic Reporting complete! Use <b>Group By</b> on the analytic account, " +
                "project or plan to follow the profitability of each cost centre."
            )),
            run: "click",
        },
    ],
});
