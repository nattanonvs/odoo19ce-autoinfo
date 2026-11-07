import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Prepayment Tour
 *
 * Walks the user through the "Prepare Payments" workflow of
 * od19_accounting_prepayment:
 *  1. Accounting ▸ Vendors ▸ Prepare Payments — the OCA `account.billing`
 *     document (renamed from "Billing" to the OD15 wording "Prepare Payments")
 *  2. The "Prepare Payments" smart button that back-links a Vendor Bill,
 *     a Purchase Order or a Payment to the prepayment batch
 */
registry.category("web_tour.tours").add("od19_prepayment_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้ขั้นตอน <b>เตรียมจ่าย (Prepare Payments)</b> กันเลย"))
        ),

        // --- Prepare Payments register (Vendors) ---
        {
            trigger: navSection("Vendors"),
            content: markup(_t("เปิดเมนู <b>Vendors / ผู้ขาย</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Prepare Payments"),
            content: markup(_t(
                "เปิด <b>Prepare Payments / เตรียมจ่าย</b> — ทะเบียนที่รวบรวมใบตั้งหนี้ผู้ขาย " +
                "หลายใบไว้จ่ายรวมกันในรอบเดียว"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Prepare Payments"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "แต่ละแถวคือชุดเอกสาร <b>เตรียมจ่าย</b>: เลือกผู้ขายและงวดวันที่ครบกำหนด " +
                "แล้วระบบจะรวบใบตั้งหนี้ที่ค้างจ่ายมาให้ จากนั้นกด <b>Validate</b> เพื่อยืนยัน " +
                "และ <b>Register Payment</b> เพื่อตั้งจ่ายทั้งชุด"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Back-link smart button on the source documents ---
        {
            trigger: navSection("Vendors"),
            content: markup(_t("กลับไปที่เมนู <b>Vendors</b> เพื่อดูฝั่งใบตั้งหนี้")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Bills"),
            content: markup(_t("เปิด <b>Bills / ใบตั้งหนี้ผู้ขาย</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Bills"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "เมื่อเปิดใบตั้งหนี้ (Vendor Bill) ใบสั่งซื้อ (Purchase Order) หรือรายการจ่าย " +
                "(Payment) จะมีปุ่มอัจฉริยะ <b>Prepare Payments</b> แสดงจำนวนรายการเตรียมจ่าย " +
                "ที่ผูกกับเอกสารนั้น — กดเพื่อเปิดดูย้อนหลังได้ทันที"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Prepayment tour complete! รวบใบตั้งหนี้ผู้ขาย → <b>Prepare Payments</b> → " +
                "<b>Validate</b> → <b>Register Payment</b> แล้วย้อนดูได้จากปุ่ม " +
                "<b>Prepare Payments</b> บนเอกสารต้นทาง"
            )),
            run: "click",
        },
    ],
});
