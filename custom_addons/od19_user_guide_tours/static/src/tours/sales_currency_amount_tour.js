import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Currency Amount Tour
 *
 * Walks the user through the extra currency column added by
 * od19_sales_currency_amount on the sale order list (sale.sale_order_tree,
 * shared by Quotations and Orders):
 *  - amount_untaxed      : ยอดรวมก่อนภาษีในสกุลของเอกสาร (document currency)
 *  - amount_untaxed_curr : ยอดเดียวกันแปลงเป็นสกุลของบริษัท (company currency)
 *
 * The company-currency amount is converted with the order exchange rate, so it
 * matters whenever the order currency differs from the company currency.
 */
registry.category("web_tour.tours").add("od19_sales_currency_amount_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาดู <b>ยอดเงินสองสกุล</b> ในรายการใบเสนอราคากัน"))
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
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ในมุมมองรายการ ระบบแสดงยอดเงินก่อนภาษีทั้ง <b>สกุลของเอกสาร</b> และ " +
                "<b>สกุลของบริษัท</b> ควบคู่กัน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_cell[name='amount_untaxed']",
            content: markup(_t(
                "คอลัมน์ <b>Untaxed Amount</b> คือยอดก่อนภาษีใน <b>สกุลของเอกสาร</b> " +
                "(สกุลที่ออกใบเสนอราคา)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_cell[name='amount_untaxed_curr']",
            content: markup(_t(
                "คอลัมน์ <b>Untaxed Amount (Company Currency)</b> คือยอดเดียวกันที่แปลงเป็น " +
                "<b>สกุลของบริษัท</b> ด้วยอัตราแลกเปลี่ยนของเอกสาร — เมื่อสกุลเอกสารต่างจากสกุลบริษัท " +
                "ตัวเลขสองคอลัมน์นี้จะไม่เท่ากัน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทัวร์ Sales Currency Amount เสร็จสิ้น! ดูยอดก่อนภาษีได้ทั้งในสกุลเอกสาร " +
                "และสกุลบริษัทพร้อมกันในคอลัมน์เดียวของรายการใบเสนอราคา"
            )),
            run: "click",
        },
    ],
});
