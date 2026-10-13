import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Management Review Tour
 *
 * Walks the user through the management review lifecycle:
 *  Draft → Planned → In Progress → Reviewed → Closed
 */
registry.category("web_tour.tours").add("od19_iso_management_review_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's conduct a <b>Management Review</b> of the management system."))
        ),

        {
            trigger: ".o_menu_sections a:contains('การทบทวนระบบจัดการ')",
            content: markup(_t("Open the <b>การทบทวนระบบจัดการ (Management Review)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new management review meeting."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the review name."),
            run: "edit Management Review Meeting Q4 2026",
        },
        {
            trigger: ".o_field_widget[name='date'] input",
            content: _t("Set the review meeting date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='reviewer_id'] input",
            content: _t("Set the lead reviewer (top management)."),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Management Review Workflow ---
        {
            trigger: "button[name='action_plan']",
            content: markup(_t("Click <b>วางแปรยัง</b> (Plan) to schedule the review.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มประชุม</b> (Start) when the meeting begins.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_reviewed']",
            content: markup(_t(
                "Click <b>ทบทวนแล้ว</b> (Reviewed) when all inputs have been discussed " +
                "(audit results, customer feedback, process performance, etc.)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t(
                "Click <b>ปิด</b> (Close) to finalize the review. " +
                "Decisions and actions should be recorded before closing."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Management Review complete! Workflow: " +
                "<b>Draft → Planned → In Progress → Reviewed → Closed</b>. " +
                "Management review ensures the QMS remains suitable, adequate, and effective."
            )),
        },
    ],
});
