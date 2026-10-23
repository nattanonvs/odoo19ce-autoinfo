import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Meeting Room Booking Tour
 *
 * Walks the user through the meeting room booking shipped with
 * `od19_meeting_room_booking`:
 *
 *  1. Bookings     - the week calendar of every room reservation
 *  2. Room Catalog - the master data of the bookable rooms
 *
 * Everything lives under Calendar > Meeting Rooms.
 */
registry.category("web_tour.tours").add("od19_meeting_room_booking_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "calendar.mail_menu_calendar",
            markup(_t(
                "Let's book a <b>meeting room</b> from the Calendar app " +
                "(Calendar > Meeting Rooms)."
            ))
        ),

        // --- Bookings (calendar view) ---
        {
            trigger: navSection("Meeting Rooms"),
            content: markup(_t("Open the <b>Meeting Rooms</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Bookings"),
            content: markup(_t(
                "Open <b>Bookings</b>: all room reservations in a week calendar, " +
                "coloured by room."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_calendar_view",
            content: markup(_t(
                "Bookings open in the <b>calendar</b> view. Click an empty slot to create a " +
                "booking, or drag an existing one to move it to another time."
            )),
            run: "click",
        },

        // --- Room Catalog ---
        {
            trigger: navSection("Meeting Rooms"),
            content: markup(_t("Re-open the <b>Meeting Rooms</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Room Catalog"),
            content: markup(_t(
                "Open <b>Room Catalog</b> - the master data of every bookable room."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each room shows its <b>capacity</b>, an <b>availability</b> badge " +
                "(Available / Reserved / In Use) and how many <b>bookings</b> it already has."
            )),
            run: "click",
        },
        {
            trigger: ".o_data_row:contains('MR-401') .o_data_cell[name='name']",
            content: markup(_t("Open the <b>MR-401</b> room.")),
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "The room form holds the <b>building</b>, <b>floor</b>, <b>capacity</b>, the " +
                "available <b>equipment</b> (projector, video conference, whiteboard, large " +
                "display) and any <b>room-specific policy</b>."
            )),
            run: "click",
        },
        {
            trigger: "button[name='action_view_bookings']",
            content: markup(_t(
                "The <b>Bookings</b> smart button jumps straight to the reservations of this room."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_calendar_view, .o_list_renderer",
            content: markup(_t(
                "You now only see the bookings of that room. A booking follows the status " +
                "workflow <b>Booked -> In Use -> Done</b>, with <b>Cancel Booking</b> and " +
                "<b>Reopen</b> to move it back."
            )),
            run: "click",
        },
    ],
});
