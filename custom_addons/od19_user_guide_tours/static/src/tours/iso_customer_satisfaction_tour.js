import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Customer Satisfaction Tour
 *
 * Walks the user through:
 *  1. Creating a customer satisfaction survey
 *  2. Survey workflow: Draft → Sent → Completed → Closed
 *  3. Periodic reporting
 */
registry.category("web_tour.tours").add("od19_iso_customer_satisfaction_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's measure <b>Customer Satisfaction</b> with surveys and reports."))
        ),

        {
            trigger: ".o_menu_sections a:contains('ความพึงพอใจลูกค้า')",
            content: markup(_t("Open the <b>ความพึงพอใจลูกค้า (Customer Satisfaction)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('แบบสอบถามความพึงพอใจ')",
            content: markup(_t("Open <b>แบบสอบถามความพึงพอใจ (Surveys)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new customer satisfaction survey."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the survey name."),
            run: "edit Customer Satisfaction Survey Q4 2026",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_sent'] input",
            content: _t("Set the survey send date."),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Survey Workflow ---
        {
            trigger: "button[name='action_sent']",
            content: markup(_t("Click <b>ส่งแบบสอบถาม</b> (Sent) when the survey is sent to the customer.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_complete']",
            content: markup(_t("Click <b>ตอบกลับแล้ว</b> (Completed) when the customer responds.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t("Click <b>ปิด</b> (Close) to close the survey.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Periodic Report ---
        {
            trigger: ".o_menu_sections a:contains('รายงานรายงวด')",
            content: markup(_t(
                "Open <b>รายงานรายงวด (Periodic Reports)</b> to aggregate satisfaction scores " +
                "and analyze trends over time."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Customer Satisfaction complete! Survey workflow: " +
                "<b>Draft → Sent → Completed → Closed</b>. " +
                "Use periodic reports to track satisfaction trends and identify improvement areas."
            )),
        },
    ],
});
