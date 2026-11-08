import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Security Roles Tour
 *
 * Walks the user through the central role / department-scope model managed by
 * od19_security_roles (Layer-1 security groups + the res.users "Role"):
 *  1. Open Settings > Users & Companies > Users
 *  2. Review the role and department columns
 *  3. Inspect a user's Access Rights: Role, department scope and OD19 Roles
 */
registry.category("web_tour.tours").add("od19_security_roles_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("มาดูการจัดการ <b>บทบาทและขอบเขตแผนก</b> ของผู้ใช้งานกัน"))
        ),
        {
            trigger: navSection("Users & Companies"),
            content: markup(_t("เปิดเมนู <b>Users & Companies</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Users"),
            content: markup(_t("เปิด <b>Users</b> เพื่อดูรายชื่อผู้ใช้งานทั้งหมด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Users"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ลิสต์ผู้ใช้แสดง <b>บทบาท (Role)</b> และคอลัมน์ <b>แผนก</b> " +
                "ที่ถูก mirror มาจากแผนกของพนักงานโดยอัตโนมัติ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t("เปิดผู้ใช้คนแรกเพื่อดูรายละเอียดสิทธิ์")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Access Rights')",
            content: markup(_t("เปิดแท็บ <b>Access Rights</b> ที่รวมบทบาทและกลุ่มความปลอดภัย")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='role']",
            content: markup(_t(
                "<b>Role</b> คือบทบาทกลางของ OD19 (เช่น ผู้จัดการบัญชี/ขาย) " +
                "แต่ละบทบาทจะ imply กลุ่มความปลอดภัยที่จำเป็นให้โดยอัตโนมัติ"
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_department_id']",
            content: markup(_t(
                "<b>แผนก</b> กำหนดขอบเขตการมองเห็นข้อมูล (อ่านอย่างเดียว) " +
                "ควบคู่กับกลุ่มกลาง <b>OD19 Department Scope / All Departments</b>"
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>บทบาทความปลอดภัย</b> แล้ว! บริหารบทบาทที่ Role " +
                "และกำหนดขอบเขตแผนกที่ Access Rights → OD19 Roles"
            )),
            run: "click",
        },
    ],
});
