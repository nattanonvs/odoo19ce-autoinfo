import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Project & Analytic Accounting Tour
 *
 * Walks the user through:
 *  1. Creating a Project with Job Number
 *  2. Setting Job Type, Department, Project Owner, and Contractors
 *  3. Linking analytic account for P&L tracking
 *  4. The project context hierarchy (Owner → Project → Contractor → Contract)
 */
registry.category("web_tour.tours").add("od19_project_analytic_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "project.menu_main_pm",
            markup(_t(
                "Let's set up a <b>Project</b> with a <b>Job Number</b> to track P&amp;L per project."
            ))
        ),

        {
            trigger: ".o-kanban-button-new",
            content: _t("Create a new project."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='job_no'] input",
            content: markup(_t(
                "Enter the <b>Job Number</b> (e.g. JOB-2026-001). This is the unique identifier for the project."
            )),
            run: "edit JOB-2026-001",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the project name."),
            run: "edit Building A Construction",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer (commercial customer)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='job_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Set the <b>Job Type</b> (construction, service, maintenance, etc.)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department'] input",
            content: _t("Set the responsible department."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='project_owner_id'] input",
            content: markup(_t(
                "Select the <b>Project Owner</b> (filtered to partners marked as Project Owner)."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='contractor_ids'] input",
            content: markup(_t(
                "Add <b>Contractors</b> working on this project. " +
                "One project can have multiple contractors."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: ".o_kanban_view, .o_list_view",
            content: markup(_t(
                "Project setup complete! The hierarchy is: " +
                "<b>1 Project Owner → Many Projects → Many Contractors → Many Contracts</b>. " +
                "Each project has a unique <b>Job Number</b> and an analytic account to track " +
                "revenue, costs, and profit per project."
            )),
            run: "click",
        },
    ],
});
