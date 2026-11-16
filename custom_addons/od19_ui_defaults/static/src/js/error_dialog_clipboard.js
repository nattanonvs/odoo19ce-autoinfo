/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ErrorDialog, RPCErrorDialog } from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";

/**
 * `navigator.clipboard` is only exposed in a secure context (HTTPS or
 * localhost). When Odoo is served over plain HTTP -- as on the pre-production
 * host -- it is `undefined`, so the error dialogs' "Copy" button throws
 * "Cannot read properties of undefined (reading 'writeText')" and the dialog
 * closes before the user can read or report the traceback.
 *
 * Route the copy through the legacy `document.execCommand("copy")` when the
 * Clipboard API is unavailable so the button keeps working on insecure origins.
 */
function copyWithExecCommand(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "0";
    textarea.style.left = "-1000px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
        document.execCommand("copy");
    } finally {
        textarea.remove();
    }
}

function copyToClipboard(text) {
    const clipboard = browser.navigator && browser.navigator.clipboard;
    if (clipboard && typeof clipboard.writeText === "function") {
        return clipboard.writeText(text).catch(() => copyWithExecCommand(text));
    }
    copyWithExecCommand(text);
    return Promise.resolve();
}

patch(ErrorDialog.prototype, {
    onClickClipboard() {
        copyToClipboard(
            `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.props.traceback}`
        );
        this.showTooltip();
    },
});

patch(RPCErrorDialog.prototype, {
    onClickClipboard() {
        copyToClipboard(
            `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.traceback}`
        );
        this.showTooltip();
    },
});
