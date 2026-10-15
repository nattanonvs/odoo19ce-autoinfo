import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Misc Features Tour
 *
 * Walks the user through:
 *  1. Runtime Guard - environment / version health check
 *  2. Repeat Customer Enhanced - repeat-business analysis report
 */
registry.category("web_tour.tours").add("od19_misc_features_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_misc_features.menu_od19_misc_features_root",
            markup(_t("Let's explore the <b>Misc Features</b>: Runtime Guard and Repeat Customer analysis."))
        ),

        // --- Runtime Guard ---
        {
            trigger: ".o_menu_sections a:contains('Runtime Guard')",
            content: markup(_t("Open <b>Runtime Guard</b> to check the system health.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Run Runtime Check')",
            content: markup(_t(
                "Open <b>Run Runtime Check</b> to capture the current Odoo version, Python version, " +
                "installed-module count and database size."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "footer button[name='action_run_check']",
            content: markup(_t(
                "Click <b>Run Check</b> to execute the guard. The result is stored as a history record " +
                "for later comparison."
            )),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each check is logged with the date, versions and metrics, so you can track " +
                "environment drift over time."
            )),
        },

        // --- Repeat Customer Enhanced ---
        {
            trigger: ".o_menu_sections a:contains('Repeat Customer Enhanced')",
            content: markup(_t(
                "Open <b>Repeat Customer Enhanced</b> to analyse repeat business."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Confirmed sale orders are grouped by the <b>actual partner</b> (shipping partner " +
                "if set, otherwise the customer), showing <b>last order date</b>, <b>order count</b> " +
                "and <b>total amount</b>."
            )),
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Use this report to identify your most loyal contractors and project owners, " +
                "and to spot repeat-business opportunities."
            )),
        },
    ],
});
