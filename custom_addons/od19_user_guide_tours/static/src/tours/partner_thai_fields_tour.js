import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Partner Thai Fields Tour
 *
 * Walks the user through the Thai-specific fields that
 * od19_partner_thai_fields adds to the standard partner form:
 *  - tax_name, branch_code           (next to VAT — ใบกำกับภาษี / รหัสสาขา)
 *  - od19_subdistrict, od19_amphoe    (next to City — ตำบล/อำเภอ)
 *  - name_en, fax                     (next to Website — ชื่อ/แฟกซ์)
 */
registry.category("web_tour.tours").add("od19_partner_thai_fields_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "contacts.menu_contacts",
            markup(_t("มาดูฟิลด์ภาษาไทยสำหรับคู่ค้าในแอป <b>Contacts</b> กัน"))
        ),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("นี่คือลิสต์คู่ค้าทั้งหมด — เปิดรายการใดก็ได้เพื่อดูฟิลด์ภาษาไทย")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='complete_name']",
            content: markup(_t("เปิดคู่ค้ารายแรกเพื่อดูรายละเอียด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='tax_name']",
            content: markup(_t(
                "<b>Tax Invoice Name</b> — ชื่อที่ใช้พิมพ์บนใบกำกับภาษี " +
                "หากเว้นว่างระบบจะใช้ชื่อคู่ค้าแทน"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='branch_code']",
            content: markup(_t(
                "<b>Branch Code</b> — รหัสสาขา 5 หลักสำหรับรายงานภาษี " +
                "(ใช้ <b>00000</b> สำหรับสำนักงานใหญ่)"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_subdistrict']",
            content: markup(_t("<b>ตำบล/แขวง</b> (Subdistrict / Tambon) ที่อยู่คู่ค้า")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_amphoe']",
            content: markup(_t("<b>อำเภอ/เขต</b> (Amphoe / District) ของที่อยู่")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='name_en']",
            content: markup(_t("<b>ชื่อภาษาอังกฤษ</b> สำหรับการติดต่อหรือจัดส่งระหว่างประเทศ")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='fax']",
            content: markup(_t("<b>แฟกซ์</b> ของคู่ค้า (ฟิลด์มาตรฐานที่เปิดใช้ในโมดูลนี้)")),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>ฟิลด์ภาษาไทยของคู่ค้า</b> แล้ว! กรอก Tax Name, Branch Code, " +
                "ตำบล/อำเภอ และชื่อภาษาอังกฤษ เพื่อให้เอกสารภาษาไทยและใบกำกับภาษีถูกต้องครบถ้วน"
            )),
            run: "click",
        },
    ],
});
