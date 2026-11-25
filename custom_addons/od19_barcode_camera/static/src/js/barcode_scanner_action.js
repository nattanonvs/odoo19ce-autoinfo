/** @odoo-module **/
// Copyright 2026 OD19
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

/**
 * Fullscreen mobile barcode scanner for inventory operations.
 *
 * Reuses the core ``web.BarcodeVideoScanner`` (BarcodeDetector API with a ZXing
 * fallback) so we inherit the same browser/device handling as Odoo itself.
 * Every captured code is resolved server-side through
 * ``od19.barcode.scan.wizard`` and, when opened from a transfer, the operator
 * can write the scanned quantity straight onto the matching move line.
 */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import {
    BarcodeVideoScanner,
    isBarcodeScannerSupported,
} from "@web/core/barcode/barcode_video_scanner";

const TYPE_LABELS = {
    product: _t("สินค้า"),
    lot: _t("ล็อต/ซีเรียล"),
    location: _t("ตำแหน่งจัดเก็บ"),
    package: _t("หีบห่อ"),
    unknown: _t("ไม่รู้จัก"),
};

export class BarcodeScannerAction extends Component {
    static template = "od19_barcode_camera.BarcodeScannerAction";
    static components = { BarcodeVideoScanner };
    static props = {
        "*": true,
        action: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        const params = (this.props.action && this.props.action.params) || {};
        this.state = useState({
            pickingId: params.picking_id || false,
            pickingName: params.picking_name || "",
            isSupported: isBarcodeScannerSupported(),
            isScanning: false,
            isBusy: false,
            manualCode: "",
            errorMessage: "",
            results: [],
        });
    }

    get typeLabels() {
        return TYPE_LABELS;
    }

    // ------------------------------------------------------------------
    // Scanner UI
    // ------------------------------------------------------------------
    toggleScanner() {
        this.state.errorMessage = "";
        this.state.isScanning = !this.state.isScanning;
    }

    onScannerError(error) {
        this.state.errorMessage = error.message || String(error);
    }

    async onScannerResult(code) {
        await this.processBarcode(code);
    }

    onManualKeydown(ev) {
        if (ev.key === "Enter") {
            this.submitManual();
        }
    }

    async submitManual() {
        const code = (this.state.manualCode || "").trim();
        if (!code) {
            return;
        }
        this.state.manualCode = "";
        await this.processBarcode(code);
    }

    // ------------------------------------------------------------------
    // Resolution
    // ------------------------------------------------------------------
    async processBarcode(code) {
        if (this.state.isBusy || !code) {
            return;
        }
        this.state.isBusy = true;
        try {
            const result = await this.orm.call(
                "od19.barcode.scan.wizard",
                "resolve_barcode",
                [code, this.state.pickingId || false]
            );
            this.pushResult(result);
            this.vibrate();
        } catch (error) {
            this.state.errorMessage = error.message || String(error);
        } finally {
            this.state.isBusy = false;
        }
    }

    pushResult(result) {
        result.clientId = `scan-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        result.qty =
            result.picking && result.picking.move_line_id
                ? result.picking.expected_qty
                : 1;
        result.applied = false;
        result.applying = false;
        this.state.results.unshift(result);
        if (this.state.results.length > 50) {
            this.state.results.pop();
        }
    }

    vibrate() {
        try {
            browser.navigator.vibrate?.(60);
        } catch {
            // ignore: vibration is a nice-to-have
        }
    }

    // ------------------------------------------------------------------
    // Actions on a result
    // ------------------------------------------------------------------
    async applyResult(result) {
        if (!this.state.pickingId || result.applying) {
            return;
        }
        result.applying = true;
        try {
            const qty = Number(result.qty);
            const outcome = await this.orm.call(
                "od19.barcode.scan.wizard",
                "apply_scan_to_picking",
                [this.state.pickingId, result.barcode, Number.isFinite(qty) ? qty : null]
            );
            if (outcome.success) {
                result.applied = true;
                this.notification.add(outcome.message, { type: "success" });
            } else {
                this.notification.add(outcome.message, { type: "warning" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            result.applying = false;
        }
    }

    openRecord(result) {
        if (!result.res_model || !result.res_id) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: result.res_model,
            res_id: result.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    clearResults() {
        this.state.results = [];
    }
}

registry.category("actions").add("od19_barcode_camera.scan", BarcodeScannerAction);
