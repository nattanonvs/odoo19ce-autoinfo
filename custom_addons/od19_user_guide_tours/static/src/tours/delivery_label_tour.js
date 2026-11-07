import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Delivery Label Tour
 *
 * Walks the user through the printable delivery cover sheet (FM-PU-12) added
 * to delivery orders by od19_delivery_label:
 *  1. Open Inventory > Operations > Deliveries
 *  2. Open a delivery order and check the DEPT / Project fields
 *  3. Fill the "ใบปะหน้าสินค้า" tab (delivery reasons + contact)
 *  4. Print the report from the Print menu
 *
 * Fields come from views/stock_picking_views.xml (od19_department_code,
 * project_id, the delivery reasons and the contact block) and the report is
 * report/delivery_label_report.xml (ใบปะหน้าสินค้ารอส่ง (FM-PU-12)).
 */
registry.category("web_tour.tours").add("od19_delivery_label_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("มาดู <b>ใบปะหน้าสินค้ารอส่ง (FM-PU-12)</b> บนใบส่งของกัน"))
        ),

        {
            trigger: navSection("Operations"),
            content: markup(_t("เปิดเมนู <b>Operations</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Deliveries"),
            content: markup(_t("เปิด <b>Deliveries</b> (ใบส่งของขาออก)")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Deliveries"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("นี่คือรายการใบส่งของ (การเคลื่อนไหวขาออก) ทั้งหมด")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("คลิกเปิดใบส่งของหนึ่งใบเพื่อดูข้อมูลใบปะหน้า")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_field_widget[name='od19_department_code']",
            content: markup(_t(
                "<b>DEPT</b> (รหัสแผนก) ใช้พิมพ์บนใบปะหน้า FM-PU-12 และเป็นส่วนหนึ่งของเลขที่เอกสาร " +
                "WH/{DEPT}/OUT/... — บังคับสำหรับใบส่งของขาออก"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='project_id']",
            content: markup(_t(
                "<b>Project</b> ดึงมาจากใบสั่งขายที่เชื่อมไว้ และพิมพ์ลงในใบปะหน้าสินค้า"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: "a.nav-link:contains('ใบปะหน้าสินค้า')",
            content: markup(_t("เปิดแท็บ <b>ใบปะหน้าสินค้า</b> เพื่อกรอกเหตุผลการส่งและผู้ติดต่อ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_reason_delivery']",
            content: markup(_t(
                "ติ๊ก <b>เหตุผลการส่ง</b> (สินค้าเคลม / ส่งคืน / ชำรุด / อยู่ในประกัน / ส่งมอบสินค้า / " +
                "เอกสารสำคัญ) แล้วกรอก <b>ผู้ติดต่อสำหรับจัดส่ง</b> (ชื่อ + เบอร์โทร)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_cp_action_menus button[data-hotkey='shift+u']",
            content: markup(_t(
                "กดปุ่ม <b>Print</b> (ไอคอนเครื่องพิมพ์) แล้วเลือก " +
                "<b>ใบปะหน้าสินค้ารอส่ง (FM-PU-12)</b> เพื่อพิมพ์ใบปะหน้า"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทัวร์ใบปะหน้าสินค้าเสร็จสิ้น! ใบส่งของมี <b>DEPT</b> (บังคับสำหรับขาออก) และ " +
                "<b>Project</b> พร้อมเหตุผล/ผู้ติดต่อในแท็บใบปะหน้าสินค้า — พิมพ์ได้จากเมนู Print (FM-PU-12)"
            )),
            run: "click",
        },
    ],
});
