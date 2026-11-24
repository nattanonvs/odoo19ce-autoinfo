import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Internal Helpdesk Tour
 *
 * App-level guide for the OCA Helpdesk application. Since the 2026 internal-issue
 * revision the internal queues are dedicated sections of the single Helpdesk app,
 * so the tour walks the whole cycle:
 *  1. Open the Helpdesk app and the "IT Support" queue
 *  2. Report a ticket: subject, description, ประเภทเรื่อง (issue stream),
 *     ผู้แจ้ง (reported by), visibility and the emergency flag — the team is
 *     routed automatically from the issue stream / routing rules
 *  3. Read the "ความเป็นธรรม & คิว" tab: the fair-queue score (impact x urgency),
 *     the computed priority, the queue position and the consent / Knowledge-Base
 *     handoff
 *  4. Save the ticket and take it with "Assign to me"
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
                "รายการเรื่องภายในแสดง <b>ประเภทเรื่อง</b>, <b>ตำแหน่งในคิว</b>, " +
                "<b>การมองเห็น</b> และธง <b>ฉุกเฉิน</b> — ใช้ตัวกรอง " +
                "<em>ฉุกเฉิน / สาธารณะ / เฉพาะแผนก / ส่วนตัว</em> ที่เมนู <b>ตัวกรอง</b> เพื่อเจาะดูเรื่องที่ต้องการ"
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
            trigger: ".o_field_widget[name='issue_stream']",
            content: markup(_t(
                "เลือก <b>ประเภทเรื่อง</b> — ไอที/ระบบ, ข้อเสนอแนะปรับปรุง, คุณภาพ/ISO (CAPA) " +
                "หรือ <em>ไม่แน่ใจ</em> (ระบบจะส่งเข้าทีม Triage)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='reported_by_id']",
            content: markup(_t(
                "<b>ผู้แจ้ง (Reported by)</b> — ค่าเริ่มต้นคือผู้ใช้ปัจจุบัน " +
                "กำหนดว่าเรื่องนี้จะอยู่ในคิว <b>เรื่องของฉัน</b> ของใคร"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='visibility']",
            content: markup(_t(
                "กำหนด <b>การมองเห็น</b>: สาธารณะ (ทุกคน) / เฉพาะแผนก (จะปรากฏช่อง <em>แผนกที่มองเห็น</em>) " +
                "/ ส่วนตัว (เฉพาะผู้แจ้งและผู้รับผิดชอบ)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='emergency']",
            content: markup(_t(
                "ติ๊ก <b>ฉุกเฉิน (Emergency)</b> เพื่อแจ้งเตือนทุกช่องทางทันที " +
                "(รวมหัวหน้าทีมเจ้าของเรื่องและหัวหน้าทีม Triage)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='team_id']",
            content: markup(_t(
                "ทีมถูกกำหนดให้ <b>อัตโนมัติ</b> ตามประเภทเรื่องและกฎการส่งเรื่อง " +
                "(เรื่องที่ไม่ระบุประเภทจะเข้าทีม Triage)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='priority']",
            content: markup(_t(
                "<b>ความสำคัญ</b> คำนวณอัตโนมัติจาก <em>ผลกระทบ × ความเร่งด่วน</em> " +
                "(ผู้จัดการปรับได้พร้อมบันทึก audit)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_notebook .nav-link:contains('ความเป็นธรรม')",
            content: markup(_t("เปิดแท็บ <b>ความเป็นธรรม &amp; คิว</b> เพื่อให้คะแนนและดูตำแหน่งในคิว")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='impact']",
            content: markup(_t("ให้คะแนน <b>ผลกระทบ</b> — เฉพาะตัวเอง / หลายแผนก / กระทบทั้งบริษัท")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='urgency']",
            content: markup(_t(
                "ให้คะแนน <b>ความเร่งด่วน</b> — ไม่กระทบ / มีผลแต่มีงานแทนชั่วคราว / หยุดงานทันที"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='queue_position']",
            content: markup(_t(
                "ดู <b>ตำแหน่งในคิว</b> และ <b>งานก่อนหน้า</b> — คิวเรียงตามความสำคัญ " +
                "แล้วจึงตามลำดับคิว/รหัสเรื่อง (FIFO) อย่างเป็นธรรม"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='consent_state']",
            content: markup(_t(
                "<b>สถานะการยินยอม</b> — ปกติเป็น <em>ยินยอม (เข้าคิว)</em> " +
                "และมีช่อง <em>เปิดให้ขอแซงคิวถึง</em> กำหนดช่วงเวลาที่กดขอแซงคิวได้"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='kb_converted']",
            content: markup(_t(
                "เมื่อแนวทางแก้ไขมีค่า ให้ทำเครื่องหมาย <b>แปลงเป็น KB</b> " +
                "และอ้างอิงบทความคลังความรู้ในช่อง <em>อ้างอิงบทความ KB</em>"
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
                "→ รับเรื่องด้วย <b>Assign to me</b> → ติดตามจาก <b>เรื่องของฉัน</b> " +
                "และติดตาม/อนุมัติคำขอแซงคิวได้ที่คิว <b>คำขอแซงคิว</b>"
            )),
            run: "click",
        },
    ],
});
