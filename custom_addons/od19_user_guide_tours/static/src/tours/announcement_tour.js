import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Announcements Tour
 *
 * Walks the user through:
 *  1. Creating an announcement
 *  2. Setting the type, target audience, and expiry
 *  3. Publishing / unpublishing
 *  4. Tracking read receipts
 */
registry.category("web_tour.tours").add("od19_announcement_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_announcement.announcement_main_menu",
            markup(_t("Let's publish <b>Announcements</b> to communicate with employees."))
        ),

        {
            trigger: ".o_list_button_add",
            content: _t("Create a new announcement."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the announcement title."),
            run: "edit New Company Policy Update",
        },
        {
            trigger: ".o_field_widget[name='announcement_type'] select",
            content: markup(_t(
                "Choose the <b>type</b>: <b>Normal</b> or <b>Mandatory</b> " +
                "(mandatory announcements force users to acknowledge)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='target_type'] select",
            content: markup(_t(
                "Choose the <b>target audience</b>: All Users, Specific Department, or Role."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='body'] iframe",
            content: markup(_t("Write the <b>announcement content</b> in the rich text editor.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='expiry_date'] input",
            content: markup(_t("Set an <b>expiry date</b> so the announcement auto-archives.")),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_publish']",
            content: markup(_t(
                "Click <b>Publish</b> to make the announcement visible to the target audience."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Read Receipts')",
            content: markup(_t(
                "Open the <b>Read Receipts</b> tab to see who has read the announcement and when."
            )),
            run: "click",
        },
        {
            trigger: "button[name='action_unpublish']",
            content: markup(_t(
                "Use <b>Unpublish</b> to hide the announcement before its expiry date."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Announcements workflow complete! Create → set audience &amp; expiry → " +
                "<b>Publish</b>. Track read receipts and <b>Unpublish</b> when no longer needed."
            )),
            run: "click",
        },
    ],
});
