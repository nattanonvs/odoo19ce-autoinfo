import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Revision Tour
 *
 * Walks the user through the ISO-style revision control added to Purchase
 * Orders by od19_purchase_revision:
 *  1. Open Purchase > Orders > Purchase Orders
 *  2. Create and confirm a purchase order (approval → confirm)
 *  3. Create a revision (Create Revision) → the new document is /R00, /R01 ...
 *     while the previous document is locked as read-only.
 *
 * The revision fields come from views/purchase_order_views.xml:
 * od19_revision_no / od19_revision_status / od19_revision_of_id and the
 * "Revisions" stat button (od19_revision_count via action_view_revisions).
 */
registry.category("web_tour.tours").add("od19_purchase_revision_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("มาดูระบบ <b>ควบคุมเวอร์ชันเอกสาร / Revision</b> ของใบสั่งซื้อ (สร้าง /R00, /R01 ...) กัน"))
        ),

        {
            trigger: navSection('Orders'),
            content: markup(_t("เปิดเมนู <b>Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Purchase Orders'),
            content: markup(_t("เปิด <b>Purchase Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Purchase Orders"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ในมุมมองรายการ ใช้ตัวกรอง <b>Latest Only</b>, <b>Superseded</b> หรือ " +
                "<b>Has Revision</b> เพื่อดูสายของเวอร์ชัน และเปิดคอลัมน์ <b>Revision No.</b> / " +
                "<b>Revision Status</b> จาก Optional Columns"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t(
                "สร้างใบสั่งซื้อใหม่ แล้วทำให้เป็นเอกสารที่ยืนยันแล้วเพื่อเริ่มทำเวอร์ชัน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("เลือกผู้ขาย (Vendor)"),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("เลือกผู้ขายจากรายการแนะนำ"),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o_field_x2many_list_row_add a",
            content: _t("เพิ่มรายการสินค้า"),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o_field_widget[name='product_id'] input",
            content: _t("เลือกสินค้าที่จะสั่งซื้อ"),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("เลือกสินค้าจากรายการแนะนำ"),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_od19_submit_for_approval']",
            content: markup(_t(
                "กด <b>Submit</b> เพื่อส่งใบสั่งซื้อขออนุมัติจัดซื้อ " +
                "(ทุกใบสั่งซื้อต้องผ่านการอนุมัติก่อนยืนยัน)"
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_od19_approve']",
            content: markup(_t("ผู้จัดการ / ผู้อำนวยการจัดซื้อกด <b>Approve</b> เพื่ออนุมัติ")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[id='draft_confirm']",
            content: markup(_t("กด <b>Confirm Order</b> เพื่อยืนยันใบสั่งซื้อเป็นเอกสารจริง")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_create_revision']",
            content: markup(_t(
                "กด <b>Create Revision</b> (เฉพาะกลุ่ม Purchase Director) ระบบจะสร้างเอกสารใหม่ " +
                "โดยออกเลขต่อท้ายเป็น <b>/R00</b>, <b>/R01</b> ... และล็อกเอกสารเดิมเป็น read-only"
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_revision_no']",
            content: markup(_t(
                "เอกสารใหม่คือเวอร์ชัน <b>/R00</b> ของเอกสารเดิม (Revised From) — " +
                "ดูเวอร์ชันทั้งหมดในสายเดียวกันได้จากปุ่มสถิติ <b>Revisions</b>"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทัวร์ระบบเวอร์ชันเสร็จสิ้น! เอกสารที่ยืนยันแล้ว → <b>Create Revision</b> " +
                "จะได้เวอร์ชันใหม่ /R00, /R01 ... และเอกสารเก่าถูกล็อกไว้เป็นประวัติ"
            )),
            run: "click",
        },
    ],
});
