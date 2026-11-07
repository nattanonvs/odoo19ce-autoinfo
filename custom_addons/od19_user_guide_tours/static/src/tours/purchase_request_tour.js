import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Request Tour
 *
 * Walks the user through the OD19 extension of the OCA Purchase Request app
 * (od19_purchase_request_extend — app root `purchase_request.parent_menu_purchase_request`):
 *  1. Open the "Purchase Requests" app (register of every purchase request)
 *  2. Raise a request and fill the "Thai Info (OD19)" block
 *  3. See the line-level OD19 fields (asset + justification)
 *
 * The OD19 fields come from the module's views: the header group
 * "Thai Info (OD19)" (od19_priority / department_id / od19_budget_year /
 * od19_issue_id), the request reason (od19_request_reason) and the per-line
 * od19_asset_id / od19_justification columns (reached from Show Details).
 */
registry.category("web_tour.tours").add("od19_purchase_request_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase_request.parent_menu_purchase_request",
            markup(_t("มาทำความรู้จักแอป <b>คำขอซื้อ / Purchase Requests</b> พร้อมฟิลด์เฉพาะของ OD19 กัน"))
        ),

        {
            trigger: navSection("Purchase Requests"),
            content: markup(_t("เปิดเมนู <b>Purchase Requests</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Purchase Requests"),
            content: markup(_t("เปิดทะเบียน <b>คำขอซื้อ</b> ทั้งหมด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Purchase Requests"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "แต่ละแถวคือคำขอซื้อหนึ่งใบ ระบบแสดง <b>ความเร่งด่วน</b> เป็น badge " +
                "และสถานะการอนุมัติของคำขอ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("กด <b>New</b> เพื่อสร้างคำขอซื้อใหม่")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_priority']",
            content: markup(_t(
                "เลือก <b>ความเร่งด่วน / Priority</b>: ปกติ (Normal), ด่วน (Urgent) " +
                "หรือ ด่วนพิเศษ (Emergency)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='department_id']",
            content: markup(_t(
                "ระบุ <b>หน่วยงานที่ขอ / Requesting Department</b> " +
                "(ระบบดึงจากแผนกของพนักงานผู้ขอให้อัตโนมัติ)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_budget_year']",
            content: markup(_t(
                "กรอก <b>ปีงบประมาณ / Budget Year</b> (ค่าเริ่มต้นเป็น พ.ศ. ของปีปัจจุบัน)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_issue_id']",
            content: markup(_t(
                "ผูก <b>แหล่งที่มาจากแจ้งปัญหา / Source Issue</b> " +
                "เมื่อคำขอซื้อนี้มาจากใบแจ้งปัญหาของ Helpdesk"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_request_reason']",
            content: markup(_t(
                "กรอก <b>เหตุผลในการขอซื้อ / Request Reason</b> — บังคับเมื่อเลือกความเร่งด่วน " +
                "เป็น ด่วน หรือ ด่วนพิเศษ ไม่งั้นระบบจะไม่ให้ส่งขออนุมัติ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: markup(_t(
                "เพิ่ม <b>รายการขอซื้อ</b> แล้วกดปุ่ม <b>Show Details</b> ของรายการ " +
                "เพื่อใส่ <b>od19_asset_id</b> (ทรัพย์สิน) และ <b>od19_justification</b> " +
                "(เหตุผลรายบรรทัด)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทัวร์คำขอซื้อเสร็จสิ้น! สร้าง <b>New</b> → กรอก Thai Info (OD19): ความเร่งด่วน, " +
                "หน่วยงาน, ปีงบประมาณ, แหล่งที่มา และเหตุผล → เพิ่มรายการ → กด <b>Submit</b> " +
                "เพื่อส่งขออนุมัติ (มีปุ่ม Create RFQ / Done ต่อเมื่ออนุมัติแล้ว)"
            )),
            run: "click",
        },
    ],
});
