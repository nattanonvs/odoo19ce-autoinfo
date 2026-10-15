import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Calibration Tour
 *
 * Walks the user through:
 *  1. Registering measuring equipment
 *  2. Scheduling and performing calibration
 *  3. Calibration record workflow: Draft → Scheduled → In Progress → Passed/Failed
 */
registry.category("web_tour.tours").add("od19_iso_calibration_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Equipment Calibration</b> for ISO compliance."))
        ),

        {
            trigger: ".o_menu_sections :contains('การสอบเทียบเครื่องมือ'), .dropdown-item:contains('การสอบเทียบเครื่องมือ')",
            content: markup(_t("Open the <b>การสอบเทียบเครื่องมือ (Calibration)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('เครื่องมือวัดและสอบเทียบ'), .dropdown-item:contains('เครื่องมือวัดและสอบเทียบ')",
            content: markup(_t("Open <b>เครื่องมือวัดและสอบเทียบ (Measuring Equipment)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Register a new measuring equipment."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the equipment name."),
            run: "edit Digital Caliper 0-150mm",
        },
        {
            trigger: ".o_field_widget[name='serial_no'] input",
            content: _t("Enter the serial number."),
            run: "edit DC-2026-001",
        },
        ...stepUtils.saveForm(),

        // --- Calibration Records ---
        {
            trigger: ".o_menu_sections :contains('บันทึกการสอบเทียบ'), .dropdown-item:contains('บันทึกการสอบเทียบ')",
            content: markup(_t("Open <b>บันทึกการสอบเทียบ (Calibration Records)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new calibration record."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='equipment_id'] input",
            content: _t("Select the equipment to calibrate."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_planned'] input",
            content: _t("Set the planned calibration date."),
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Calibration Workflow ---
        {
            trigger: "button[name='action_schedule']",
            content: markup(_t("Click <b>จัดตาราง</b> (Schedule) to confirm the calibration schedule.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มสอบเทียบ</b> (Start) when calibration begins.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_pass']",
            content: markup(_t(
                "If calibration passes, click <b>ผ่าน</b> (Pass). " +
                "If it fails, click <b>ไม่ผ่าน</b> (Fail)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Calibration complete! Record workflow: " +
                "<b>Draft → Scheduled → In Progress → Passed/Failed</b>. " +
                "Track all measuring equipment and ensure calibration is done on schedule."
            )),
        },
    ],
});
