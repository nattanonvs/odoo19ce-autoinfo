import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ZKTeco Attendance Tour
 *
 * Walks the user through the ZKTeco integration shipped with
 * `od19_hr_attendance_zkteco`:
 *
 *  1. Devices    - register the terminals that push the punches
 *  2. Punch Logs - the raw punches pushed by those terminals
 *
 * Everything lives under Attendances > Configuration > ZKTeco Devices.
 */
registry.category("web_tour.tours").add("od19_hr_attendance_zkteco_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_attendance.menu_hr_attendance_root",
            markup(_t(
                "Let's connect the <b>ZKTeco</b> attendance terminals " +
                "(Attendances > Configuration > ZKTeco Devices)."
            ))
        ),

        // --- Devices ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Devices"),
            content: markup(_t(
                "Open <b>Devices</b> under <b>ZKTeco Devices</b>: every terminal that pushes " +
                "punches is registered here."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The list shows the <b>device name</b>, <b>serial number</b>, <b>location</b>, " +
                "<b>IP</b>, the live <b>status</b> badge (Online / Offline), the " +
                "<b>last activity</b> and the <b>punch count</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to register a terminal.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t(
                "Give the terminal a <b>name</b>, for example <i>Front Gate</i>."
            )),
            run: "edit OD19 Demo Terminal",
        },
        {
            trigger: ".o_field_widget[name='serial_number'] input",
            content: markup(_t(
                "Enter the <b>Serial Number</b> reported by the device (its SN parameter). " +
                "It must be unique, because incoming punches are matched to the device through it."
            )),
            run: "edit OD19-DEMO-SN-001",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "The remaining groups hold the <b>model</b> and <b>firmware</b>, the <b>network</b> " +
                "settings (IP + communication key), the <b>status</b> and the <b>company</b>. " +
                "The <b>Punch Logs</b> tab lists the punches already received from that terminal."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Punch Logs ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("Re-open the <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Punch Logs"),
            content: markup(_t(
                "Open <b>Punch Logs</b>: the raw punches pushed by the terminals."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each punch records the <b>punch time</b>, the <b>device</b>, the " +
                "<b>employee identifier</b> sent by the terminal, the resolved <b>employee</b>, " +
                "the <b>punch type</b> and the <b>status</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Rows in <span class='text-danger'>red</span> are errors and " +
                "<span class='text-warning'>orange</span> rows mean the employee could not be " +
                "matched. Both can be repaired and re-processed with the <b>Process</b> button."
            )),
            run: "click",
        },
    ],
});
