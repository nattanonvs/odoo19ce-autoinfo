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
};
