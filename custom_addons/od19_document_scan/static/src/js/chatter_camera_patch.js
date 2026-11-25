// Copyright 2026 OD19
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

/**
 * Add a "take a photo" button to every chatter in the backend.
 *
 * ``mail.Chatter`` is the single component used by every chatter (form views,
 * the attachment box, activities, ...), so patching it here covers the whole
 * system. The button opens the live camera dialog and uploads the (already
 * compressed) photos exactly like a regular attachment.
 */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { openCameraDialog } from "./camera_dialog";
import { isCameraSupported } from "./image_utils";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },

    get cameraSupported() {
        return isCameraSupported();
    },

    /**
     * Open the camera, then upload every captured photo as an attachment of the
     * current thread (mirrors what the paperclip does for picked files).
     */
    async onCameraCapture() {
        if (!this.cameraSupported) {
            this.notification.add(
                _t("อุปกรณ์หรือเบราว์เซอร์นี้ไม่รองรับกล้อง (ต้องเปิดผ่าน https หรือ localhost)"),
                { type: "warning" }
            );
            return;
        }
        if (!this.state.thread.id) {
            const saved = await this.props.saveRecord?.();
            if (!saved) {
                return;
            }
        }
        const shots = await openCameraDialog(this.env, {
            facingMode: "environment",
            multiple: true,
            prefix: "photo",
        });
        if (!shots.length) {
            return;
        }
        const thread = this.state.thread;
        for (const shot of shots) {
            const file = new File([shot.blob], shot.name, { type: shot.type });
            await this.attachmentUploader.uploadFile(file, { thread });
        }
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        if (this.rootRef.el) {
            this.rootRef.el.scrollTop = 0;
        }
        this.state.thread.scrollTop = "bottom";
    },
});
