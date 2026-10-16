import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Contacts & Customer Credit Risk Tour
 *
 * Walks the user through:
 *  1. Opening the Contacts app
 *  2. Creating a company partner and assigning Partner Roles
 *     (Commercial Customer, Project Owner, Contractor)
 *  3. Requesting credit (Sales sends request)
 *  4. Approving / rejecting credit (Accounting owner)
 *  5. Blacklisting / clearing a customer
 *  6. Reviewing the Credit & Risk tab
 */
registry.category("web_tour.tours").add("od19_contacts_credit_risk_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "contacts.menu_contacts",
            markup(_t("Let's start by managing your <b>Contacts</b> and <b>Customer Credit Risk</b>."))
        ),
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Create a new <b>Company</b> contact.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the company name."),
            run: "edit OD19 Demo Construction Co., Ltd.",
        },
        {
            trigger: ".o_field_widget[name='email'] input",
            content: markup(_t(
                "Add an <b>email</b>: a commercial customer must have at least one contact channel."
            )),
            run: "edit od19.demo@example.com",
        },
        {
            trigger: ".o_field_widget[name='company_type'] .o_radio_input[data-value='company']",
            content: _t("Set the contact type to 'Company' so partner roles become available."),
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Sales & Purchase')",
            content: markup(_t(
                "Open the <b>Sales &amp; Purchase</b> tab where the Partner Roles are shown."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_is_commercial_customer'] input[type='checkbox']",
            content: markup(_t(
                "Mark this partner as a <b>Commercial Customer</b> (the entity that orders and pays)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_is_project_owner'] input[type='checkbox']",
            content: markup(_t(
                "Mark it as a <b>Project Owner</b> if it owns the project (available only for companies)."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_od19_request_credit']",
            content: markup(_t(
                "Now request credit for this customer. <b>Sales</b> can only request; " +
                "only <b>Accounting</b> can approve."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Credit & Risk')",
            content: markup(_t(
                "Open the <b>Credit &amp; Risk</b> tab to see the full credit and blacklist information."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_credit_request_state']",
            content: markup(_t(
                "The credit status is now <b>Pending</b>, waiting for Accounting review."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_credit_review_note'] textarea",
            content: markup(_t(
                "Accounting must record a <b>review note</b> before approving."
            )),
            run: "edit Approved by Accounting - OD19 demo.",
        },
        {
            trigger: "button[name='action_od19_approve_credit']",
            content: markup(_t(
                "Accounting can now <b>Approve Credit</b>. Once approved, credit sales are allowed."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_blacklist_reason'] textarea",
            content: markup(_t(
                "A <b>blacklist reason</b> is required before blacklisting."
            )),
            run: "edit Overdue balance - OD19 demo.",
        },
        {
            trigger: "button[name='action_od19_set_blacklist']",
            content: markup(_t(
                "If a customer becomes risky, Accounting can <b>Blacklist</b> them. " +
                "Blacklisted customers cannot create Quotations or Sales Orders."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "div.ribbon span:text('Blacklisted')",
            content: markup(_t(
                "A red <b>Blacklisted</b> ribbon now warns every user. " +
                "Use <b>Clear Blacklist</b> to remove it when the risk is resolved."
            )),
            run: "click",
        },
        {
            trigger: "button[name='action_od19_clear_blacklist']",
            content: markup(_t("Click <b>Clear Blacklist</b> to restore the customer.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "That's it! You have learned how to manage partner roles, credit requests, " +
                "and blacklist status. Remember: <b>No credit approval, no credit sale</b>."
            )),
            run: "click",
        },
    ],
});
