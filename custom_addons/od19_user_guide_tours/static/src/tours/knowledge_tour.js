import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Knowledge Enhanced Tour
 *
 * Walks the user through:
 *  1. Creating a knowledge article
 *  2. Setting category, emergency flag, and keywords
 *  3. Linking to a helpdesk ticket
 *  4. Using full-text search across articles
 */
registry.category("web_tour.tours").add("od19_knowledge_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_knowledge_enhanced.knowledge_main_menu",
            markup(_t("Let's manage <b>Knowledge Articles</b> for the company wiki."))
        ),

        {
            trigger: ".o_menu_sections a:contains('Articles')",
            content: markup(_t("Open the <b>Articles</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new knowledge article."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the article title."),
            run: "edit How to process a purchase requisition",
        },
        {
            trigger: ".o_field_widget[name='category'] input",
            content: markup(_t("Set the <b>category</b> to organize the article.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='is_emergency'] input",
            content: markup(_t(
                "Toggle <b>Emergency</b> if this article is for emergency procedures " +
                "(these are highlighted in search results)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='keywords'] input",
            content: markup(_t(
                "Add <b>keywords</b> to improve search discoverability " +
                "(comma-separated, e.g. purchase, PR, requisition)."
            )),
            run: "edit purchase, PR, requisition, approval",
        },
        {
            trigger: ".o_field_widget[name='ticket_id'] input",
            content: markup(_t(
                "Optionally link the article to a <b>helpdesk ticket</b> " +
                "for context on why it was created."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Full-text search ---
        {
            trigger: ".o_searchview_input",
            content: markup(_t(
                "Use the <b>search bar</b> to search across article content, " +
                "keywords, and category. Full-text search makes finding procedures easy."
            )),
            run: "click",
        },

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Knowledge Enhanced complete! Create articles with categories, keywords, " +
                "and emergency flags. Use full-text search to find procedures quickly."
            )),
        },
    ],
});
