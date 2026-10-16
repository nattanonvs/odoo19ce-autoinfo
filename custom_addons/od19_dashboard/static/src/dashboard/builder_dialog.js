/** @odoo-module **/

import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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
    show_delta: true,
    formula_mode: "measure",
    formula_type: null,
    formula_slots: "{}",
    formula_expression: "",
    formula_basis: "previous",
    delta_basis: "previous",
    default_status: "green",
    rule_ids: [],
    grid_w: 4,
    grid_h: 2,
};

const CHART_TYPES = ["bar", "line", "pie"];

//: Measure slots the designer may bind, in the order they are offered.
const SLOT_KEYS = ["a", "b", "c", "d", "e"];
const WEIGHT_KEYS = ["w1", "w2"];

//: Names a custom expression may always use, on top of the source measures.
const IMPLICIT_NAMES = [
    "goal",
    "total_a",
    "days_in_period",
    "days_elapsed",
    "count_records",
];

//: How long the dialog waits before asking the server for a preview.
const PREVIEW_DEBOUNCE = 600;

/**
 * Web based widget designer. It is opened by the dashboard action either empty
 * (create) or pre-filled with an existing widget configuration (edit).
 *
 * Since the formula engine landed, the designer also chooses how the value is
 * computed (single measure, preset formula or custom expression) and how the
 * colour is decided (an ordered table of status rules). A debounced preview
 * shows the resulting value and the number of records the widget would collect.
 */
export class BuilderDialog extends Component {
    static template = "od19_dashboard.BuilderDialog";
    static props = {
        meta: Object,
        config: { optional: true },
        widgets: { optional: true },
        dashboardId: { optional: true },
        onSave: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this._ruleKey = 0;
        this._previewTimer = null;

        const config = this.props.config || {};
        this.state = useState({
            draft: {
                ...DEFAULT_CONFIG,
                ...config,
                rule_ids: this._prepareRules(config.rule_ids || []),
            },
            error: "",
            preview: { loading: false, data: null, error: "" },
            // Ids of the stored rules the designer removed: they are sent back
            // as ``[2, id]`` commands, otherwise Odoo would keep them.
            removedRuleIds: [],
            dragRuleIndex: null,
        });

        onWillStart(() => this._refreshPreview());
        onWillDestroy(() => this._clearPreviewTimer());
    }

    _nextRuleKey() {
        this._ruleKey += 1;
        return `new-${this._ruleKey}`;
    }

