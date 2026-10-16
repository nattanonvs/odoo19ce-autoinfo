import { _t } from "@web/core/l10n/translation";
import { stepUtils as coreStepUtils } from "@web_tour/tour_utils";

/**
 * Manual-mode friendly `stepUtils` for the OD19 user guide tours.
 *
 * Core `stepUtils.showAppsMenuItem()` declares
 * `isActive: ["auto", "community", "desktop"]`. Because that list contains
 * "auto", `TourStep.active` (web_tour/static/src/js/tour_step.js) turns the
 * step OFF as soon as the tour runs in manual mode. The "open the app
 * switcher" step is therefore silently skipped, and the following
 * `.o_app[...]` step waits for an element that is not on screen yet (starting
 * a tour redirects to `/odoo`, which lands on the first app, not on the app
 * grid). Users clicking "Onboarding" end up seeing nothing happen.
 *
 * Overriding `goToAppSteps` keeps every other core helper untouched while
 * making the app-switcher step depend on what is actually displayed instead of
 * on the tour mode.
 */
export const stepUtils = {
    ...coreStepUtils,

    showAppsMenuItem() {
        return {
            isActive: ["body:not(:has(.o_app))"],
            trigger: ".o_navbar_apps_menu button:enabled",
            tooltipPosition: "bottom",
            run: "click",
        };
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            {
                isActive: ["body:not(:has(.o_app))"],
                trigger: ".o_navbar_apps_menu button:enabled",
                content: description,
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "right",
                run: "click",
            },
        ].map((step) =>
            this.addDebugHelp(this._getHelpMessage("goToApp", dataMenuXmlid, description), step)
        );
    },

    /**
     * Manual-mode friendly `saveForm()`. Core gates the click behind
     * `isActive: ["auto"]`, so the step is inactive in manual mode: the record
     * is never saved and the following steps wait for a state that never comes.
     */
    saveForm() {
        return [
            {
                isActive: [".o_control_panel .o_form_button_save"],
                content: _t("Save the record."),
                trigger: ".o_control_panel .o_form_button_save",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".o_form_readonly, .o_form_saved",
            },
        ];
    },

    /**
     * Manual-mode friendly `discardForm()`. Same `isActive: ["auto"]` problem
     * as `saveForm()`: without the fix the form is never left, and the next
     * `goToAppSteps()` gets stuck behind the dirty form.
     */
    discardForm() {
        return [
            {
                isActive: [".o_control_panel .o_form_button_cancel"],
                content: _t("Discard the form to leave it."),
                trigger: ".o_control_panel .o_form_button_cancel",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger:
                    ".o_view_controller.o_list_view, .o_form_view > div > main > .o_form_readonly, .o_form_view > div > main > .o_form_saved",
            },
        ];
    },
};
