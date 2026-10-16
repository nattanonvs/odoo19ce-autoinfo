import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Internal Audit Tour
 *
 * Walks the user through:
 *  1. Creating an annual audit program
 *  2. Creating an audit from the program
 *  3. Audit workflow: Draft → Planned → In Progress → Report → Follow-up → Closed
 *  4. Managing audit findings
 */
registry.category("web_tour.tours").add("od19_iso_internal_audit_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Internal Audits</b> from planning to closure."))
        ),

        // --- Audit Program ---
        {
            trigger: ".o_menu_sections :contains('การตรวจสอบภายใน'), .dropdown-item:contains('การตรวจสอบภายใน')",
            content: markup(_t("Open the <b>การตรวจสอบภายใน (Internal Audit)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('แผนการตรวจสอบประจำปี'), .dropdown-item:contains('แผนการตรวจสอบประจำปี')",
            content: markup(_t("Open <b>แผนการตรวจสอบประจำปี (Annual Audit Program)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new annual audit program."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the program name."),
            run: "edit Internal Audit Program 2026",
        },
        {
            trigger: ".o_field_widget[name='year'] input",
            content: _t("Enter the audit year."),
            run: "edit 2026",
        },
        {
            trigger: ".o_field_widget[name='scope'] textarea",
            content: _t("Describe the audit scope."),
            run: "edit All departments - Quality Management System",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_approve']",
            content: markup(_t("Click <b>อนุมัติ</b> (Approve) the audit program.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Audit ---
        {
            trigger: ".o_menu_sections :contains('การตรวจสอบ'), .dropdown-item:contains('การตรวจสอบ')",
            content: markup(_t("Open <b>การตรวจสอบ (Audits)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new audit."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='title'] input",
            content: _t("Enter the audit title."),
            run: "edit QMS Audit - Production Department",
        },
        {
            trigger: ".o_field_widget[name='program_id'] input",
            content: _t("Link this audit to the annual program."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='audit_type'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>audit type</b> (Internal, External, Surveillance).")),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Audit Workflow ---
        {
            trigger: "button[name='action_plan']",
            content: markup(_t("Click <b>วางแปรยัง</b> (Plan) to set the audit in planned state.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มตรวจสอบ</b> (Start) to begin the audit.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_report']",
            content: markup(_t("Click <b>รายงานผล</b> (Report) to submit the audit report.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_follow_up']",
            content: markup(_t("Click <b>ติดตามผล</b> (Follow-up) to track corrective actions.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t("Click <b>ปิดการตรวจสอบ</b> (Close) to close the audit.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Audit Findings ---
        {
            trigger: ".o_menu_sections :contains('ผลการตรวจสอบ'), .dropdown-item:contains('ผลการตรวจสอบ')",
            content: markup(_t("Open <b>ผลการตรวจสอบ (Audit Findings)</b> to manage nonconformities found during audits.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Internal Audit complete! Workflow: " +
                "<b>Draft → Plan → In Progress → Report → Follow-up → Closed</b>. " +
                "Audit findings are linked to Nonconformity/CAPA for corrective action tracking."
            )),
            run: "click",
        },
    ],
});
