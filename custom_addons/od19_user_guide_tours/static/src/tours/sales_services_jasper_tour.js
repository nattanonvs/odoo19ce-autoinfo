import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Services Jasper (J-Report OD15) Tour
 *
 * Walks the user through the legacy Jasper print forms ported from Odoo 15
 * that live in od19_sales_services_jasper. Each form is bound to one record
 * model with `binding_type = "report"`, so it is reached from the record's
 * <b>Print</b> menu:
 *  - (J-Report OD15) Sales Services Form   ใบรับงานบริการ   (Service Card)
 *  - (J-Report OD15) Claim Form            ใบเคลม          (Warranty Claim)
 *  - (J-Report OD15) Product Return Form   ใบรับคืนสินค้า   (Product Return)
 *  - (J-Report OD15) Distribute Order Form ใบส่งของ        (Transport Order)
 *
 * The tour starts in Sales (Product Return is a Sales menu) and then switches
 * to Inventory for the flagship Sales Services Form on the Service Card. Every
 * wizard opens with target="new" (a dialog), so the tour waits for
 * `.o_dialog .modal-title` instead of using waitForAction().
 */
registry.category("web_tour.tours").add("od19_sales_services_jasper_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาเริ่มพิมพ์เอกสารงานบริการด้วยชุดรายงาน <b>(J-Report OD15)</b> กัน"))
        ),

        // --- (J-Report OD15) Product Return Form ---
        {
            trigger: navSection("Product Returns"),
            content: markup(_t("จากแอป Sales เปิดเมนู <b>Product Returns</b> (ใบรับคืนสินค้า)")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Product Returns"),
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("คลิกเปิดรายการรับคืนสินค้าหนึ่งรายการ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_cp_action_menus .o_dropdown_title:text('Print')",
            content: markup(_t("เปิดเมนู <b>Print</b> ของเอกสาร")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('(J-Report OD15) Product Return Form')",
            content: markup(_t("เลือก <b>(J-Report OD15) Product Return Form</b> = ใบรับคืนสินค้า")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "วิซาร์ดพิมพ์เปิดเป็นหน้าต่าง เลือก <b>ภาษา</b>, <b>ประเภทวันที่</b>, " +
                "<b>รูปแบบวันที่</b> แล้วกด <b>Generate</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("กด <b>Close</b> เพื่อปิดวิซาร์ด (ยังไม่พิมพ์จริง)")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- (J-Report OD15) Sales Services Form on the Service Card ---
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("สลับไปแอป <b>Inventory</b> เพื่อดูฟอร์มบัตรบริการ <b>Sales Services Form</b>"))
        ),
        {
            trigger: navSection("Products"),
            content: markup(_t("เปิดเมนู <b>Products</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Service Cards"),
            content: markup(_t("เปิด <b>Service Cards</b> (บัตรบริการ)")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("คลิกเปิดบัตรบริการหนึ่งใบ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_cp_action_menus .o_dropdown_title:text('Print')",
            content: markup(_t("เปิดเมนู <b>Print</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('(J-Report OD15) Sales Services Form')",
            content: markup(_t("เลือก <b>(J-Report OD15) Sales Services Form</b> = ใบรับงานบริการ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t("ตั้งค่าพารามิเตอร์ของรายงานแล้วกด <b>Generate</b> เพื่อสร้างเอกสาร")),
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
                "ทัวร์ Sales Services Jasper เสร็จสิ้น! รายงาน <b>(J-Report OD15)</b> ทุกใบเข้าถึงได้จากเมนู " +
                "<b>Print</b> ของเอกสารต้นทาง: Product Return Form, Sales Services Form (บัตรบริการ), " +
                "Claim Form (ใบเคลม) และ Distribute Order Form (ใบส่งของ)"
            )),
            run: "click",
        },
    ],
});