    _prepareRules(rules) {
        // ``_key`` is client side only: it keeps OWL stable while the rows are
        // reordered. ``_ruleCommands`` rebuilds every dictionary from scratch,
        // so the key never reaches the server.
        return rules.map((rule) => ({
            ...rule,
            _key: rule.id ? `rule-${rule.id}` : this._nextRuleKey(),
        }));
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

    get showGoal() {
        return this.state.draft.widget_type === "kpi";
    }

    get formulaModes() {
        return this.props.meta.formula_modes || [];
    }

    get formulaTypes() {
        return this.props.meta.formula_types || [];
    }

    get compareTypes() {
        return this.props.meta.compare_types || [];
    }

    get operators() {
        return this.props.meta.operators || [];
    }

    get statuses() {
        return this.props.meta.statuses || [];
    }

    get periodBases() {
        return this.props.meta.period_bases || [];
    }

    get isFormula() {
        return this.state.draft.formula_mode !== "measure";
    }

    get isPresetFormula() {
        return this.state.draft.formula_mode === "preset";
    }

    get isCustomFormula() {
        return this.state.draft.formula_mode === "custom";
    }

    get selectedFormula() {
        return (
            this.formulaTypes.find((item) => item.key === this.state.draft.formula_type) || null
        );
    }

    get needsWeight() {
        const formula = this.selectedFormula;
        return Boolean(formula && formula.slots.some((key) => WEIGHT_KEYS.includes(key)));
    }

    /** The slots currently bound, as a plain object (bad JSON reads as empty). */
    get slotMap() {
        try {
            const parsed = JSON.parse(this.state.draft.formula_slots || "{}");
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (error) {
            return {};
        }
    }

    /**
     * One row per slot of the selected preset. A variadic preset (sum,
     * average) grows as soon as the designer adds a slot, so c to e appear
     * only when wanted.
     */
    get slotRows() {
        const formula = this.selectedFormula;
        if (!formula) {
            return [];
        }
        const map = this.slotMap;
        const keys = [...formula.slots];
        if (formula.variadic) {
            for (const key of SLOT_KEYS) {
                if (!keys.includes(key) && map[key] !== undefined) {
                    keys.push(key);
                }
            }
        }
        return keys.map((key) => ({
            key,
            label: key.toUpperCase(),
            is_weight: WEIGHT_KEYS.includes(key),
            value: map[key] === undefined ? "" : map[key],
        }));
    }

    get canAddSlot() {
        const formula = this.selectedFormula;
        if (!formula || !formula.variadic) {
            return false;
        }
        const map = this.slotMap;
        return SLOT_KEYS.some((key) => map[key] === undefined);
    }

    /** The other widgets of the dashboard: allowed as a comparison operand. */
    get widgetOptions() {
        return (this.props.widgets || []).filter((item) => item.id !== this.state.draft.id);
    }

    get ruleRows() {
        return this.state.draft.rule_ids.map((rule, index) => ({
            ...rule,
            index,
            is_constant: rule.compare_type === "constant",
            is_percent: rule.compare_type === "percent_of_goal",
            is_widget: rule.compare_type === "widget",
        }));
    }

    /** Every name the insert buttons may offer to a custom expression. */
    get insertableNames() {
        const names = [...SLOT_KEYS, ...IMPLICIT_NAMES];
        for (const measure of this.measures) {
            if (!names.includes(measure.key)) {
                names.push(measure.key);
            }
        }
        for (const widget of this.widgetOptions) {
            names.push(`widget_${widget.id}`);
        }
        return names;
    }

    // ------------------------------------------------------------------
    // Preview getters
    // ------------------------------------------------------------------
    get previewExpression() {
        const data = this.state.preview.data;
        return data ? data.formula_expression || "" : "";
    }

    get previewValue() {
        const data = this.state.preview.data;
        if (!data) {
            return "";
        }
        return this._number(data.value);
    }

    get previewRecords() {
        const data = this.state.preview.data;
        return data ? data.record_count : 0;
    }

    get previewStatusLabel() {
        const data = this.state.preview.data;
        if (!data) {
            return "";
        }
        const match = this.statuses.find((item) => item.key === data.status);
        return match ? match.label : data.status;
    }

    get previewOperands() {
        const data = this.state.preview.data;
        if (!data) {
            return [];
        }
        return (data.operands || []).map((operand) => ({
            key: operand.alias,
            label: operand.label,
            text: this._number(operand.value),
        }));
    }

    get previewSeries() {
        const data = this.state.preview.data;
        if (!data) {
            return [];
        }
        return (data.series_preview || []).map((point, index) => ({
            key: `${point.label}-${index}`,
            label: point.label,
            text: this._number(point.value),
        }));
    }

    _number(value) {
        if (value === null || value === undefined) {
            return "—";
        }
        const number = Number(value);
        if (Number.isNaN(number)) {
            return String(value);
        }
        return number.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    get dialogTitle() {
        return this.state.draft.id ? _t("Edit Widget") : _t("Add Widget");
    }

    get sourceHint() {
        const source = this.currentSource;
        return source ? source.model_name : "";
    }

    // ------------------------------------------------------------------
    // Handlers: data
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
        // The slots of the previous source no longer resolve.
        draft.formula_slots = "{}";
        this._schedulePreview();
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
        this._schedulePreview();
    }

    onFormulaChange() {
        this._schedulePreview();
    }

    onFormulaModeChange(ev) {
        const draft = this.state.draft;
        draft.formula_mode = ev.target.value;
        // The stored expression only belongs to the custom mode: reset it so a
        // measure / preset widget never leaves the internal alias "value" (or a
        // stale preset expression) behind in the custom textarea.
        draft.formula_expression = "";
        if (draft.formula_mode === "preset" && !draft.formula_type) {
            const first = this.formulaTypes[0];
            if (first) {
                draft.formula_type = first.key;
            }
        }
        this.state.error = "";
        this._schedulePreview();
    }

    onFormulaTypeChange(ev) {
        const draft = this.state.draft;
        draft.formula_type = ev.target.value;
        // The slots of the previous preset no longer apply.
        draft.formula_slots = "{}";
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Handlers: formula slots
    // ------------------------------------------------------------------
    setSlot(key, value) {
        const map = { ...this.slotMap };
        map[key] = WEIGHT_KEYS.includes(key) ? Number(value) || 0 : value;
        this.state.draft.formula_slots = JSON.stringify(map);
        this._schedulePreview();
    }

    addSlot() {
        const map = { ...this.slotMap };
        const next = SLOT_KEYS.find((key) => map[key] === undefined);
        if (!next) {
            return;
        }
        // An empty value keeps the row visible; ``_boundSlots`` drops it again
        // before the payload leaves the browser.
        map[next] = "";
        this.state.draft.formula_slots = JSON.stringify(map);
    }

    insertName(name) {
        const draft = this.state.draft;
        const current = draft.formula_expression || "";
        const spacer = current && !current.endsWith(" ") ? " " : "";
        draft.formula_expression = `${current}${spacer}${name}`;
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Handlers: status rules
    // ------------------------------------------------------------------
    addRule() {
        const draft = this.state.draft;
        draft.rule_ids = [
            ...draft.rule_ids,
            {
                id: 0,
                _key: this._nextRuleKey(),
                name: "",
                sequence: (draft.rule_ids.length + 1) * 10,
                active: true,
                operator: ">=",
                compare_type: "goal",
                compare_value: 0,
                compare_percent: 0,
                compare_widget_id: this.widgetOptions.length ? this.widgetOptions[0].id : false,
                status: this.statuses.length ? this.statuses[0].key : "red",
            },
        ];
        this._schedulePreview();
    }

    updateRule(index, key, value) {
        const rules = [...this.state.draft.rule_ids];
        const rule = { ...rules[index], [key]: value };
        if (key === "compare_type") {
            // Switching the comparison resets the operand it no longer uses.
            rule.compare_value = 0;
            rule.compare_percent = 0;
            rule.compare_widget_id = this.widgetOptions.length ? this.widgetOptions[0].id : false;
        }
        rules[index] = rule;
        this.state.draft.rule_ids = rules;
        this._schedulePreview();
    }

    removeRule(index) {
        const rules = [...this.state.draft.rule_ids];
        const [removed] = rules.splice(index, 1);
        if (removed && removed.id) {
            this.state.removedRuleIds = [...this.state.removedRuleIds, removed.id];
        }
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    moveRule(index, delta) {
        const target = index + delta;
        const rules = [...this.state.draft.rule_ids];
        if (target < 0 || target >= rules.length) {
            return;
        }
        const [moved] = rules.splice(index, 1);
        rules.splice(target, 0, moved);
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    _renumberRules() {
        this.state.draft.rule_ids = this.state.draft.rule_ids.map((rule, index) => ({
            ...rule,
            sequence: (index + 1) * 10,
        }));
    }

    onRuleDragStart(ev, index) {
        this.state.dragRuleIndex = index;
        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", String(index));
        }
    }

    onRuleDragOver(ev) {
        ev.preventDefault();
    }

    onRuleDrop(ev, index) {
        ev.preventDefault();
        const from = this.state.dragRuleIndex;
        this.state.dragRuleIndex = null;
        if (from === null || from === undefined || from === index) {
            return;
        }
        const rules = [...this.state.draft.rule_ids];
        const [moved] = rules.splice(from, 1);
        rules.splice(index, 0, moved);
        this.state.draft.rule_ids = rules;
        this._renumberRules();
        this._schedulePreview();
    }

    // ------------------------------------------------------------------
    // Live preview
    // ------------------------------------------------------------------
    _clearPreviewTimer() {
        if (this._previewTimer) {
            clearTimeout(this._previewTimer);
            this._previewTimer = null;
        }
    }

    _schedulePreview() {
        this._clearPreviewTimer();
        this._previewTimer = setTimeout(() => this._refreshPreview(), PREVIEW_DEBOUNCE);
    }

    async _refreshPreview() {
        this._clearPreviewTimer();
        const values = this._previewValues();
        if (!values.name || !values.source_id) {
            // Not enough to compute anything yet: do not bother the server.
            this.state.preview = { loading: false, data: null, error: "" };
            return;
        }
        this.state.preview = { loading: true, data: this.state.preview.data, error: "" };
        try {
            const data = await this.orm.call("od19.dashboard", "preview_widget", [
                values,
                this.state.draft.date_range,
            ]);
            this.state.preview = { loading: false, data, error: "" };
        } catch (error) {
            this.state.preview = { loading: false, data: null, error: this._errorText(error) };
        }
    }

    _errorText(error) {
        const data = (error && error.data) || {};
        return data.message || (error && error.message) || _t("The preview could not be computed.");
    }

    _previewValues() {
        const values = this._buildValues();
        // The draft must know its dashboard so a reference to another widget can
        // be resolved while designing. ``onSave`` never sends this key.
        if (this.props.dashboardId) {
            values.dashboard_id = this.props.dashboardId;
        }
        return values;
    }

    _buildValues() {
        const draft = this.state.draft;
        return {
            ...(draft.id ? { id: draft.id } : {}),
            name: draft.name,
            subtitle: draft.subtitle,
            widget_type: draft.widget_type,
            value_format: draft.value_format,
            color: draft.color,
            source_id: draft.source_id,
            measure_key: draft.measure_key,
            groupby_key: draft.groupby_key,
            date_key: draft.date_key,
            date_range: draft.date_range,
            domain: draft.domain,
            limit: draft.limit,
            goal_value: draft.goal_value,
            show_delta: draft.show_delta,
            formula_mode: draft.formula_mode,
            formula_type: draft.formula_type || null,
            formula_slots: JSON.stringify(this._boundSlots()),
            formula_expression: draft.formula_expression,
            formula_basis: draft.formula_basis,
            delta_basis: draft.delta_basis,
            default_status: draft.default_status,
            rule_ids: this._ruleCommands(),
            grid_w: draft.grid_w,
            grid_h: draft.grid_h,
        };
    }

    /** Only the slots the designer actually filled in. */
    _boundSlots() {
        const bound = {};
        for (const [key, value] of Object.entries(this.slotMap)) {
            if (value === "" || value === null || value === undefined) {
                continue;
            }
            if (WEIGHT_KEYS.includes(key) && !Number(value)) {
                continue;
            }
            bound[key] = value;
        }
        return bound;
    }

    /**
     * The rule list as One2many commands. ``[1, id, {...}]`` updates a stored
     * rule, ``[0, 0, {...}]`` adds one and ``[2, id]`` deletes the rules the
     * designer removed (a plain rewrite never deletes anything).
     */
    _ruleCommands() {
        const commands = [];
        for (const rule of this.state.draft.rule_ids) {
            const data = {
                name: rule.name || "",
                sequence: rule.sequence,
                active: rule.active !== false,
                operator: rule.operator,
                compare_type: rule.compare_type,
                compare_value: Number(rule.compare_value) || 0,
                compare_percent: Number(rule.compare_percent) || 0,
                compare_widget_id: rule.compare_widget_id || false,
                status: rule.status,
            };
            commands.push(rule.id ? [1, rule.id, data] : [0, 0, data]);
        }
        for (const ruleId of this.state.removedRuleIds) {
            commands.push([2, ruleId]);
        }
        return commands;
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
        if (this.isPresetFormula && !draft.formula_type) {
            this.state.error = _t("Choose a preset formula.");
            return;
        }
        if (this.isCustomFormula && !(draft.formula_expression || "").trim()) {
            this.state.error = _t("Type the formula of this widget.");
            return;
        }
        this.props.onSave(this._buildValues());
    }
}
