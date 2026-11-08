import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Operational Closure Tour
 *
 * Walks the user through the operational closure gating added by
 * od19_accounting_operational_closure:
 *  1. Accounting ▸ Accounting ▸ Journal Entries — the closure fields carried
 *     on every account.move
 *  2. The same closure state exposed on Sales Orders and Purchase Orders
 *     (incl. the "Accept Service" button on PO service lines)
 */
registry.category("web_tour.tours").add("od19_operational_closure_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("มาเรียนรู้ <b>การปิดงานเชิงปฏิบัติการ (Operational Closure)</b> กัน"))
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
                "ทุกเอกสารบัญชีจะพาสถานะการปิดงานเชิงปฏิบัติการติดมาด้วย " +
                "เพื่อให้รู้ว่าเอกสารนี้ปิดครบทุกขั้นหรือยัง"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อดูโครงสร้างเอกสารบัญชี")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "ในส่วนหัวของเอกสารมี 3 ฟิลด์ควบคุม: <b>od19_operational_flow</b> (เส้นทางปฏิบัติการ), " +
                "<b>od19_operational_closure_state</b> (สถานะการปิดงาน) และ " +
                "<b>od19_source_document</b> (เอกสารต้นทาง)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "สถานะการปิดงานเดียวกันนี้ยังแสดงบน <b>ใบสั่งขาย (Sales Order)</b> " +
                "(od19_invoice_closure_state) และ <b>ใบสั่งซื้อ (Purchase Order)</b> " +
                "(od19_vendor_bill_closure_state) พร้อมปุ่ม <b>Accept Service</b> " +
                "ในบรรทัดบริการของใบสั่งซื้อ"
            )),
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Operational Closure tour complete! ใช้สถานะการปิดงานเพื่อยืนยันว่าเอกสาร " +
                "ขาย/ซื้อ/บัญชี ปิดครบทั้งการออกบิล การรับบริการ และการตั้งหนี้ ก่อนปิดงวดบัญชี"
            )),
            run: "click",
        },
    ],
});
