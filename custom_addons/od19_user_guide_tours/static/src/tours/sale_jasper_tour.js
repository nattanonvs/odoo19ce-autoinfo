import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sale Jasper (J-Report OD15) Tour
 *
 * Walks the user through the legacy JasperReports of od19_sale_jasper, ported
 * from Odoo 15. They are all bound to sale.order with
 * `binding_type = "report"`, so they are reached the standard way: open a
 * (quotation / sale order) record and use its <b>Print</b> menu:
 *  1. (J-Report OD15) Sale Order Form    - ใบสั่งขาย
 *  2. the Sales Reports wizard           - e.g. (J-Report OD15) Sale Order Values Report
 *
 * Each wizard opens with target="new" (a dialog), so the tour waits for
 * `.o_dialog .modal-title` instead of using waitForAction().
 */
registry.category("web_tour.tours").add("od19_sale_jasper_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาเริ่มพิมพ์เอกสารขายด้วยชุดรายงาน <b>(J-Report OD15)</b> กัน"))
        ),

        // --- Open a sale order ---
        {
            trigger: navSection("Orders"),
            content: markup(_t("เปิดเมนู <b>Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Quotations"),
            content: markup(_t("เปิดรายการ <b>Quotations</b> เพื่อเข้าไปดูใบเสนอราคา")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Quotations"),
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("คลิกเปิดใบเสนอราคาหนึ่งใบ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_statusbar",
            content: markup(_t(
                "เอกสารขายทุกใบจะมีเมนู <b>Print</b> (ไอคอนเครื่องพิมพ์) อยู่บนแถบเครื่องมือ " +
                "ใช้พิมพ์รายงานที่พอร์ตมาจาก JasperReports ของ Odoo 15"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- (J-Report OD15) Sale Order Form ---
        {
            trigger: ".o_cp_action_menus .o_dropdown_title:text('Print')",
            content: markup(_t("เปิดเมนู <b>Print</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('(J-Report OD15) Sale Order Form')",
            content: markup(_t("เลือก <b>(J-Report OD15) Sale Order Form</b> = ใบสั่งขาย")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "วิซาร์ดพิมพ์จะเปิดเป็นหน้าต่าง เลือก <b>ภาษา</b>, <b>ประเภทวันที่</b> และ " +
                "<b>รูปแบบวันที่</b> แล้วกด <b>Generate</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("กด <b>Close</b> เพื่อปิดวิซาร์ด (ทัวร์ยังไม่พิมพ์จริง)")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- Sales Reports wizard ---
        {
            trigger: ".o_cp_action_menus .o_dropdown_title:text('Print')",
            content: markup(_t("เปิดเมนู <b>Print</b> อีกครั้งเพื่อดูกลุ่มรายงาน <b>Sales Reports</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('(J-Report OD15) Sale Order Values Report')",
            content: markup(_t(
                "เลือก <b>(J-Report OD15) Sale Order Values Report</b> — รายงานยอดขายตามช่วงวันที่ " +
                "และกลุ่มข้อมูล"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "รายงานนี้ต้องระบุ <b>วันที่เริ่ม / สิ้นสุด</b> และ <b>กลุ่ม</b> ของรายงาน " +
                "จากนั้นกด <b>Generate</b> เพื่อสร้างไฟล์"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("ปิดวิซาร์ดได้เลย")),
            tooltipPosition: "top",
            run: "click",
        },

        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer, .o_kanban_view, .o_form_view",
            content: markup(_t(
                "ทัวร์ Sale Jasper เสร็จสิ้น! รายงาน <b>(J-Report OD15)</b> ทุกตัวเข้าถึงได้จากเมนู " +
                "<b>Print</b> ของเอกสารขาย และใช้หน้าตาวิซาร์ดเดียวกัน"
            )),
            run: "click",
        },
    ],
});
