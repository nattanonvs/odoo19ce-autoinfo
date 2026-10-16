import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Notification Multi-Channel Tour
 *
 * Walks the user through:
 *  1. Configuring notification channels (email, SMS, Line, etc.)
 *  2. Setting personal notification preferences per event
 *  3. Monitoring the notification queue and retrying failed sends
 */
registry.category("web_tour.tours").add("od19_notification_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("Let's configure <b>Multi-Channel Notifications</b> (Email, SMS, Line, etc.)."))
        ),

        // --- Notification Channels ---
        {
            trigger: ".o_menu_sections :contains('Notifications'), .dropdown-item:contains('Notifications')",
            content: markup(_t("Open the <b>Notifications</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_sections :contains('Channels'), .dropdown-item:contains('Channels')",
            content: markup(_t("Open <b>Channels</b> to configure notification delivery channels.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new notification channel."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the channel name (e.g. Email Notifications)."),
            run: "edit Email Notifications",
        },
        {
            trigger: ".o_field_widget[name='channel_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Select the <b>channel type</b>: Email, SMS, Line, or other supported channels."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='sequence'] input",
            content: markup(_t(
                "Set the <b>sequence</b> (lower number = higher priority when multiple channels match)."
            )),
            run: "edit 10",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Notification Preferences ---
        {
            trigger: ".o_menu_sections :contains('My Preferences'), .dropdown-item:contains('My Preferences')",
            content: markup(_t("Open <b>My Preferences</b> to choose how you want to be notified.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new notification preference."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='event'] .o_select_menu_toggler",
            content: markup(_t(
                "Select the <b>event</b> you want to be notified about " +
                "(e.g. new ticket assigned, approval requested)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='channel_ids'] input",
            content: markup(_t(
                "Select the <b>channels</b> to use for this event " +
                "(you can pick multiple, e.g. Email + Line)."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Notification Queue ---
        {
            trigger: ".o_menu_sections :contains('Notification Queue'), .dropdown-item:contains('Notification Queue')",
            content: markup(_t(
                "Open the <b>Notification Queue</b> to monitor outgoing notifications."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first",
            content: markup(_t("Open a notification to check its status and resend if needed.")),
            run: "click",
        },
        {
            trigger: "button[name='action_send']",
            content: markup(_t(
                "If a notification is pending or failed, click <b>Send Now</b> to retry delivery."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Notification Multi-Channel complete! Configure <b>Channels</b>, set personal " +
                "<b>Preferences</b> per event, and monitor the <b>Queue</b> for delivery status. " +
                "Failed notifications can be retried with <b>Send Now</b>."
            )),
            run: "click",
        },
    ],
});
