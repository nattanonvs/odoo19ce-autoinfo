import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO DAR Tour
 *
 * The Document Action Request (ใบคำขอ DAR) drives every change to a controlled
 * document through the same 4-level approval used by ISO Document Control:
 *  ร่าง → รอตรวจทาน → รออนุมัติ → รออนุมัติสุดท้าย → อนุมัติแล้ว → ปิด.
 *
 * The DAR menus live under ISO Management > ควบคุมเอกสาร, next to the
 * "ทะเบียนสำเนา" (copy register) and "รายงานสรุป DAR" reports.
 *
 * Each approval step is guarded server-side by `_check_approval_role`: the
 * acting user must be the configured reviewer / approver / final approver (an
 * administrator bypasses the check), therefore the tour sets all three roles to
 * the same user before walking the workflow.
 */
registry.category("web_tour.tours").add("od19_iso_dar_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t(
                "Let's raise a <b>Document Action Request (DAR)</b> and walk it through the " +
                "approval workflow."
            ))
        ),

        // --- เปิดเมนู ใบคำขอ DAR ---
        {
            trigger: navSection("ควบคุมเอกสาร"),
            content: markup(_t("Open the <b>ควบคุมเอกสาร</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("ใบคำขอ DAR"),
            content: markup(_t(
                "Open <b>ใบคำขอ DAR</b>: one request per change to a controlled document."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ใบคำขอ DAR"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The list shows the <b>เลขที่ DAR</b>, <b>ประเภทคำขอ</b> " +
                "(ออกใหม่ / แก้ไข / เลิกใช้ / ขอสำเนา), the referenced document, " +
                "the department and the coloured <b>สถานะ</b>."
            )),
            run: "click",
        },

        // --- สร้างใบคำขอใหม่ ---
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a request.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='reason'] textarea",
            content: markup(_t(
                "Explain the <b>เหตุผล / ความจำเป็น</b> of the request."
            )),
            run: "edit ขอเอกสารควบคุมใหม่สำหรับขั้นตอนจัดซื้อ",
        },
        // Approval roles: an empty Many2one input shows no usable suggestion, so
        // each role is typed first and then picked from the suggestion list.
        {
            trigger: ".o_field_widget[name='reviewer_id'] input",
            content: markup(_t("Set the <b>ผู้ตรวจทาน</b> (Reviewer).")),
            run: "edit Administrator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Administrator')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='approver_id'] input",
            content: markup(_t("Set the <b>ผู้อนุมัติ</b> (Approver).")),
            run: "edit Administrator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Administrator')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='final_approver_id'] input",
            content: markup(_t("Set the <b>ผู้อนุมัติสุดท้าย</b> (Final Approver).")),
            run: "edit Administrator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Administrator')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='effective_date'] .o_input",
            content: markup(_t("Set the <b>วันที่มีผล</b> (effective date).")),
            run: "edit 2026-10-01",
        },
        ...stepUtils.saveForm(),

        // --- 4-level approval workflow ---
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
            trigger: "button[name='action_close']",
            content: markup(_t(
                "Once approved, click <b>ปิดใบ</b> (Close) to archive the request."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- ทะเบียนสำเนา (copy register) ---
        {
            trigger: navSection("ควบคุมเอกสาร"),
            content: markup(_t("Re-open the <b>ควบคุมเอกสาร</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("ทะเบียนสำเนา"),
            content: markup(_t(
                "Open <b>ทะเบียนสำเนา</b>: the register of controlled and uncontrolled " +
                "copies issued for each document."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ทะเบียนสำเนา"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each row records the <b>ประเภทสำเนา</b>, the <b>ผู้รับ</b>, the " +
                "<b>เลขที่สำเนา</b> and the <b>วันที่ออก</b>."
            )),
            run: "click",
        },

        // --- รายงานสรุป DAR (summary report) ---
        {
            trigger: navSection("ควบคุมเอกสาร"),
            content: markup(_t("Re-open the <b>ควบคุมเอกสาร</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("รายงานสรุป DAR"),
            content: markup(_t(
                "Open <b>รายงานสรุป DAR</b>: a pivot/graph view of all requests grouped by " +
                "<b>สถานะ</b> and <b>ประเภท</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("รายงานสรุป DAR"),
        {
            trigger: ".o_pivot_view, .o_graph_renderer, .o_list_renderer",
            content: markup(_t(
                "Use the pivot and graph views to monitor how many requests are pending, " +
                "approved or rejected across the organisation."
            )),
            run: "click",
        },
    ],
});
