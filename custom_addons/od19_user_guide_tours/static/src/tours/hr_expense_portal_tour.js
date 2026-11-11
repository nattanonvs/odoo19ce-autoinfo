import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 HR Expense Portal Tour
 *
 * Walks the employee through the two employee-facing entries that
 * od19_hr_expense_portal adds to the standard Expenses app:
 *  1. "ยื่นใบเบิกค่าใช้จ่าย" — a single-dialog wizard to raise a new expense
 *     (category, employee, date, description, amount or mileage, submit now)
 *  2. "ใบเบิกของฉัน" — a personal kanban of the employee's own expenses
 */
registry.category("web_tour.tours").add("od19_hr_expense_portal_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("มาลองใช้พอร์ทัล <b>เบิกค่าใช้จ่าย</b> ของพนักงานกัน"))
        ),

        // --- 1. Quick create wizard ---
        {
            trigger: navSection("ยื่นใบเบิกค่าใช้จ่าย"),
            content: markup(_t(
                "เปิด <b>ยื่นใบเบิกค่าใช้จ่าย</b> เพื่อสร้างใบเบิกใหม่ในหน้าต่างเดียว"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='expense_category_id']",
            content: markup(_t(
                "เลือก <b>หมวดค่าใช้จ่าย</b> — ถ้าเป็นหมวดค่าเดินทาง (Mileage) " +
                "ระบบจะสลับช่องเป็น ระยะทาง × อัตราต่อกิโลเมตรให้อัตโนมัติ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='employee_id']",
            content: markup(_t("ยืนยัน <b>พนักงาน</b> เจ้าของใบเบิก (ค่าเริ่มต้นคือตัวคุณเอง)")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='expense_date']",
            content: markup(_t("ระบุ <b>วันที่</b> ที่เกิดค่าใช้จ่าย")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='description'] input",
            content: markup(_t("กรอก <b>รายละเอียด</b> ของค่าใช้จ่าย")),
            run: "edit ค่าเดินทางเข้าพบลูกค้า - เดโม OD19",
        },
        {
            trigger: ".o_field_widget[name='total_amount']",
            content: markup(_t(
                "<b>ยอดรวม</b> คำนวณให้เองจากจำนวนเงิน หรือ ระยะทาง × อัตรา ในกรณี Mileage"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='submit_now']",
            content: markup(_t(
                "ติ๊ก <b>ส่งอนุมัติทันที</b> เพื่อยื่นขออนุมัติหลังสร้าง " +
                "หรือเอาออกเพื่อเก็บเป็นฉบับร่างก่อน"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: "footer button[special='cancel']",
            content: markup(_t(
                "กด <b>ยกเลิก</b> ที่นี่เพื่อดูขั้นตอนโดยไม่สร้างข้อมูลตัวอย่างจริง " +
                "(ปุ่ม <b>ยื่นใบเบิก</b> จะสร้างและส่งใบเบิกจริง)"
            )),
            tooltipPosition: "top",
            run: "click",
        },

        // --- 2. My Expenses kanban ---
        {
            trigger: navSection("ใบเบิกของฉัน"),
            content: markup(_t("เปิด <b>ใบเบิกของฉัน</b> เพื่อดูใบเบิกทั้งหมดของคุณ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
            content: markup(_t(
                "การ์ดแต่ละใบคือหนึ่งใบเบิก จัดกลุ่มตาม <b>สถานะ</b> " +
                "และแสดงพนักงาน เจ้าของ และคำใบ้การอนุมัติ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_kanban_view",
            content: markup(_t(
                "จบการแนะนำ <b>พอร์ทัลเบิกค่าใช้จ่าย</b> แล้ว! ยื่นใบเบิกผ่านวิซาร์ด " +
                "แล้วติดตามสถานะของตัวเองได้จาก <b>ใบเบิกของฉัน</b>"
            )),
            run: "click",
        },
    ],
});
