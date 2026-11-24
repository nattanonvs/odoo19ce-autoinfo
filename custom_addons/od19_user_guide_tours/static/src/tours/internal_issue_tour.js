import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Internal Issue Tour
 *
 * Walks the user through the internal-issue workflow that od19_internal_issue
 * layers on top of the OCA Helpdesk ticket. The 2026 revision replaced the old
 * tier-validation flow with a "fair queue":
 *  1. Report the issue in the IT Support queue (subject, description)
 *  2. Classify it: ประเภทเรื่อง (issue stream) + ผู้แจ้ง + visibility (public /
 *     department / private) + emergency flag
 *  3. Score it fairly — Impact × Urgency -> the Odoo priority is computed
 *  4. Follow the queue: open the "ความเป็นธรรม & คิว" tab to read the queue
 *     position / ahead count, the consent window and the Knowledge-Base handoff
 *  5. (optionally) ask to jump the queue, which needs a two-level approval
 *     (หัวหน้าแผนกผู้แจ้ง -> หัวหน้าทีมเจ้าของคิว) and is tracked in the
 *     "คำขอแซงคิว" queue
 */
registry.category("web_tour.tours").add("od19_internal_issue_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "helpdesk_mgmt.helpdesk_ticket_main_menu",
            markup(_t("มาดูขั้นตอนการจัดการ <b>ปัญหาภายใน</b> (Internal Issue) กัน"))
        ),

        {
            trigger: navSection("IT Support"),
            content: markup(_t("เปิดคิว <b>IT Support</b> — ทีมดูแลไอที/ระบบขององค์กร")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("IT Support"),
        {
            trigger: ".o_list_renderer, .o_kanban_view",
            content: markup(_t(
                "คิวภายในแสดง <b>ประเภทเรื่อง</b>, <b>ตำแหน่งในคิว</b>, <b>การมองเห็น</b> " +
                "และธง <b>ฉุกเฉิน</b> — ใช้ตัวกรอง <em>ฉุกเฉิน / สาธารณะ / เฉพาะแผนก / ส่วนตัว</em> " +
                "ที่เมนู <b>ตัวกรอง</b> เพื่อเจาะดูเรื่องที่ต้องการ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_button_add, .o-kanban-button-new",
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
                "ใช้กำหนดว่าเรื่องนี้จะอยู่ในคิว <b>เรื่องของฉัน</b> ของใคร"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='visibility']",
            content: markup(_t(
                "กำหนด <b>การมองเห็น</b>: สาธารณะ (ทุกคน) / เฉพาะแผนก (จะปรากฏช่อง <em>แผนกที่มองเห็น</em> ให้ระบุ) " +
                "/ ส่วนตัว (เฉพาะผู้แจ้งและผู้รับผิดชอบ)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='emergency']",
            content: markup(_t(
                "ติ๊ก <b>ฉุกเฉิน (Emergency)</b> เพื่อแจ้งเตือนทุกช่องทางทันที " +
                "(รวมหัวหน้าทีมและทีม Triage) แต่การแทรกคิวยังต้องผ่านการอนุมัติแซงคิว"
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
            content: markup(_t(
                "เปิดแท็บ <b>ความเป็นธรรม &amp; คิว</b> เพื่อให้คะแนนและดูตำแหน่งในคิว"
            )),
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
            isActive: ["button[name='action_request_jump']:visible"],
            trigger: "button[name='action_request_jump']:visible",
            content: markup(_t(
                "ถ้าจำเป็นต้องด่วนกว่า ให้กด <b>ขอแซงคิว</b> — ต้องอนุมัติ 2 ชั้น " +
                "(หัวหน้าแผนกผู้แจ้ง → หัวหน้าทีมเจ้าของคิว)"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),

        // ติดตามคิวคำขอแซงคิว (แสดงเฉพาะเมื่อเมนูอยู่ในแถบนำทาง)
        {
            isActive: [navSection("คำขอแซงคิว")],
            trigger: navSection("คำขอแซงคิว"),
            content: markup(_t("เปิดคิว <b>คำขอแซงคิว</b> เพื่อติดตาม/อนุมัติคำขอทั้งหมด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [navSection("คำขอแซงคิว")],
            ...waitForAction("คำขอแซงคิว"),
        },
        {
            isActive: [navSection("คำขอแซงคิว")],
            trigger: ".o_list_renderer",
            content: markup(_t(
                "แต่ละคำขอแสดง <b>สถานะ</b> (ร่าง → รอหัวหน้าแผนก → รอหัวหน้าทีม → อนุมัติ/ปฏิเสธ/หมดอายุ), " +
                "<b>ผู้อนุมัติ</b> และ <b>กำหนดหมดอายุ</b>"
            )),
            tooltipPosition: "bottom",
        },

        {
            trigger: navSection("IT Support"),
            content: markup(_t("กลับมาที่คิว <b>IT Support</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("IT Support"),
        {
            trigger: ".o_list_renderer, .o_kanban_view",
            content: markup(_t(
                "จบการแนะนำ <b>ปัญหาภายใน</b> แล้ว! แจ้งเรื่อง → จัดประเภท/ให้คะแนน " +
                "→ ระบบคำนวณความสำคัญและจัดคิวอย่างเป็นธรรม → ติดตามจากคิวและคำขอแซงคิว"
            )),
            run: "click",
        },
    ],
});
