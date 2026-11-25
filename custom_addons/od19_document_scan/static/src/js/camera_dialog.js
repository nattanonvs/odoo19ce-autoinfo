// Copyright 2026 OD19
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

/**
 * Live camera dialog used to take photos with a phone/tablet camera and feed
 * them (already compressed) either to the chatter or to a binary field.
 *
 * The stream handling mirrors ``web.BarcodeVideoScanner`` so behaviour is the
 * same across browsers, including the iOS WebKit workaround.
 */

import { Component, onMounted, onWillUnmount, status, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { delay } from "@web/core/utils/concurrency";
import { Dialog } from "@web/core/dialog/dialog";
import { isIOS } from "@web/core/browser/feature_detection";
import {
    DEFAULT_PHOTO_PARAMS,
    blobToBase64,
    captureVideoFrame,
    isCameraSupported,
    photoFilename,
} from "./image_utils";

export class CameraDialog extends Component {
    static template = "od19_document_scan.CameraDialog";
    static components = { Dialog };
    static props = {
        captureParams: { type: Object, optional: true },
        facingMode: { type: String, optional: true },
        multiple: { type: Boolean, optional: true },
        prefix: { type: String, optional: true },
        close: Function,
        onCapture: Function,
    };
    static defaultProps = {
        captureParams: DEFAULT_PHOTO_PARAMS,
        facingMode: "environment",
        multiple: true,
        prefix: "scan",
    };

    setup() {
        this.videoRef = useRef("videoPreview");
        this.videoEl = null;
        this.stream = null;
        this.state = useState({
            errorMessage: isCameraSupported()
                ? ""
                : _t(
                      "อุปกรณ์หรือเบราว์เซอร์นี้ไม่รองรับกล้อง " +
                          "(ต้องเปิดผ่าน https หรือ localhost)"
                  ),
            facingMode: this.props.facingMode,
            isBusy: false,
            isReady: false,
            shots: [],
        });
        onMounted(() => this.startCamera());
        onWillUnmount(() => this.stopCamera());
    }

    // ------------------------------------------------------------------
    // Camera lifecycle
    // ------------------------------------------------------------------
    async startCamera() {
        if (!isCameraSupported()) {
            return;
        }
        this.stopCamera();
        let stream;
        try {
            stream = await browser.navigator.mediaDevices.getUserMedia({
                video: { facingMode: this.state.facingMode },
                audio: false,
            });
        } catch (err) {
            const errors = {
                NotFoundError: _t("ไม่พบกล้องในอุปกรณ์นี้"),
                NotAllowedError: _t("กรุณาอนุญาตให้เว็บไซต์เข้าถึงกล้องก่อน"),
            };
            this.state.errorMessage = errors[err.name] || err.message;
            return;
        }
        if (status(this) === "destroyed") {
            stream.getTracks().forEach((track) => track.stop());
            return;
        }
        this.stream = stream;
        if (!this.videoEl) {
            const el = this.videoRef.el;
            if (!el) {
                this.stopCamera();
                return;
            }
            if (isIOS()) {
                // WebKit does not paint a MediaStream inside a <video> cloned
                // from a <template>; re-import it into the main document.
                // See https://bugs.webkit.org/show_bug.cgi?id=320979
                const clone = document.importNode(el);
                el.replaceWith(clone);
                this.videoEl = clone;
            } else {
                this.videoEl = el;
            }
        }
        this.videoEl.srcObject = this.stream;
        await this.waitForVideo();
        if (!this.videoEl) {
            return;
        }
        if (this.videoEl.paused) {
            await this.videoEl.play();
        }
        this.state.isReady = true;
    }

    async waitForVideo() {
        while (this.videoEl && (this.videoEl.readyState < 2 || !this.videoEl.videoWidth)) {
            await delay(30);
            if (status(this) === "destroyed") {
                return;
            }
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
    }

    async switchCamera() {
        this.state.facingMode = this.state.facingMode === "environment" ? "user" : "environment";
        this.state.isReady = false;
        await this.startCamera();
    }

    // ------------------------------------------------------------------
    // Capture
    // ------------------------------------------------------------------
    async capture() {
        if (!this.state.isReady || this.state.isBusy) {
            return;
        }
        this.state.isBusy = true;
        let shot;
        try {
            const blob = await captureVideoFrame(this.videoEl, this.props.captureParams);
            const data = await blobToBase64(blob);
            shot = {
                blob,
                data,
                name: photoFilename(this.props.prefix),
                type: blob.type || "image/jpeg",
                url: URL.createObjectURL(blob),
            };
        } catch (err) {
            this.state.errorMessage = err.message || String(err);
            this.state.isBusy = false;
            return;
        }
        this.state.isBusy = false;
        if (this.props.multiple) {
            this.state.shots.push(shot);
        } else {
            this.finish([shot]);
        }
    }

    removeShot(index) {
        const [shot] = this.state.shots.splice(index, 1);
        if (shot && shot.url) {
            URL.revokeObjectURL(shot.url);
        }
    }

    finish(shots = this.state.shots) {
        const payload = shots.map(({ blob, data, name, type }) => ({ blob, data, name, type }));
        // Resolve before closing: closing triggers the dialog ``onClose`` hook,
        // which resolves the promise with an empty list.
        this.props.onCapture(payload);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}

/**
 * Open the camera and resolve with the captured photos.
 *
 * @param {Object} env the OWL env (needs the ``dialog`` service)
 * @param {Object} [options] forwarded to :class:`CameraDialog`
 * @returns {Promise<Array<{blob: Blob, data: string, name: string, type: string}>>}
 *          an empty array when the user closes the dialog without taking a photo
 */
export function openCameraDialog(env, options = {}) {
    let settled = false;
    let resolvePromise;
    const promise = new Promise((resolve) => {
        resolvePromise = resolve;
    });
    const settle = (value) => {
        if (!settled) {
            settled = true;
            resolvePromise(value);
        }
    };
    env.services.dialog.add(
        CameraDialog,
        {
            ...options,
            onCapture: (shots) => settle(shots || []),
        },
        { onClose: () => settle([]) }
    );
    return promise;
}
