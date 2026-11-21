import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Internal Helpdesk Tour
 *
 * Walks the user through the internal IT helpdesk. Since the 2026 internal-issue
 * revision the internal queues are dedicated sections of the single OCA Helpdesk
 * application, so the tour opens them directly:
 *  1. Open the Helpdesk app
 *  2. Open the "IT Support" queue and browse the internal tickets
 *  3. Report a ticket (subject, description) — the team is routed automatically
 *  4. Assign the ticket to yourself
 *  5. Follow your own reported issues from the "เรื่องของฉัน" (my issues) queue
 */
registry.category("web_tour.tours").add("od19_internal_helpdesk_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "helpdesk_mgmt.helpdesk_ticket_main_menu",
            markup(_t("มาดูขั้นตอนการจัดการตั๋ว <b>Internal Helpdesk</b> กัน"))
        ),

        {
            trigger: navSection("IT Support"),
            content: markup(_t("เปิดคิว <b>IT Support</b> — คิวงานไอที/ระบบขององค์กร")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("IT Support"),
        {
            trigger: ".o_list_renderer, .o_kanban_view",
            content: markup(_t(
                "รายการเรื่องภายในของทีม พร้อม <b>ประเภทเรื่อง</b>, <b>ตำแหน่งในคิว</b> " +
                "และ <b>การมองเห็น</b>"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_button_add, .o-kanban-button-new",
            content: markup(_t("กด <b>สร้าง</b> เพื่อแจ้งเรื่องใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("กรอก <b>หัวข้อ</b> ของเรื่อง")),
            run: "edit เครื่องพิมพ์ชั้น 3 ใช้งานไม่ได้",
        },
        {
            trigger: ".o_field_widget[name='description'] .odoo-editor-editable",
            content: markup(_t("<b>รายละเอียด</b> เป็นฟิลด์บังคับ — อธิบายอาการของปัญหาให้ชัดเจน")),
            tooltipPosition: "bottom",
            run: "editor เครื่องพิมพ์ชั้น 3 ไม่ตอบสนองเมื่อสั่งพิมพ์จากระบบ ERP",
        },
        {
            trigger: ".o_field_widget[name='team_id']",
            content: markup(_t(
                "ทีมถูกกำหนดให้ <b>อัตโนมัติ</b> ตามประเภทเรื่องและกฎการส่งเรื่อง " +
                "(เรื่องที่ไม่ระบุประเภทจะเข้าทีม Triage)"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.saveForm(),
        {
            isActive: ["button[name='assign_to_me']:visible"],
            trigger: "button[name='assign_to_me']:visible",
            content: markup(_t("กด <b>Assign to me</b> เพื่อรับเรื่องนี้ไปดูแล")),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: navSection("เรื่องของฉัน"),
            content: markup(_t("เปิดคิว <b>เรื่องของฉัน</b> — รวมเรื่องที่คุณเป็นผู้แจ้ง")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("เรื่องของฉัน"),

        {
            trigger: ".o_list_view, .o_kanban_view",
            content: markup(_t(
                "จบการแนะนำ <b>Internal Helpdesk</b> แล้ว! แจ้งเรื่อง → ระบบส่งเข้าทีมตามประเภท " +
                "→ รับเรื่องด้วย <b>Assign to me</b> → ติดตามจาก <b>เรื่องของฉัน</b>"
            )),
            run: "click",
        },
    ],
});
