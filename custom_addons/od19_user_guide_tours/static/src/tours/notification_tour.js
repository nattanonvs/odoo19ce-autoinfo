import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
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
            trigger: navSection("Notifications"),
            content: markup(_t("Open the <b>Notifications</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Channels"),
            content: markup(_t("Open <b>Channels</b> to configure notification delivery channels.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: _t("Open an existing notification channel to review how it is configured."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='channel_type']",
            content: markup(_t(
                "The <b>channel type</b> defines how notifications are delivered: Email, Odoo Inbox or LINE. " +
                "Only one channel per type is allowed, so the system keeps exactly one delivery channel per medium."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='sequence']",
            content: markup(_t(
                "The <b>sequence</b> controls priority (lower number = higher priority when multiple channels match)."
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Notification Preferences ---
        {
            trigger: navSection("Notifications"),
            content: markup(_t("Reopen the <b>Notifications</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("My Preferences"),
            content: markup(_t("Open <b>My Preferences</b> to choose how you want to be notified.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // A preference already saved by a previous run cannot be created again
        // (constraint: one preference per event per user). Open the existing one
        // in that case, otherwise create a new one.
        {
            isActive: [".o_list_renderer .o_data_row"],
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='event']",
            content: _t("Open your existing notification preference to review it."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [".o_list_renderer:not(:has(.o_data_row))"],
            trigger: ".o_list_button_add",
            content: _t("Create a new notification preference."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [".o_form_editable"],
            trigger: ".o_field_widget[name='user_id'] input",
            content: _t("Assign the preference to a user (required)."),
            run: "click",
        },
        {
            isActive: [".o_form_editable"],
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the user from the suggestion list."),
            run: "click",
        },
        {
            isActive: [".o_form_editable"],
            trigger: ".o_field_widget[name='event'] .o_select_menu_toggler",
            content: markup(_t(
                "Select the <b>event</b> you want to be notified about " +
                "(e.g. new ticket assigned, approval requested)."
            )),
            run: "click",
        },
        {
            isActive: [".o_form_editable"],
            trigger: ".o_field_widget[name='channel_ids'] input",
            content: markup(_t(
                "Select the <b>channels</b> to use for this event " +
                "(you can pick multiple, e.g. Email + Line)."
            )),
            run: "click",
        },
        {
            isActive: [".o_form_editable"],
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick a channel from the suggestion list."),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Notification Queue ---
        // Note: "Notification Queue" is a top-level entry of the Settings app
        // (sibling of the "Notifications" menu), not a child of it.
        {
            trigger: navSection("Notification Queue"),
            content: markup(_t(
                "Open the <b>Notification Queue</b> to monitor outgoing notifications."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_view, .o_list_renderer",
            content: markup(_t(
                "Every outgoing notification is queued with its delivery <b>status</b> " +
                "(pending, sending, sent or failed). Open a pending or failed entry and click " +
                "<b>Send Now</b> to retry delivery."
            )),
            run: "click",
        },
        {
            trigger: ".o_content",
            content: markup(_t(
                "Notification Multi-Channel complete! Configure <b>Channels</b>, set personal " +
                "<b>Preferences</b> per event, and monitor the <b>Queue</b> for delivery status. " +
                "Failed notifications can be retried with <b>Send Now</b>."
            )),
            run: "click",
        },
    ],
});
