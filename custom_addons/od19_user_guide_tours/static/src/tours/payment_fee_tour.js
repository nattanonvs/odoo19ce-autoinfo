import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Payment Fee Tour
 *
 * Walks the user through the payment fee / bank charges feature of
 * od19_accounting_payment_fee:
 *  1. Vendors ▸ Payments — create a payment
 *  2. Record the bank fee (`fee_amount`) and its expense account (`fee_account_id`)
 *  3. The fee is split out of the principal amount automatically
 */
registry.category("web_tour.tours").add("od19_payment_fee_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้การบันทึก <b>ค่าธรรมเนียมการจ่าย (Payment Fee)</b> กัน"))
        ),

        // --- Open a vendor payment ---
        {
            trigger: navSection("Vendors"),
            content: markup(_t("เปิดเมนู <b>Vendors / ผู้ขาย</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Payments"),
            content: markup(_t("เปิด <b>Payments / รายการจ่ายผู้ขาย</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Vendor Payments"),
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อสร้างรายการจ่ายใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Amount + fee ---
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: markup(_t("กรอก <b>จำนวนเงิน</b> ที่จ่าย")),
            run: "edit 10000",
        },
        {
            trigger: ".o_field_widget[name='fee_amount'] input",
            content: markup(_t(
                "ช่อง <b>Payment Fee / ค่าธรรมเนียม</b> ใช้บันทึกค่าธรรมเนียมธนาคาร " +
                "หรือส่วนต่างที่ถูกหักจากยอดจ่าย"
            )),
            run: "edit 100",
        },
        {
            trigger: ".o_field_widget[name='fee_account_id'] input",
            content: markup(_t(
                "เมื่อกรอกค่าธรรมเนียมแล้ว ต้องเลือก <b>บัญชีค่าธรรมเนียม (Fee Account)</b> " +
                "ซึ่งเป็นบัญชีประเภทค่าใช้จ่าย — ระบบจะสร้างรายการค่าธรรมเนียมให้อัตโนมัติ"
            )),
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: markup(_t("เลือกบัญชีค่าใช้จ่ายสำหรับค่าธรรมเนียม")),
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Payment Fee tour complete! ตั้งยอดจ่าย → ใส่ <b>ค่าธรรมเนียม</b> → " +
                "เลือก <b>บัญชีค่าธรรมเนียม</b> แล้วระบบจะแยกค่าธรรมเนียมออกจากยอดเงินต้นให้เอง"
            )),
            run: "click",
        },
    ],
});
