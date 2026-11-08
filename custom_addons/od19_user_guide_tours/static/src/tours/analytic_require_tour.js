import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Analytic Requirement Tour
 *
 * Walks the user through the analytic account requirement of
 * od19_accounting_analytic_require:
 *  1. Accounting ▸ Accounting ▸ Journal Entries — Post is blocked when a
 *     configured account is missing its analytic account
 *  2. The info banner shown on the entry form
 *  3. Where to configure the required accounts / journals on the company
 */
registry.category("web_tour.tours").add("od19_analytic_require_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้การ <b>บังคับกรอกบัญชีวิเคราะห์ (Analytic Account)</b> กัน"))
        ),

        // --- Journal Entries ---
        {
            trigger: navSection("Accounting"),
            content: markup(_t("เปิดเมนู <b>Accounting / บัญชี</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Journal Entries"),
            content: markup(_t("เปิด <b>Journal Entries / รายการบัญชี</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Journal Entries"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "รายการบัญชีทั้งหมดอยู่ที่นี่ — เมื่อกดยืนยัน (<b>Post</b>) ระบบจะตรวจว่าบัญชี " +
                "ที่กำหนดไว้ในข้อกำหนดบริษัทมี <b>บัญชีวิเคราะห์</b> ครบหรือไม่ ถ้าขาดจะไม่ให้ผ่าน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อดูคำเตือนบนเอกสาร")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "เมื่อสมุดรายวันไม่ถูกตั้งให้บังคับบัญชีวิเคราะห์ ระบบจะแสดงแถบเตือน " +
                "“Note: Analytic account may be required for some accounts in this entry.” " +
                "เพื่อย้ำให้ผู้ทำบัญชีตรวจสอบก่อนกด Post"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ตั้งค่าได้ที่ <b>Settings ▸ Users &amp; Companies ▸ Companies</b> แท็บ " +
                "<b>Accounting</b> กลุ่ม <b>Analytic Requirement</b> โดยเลือก " +
                "<b>บัญชีที่ต้องใช้บัญชีวิเคราะห์</b> (od19_analytic_required_account_ids) " +
                "และ <b>สมุดรายวันที่บังคับ</b> (od19_analytic_require_journal_ids)"
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Analytic Requirement tour complete! กำหนดบัญชี/สมุดรายวันที่ต้องมีบัญชีวิเคราะห์ " +
                "แล้วระบบจะบล็อกการ Post ที่ตกหล่นให้เอง"
            )),
            run: "click",
        },
    ],
});
