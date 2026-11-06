/**
 * OD19 Offline Draft — FormController patch.
 *
 * ต่อเฉพาะ lifecycle: autosave แบบ debounce, เช็คร่างตอนเปิดฟอร์ม,
 * ล้างร่างเมื่อบันทึกจริงสำเร็จ — ไม่แก้ logic เดิมของฟอร์ม
 */
import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { DraftBanner } from "./draft_banner";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.od19DraftService = useService("od19_draft");
        this.od19DraftEnabled = this.od19DraftService.isEnabled(this.props.resModel);
        this.od19DraftBanner = useState({ visible: false, draft: null });
        this.od19DraftTimer = null;
        this.od19DraftPendingPayload = null;
        this.od19DraftKeyResId = 0;
        if (!this.od19DraftEnabled) {
            return;
        }
        // FIELD_IS_DIRTY ยิงเมื่อค่าฟิลด์ถูกแก้ (ตอนพิมพ์ และตอน commit ค่าลง model)
        // เป็นสัญญาณเดียวที่เชื่อถือได้ว่าผู้ใช้กำลังแก้ข้อมูลจริงบนฟอร์มนี้
        useBus(this.model.bus, "FIELD_IS_DIRTY", () => this._od19CollectPayload());
        onMounted(() => this._od19LookupDraft());
        onWillUnmount(() => this._od19FlushPending());
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
        this.od19DraftPendingPayload = payload;
        // จำคีย์ ณ ตอนบันทึกร่าง (เรกคอร์ดใหม่ = 0) เพื่อล้างให้ตรงคีย์ตอน save จริง
        this.od19DraftKeyResId = this._od19RecordKey();
        const delay = (this.od19DraftService.config || {}).debounce_ms || 2000;
        this.od19DraftTimer = setTimeout(() => this._od19FlushPending(), delay);
    },

    async _od19FlushPending() {
        this._od19CancelTimer();
        const payload = this.od19DraftPendingPayload;
        this.od19DraftPendingPayload = null;
        if (!payload) {
            return;
        }
        const resId = this.od19DraftKeyResId;
        await this.od19DraftService.save(this.props.resModel, resId, payload);
        await this.od19DraftService.syncNow(this.props.resModel, resId, payload);
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
        this._od19CancelTimer();
        this.od19DraftPendingPayload = null;
        await this.od19DraftService.clear(this.props.resModel, resId);
        await this.od19DraftService.discardNow(this.props.resModel, resId);
        this.od19DraftBanner.visible = false;
        this.od19DraftBanner.draft = null;
    },

    async onRecordSaved(record) {
        const result = await super.onRecordSaved(...arguments);
        if (this.od19DraftEnabled && record) {
            this._od19CancelTimer();
            this.od19DraftPendingPayload = null;
            // ล้างทั้งคีย์ที่บันทึกร่างไว้ (เรกคอร์ดใหม่ = 0) และคีย์ของเรกคอร์ดจริง
            const keys = new Set([this.od19DraftKeyResId]);
            if (record.resId) {
                keys.add(record.resId);
            }
            for (const resId of keys) {
                await this.od19DraftService.clear(this.props.resModel, resId);
                await this.od19DraftService.markApplied(this.props.resModel, resId);
            }
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
