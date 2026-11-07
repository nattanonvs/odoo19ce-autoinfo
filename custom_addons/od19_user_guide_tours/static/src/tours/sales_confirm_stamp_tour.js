import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Confirm Stamp Tour
 *
 * Walks the user through the red <b>CONFIRMED</b> stamp of od19_sales_confirm_stamp:
 *  1. Open a sale order and its <b>Stamp</b> page
 *  2. Stamp Date (the switch that drives the stamp) and Stamp Code
 *  3. The printed "Quotation / Order (with Stamp)" report that paints the box
 *
 * The stamp is rendered only when the order is confirmed AND Stamp Date is
 * filled in (report_saleorder_stamp.xml).
 */
registry.category("web_tour.tours").add("od19_sales_confirm_stamp_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาเรียนรู้ตราประทับ <b>CONFIRMED</b> บนใบเสนอราคากัน"))
        ),

        {
            trigger: navSection("Orders"),
            content: markup(_t("เปิดเมนู <b>Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Quotations"),
            content: markup(_t("เปิดรายการ <b>Quotations</b>")),
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
            trigger: ".o_notebook .nav-link:contains('Stamp')",
            content: markup(_t(
                "เปิดแท็บ <b>Stamp</b> ที่อยู่ท้ายฟอร์ม กลุ่ม <b>Confirmed Stamp</b> เก็บข้อมูลที่ใช้พิมพ์ตรา"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='stamp_date']",
            content: markup(_t(
                "<b>Stamp Date</b> คือตัวเปิด/ปิดตราประทับ — ถ้าวันที่ว่าง ตรา " +
                "<b>CONFIRMED</b> จะไม่ขึ้นบนเอกสารที่พิมพ์"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='stamp_code']",
            content: markup(_t(
                "<b>Stamp Code</b> คือรหัสที่โชว์ในช่อง CODE ของตรา (เช่นรหัสโครงการ) " +
                "ส่วน <b>DELIVERY ON</b> ใช้ Commitment Date, <b>JOB</b> ใช้เลข Job ของ Project " +
                "และ <b>SIGN</b> ใช้ผู้ที่กดยืนยันออเดอร์"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_cp_action_menus",
            content: markup(_t(
                "เมื่อออเดอร์ถูก <b>ยืนยัน</b> และ Stamp Date ถูกกรอกแล้ว ให้ใช้เมนู <b>Print</b> " +
                "เลือก <b>Quotation / Order (with Stamp)</b> เพื่อพิมพ์ใบเสนอราคาที่มีตราแดง " +
                "<b>CONFIRMED</b> ต่อท้าย"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer, .o_kanban_view, .o_form_view",
            content: markup(_t(
                "ทัวร์ Confirm Stamp เสร็จสิ้น! กรอก <b>Stamp Date</b> และ <b>Stamp Code</b> " +
                "บนแท็บ Stamp แล้วพิมพ์ด้วย <b>Quotation / Order (with Stamp)</b> เพื่อได้ตรา CONFIRMED"
            )),
            run: "click",
        },
    ],
});
