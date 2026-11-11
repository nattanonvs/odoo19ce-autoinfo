import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Payment Voucher Tour
 *
 * Walks the user through the payment voucher / receipt workflow of
 * od19_accounting_payment_voucher_reports:
 *  1. Vendors ▸ Payment Vouchers / ใบสำคัญจ่าย (outbound register)
 *  2. The Prepare → Approve → Override gate on the account.payment form
 *  3. Customers ▸ Prepare Receipt / ใบสำคัญรับเงิน (inbound register)
 *  4. The Accounts Payable Prepare/Approve gate in Settings
 */
registry.category("web_tour.tours").add("od19_payment_voucher_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้ <b>ใบสำคัญจ่าย / ใบสำคัญรับเงิน</b> พร้อมขั้นตอน เตรียม–อนุมัติ กัน"))
        ),

        // --- Payment Vouchers register (Vendors) ---
        {
            trigger: navSection("Vendors"),
            content: markup(_t("เปิดเมนู <b>Vendors / ผู้ขาย</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Payment Vouchers / ใบสำคัญจ่าย"),
            content: markup(_t("เปิดทะเบียน <b>ใบสำคัญจ่าย (Payment Vouchers)</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Payment Vouchers / ใบสำคัญจ่าย"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทะเบียนนี้แสดงใบสำคัญจ่ายทุกสถานะ: <b>ร่าง → เตรียมจ่าย → อนุมัติ → จ่ายแล้ว</b> " +
                "พร้อมตัวกรอง ยังไม่จ่าย / เตรียมจ่ายแล้ว / อนุมัติแล้ว และปุ่ม " +
                "<b>พิมพ์ทะเบียน / Print Register</b> ด้านบนของรายการ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อเปิดใบสำคัญจ่ายใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "บนใบสำคัญมีปุ่มควบคุม 3 ปุ่ม: <b>เตรียมจ่าย / Prepare</b> (ผู้จัดทำกดเพื่อส่งเรื่อง) " +
                "→ <b>อนุมัติ / Approve</b> (ผู้อนุมัติกดยืนยัน) และ " +
                "<b>ข้ามการอนุมัติ / Override</b> (สำหรับหัวหน้างานเมื่อจำเป็น)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Payment Receipt register (Customers) ---
        {
            trigger: navSection("Customers"),
            content: markup(_t("เปิดเมนู <b>Customers / ลูกค้า</b> ฝั่งรับเงิน")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Prepare Receipt"),
            content: markup(_t("เปิดทะเบียน <b>Prepare Receipt / ใบสำคัญรับเงิน</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Prepare Receipt"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ใบสำคัญรับเงินคือรายการรับชำระจากลูกค้า (inbound) ใช้ขั้นตอนเตรียม–อนุมัติ " +
                "แบบเดียวกัน และพิมพ์ใบสำคัญรับเงินได้จากเมนู Print"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Payment Voucher tour complete! เปิด/ปิดประตูควบคุมได้ที่ " +
                "<b>Configuration ▸ Settings</b> หัวข้อ " +
                "<b>Accounts Payable – Prepare/Approve Gate</b> " +
                "(บังคับ เตรียม → อนุมัติ ก่อนจ่าย และแยกหน้าที่ผู้จัดทำ–ผู้อนุมัติ)"
            )),
            run: "click",
        },
    ],
});
