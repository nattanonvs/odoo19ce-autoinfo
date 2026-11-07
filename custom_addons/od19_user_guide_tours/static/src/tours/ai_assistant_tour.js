import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 AI Assistant Tour
 *
 * Walks the user through the self-hosted AI Assistant application
 * (od19_ai_assistant — "AI Assistant / ผู้ช่วย AI"):
 *  1. Open the "AI Assistant" app and browse past conversations
 *  2. Start a new conversation and type a question
 *  3. Send it with "Ask AI"
 *  4. Read the answer (or the error message when the endpoint is not reachable)
 */
registry.category("web_tour.tours").add("od19_ai_assistant_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_ai_assistant.menu_od19_ai_root",
            markup(_t("มาลองใช้ <b>ผู้ช่วย AI</b> ที่รันบนเครื่อง/เซิร์ฟเวอร์ของคุณเองกัน"))
        ),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ลิสต์นี้เก็บ <b>ประวัติการสนทนา</b> ทั้งหมด: วันที่สร้าง ผู้ใช้ " +
                "<b>สถานะ</b> (สำเร็จ/ผิดพลาด) และโมเดลที่ใช้"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>สร้าง</b> เพื่อเริ่มบทสนทนาใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='prompt'] textarea",
            content: markup(_t("พิมพ์ <b>คำถาม</b> ที่ต้องการถามผู้ช่วย AI")),
            run: "edit สรุปยอดค้างชำระของลูกค้ารายใหญ่ให้หน่อย",
        },
        {
            trigger: "button[name='action_ask']",
            content: markup(_t(
                "กด <b>Ask AI</b> เพื่อส่งคำถามไปยังปลายทาง AI " +
                "(Ollama หรือ endpoint ที่รองรับ OpenAI)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='state']",
            content: markup(_t(
                "สถานะจะเปลี่ยนเป็น <b>เสร็จสิ้น</b> เมื่อได้คำตอบ " +
                "หรือ <b>ผิดพลาด</b> หากเชื่อมต่อปลายทางไม่ได้"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='response'], .o_field_widget[name='error_message']",
            content: markup(_t(
                "<b>คำตอบ</b> จะแสดงในส่วน Answer ส่วน <b>ข้อความผิดพลาด</b> " +
                "จะแสดงเมื่อตั้งค่า endpoint ไม่ถูกต้อง — แก้ไขได้ที่ General Settings → AI Assistant"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>ผู้ช่วย AI</b> แล้ว! สร้างบทสนทนา พิมพ์คำถาม แล้วกด Ask AI " +
                "เพื่อรับคำตอบจากโมเดลภายในเครื่อง"
            )),
            run: "click",
        },
    ],
});
