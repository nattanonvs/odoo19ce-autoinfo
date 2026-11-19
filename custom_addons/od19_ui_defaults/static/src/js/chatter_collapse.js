/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

/**
 * Odoo 19 has no native way to collapse the whole Chatter panel: the panel can
 * only be shown or hidden by the view layout (aside on wide screens, below the
 * sheet otherwise). This patch adds a chevron button on the chatter topbar that
 * collapses or expands the entire panel and remembers the choice per user.
 *
 * The collapsed state is a simple boolean kept in `localStorage` (keyed by the
 * user id) so the preference survives reloads, and the CSS
 * (chatter_collapse.css) reacts to the `active` marker on the toggle button --
 * no DOM juggling required, which keeps the patch resilient to layout changes.
 */
const STORAGE_KEY_PREFIX = "od19_ui_defaults.chatter_collapsed";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.isChatterCollapsed = this.readChatterCollapsePreference();
    },

    get chatterCollapseButtonLabel() {
        return this.state.isChatterCollapsed ? _t("Expand chatter") : _t("Collapse chatter");
    },

    readChatterCollapsePreference() {
        return browser.localStorage.getItem(`${STORAGE_KEY_PREFIX}.${user.userId}`) === "1";
    },

    toggleChatterCollapse() {
        this.state.isChatterCollapsed = !this.state.isChatterCollapsed;
        browser.localStorage.setItem(
            `${STORAGE_KEY_PREFIX}.${user.userId}`,
            this.state.isChatterCollapsed ? "1" : "0"
        );
    },
});
