/** Auto-Info Employee Portal — backend shortcut to jump back to the portal. */
import { registry } from "@web/core/registry";

export const od19PortalHotkeyService = {
    dependencies: ["hotkey", "action"],
    start(env, { hotkey, action }) {
        // Alt+P opens the employee portal from anywhere in the backend.
        // "alt" is the overlay modifier of the hotkey service, so the shortcut
        // also works while a dialog or an overlay is open.
        hotkey.add(
            "alt+p",
            () => {
                action.doAction({
                    type: "ir.actions.act_url",
                    url: "/employee-portal",
                    target: "self",
                });
            },
            { global: true }
        );
    },
};

registry.category("services").add("od19_portal_hotkey", od19PortalHotkeyService);
