import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Currency Rate BOT Tour
 *
 * Walks the user through the Bank of Thailand exchange rate provider of
 * od19_currency_rate_bot (built on the OCA `currency_rate_update` module):
 *  1. Accounting ▸ Configuration ▸ Currency Rates Providers
 *  2. Create a provider with Service = BOT (Bank of Thailand)
 *  3. The BOT token in Settings and the currency mini bar on documents
 */
registry.category("web_tour.tours").add("od19_currency_rate_bot_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้การดึง <b>อัตราแลกเปลี่ยนจากธนาคารแห่งประเทศไทย (BOT)</b> กัน"))
        ),

        // --- Currency Rates Providers ---
        {
            trigger: navSection("Configuration"),
            content: markup(_t("เปิดเมนู <b>Configuration / ตั้งค่า</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Currency Rates Providers"),
            content: markup(_t("เปิด <b>Currency Rates Providers / ผู้ให้บริการอัตราแลกเปลี่ยน</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Currency Rates Providers"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ที่นี่รวมผู้ให้บริการอัตราแลกเปลี่ยนทั้งหมด รวมถึง <b>BOT — Bank of Thailand</b> " +
                "ที่โมดูลนี้เพิ่มเข้ามา โดยดึงอัตราอ้างอิงจากธนาคารแห่งประเทศไทยเป็นฐาน THB"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อสร้างผู้ให้บริการใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='service'] .o_select_menu_toggler",
            content: markup(_t(
                "เลือก <b>Service = BOT (Bank of Thailand)</b> แล้วกำหนดสกุลเงินที่ต้องการดึง " +
                "และรอบการอัปเดต (กด <b>Update Rates Now</b> เพื่อดึงทันที)"
            )),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains('Bank of Thailand')",
            content: markup(_t("เลือกผู้ให้บริการ <b>Bank of Thailand</b>")),
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "หมายเหตุ: BOT ให้อัตราอ้างอิงจากเงินบาท (THB) เท่านั้น หากสกุลเงินหลักของบริษัท " +
                "ไม่ใช่ THB ระบบจะแสดงคำเตือนว่าอัตราที่แปลงได้อาจคลาดเคลื่อน"
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ตั้งค่า Token ของ BOT ได้ที่ <b>Configuration ▸ Settings</b> หัวข้อ " +
                "<b>BOT Provider</b> และบนเอกสาร (ใบแจ้งหนี้/ใบสั่งซื้อ/ใบสั่งขาย/รายการจ่าย) " +
                "จะมี <b>แถบสกุลเงิน (currency mini bar)</b> โชว์อัตราแลกเปลี่ยนล่าสุด " +
                "พร้อมปุ่มรีเฟรชอัตราให้"
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Currency Rate BOT tour complete! ใช้ผู้ให้บริการ <b>BOT</b> ดึงอัตราแลกเปลี่ยน " +
                "อัตโนมัติ และดูอัตราล่าสุดได้จากแถบสกุลเงินบนเอกสาร"
            )),
            run: "click",
        },
    ],
});
