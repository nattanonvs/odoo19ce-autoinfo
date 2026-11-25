// Copyright 2026 OD19
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

/**
 * ``od19_camera`` field widget: a binary (image) field that can be filled either
 * with a file picker or by taking a photo with the device camera.
 */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import {
    BinaryField,
    ListBinaryField,
    binaryField,
} from "@web/views/fields/binary/binary_field";
import { openCameraDialog } from "./camera_dialog";
import { isCameraSupported } from "./image_utils";

/** Shared camera behaviour for both the form and the list widget. */
const cameraFieldMixin = {
    get cameraSupported() {
        return isCameraSupported();
    },

    get previewUrl() {
        const value = this.props.record.data[this.props.name];
        if (!value) {
            return null;
        }
        if (typeof value === "string") {
            return `data:image/jpeg;base64,${value}`;
        }
        // A binary-size placeholder (record not loaded yet): fall back to the route.
        const { resModel, resId } = this.props.record;
        return resId ? `/web/image/${resModel}/${resId}/${this.props.name}` : null;
    },

    async onCameraCapture() {
        if (!this.cameraSupported) {
            this.notification.add(
                _t("อุปกรณ์หรือเบราว์เซอร์นี้ไม่รองรับกล้อง (ต้องเปิดผ่าน https หรือ localhost)"),
                { type: "warning" }
            );
            return;
        }
        const shots = await openCameraDialog(this.env, {
            facingMode: "environment",
            multiple: false,
            prefix: "scan",
        });
        if (!shots.length) {
            return;
        }
        const [shot] = shots;
        await this.update({ data: shot.data, name: shot.name });
    },
};

export class ScanCameraField extends BinaryField {
    static template = "od19_document_scan.ScanCameraField";
}

export class ListScanCameraField extends ListBinaryField {
    static template = "od19_document_scan.ListScanCameraField";
}

Object.assign(ScanCameraField.prototype, cameraFieldMixin);
Object.assign(ListScanCameraField.prototype, cameraFieldMixin);

export const scanCameraField = {
    ...binaryField,
    component: ScanCameraField,
    displayName: _t("Scan / Camera image"),
};

export const listScanCameraField = {
    ...scanCameraField,
    component: ListScanCameraField,
};

registry.category("fields").add("od19_camera", scanCameraField);
registry.category("fields").add("list.od19_camera", listScanCameraField);
