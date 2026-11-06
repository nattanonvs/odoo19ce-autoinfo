/**
 * OD19 Offline Draft — FormController patch.
 *
 * ต่อเฉพาะ lifecycle: autosave แบบ debounce, เช็คร่างตอนเปิดฟอร์ม,
 * ล้างร่างเมื่อบันทึกจริงสำเร็จ — ไม่แก้ logic เดิมของฟอร์ม
 */
import { onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { DraftBanner } from "./draft_banner";

const RELATIONAL_MARKERS = ["2many", "many2one", "reference"];

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.od19DraftService = useService("od19_draft");
        this.od19DraftEnabled = this.od19DraftService.isEnabled(this.props.resModel);
        this.od19DraftBanner = useState({ visible: false, draft: null });
        this.od19DraftTimer = null;
        if (!this.od19DraftEnabled) {
            return;
        }
        onMounted(() => this._od19LookupDraft());
        onWillUnmount(() => this._od19CancelTimer());
        useEffect(
            () => {
                this._od19CollectPayload();
            },
            () => [this.model.root.resId, this.model.root.isInEdition]
        );
    },

    _od19RecordKey() {
        return this.model.root.resId || this.props.resId || 0;
    },

    _od19CollectPayload() {
        const root = this.model.root;
        if (!root || !root.isInEdition) {
            return null;
        }
        const payload = {};
        for (const [name, value] of Object.entries(root.data)) {
            if (value === undefined || value === null || typeof value === "function") {
                continue;
            }
            if (value && typeof value === "object" && !Array.isArray(value)) {
                continue; // ตัด many2one/x2many ออก เก็บเฉพาะค่าฟิลด์เชิงสเกลาร์
            }
            payload[name] = value;
        }
        this._od19ScheduleSave(payload);
        return payload;
    },

    _od19ScheduleSave(payload) {
        this._od19CancelTimer();
        const delay = (this.od19DraftService.config || {}).debounce_ms || 2000;
        this.od19DraftTimer = setTimeout(async () => {
            const resId = this._od19RecordKey();
            await this.od19DraftService.save(this.props.resModel, resId, payload);
            await this.od19DraftService.syncNow(this.props.resModel, resId, payload);
        }, delay);
    },

    _od19CancelTimer() {
        if (this.od19DraftTimer) {
            clearTimeout(this.od19DraftTimer);
            this.od19DraftTimer = null;
        }
    },

    async _od19LookupDraft() {
        const resId = this.props.resId || 0;
        const draft = await this.od19DraftService.load(this.props.resModel, resId);
        if (draft && draft.payload && Object.keys(draft.payload).length) {
            this.od19DraftBanner.visible = true;
            this.od19DraftBanner.draft = draft;
        }
    },

    async od19RestoreDraft() {
        const draft = this.od19DraftBanner.draft;
        if (!draft) {
            return;
        }
        await this.model.root.update(draft.payload, { save: false });
        this.od19DraftBanner.visible = false;
    },

    async od19DiscardDraft() {
        const resId = this._od19RecordKey();
        await this.od19DraftService.clear(this.props.resModel, resId);
        try {
            await this.od19DraftService.syncNow(this.props.resModel, resId, null);
        } catch (error) {
            // fail-safe
        }
        this.od19DraftBanner.visible = false;
        this.od19DraftBanner.draft = null;
    },

    async onRecordSaved(record) {
        const result = await super.onRecordSaved(...arguments);
        if (this.od19DraftEnabled && record) {
            this._od19CancelTimer();
            await this.od19DraftService.clear(this.props.resModel, record.resId);
            this.od19DraftBanner.visible = false;
            this.od19DraftBanner.draft = null;
        }
        return result;
    },
});

patch(FormController, {
    components: {
        ...FormController.components,
        DraftBanner,
    },
});

void RELATIONAL_MARKERS;
