import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 MIS Reports Tour
 *
 * Walks the user through the MIS Builder reporting engine (OCA `mis_builder`),
 * reachable from Accounting > Reporting > MIS Reporting:
 *
 *  1. MIS Reports            - saved report instances (temporary = False)
 *  2. Last Reports Generated - ad-hoc instances produced by one-off runs
 *
 * The "MIS Reporting" entry is a sub-menu: the Reporting dropdown renders it
 * as a group header, and the two leaf actions under it as dropdown items.
 */
registry.category("web_tour.tours").add("od19_mis_reports_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t(
                "Let's explore <b>MIS Reports</b>: management information built on " +
                "reusable KPI templates."
            ))
        ),

        // --- MIS Reports (saved instances) ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('MIS Reporting')",
            content: markup(_t("Open the <b>MIS Reporting</b> group.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("MIS Reports"),
            content: markup(_t(
                "Open <b>MIS Reports</b>: every saved instance of a KPI report."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Opening a menu entry switches the action asynchronously: the previous
        // view stays mounted for a few frames. Waiting for the expected action
        // name in the breadcrumb guarantees the new list is on screen before the
        // tour continues.
        waitForAction("MIS Reports"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each row is a <b>report instance</b>: its <b>name</b>, the <b>Template</b> it " +
                "uses, the <b>target moves</b> (draft or all) and the current <b>pivot date</b>. " +
                "The row buttons <b>Preview</b>, <b>Print</b> and <b>Export</b> render or download it."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to configure a new report instance.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Pick a <b>Template</b>, set the <b>Comparison</b> and <b>Period</b> columns, then " +
                "hit <b>Preview</b> to render the KPI grid."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Last Reports Generated (ad-hoc instances) ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Re-open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('MIS Reporting')",
            content: markup(_t("Open the <b>MIS Reporting</b> group.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Last Reports Generated"),
            content: markup(_t(
                "Open <b>Last Reports Generated</b>: the temporary instances produced by one-off runs."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Last Reports Generated"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every ad-hoc MIS run is kept here so it can be reopened or exported later. " +
                "Use <b>MIS Reports</b> for recurring reports and <b>Last Reports Generated</b> " +
                "for the ones you ran on the fly."
            )),
            run: "click",
        },
    ],
});
