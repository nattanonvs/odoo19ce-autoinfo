import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Web Navigation Tour
 *
 * Highlights the global Back / Forward "unified segment" that
 * od19_web_navigation injects into the NavBar, just before the Home Menu:
 *  1. Open the Contacts app (this records a navigation history entry)
 *  2. Discover the segmented back / forward control
 *  3. Go back, then forward again
 *  4. Land back on the Contacts app
 */
registry.category("web_tour.tours").add("od19_web_navigation_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "contacts.menu_contacts",
            markup(_t("เริ่มจากเปิดแอป <b>Contacts</b> กันก่อน"))
        ),
        {
            trigger: ".od19-nav-segmented",
            content: markup(_t(
                "นี่คือ <b>ปุ่มประวัติการนำทาง</b> (Unified Segment) ที่วางไว้ก่อนเมนู Home " +
                "ประกอบด้วยปุ่มย้อนกลับและไปข้างหน้า ใช้ได้จากทุกหน้าจอของระบบ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: "button[aria-label='ย้อนกลับ']",
            content: markup(_t(
                "กด <b>ย้อนกลับ</b> เพื่อย้อนไปหน้าก่อนหน้า (หรือใช้คีย์ลัด <b>Alt + ←</b>)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[aria-label='ไปข้างหน้า']:not([disabled])",
            content: markup(_t(
                "ตอนนี้ <b>ไปข้างหน้า</b> เปิดใช้งานแล้ว กดเพื่อกลับไปหน้าเดิม " +
                "(หรือใช้คีย์ลัด <b>Alt + →</b>)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_menu_brand[data-menu-xmlid='contacts.menu_contacts']",
            content: markup(_t("เรากลับมาอยู่ที่แอป <b>Contacts</b> เหมือนเดิมแล้ว")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_content",
            content: markup(_t(
                "จบการแนะนำ <b>ปุ่มนำทาง</b> แล้ว! ใช้ย้อนกลับ/ไปข้างหน้าเพื่อสลับหน้า " +
                "ได้อย่างรวดเร็วจากทุกที่ในระบบ"
            )),
            run: "click",
        },
    ],
});
