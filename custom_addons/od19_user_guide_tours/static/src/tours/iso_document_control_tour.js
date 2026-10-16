import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Document Control Tour
 *
 * Walks the user through the 4-level document approval workflow:
 *  Draft → Review → Approval → Final Approval → Approved (→ Obsolete)
 */
registry.category("web_tour.tours").add("od19_iso_document_control_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>ISO Document Control</b> with the 4-level approval workflow."))
        ),

        // --- Configuration: Standards ---
        {
            trigger: navSection('ตั้งค่า'),
            content: markup(_t("Open the <b>ตั้งค่า (Configuration)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('มาตรฐาน ISO'),
            content: markup(_t("Open <b>มาตรฐาน ISO</b> to define ISO standards (e.g. ISO 9001, ISO 14001).")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new ISO standard."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='code'] input",
            content: markup(_t("Enter the <b>standard code</b> (e.g. ISO9001).")),
            run: "edit ISO9001",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the standard name (e.g. ISO 9001:2015)."),
            run: "edit ISO 9001:2015",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Document Categories ---
        {
            trigger: navSection('ตั้งค่า'),
            content: markup(_t("Open the <b>ตั้งค่า (Configuration)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('ประเภทเอกสาร'),
            content: markup(_t("Open <b>ประเภทเอกสาร</b> to define document categories.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new document category."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='prefix'] input",
            content: markup(_t("Enter the <b>prefix</b> for document codes (e.g. MANUAL).")),
            run: "edit MANUAL",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the category name (e.g. Quality Manual)."),
            run: "edit Quality Manual",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Create Controlled Document ---
        {
            trigger: navSection('ควบคุมเอกสาร'),
            content: markup(_t("Open the <b>ควบคุมเอกสาร</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('เอกสารควบคุม'),
            content: markup(_t("Open <b>เอกสารควบคุม</b> to create a controlled document.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new controlled document."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='document_title'] input",
            content: _t("Enter the document title."),
            run: "edit Purchase Order Procedure",
        },
        {
            trigger: ".o_field_widget[name='category_id'] input",
            content: _t("Select the document category."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id'] input",
            content: markup(_t("Select the <b>department</b> (its code becomes the document code prefix, e.g. PU, SA, QA, IA).")),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='owner_id'] input",
            content: _t("Set the document owner."),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='effective_date'] .o_input",
            content: _t("Set the effective date."),
            run: "edit 2026-10-01",
        },
        {
            trigger: ".o_field_widget[name='review_date'] .o_input",
            content: _t("Set the next review date."),
            run: "edit 2027-10-01",
        },
        // 4-level approval roles
        {
            trigger: ".o_field_widget[name='drafter_id'] input",
            content: markup(_t("Set the <b>Drafter</b> (ผู้จัดทำ).")),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='reviewer_id'] input",
            content: markup(_t("Set the <b>Reviewer</b> (ผู้ตรวจทาน).")),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='approver_id'] input",
            content: markup(_t("Set the <b>Approver</b> (ผู้อนุมัติ).")),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='final_approver_id'] input",
            content: markup(_t("Set the <b>Final Approver</b> (ผู้อนุมัติสุดท้าย).")),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item",
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- 4-Level Approval Workflow ---
        {
            trigger: "button[name='action_submit_for_review']",
            content: markup(_t("Click <b>ส่งตรวจทาน</b> (Submit for Review).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_review_approve']",
            content: markup(_t("The Reviewer clicks <b>ตรวจทานผ่าน</b> (Review Approve).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_approve']",
            content: markup(_t("The Approver clicks <b>อนุมัติ</b> (Approve).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_final_approve']",
            content: markup(_t("The Final Approver clicks <b>อนุมัติสุดท้าย</b> (Final Approve).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_mark_obsolete']",
            content: markup(_t(
                "When the document is no longer needed, click <b>เลิกใช้</b> (Mark Obsolete). " +
                "Use <b>สร้าง Revision ใหม่</b> to create a new revision."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ISO Document Control complete! Workflow: <b>Draft → Review → Approval → Final Approval → Approved</b>. " +
                "The 4-level approval ensures proper document control and traceability."
            )),
            run: "click",
        },
    ],
});
