import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Supplier Quality Tour
 *
 * Walks the user through:
 *  1. Evaluating suppliers
 *  2. Evaluation workflow: Draft → In Progress → Done
 *  3. Approved Supplier List (ASL)
 */
registry.category("web_tour.tours").add("od19_iso_supplier_quality_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Supplier Quality</b> evaluations and the Approved Supplier List."))
        ),

        {
            trigger: ".o_menu_sections :contains('คุณภาพผู้จำหน่าย'), .dropdown-item:contains('คุณภาพผู้จำหน่าย')",
            content: markup(_t("Open the <b>คุณภาพผู้จำหน่าย (Supplier Quality)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('การประเมินผู้จำหน่าย'), .dropdown-item:contains('การประเมินผู้จำหน่าย')",
            content: markup(_t("Open <b>การประเมินผู้จำหน่าย (Supplier Evaluations)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new supplier evaluation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the supplier to evaluate."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='evaluation_date'] input",
            content: _t("Set the evaluation date."),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Evaluation Workflow ---
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มประเมิน</b> (Start) to begin the evaluation.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_done']",
            content: markup(_t(
                "After scoring the supplier on quality, delivery, and service, " +
                "click <b>เสร็จสิ้น</b> (Done) to finalize the evaluation."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Approved Supplier List ---
        {
            trigger: ".o_menu_sections :contains('รายชื่อผู้จำหน่ายที่อนุมัติ'), .dropdown-item:contains('รายชื่อผู้จำหน่ายที่อนุมัติ')",
            content: markup(_t(
                "Open <b>รายชื่อผู้จำหน่ายที่อนุมัติ (ASL)</b> to manage the list of approved suppliers. " +
                "Only suppliers with passing evaluations should be on this list."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Supplier Quality complete! Evaluation workflow: " +
                "<b>Draft → In Progress → Done</b>. " +
                "Maintain the Approved Supplier List (ASL) based on evaluation results."
            )),
            run: "click",
        },
    ],
});
