/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Default configuration of a brand new widget. The keys mirror
 * ``od19.dashboard.widget._to_config`` so the very same dictionary can be sent
 * back to ``create_widget`` / ``update_widget``.
 */
const DEFAULT_CONFIG = {
    name: "",
    subtitle: "",
    widget_type: "kpi",
    value_format: "number",
    color: "",
    source_id: null,
    measure_key: "__count",
    groupby_key: "",
    date_key: "",
    date_range: "last_30_days",
    domain: "[]",
    limit: 10,
    goal_value: 0,
    threshold_mode: "none",
    warning_value: 0,
    critical_value: 0,
    show_delta: true,
    grid_w: 4,
    grid_h: 2,
};

const CHART_TYPES = ["bar", "line", "pie"];

/**
 * Web based widget designer. It is opened by the dashboard action either empty
 * (create) or pre-filled with an existing widget configuration (edit).
 */
export class BuilderDialog extends Component {
    static template = "od19_dashboard.BuilderDialog";
    static props = {
        meta: Object,
        config: { optional: true },
        onSave: Function,
        onClose: Function,
    };

    setup() {
        this.state = useState({
            draft: { ...DEFAULT_CONFIG, ...(this.props.config || {}) },
            error: "",
        });
    }

    // ------------------------------------------------------------------
    // Meta getters
    // ------------------------------------------------------------------
    get sources() {
        return this.props.meta.sources || [];
    }

    get widgetTypes() {
        return this.props.meta.widget_types || [];
    }

    get valueFormats() {
        return this.props.meta.value_formats || [];
    }

    get thresholdModes() {
        return this.props.meta.threshold_modes || [];
    }

    get dateRanges() {
        return this.props.meta.date_ranges || [];
    }

    get currentSource() {
        return this.sources.find((source) => source.id === this.state.draft.source_id) || null;
    }

    get measures() {
        return this.currentSource ? this.currentSource.measures : [];
    }

    get groupbys() {
        return this.currentSource ? this.currentSource.groupbys : [];
    }

    get dates() {
        return this.currentSource ? this.currentSource.dates : [];
    }

    get isChart() {
        return CHART_TYPES.includes(this.state.draft.widget_type);
    }

    get showThreshold() {
        return this.state.draft.threshold_mode !== "none";
    }

    get showGoal() {
        return this.state.draft.widget_type === "kpi";
    }

    get dialogTitle() {
        return this.state.draft.id ? _t("Edit Widget") : _t("Add Widget");
    }

    get sourceHint() {
        const source = this.currentSource;
        return source ? source.model_name : "";
    }

    // ------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------
    onSourceChange(ev) {
        const sourceId = parseInt(ev.target.value, 10) || null;
        const draft = this.state.draft;
        draft.source_id = sourceId;
        const source = this.currentSource;
        const measureKeys = (source ? source.measures : []).map((item) => item.key);
        if (!measureKeys.includes(draft.measure_key)) {
            draft.measure_key = "__count";
        }
        const groupbyKeys = (source ? source.groupbys : []).map((item) => item.key);
        if (!groupbyKeys.includes(draft.groupby_key)) {
            draft.groupby_key = "";
        }
        const dateKeys = (source ? source.dates : []).map((item) => item.key);
        if (!dateKeys.includes(draft.date_key)) {
            draft.date_key = "";
        }
    }

    onTypeChange(ev) {
        const widgetType = ev.target.value;
        this.state.draft.widget_type = widgetType;
        if (CHART_TYPES.includes(widgetType) && !this.state.draft.groupby_key) {
            const first = this.groupbys[0];
            if (first) {
                this.state.draft.groupby_key = first.key;
            }
        }
        this.state.error = "";
    }

    onSave() {
        const draft = this.state.draft;
        if (!draft.name || !draft.name.trim()) {
            this.state.error = _t("Give the widget a name.");
            return;
        }
        if (!draft.source_id) {
            this.state.error = _t("Choose a data source.");
            return;
        }
        if (CHART_TYPES.includes(draft.widget_type) && !draft.groupby_key) {
            this.state.error = _t("Chart widgets need a group by field.");
            return;
        }
        const values = {};
        for (const [key, value] of Object.entries(draft)) {
            if (key === "id" || value === undefined) {
                continue;
            }
            values[key] = value;
        }
        this.props.onSave(values);
    }
}
