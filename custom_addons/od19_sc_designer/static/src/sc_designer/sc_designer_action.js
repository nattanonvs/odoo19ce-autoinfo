/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const TAB_MODEL = {
    menu: "od19.sc.menu.node",
    field: "od19.sc.field.def",
    theme: "od19.sc.design.token",
    formula: "od19.sc.formula",
    integration: "od19.sc.integration.endpoint",
};

const EMPTY_FORM = {
    menu: { name: "", parent_id: false, menu_type: "group", target_model: "",
            view_mode: "list,form", target_url: "", client_tag: "", sequence: 10,
            active: true, group_ids: [] },
    field: { target_model: "", mode: "create", name: "", field_description: "",
             ttype: "char", required: false, readonly: false, invisible: false,
             help: "", selection_values: "", relation: "", sequence: 10, active: true },
    theme: { key: "--sc-primary", value: "#7c5cff", sequence: 10, active: true },
    formula: { name: "", target_model: "", target_field: "", expression: "",
               trigger: "on_write", cron_interval_number: 1, cron_interval_type: "hours",
               sequence: 10, active: true },
    integration: { name: "", direction: "outbound", url: "", method: "POST", headers: "",
                   payload_template: "", auth_token_param: "", mapping_model: "",
                   schedule: false, cron_interval_number: 24, cron_interval_type: "hours",
                   sequence: 10, active: true },
};

/**
 * Service Center Designer — the front-end that lets users design the five
 * config-engine dimensions (Menu / Field / Theme / Formula / Integration)
 * and Preview / Apply / Rollback without writing code.
 */
