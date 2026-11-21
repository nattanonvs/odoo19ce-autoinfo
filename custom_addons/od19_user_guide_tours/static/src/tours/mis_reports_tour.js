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
 *  1. MIS Reports            - saved report instances (temporary = False):
 *                              configure a new one, then open the seeded
 *                              "งบแสดงฐานะทางการเงิน (Balance Sheet)" instance
 *                              and read its KPI table.
 *  2. Last Reports Generated - ad-hoc instances produced by one-off runs.
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
            content: markup(_t("The <b>MIS Reporting</b> group gathers the MIS Builder reports.")),
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
        // --- Configure a new instance (template + comparison columns) ---
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
                "hit <b>Preview</b> to render the KPI grid. We will not save this one."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Open the seeded Balance Sheet instance ---
        {
            trigger: ".o_list_renderer .o_data_row:contains('Balance Sheet') .o_data_cell:contains('Balance Sheet')",
            content: markup(_t("Open the seeded <b>งบแสดงฐานะทางการเงิน (Balance Sheet)</b> instance.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='report_id']",
            content: markup(_t("<b>Template</b> is the KPI definition (<code>mis.report</code>); the Balance Sheet template maps each Odoo <code>account_type</code> to a report line.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='comparison_mode']",
            content: markup(_t("With <b>comparison mode</b> enabled the instance shows several periods side by side: เดือนปัจจุบัน / เดือนก่อน / เดือนเดียวกันปีก่อน.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='target_move']",
            content: markup(_t("<b>Target Moves</b> = <b>Posted</b> means only posted journal entries are included in the balances.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: "button[name='preview']",
            content: markup(_t("Click <b>Preview</b> to compute and display the report.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".oe_mis_builder_content table.mis_builder",
            content: markup(_t("Every line is a <b>KPI</b> and every column is a comparison period. The amounts come straight from the account balances.")),
            timeout: 30000,
        },
        {
            trigger: "table.mis_builder tbody td:contains('รวมสินทรัพย์')",
            content: markup(_t("<b>รวมสินทรัพย์ (Total assets)</b> is the sum of the six asset lines above it: cash, receivables, other current assets, prepayments, non-current and fixed assets.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: "table.mis_builder tbody td:contains('รวมหนี้สินและส่วนของผู้ถือหุ้น')",
            content: markup(_t("<b>รวมหนี้สินและส่วนของผู้ถือหุ้น</b> = total liabilities + total equity. It must equal <b>รวมสินทรัพย์</b> — that is the accounting equation.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: "table.mis_builder tbody td:contains('ผลต่าง')",
            content: markup(_t("The <b>bs_check</b> line shows <b>สินทรัพย์ − หนี้สินและส่วนของผู้ถือหุ้น</b>. It must be <b>0</b>; the row turns red (<i>BS - Bad</i>) when the books do not balance.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: "table.mis_builder tbody td:first-child",
            content: markup(_t("Above the table, <b>Refresh</b> recomputes the figures, <b>Print</b> renders a PDF (landscape for this report) and <b>Export</b> downloads an XLSX. The <b>Base date</b> field shifts every relative period, and clicking a figure <b>drills down</b> to the underlying journal items.")),
            tooltipPosition: "top",
        },

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
