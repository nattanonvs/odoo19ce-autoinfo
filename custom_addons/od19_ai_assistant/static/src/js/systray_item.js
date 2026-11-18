/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { aiPanelState, toggleAiPanel } from "./ai_panel";

/**
 * Systray button that opens/closes the shared AI panel on every page.
 *
 * Hotkey ``alt+shift+p`` — chosen because ``alt+shift+a`` is already taken by
 * the mail activities menu (addons/mail/.../activity_menu.js:28).
 */
export class Od19AiSystrayItem extends Component {
    static template = "od19_ai_assistant.SystrayItem";
    static props = {};

    setup() {
        // Subscribe to the shared panel state (direct reads do not subscribe).
        this.panelState = useState(aiPanelState);
        useHotkey("alt+shift+p", () => toggleAiPanel());
    }

    get isOpen() {
        return this.panelState.open;
    }

    toggle() {
        toggleAiPanel();
    }
}

registry
    .category("systray")
    .add("od19_ai_assistant.ai_button", { Component: Od19AiSystrayItem }, { sequence: 50 });