export class ScDesignerAction extends Component {
    static template = "od19_sc_designer.ScAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            templates: [],
            meta: {},
            groups: [],
            selectedId: null,
            activeTab: "menu",
            header: { name: "", code: "", department: "", header_title: "", header_subtitle: "" },
            data: { menu: [], field: [], theme: [], formula: [], integration: [] },
            form: { open: false, recId: null, tab: "menu", vals: {} },
            newTemplate: { open: false, name: "", code: "", department: "", header_title: "", header_subtitle: "" },
        });

        onWillStart(async () => {
            await this._loadBootstrap();
        });
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async _loadBootstrap() {
        const res = await this.orm.call("od19.sc.designer", "get_bootstrap", []);
        this.state.templates = res.templates;
        this.state.meta = res.meta;
        this.state.groups = await this.orm.searchRead(
            "res.groups", [], ["id", "name"], { limit: 300, order: "name" });
        if (res.templates.length) {
            this.state.selectedId = res.templates[0].id;
            await this._loadTemplate();
        }
        this.state.loading = false;
    }

    async _loadTemplate() {
        if (!this.state.selectedId) {
            return;
        }
        const data = await this.orm.call(
            "od19.sc.designer", "get_template", [this.state.selectedId]);
        this.state.header = {
            name: data.template.name || "",
            code: data.template.code || "",
            department: data.template.department || "",
            header_title: data.template.header_title || "",
            header_subtitle: data.template.header_subtitle || "",
        };
        this.state.data = {
            menu: data["od19.sc.menu.node"],
            field: data["od19.sc.field.def"],
            theme: data["od19.sc.design.token"],
            formula: data["od19.sc.formula"],
            integration: data["od19.sc.integration.endpoint"],
        };
    }

    get currentModel() {
        return TAB_MODEL[this.state.activeTab];
    }

    get rows() {
        return this.state.data[this.state.activeTab] || [];
    }

    // ------------------------------------------------------------------
    // UI events
    // ------------------------------------------------------------------
    async onSelectTemplate(ev) {
        this.state.selectedId = Number(ev.target.value);
        this.state.form.open = false;
        await this._loadTemplate();
    }

    setTab(tab) {
        this.state.activeTab = tab;
        this.state.form.open = false;
    }

    openNewRecord() {
        this.state.form = {
            open: true,
            recId: null,
            tab: this.state.activeTab,
            vals: { ...EMPTY_FORM[this.state.activeTab] },
        };
    }

    openEditRecord(rec) {
        const tab = this.state.activeTab;
        const vals = { ...EMPTY_FORM[tab] };
        for (const key of Object.keys(vals)) {
            if (key in rec) {
                let value = rec[key];
                if (Array.isArray(value) && key === "group_ids") {
                    value = value.map(Number);
                }
                if (Array.isArray(value) && key === "parent_id") {
                    value = value[0];
                }
                vals[key] = value;
            }
        }
        this.state.form = { open: true, recId: rec.id, tab, vals };
    }

    closeForm() {
        this.state.form.open = false;
    }

    toggleGroup(groupId) {
        const id = Number(groupId);
        const ids = this.state.form.vals.group_ids || [];
        this.state.form.vals.group_ids = ids.includes(id)
            ? ids.filter((value) => value !== id)
            : [...ids, id];
    }

    async saveForm() {
        const tab = this.state.form.tab;
        const model = TAB_MODEL[tab];
        const vals = { ...this.state.form.vals };
        if (tab === "menu") {
            vals.parent_id = vals.parent_id ? Number(vals.parent_id) : false;
            vals.group_ids = (vals.group_ids || []).map(Number);
        }
        try {
            await this.orm.call("od19.sc.designer", "save_record",
                [model, this.state.selectedId, vals, this.state.form.recId || false]);
            this.state.form.open = false;
            await this._loadTemplate();
            this.notification.add(_t("Saved."), { type: "success" });
        } catch (error) {
            this._notifyError(error);
        }
    }

    async deleteRecord(rec) {
        if (!window.confirm(_t("Delete this record?"))) {
            return;
        }
        try {
            await this.orm.call("od19.sc.designer", "delete_record", [this.currentModel, rec.id]);
            await this._loadTemplate();
            this.notification.add(_t("Deleted."), { type: "success" });
        } catch (error) {
            this._notifyError(error);
        }
    }

    async saveHeader() {
        try {
            await this.orm.call("od19.sc.designer", "save_template", [this.state.selectedId, this.state.header]);
            this.notification.add(_t("Template header saved."), { type: "success" });
            await this._loadBootstrap();
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // Apply / preview / rollback
    // ------------------------------------------------------------------
    async applyTemplate() {
        try {
            await this.orm.call("od19.sc.designer", "apply_template", [this.state.selectedId]);
            this.notification.add(_t("Applied — the template is now live."), { type: "success" });
            await this._loadTemplate();
        } catch (error) {
            this._notifyError(error);
        }
    }

    async previewTemplate() {
        try {
            const res = await this.orm.call("od19.sc.designer", "preview_template", [this.state.selectedId]);
            this.notification.add(
                _t("Menus: %s · Fields: %s · Tokens: %s · Formulas: %s · Integrations: %s · Revisions: %s")
                    .replace("%s", res.menu_nodes).replace("%s", res.field_defs)
                    .replace("%s", res.design_tokens).replace("%s", res.formulas)
                    .replace("%s", res.integrations).replace("%s", res.revisions),
                { type: "info", sticky: true });
        } catch (error) {
            this._notifyError(error);
        }
    }

    async rollbackTemplate() {
        try {
            await this.orm.call("od19.sc.designer", "rollback_template", [this.state.selectedId]);
            this.notification.add(_t("Rolled back to the previous revision."), { type: "warning" });
            await this._loadTemplate();
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // Per-record test helpers
    // ------------------------------------------------------------------
    async testFormula(rec, ev) {
        ev.stopPropagation();
        try {
            const result = await this.orm.call("od19.sc.designer", "test_formula", [rec.id]);
            this.notification.add(result || _t("Formula evaluated."), { type: "success" });
            await this._loadTemplate();
        } catch (error) {
            this._notifyError(error);
        }
    }

    async testIntegration(rec, ev) {
        ev.stopPropagation();
        try {
            const result = await this.orm.call("od19.sc.designer", "test_integration", [rec.id]);
            this.notification.add(result || _t("Connection attempted."), { type: "info" });
            await this._loadTemplate();
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // New template
    // ------------------------------------------------------------------
    async createTemplate() {
        try {
            const id = await this.orm.call("od19.sc.template", "create", [{
                name: this.state.newTemplate.name || _t("New Template"),
                code: this.state.newTemplate.code,
                department: this.state.newTemplate.department,
                header_title: this.state.newTemplate.header_title,
                header_subtitle: this.state.newTemplate.header_subtitle,
            }]);
            this.state.newTemplate = { open: false, name: "", code: "", department: "", header_title: "", header_subtitle: "" };
            await this._loadBootstrap();
            this.state.selectedId = id;
            await this._loadTemplate();
            this.notification.add(_t("Template created."), { type: "success" });
        } catch (error) {
            this._notifyError(error);
        }
    }

    _notifyError(error) {
        const message = (error && (error.data && error.data.message || error.message)) || String(error);
        this.notification.add(message, { type: "danger" });
    }
}

registry.category("actions").add("od19_sc.designer", ScDesignerAction);
