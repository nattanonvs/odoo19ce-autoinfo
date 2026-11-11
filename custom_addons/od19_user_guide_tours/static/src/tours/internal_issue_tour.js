import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Internal Issue Tour
 *
 * Walks the user through the internal issue workflow that od19_internal_issue
 * adds on top of the OCA Helpdesk ticket:
 *  1. Open the "Internal Helpdesk" queue of the Helpdesk app
 *  2. Report a ticket (subject, description)
 *  3. Set the visibility (Public / Department / Private) and the Emergency flag
 *  4. Follow the tier-validation workflow:
 *     ร่าง → ส่งตรวจสอบ → ตรวจสอบผ่าน → กำลังดำเนินการ → เสร็จสิ้น
 */
registry.category("web_tour.tours").add("od19_internal_issue_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "helpdesk_mgmt.helpdesk_ticket_main_menu",
            markup(_t("มาดูขั้นตอนการจัดการ <b>ปัญหาภายใน</b> (Internal Issue) กัน"))
        ),

        {
            trigger: navSection("Internal Helpdesk"),
            content: markup(_t("เปิดเมนู <b>Internal Helpdesk</b> ภายในแอป Helpdesk")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Internal Tickets"),
            content: markup(_t("เปิดคิว <b>Internal Tickets</b> ของทีมภายใน")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Internal Tickets"),
        {
            trigger: ".o_kanban_view",
            content: markup(_t(
                "การ์ดแต่ละใบคือหนึ่งปัญหา จัดกลุ่มตาม <b>ขั้นตอน</b> " +
                "ลากการ์ดไปขั้นถัดไปเพื่อเลื่อนสถานะ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o-kanban-button-new",
            content: markup(_t("กด <b>สร้าง</b> เพื่อแจ้งปัญหาภายในใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("กรอก <b>หัวข้อ</b> ของปัญหา")),
            run: "edit เครื่องพิมพ์ชั้น 3 ใช้งานไม่ได้",
        },
        {
            trigger: ".o_field_widget[name='description'] .odoo-editor-editable",
            content: markup(_t("<b>รายละเอียด</b> เป็นฟิลด์บังคับ — อธิบายอาการของปัญหาให้ชัดเจน")),
            tooltipPosition: "bottom",
            run: "editor เครื่องพิมพ์ชั้น 3 ไม่ตอบสนองเมื่อสั่งพิมพ์จากระบบ ERP",
        },
        {
            trigger: ".o_field_widget[name='visibility']",
            content: markup(_t(
                "กำหนด <b>การมองเห็น</b>: Public (ทุกคน) / Department (เฉพาะแผนก) / " +
                "Private (เฉพาะผู้แจ้งและผู้รับผิดชอบ) — เลือก Department แล้วช่องแผนกจะปรากฏขึ้น"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='is_emergency']",
            content: markup(_t(
                "ติ๊ก <b>ฉุกเฉิน (Emergency)</b> หากปัญหาต้องได้รับการอนุมัติเร่งด่วน"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.saveForm(),
        {
            isActive: ["button[name='action_submit']:visible"],
            trigger: "button[name='action_submit']:visible",
            content: markup(_t(
                "กด <b>ส่งตรวจสอบ</b> เพื่อเข้าสู่กระบวนการอนุมัติ (tier validation) " +
                "ก่อนเริ่มดำเนินการ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='state']",
            content: markup(_t(
                "แถบสถานะเดินตาม <b>ร่าง → ส่งตรวจสอบ → ตรวจสอบผ่าน → กำลังดำเนินการ → เสร็จสิ้น</b> " +
                "เมื่อตรวจสอบผ่านแล้วจึงเริ่มดำเนินการและปิดงานได้"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_kanban_view, .o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>ปัญหาภายใน</b> แล้ว! แจ้งปัญหา → กำหนดการมองเห็น/ความฉุกเฉิน " +
                "→ ส่งตรวจสอบ → ดำเนินการจนเสร็จสิ้น"
            )),
            run: "click",
        },
    ],
});
