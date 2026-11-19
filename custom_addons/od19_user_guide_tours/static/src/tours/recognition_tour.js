import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Employee Recognition Tour
 *
 * Recognition lives under the Employees app (HR root), restricted to the
 * `group_recognition_manager` group:
 *
 *  1. Kudos  - a public thank-you from one employee to another (optional Badge)
 *  2. Badges - the reusable recognition tags (icon + colour) used by Kudos
 *
 * The Kudos tour is intentionally read-only beyond opening a fresh form: a
 * Kudos needs a linked employee as author, which depends on the HR data of the
 * running database, so the tour explains the fields and discards the draft
 * instead of saving.
 */
registry.category("web_tour.tours").add("od19_recognition_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr.menu_hr_root",
            markup(_t(
                "Let's celebrate colleagues with <b>Recognition</b> (Kudos and Badges)."
            ))
        ),

        // --- Kudos ---
        {
            trigger: navSection("Recognition"),
            content: markup(_t("Open the <b>Recognition</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Kudos"),
            content: markup(_t(
                "Open <b>Kudos</b>: a public thank-you from one employee to another."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        // The action switch is asynchronous; wait for the target list before
        // clicking anything inside it.
        waitForAction("Kudos"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each row shows the <b>ผู้ให้ (From)</b>, <b>ผู้รับ (To)</b>, the optional " +
                "<b>Badge</b>, the <b>ข้อความ</b> and whether it is <b>เผยแพร่สาธารณะ</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to open a blank Kudos.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='recipient_id'] input",
            content: markup(_t(
                "<b>From</b> defaults to you. Set <b>To</b> to the colleague you want to thank " +
                "(you cannot give a Kudos to yourself)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='message'] textarea, .o_field_widget[name='message']",
            content: markup(_t(
                "Write the <b>ข้อความ</b> (500 characters max), optionally attach a <b>Badge</b>, " +
                "then <b>Save</b>."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Badges ---
        {
            trigger: navSection("Recognition"),
            content: markup(_t("Re-open the <b>Recognition</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Badges"),
            content: markup(_t(
                "Open <b>Badges</b>: the reusable tags (ชื่อ / ไอคอน / สี) that Kudos can reference."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Badges"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The badge list is editable inline: add a <b>ชื่อ</b>, pick a Font Awesome " +
                "<b>ไอคอน</b> and a <b>สี</b>, and drag the handle to reorder them."
            )),
            run: "click",
        },
    ],
});
