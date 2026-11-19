import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Document Hub Tour
 *
 * Walks the user through the central document centre ("ศูนย์เอกสาร"), an
 * application whose root menu owns three leaf menus:
 *
 *  1. คลังเอกสารกลาง        - every stored document (ir.attachment + OD19 fields)
 *  2. หมวดหมู่เอกสาร        - the category tree used to classify documents
 *  3. นโยบายการเก็บรักษา    - how long each document type is kept
 *
 * Because the app root has no sub-sections, the three entries render directly
 * in the navbar (`.o_menu_sections`); `navSection()` targets them.
 */
registry.category("web_tour.tours").add("od19_document_hub_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_document_hub.menu_od19_document_root",
            markup(_t(
                "Let's explore the <b>Document Hub</b>: one central place that stores, " +
                "classifies and retains every document."
            ))
        ),

        // --- คลังเอกสารกลาง (central library) ---
        {
            trigger: navSection("คลังเอกสารกลาง"),
            content: markup(_t(
                "Open <b>คลังเอกสารกลาง</b>, the central library that lists every stored document."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Opening a menu entry switches the action asynchronously: waiting for
        // the breadcrumb guarantees the new list is really on screen.
        waitForAction("คลังเอกสารกลาง"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each row is a document with its <b>หมวดเอกสาร</b>, <b>ที่มา</b> " +
                "(รับจากภายนอก / สร้างจากระบบ), <b>วันที่เอกสาร</b> and " +
                "<b>ชั้นความลับ</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            content: markup(_t(
                "Use the search filters <b>รับจากภายนอก</b> / <b>สร้างจากระบบ</b> / " +
                "<b>รอสกัดข้อความ</b>, or group by <b>หมวดเอกสาร</b>, <b>ที่มา</b> or " +
                "<b>แผนก</b> to find a document quickly."
            )),
            run: "click",
        },

        // --- หมวดหมู่เอกสาร (categories) ---
        {
            trigger: navSection("หมวดหมู่เอกสาร"),
            content: markup(_t(
                "Open <b>หมวดหมู่เอกสาร</b> to organise documents into a category tree."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("หมวดหมู่เอกสาร"),
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to add a category.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Give the category a <b>name</b>.")),
            run: "edit เอกสารทั่วไป",
        },
        {
            trigger: ".o_field_widget[name='code'] input",
            content: markup(_t(
                "Set a short <b>code</b>: it is used as a prefix when documents are indexed."
            )),
            run: "edit GEN",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- นโยบายการเก็บรักษา (retention policies) ---
        {
            trigger: navSection("นโยบายการเก็บรักษา"),
            content: markup(_t(
                "Open <b>นโยบายการเก็บรักษา</b> to define how long each document type is kept."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("นโยบายการเก็บรักษา"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "A policy sets the <b>ระยะเวลา (เดือน)</b>, the <b>การดำเนินการ</b> once it " +
                "expires (archive / destroy) and the <b>จุดเริ่มนับ</b>. Document Hub keeps " +
                "the whole document lifecycle traceable."
            )),
            run: "click",
        },
    ],
});
