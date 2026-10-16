import logging
from datetime import date, datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_date, format_datetime
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

WIDGET_TYPES = [
    ("kpi", "KPI Value"),
    ("bar", "Bar Chart"),
    ("line", "Line Chart"),
    ("pie", "Pie Chart"),
    ("list", "List"),
]

VALUE_FORMATS = [
    ("number", "Number"),
    ("currency", "Currency"),
    ("percent", "Percent"),
    ("hours", "Hours"),
]

THRESHOLD_MODES = [
    ("none", "No threshold"),
    ("higher_is_better", "Higher is better"),
    ("lower_is_better", "Lower is better"),
]

AUDIENCES = [
    ("owner", "Owner / Executive"),
    ("management", "Management"),
    ("operational", "Operational Lead"),
]

DATE_RANGES = [
    ("all_time", "All Time"),
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("last_7_days", "Last 7 Days"),
    ("last_30_days", "Last 30 Days"),
    ("last_90_days", "Last 90 Days"),
    ("this_month", "This Month"),
    ("this_quarter", "This Quarter"),
    ("this_year", "This Year"),
    ("next_7_days", "Next 7 Days"),
    ("overdue", "Overdue"),
]

# Grid limits shared with the front-end builder.
MIN_GRID_W, MAX_GRID_W = 2, 12
MIN_GRID_H, MAX_GRID_H = 1, 6


class Od19Dashboard(models.Model):
    _name = "od19.dashboard"
    _description = "Dashboard"
    _order = "audience, sequence, name"

    name = fields.Char(required=True)
    audience = fields.Selection(
        selection=AUDIENCES,
        required=True,
        default="management",
        help="Role this dashboard is designed for, as defined in the dashboard blueprint.",
    )
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        help="User who designed the dashboard and can keep editing it.",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "od19_dashboard_group_rel",
        "dashboard_id",
        "group_id",
        string="Visible to Groups",
        help="Leave empty to make the dashboard visible to every internal user.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "od19_dashboard_user_rel",
        "dashboard_id",
        "user_id",
        string="Visible to Users",
    )

    is_default = fields.Boolean(
        help="Default dashboard offered to the audience when no dashboard is selected.",
    )
    shared = fields.Boolean(
        default=True,
        help="Uncheck to keep the dashboard private to its owner.",
    )
    default_date_range = fields.Selection(
        selection=DATE_RANGES,
        default="last_30_days",
        required=True,
    )
    color = fields.Char(
        default="#9E2424",
        help="Accent colour used by the dashboard header.",
    )

    widget_ids = fields.One2many("od19.dashboard.widget", "dashboard_id", string="Widgets")
    widget_count = fields.Integer(compute="_compute_widget_count")

    _name_company_default = models.Constraint(
        "unique(name, company_id)",
        "A dashboard with this name already exists for this company.",
    )

    @api.depends("widget_ids")
    def _compute_widget_count(self):
        for dashboard in self:
            dashboard.widget_count = len(dashboard.widget_ids)

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    def _can_edit(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group("od19_dashboard.group_od19_dashboard_manager"):
            return True
        return self.owner_id == user and user.has_group(
            "od19_dashboard.group_od19_dashboard_user"
        )

    def _check_edit_access(self):
        self.ensure_one()
        if not self._can_edit():
            raise AccessError(_("You are not allowed to design this dashboard."))

    # ------------------------------------------------------------------
    # Front-end API
    # ------------------------------------------------------------------
    @api.model
    def get_user_dashboards(self):
        """Return dashboards readable by the current user for the selector."""
        dashboards = self.search([("active", "=", True)])
        audience_labels = dict(self._fields["audience"].selection)
        return [
            {
                "id": dashboard.id,
                "name": dashboard.name,
                "audience": dashboard.audience,
                "audience_label": audience_labels.get(dashboard.audience, dashboard.audience),
                "is_default": dashboard.is_default,
                "can_edit": dashboard._can_edit(),
                "shared": dashboard.shared,
            }
            for dashboard in dashboards
        ]

    @api.model
    def get_builder_meta(self):
        """Return everything the builder dialog needs to render its forms."""
        sources = self.env["od19.dashboard.source"].search([("active", "=", True)])
        company = self.env.company
        return {
            "sources": [source._to_meta() for source in sources],
            "widget_types": [{"key": key, "label": label} for key, label in WIDGET_TYPES],
            "value_formats": [{"key": key, "label": label} for key, label in VALUE_FORMATS],
            "threshold_modes": [{"key": key, "label": label} for key, label in THRESHOLD_MODES],
            "date_ranges": [{"key": key, "label": label} for key, label in DATE_RANGES],
            "audiences": [{"key": key, "label": label} for key, label in AUDIENCES],
            "currency": {
                "symbol": company.currency_id.symbol or "",
                "position": company.currency_id.position or "before",
                "decimal_places": company.currency_id.decimal_places or 2,
            },
            "grid": {"min_w": MIN_GRID_W, "max_w": MAX_GRID_W, "min_h": MIN_GRID_H, "max_h": MAX_GRID_H},
        }

    @api.model
    def get_dashboard_data(self, dashboard_id, date_range=None, date_from=None, date_to=None):
        """Return the dashboard definition and the computed value of every widget."""
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard.check_access_rights("read")
        dashboard.check_access_rule("read")

        widgets = []
        for widget in dashboard.widget_ids.filtered("active").sorted(
            lambda widget: (widget.sequence, widget.id)
        ):
            data = widget._get_widget_data(date_range, date_from, date_to)
            data["config"] = widget._to_config()
            widgets.append(data)

        return {
            "dashboard": {
                "id": dashboard.id,
                "name": dashboard.name,
                "audience": dashboard.audience,
                "description": dashboard.description or "",
                "color": dashboard.color or "#9E2424",
                "default_date_range": dashboard.default_date_range,
                "can_edit": dashboard._can_edit(),
                "owner_name": dashboard.owner_id.name,
            },
            "widgets": widgets,
            "meta": {
                "date_range": date_range or dashboard.default_date_range,
                "generated_at": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    @api.model
    def save_layout(self, dashboard_id, layout):
        """Persist the order / size of the widgets after a drag or resize."""
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard.check_access_rights("write")
        dashboard._check_edit_access()

        for item in layout or []:
            widget = dashboard.widget_ids.filtered(lambda w: w.id == item.get("id"))
            if not widget:
                continue
            widget.write(
                {
                    "sequence": int(item.get("sequence", widget.sequence) or 0),
                    "grid_w": min(max(int(item.get("grid_w", widget.grid_w) or widget.grid_w), MIN_GRID_W), MAX_GRID_W),
                    "grid_h": min(max(int(item.get("grid_h", widget.grid_h) or widget.grid_h), MIN_GRID_H), MAX_GRID_H),
                }
            )
        return True

    @api.model
    def create_widget(self, dashboard_id, values):
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard._check_edit_access()
        dashboard.check_access_rights("write")

        values = dict(values or {})
        values["dashboard_id"] = dashboard.id
        if not values.get("sequence"):
            last = dashboard.widget_ids.mapped("sequence")
            values["sequence"] = (max(last) + 10) if last else 10
        widget = self.env["od19.dashboard.widget"].create(values)
        return {"id": widget.id, "config": widget._to_config()}

    @api.model
    def update_widget(self, widget_id, values):
        widget = self.env["od19.dashboard.widget"].browse(widget_id).exists()
        if not widget:
            raise UserError(_("This widget does not exist or is no longer available."))
        widget.dashboard_id._check_edit_access()
        widget.check_access_rights("write")
        widget.write(dict(values or {}))
        return {"id": widget.id, "config": widget._to_config()}

    @api.model
    def delete_widget(self, widget_id):
        widget = self.env["od19.dashboard.widget"].browse(widget_id).exists()
        if not widget:
            return True
        widget.dashboard_id._check_edit_access()
        widget.check_access_rights("unlink")
        widget.unlink()
        return True

    @api.model
    def duplicate_dashboard(self, dashboard_id, new_name=None):
        """Copy a dashboard into a private one owned by the current user.

        A designer may copy any dashboard they can read, including the shared
        baseline dashboards, which is how the delivered roles are customised.
        """
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        if not self.env.user.has_group("od19_dashboard.group_od19_dashboard_user"):
            raise AccessError(_("You need the Dashboard Designer role to copy a dashboard."))
        dashboard.check_access_rights("read")
        dashboard.check_access_rule("read")
        new_dashboard = dashboard.copy(
            {
                "name": new_name or _("%s (copy)") % dashboard.name,
                "owner_id": self.env.user.id,
                "is_default": False,
            }
        )
        return new_dashboard.id


class Od19DashboardWidget(models.Model):
    _name = "od19.dashboard.widget"
    _description = "Dashboard Widget"
    _order = "dashboard_id, sequence, id"

    dashboard_id = fields.Many2one(
        "od19.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    name = fields.Char(required=True, default=lambda self: _("New Widget"))
    subtitle = fields.Char()
    widget_type = fields.Selection(
        selection=WIDGET_TYPES,
        required=True,
        default="kpi",
    )
    value_format = fields.Selection(
        selection=VALUE_FORMATS,
        required=True,
        default="number",
    )
    color = fields.Char(help="Optional accent colour for the widget header.")

    source_id = fields.Many2one(
        "od19.dashboard.source",
        required=True,
        ondelete="restrict",
        string="Data Source",
    )
    model_name = fields.Char(related="source_id.model_name", string="Model")
    measure_key = fields.Char(
        required=True,
        default="__count",
        help="Field of the data source used as measure, or '__count'.",
    )
    groupby_key = fields.Char(help="Field of the data source used to group the values.")
    date_key = fields.Char(help="Date field of the data source used for the period filter.")
    date_range = fields.Selection(selection=DATE_RANGES, default="last_30_days", required=True)
    domain = fields.Char(
        default="[]",
        help="Additional Odoo domain applied to the data source, as a Python list.",
    )
    limit = fields.Integer(default=10)

    goal_value = fields.Float()
    threshold_mode = fields.Selection(selection=THRESHOLD_MODES, default="none", required=True)
    warning_value = fields.Float()
    critical_value = fields.Float()
    show_delta = fields.Boolean(default=True, string="Show Period Comparison")

    grid_w = fields.Integer(default=4, string="Width (columns)")
    grid_h = fields.Integer(default=2, string="Height (rows)")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains("widget_type", "groupby_key")
    def _check_groupby_required(self):
        for widget in self:
            if widget.widget_type in ("bar", "line", "pie") and not widget.groupby_key:
                raise ValidationError(
                    _("Chart widgets require a group by field (widget: %s).") % widget.name
                )

    @api.constrains("measure_key", "groupby_key", "date_key", "source_id")
    def _check_source_fields(self):
        for widget in self:
            source = widget.source_id
            if not source:
                continue
            if widget.measure_key and widget.measure_key != "__count" and not source._measure_field(widget.measure_key):
                raise ValidationError(
                    _("Measure '%s' is not available on data source '%s'.")
                    % (widget.measure_key, source.name)
                )
            if widget.groupby_key and not source._groupby_field(widget.groupby_key):
                raise ValidationError(
                    _("Group by '%s' is not available on data source '%s'.")
                    % (widget.groupby_key, source.name)
                )
            if widget.date_key and not source._date_field(widget.date_key):
                raise ValidationError(
                    _("Date field '%s' is not available on data source '%s'.")
                    % (widget.date_key, source.name)
                )
            if widget.threshold_mode == "higher_is_better" and widget.critical_value > widget.warning_value:
                raise ValidationError(
                    _("For 'higher is better' the critical value must be lower than the warning value.")
                )
            if widget.threshold_mode == "lower_is_better" and widget.critical_value < widget.warning_value:
                raise ValidationError(
                    _("For 'lower is better' the critical value must be higher than the warning value.")
                )

    @api.constrains("domain")
    def _check_domain(self):
        for widget in self:
            if not (widget.domain or "").strip():
                continue
            try:
                parsed = safe_eval(widget.domain)
            except Exception as error:  # noqa: BLE001 - surface the parsing error to the user
                raise ValidationError(
                    _("The filter of widget '%s' is not a valid domain: %s") % (widget.name, error)
                ) from error
            if not isinstance(parsed, list):
                raise ValidationError(
                    _("The filter of widget '%s' must be a list (Odoo domain).") % widget.name
                )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def _to_config(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle or "",
            "widget_type": self.widget_type,
            "value_format": self.value_format,
            "color": self.color or "",
            "source_id": self.source_id.id,
            "measure_key": self.measure_key,
            "groupby_key": self.groupby_key or "",
            "date_key": self.date_key or "",
            "date_range": self.date_range,
            "domain": self.domain or "[]",
            "limit": self.limit,
            "goal_value": self.goal_value,
            "threshold_mode": self.threshold_mode,
            "warning_value": self.warning_value,
            "critical_value": self.critical_value,
            "show_delta": self.show_delta,
            "grid_w": self.grid_w,
            "grid_h": self.grid_h,
            "sequence": self.sequence,
        }

    # ------------------------------------------------------------------
    # Data computation
    # ------------------------------------------------------------------
    def _get_widget_data(self, date_range=None, date_from=None, date_to=None):
        self.ensure_one()
        data = {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle or "",
            "widget_type": self.widget_type,
            "value_format": self.value_format,
            "color": self.color or "",
            "goal_value": self.goal_value,
            "threshold_mode": self.threshold_mode,
            "grid_w": self.grid_w,
            "grid_h": self.grid_h,
            "sequence": self.sequence,
            "status": "grey",
            "value": None,
            "delta": None,
            "series": [],
            "rows": [],
            "message": False,
        }

        source = self.source_id
        if not source or not source.model_name or source.model_name not in self.env:
            data["message"] = _("The data source of this widget is not installed in this database.")
            return data

        model = self.env[source.model_name]
        try:
            model.check_access_rights("read")
        except AccessError:
            data["message"] = _("You do not have read access on %s.") % source.name
            return data

        aggregate_spec = source._aggregate_spec(self.measure_key)
        if not aggregate_spec:
            data["message"] = _("The measure configured on this widget is not available any more.")
            return data

        try:
            domain = self._build_domain(date_range, date_from, date_to)
        except ValidationError as error:
            data["message"] = str(error)
            return data

        try:
            if self.widget_type == "kpi":
                self._fill_kpi_data(data, model, domain, aggregate_spec, date_range, date_from, date_to)
            elif self.widget_type in ("bar", "line", "pie"):
                self._fill_chart_data(data, model, domain, aggregate_spec)
            else:
                self._fill_list_data(data, model, domain)
        except (AccessError, UserError) as error:
            data["message"] = str(error)
            data["status"] = "grey"
        except Exception as error:  # noqa: BLE001 - never break the whole dashboard
            _logger.exception("Dashboard widget %s could not be computed", self.id)
            data["message"] = _("This widget could not be computed: %s") % error
            data["status"] = "grey"
        return data

    def _fill_kpi_data(self, data, model, domain, aggregate_spec, date_range, date_from, date_to):
        rows = model._read_group(domain, [], [aggregate_spec], limit=1)
        value = self._to_number(rows[0][0]) if rows and rows[0] else 0.0
        data["value"] = value
        data["status"] = self._compute_status(value)

        if self.show_delta:
            previous_domain = self._build_domain(date_range, date_from, date_to, previous=True)
            previous_rows = model._read_group(previous_domain, [], [aggregate_spec], limit=1)
            previous_value = self._to_number(previous_rows[0][0]) if previous_rows and previous_rows[0] else 0.0
            if previous_value:
                data["delta"] = round((value - previous_value) / previous_value * 100, 1)
            elif value:
                data["delta"] = 100.0
            else:
                data["delta"] = 0.0

    def _fill_chart_data(self, data, model, domain, aggregate_spec):
        groupby_spec = self._groupby_spec()
        if not groupby_spec:
            data["message"] = _("Choose a group by field for this chart.")
            return
        limit = self.limit if self.limit > 0 else None
        if self.widget_type == "line":
            # A line chart is a trend: take the most recent buckets, then
            # present them in chronological order.
            rows = model._read_group(
                domain,
                [groupby_spec],
                [aggregate_spec],
                order="%s desc" % groupby_spec,
                limit=limit,
            )
        else:
            rows = model._read_group(
                domain,
                [groupby_spec],
                [aggregate_spec],
                order="%s desc" % aggregate_spec,
                limit=limit,
            )
        series = []
        for row in rows:
            group_value = row[0]
            aggregate_value = row[1] if len(row) > 1 else 0
            series.append(
                {
                    "label": self._group_label(group_value),
                    "value": self._to_number(aggregate_value),
                }
            )
        if self.widget_type == "line":
            series.reverse()
        data["series"] = series
        data["status"] = "green" if series else "grey"
        if not series:
            data["message"] = _("No data for the selected period.")

    def _fill_list_data(self, data, model, domain):
        measure_field = False
        if self.measure_key and self.measure_key != "__count":
            field = model._fields.get(self.measure_key)
            if field and field.type in ("float", "integer", "monetary"):
                measure_field = self.measure_key
        limit = self.limit if self.limit > 0 else 10
        records = model.search(
            domain,
            limit=limit,
            order="%s desc" % measure_field if measure_field else "id desc",
        )
        rows = []
        for record in records:
            value = None
            if measure_field:
                value = self._to_number(record[measure_field])
            rows.append(
                {
                    "id": record.id,
                    "label": record.display_name,
                    "value": value,
                    "extra": self._record_extra(record),
                }
            )
        data["rows"] = rows
        data["status"] = "green" if rows else "grey"
        if not rows:
            data["message"] = _("No record matches the selected filters.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _groupby_spec(self):
        self.ensure_one()
        if not self.groupby_key:
            return False
        field = self.source_id._groupby_field(self.groupby_key)
        if not field:
            return False
        if field.granularity:
            return "%s:%s" % (field.field_name, field.granularity)
        return field.field_name

    def _build_domain(self, date_range=None, date_from=None, date_to=None, previous=False):
        self.ensure_one()
        domain = []
        raw_domain = (self.domain or "").strip()
        if raw_domain:
            try:
                parsed = safe_eval(raw_domain)
            except Exception as error:  # noqa: BLE001
                raise ValidationError(
                    _("The filter of widget '%s' is not valid: %s") % (self.name, error)
                ) from error
            if not isinstance(parsed, list):
                raise ValidationError(
                    _("The filter of widget '%s' must be a list (Odoo domain).") % self.name
                )
            domain += parsed

        effective_range = date_range or self.date_range or "all_time"
        if self.date_key and effective_range != "all_time":
            domain += self._date_bounds(effective_range, date_from, date_to, previous)
        return domain

    def _date_bounds(self, range_key, date_from, date_to, previous=False):
        self.ensure_one()
        model = self.env[self.source_id.model_name]
        field = model._fields.get(self.date_key)
        field_type = field.type if field else "date"
        today = fields.Date.context_today(self)

        start = end = None
        if date_from or date_to:
            start = fields.Date.to_date(date_from) if date_from else None
            end = fields.Date.to_date(date_to) if date_to else None
        elif range_key == "today":
            start = end = today
        elif range_key == "yesterday":
            start = end = today - timedelta(days=1)
        elif range_key == "last_7_days":
            start, end = today - timedelta(days=6), today
        elif range_key == "last_30_days":
            start, end = today - timedelta(days=29), today
        elif range_key == "last_90_days":
            start, end = today - timedelta(days=89), today
        elif range_key == "this_month":
            start, end = today.replace(day=1), today
        elif range_key == "this_quarter":
            start, end = today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1), today
        elif range_key == "this_year":
            start, end = today.replace(month=1, day=1), today
        elif range_key == "next_7_days":
            start, end = today, today + timedelta(days=7)
        elif range_key == "overdue":
            start, end = None, today - timedelta(days=1)
        else:
            return []

        if previous and start and end:
            length = (end - start).days + 1
            end = start - timedelta(days=1)
            start = end - timedelta(days=length - 1)

        if field_type == "date":
            if start:
                return [(self.date_key, ">=", start.isoformat())]
            if end:
                return [(self.date_key, "<=", end.isoformat())]
            return []
        if start:
            return [(self.date_key, ">=", "%s 00:00:00" % start.isoformat())]
        if end:
            return [(self.date_key, "<=", "%s 23:59:59" % end.isoformat())]
        return []

    def _compute_status(self, value):
        self.ensure_one()
        if value is None or self.threshold_mode == "none":
            return "green" if value is not None else "grey"
        if self.threshold_mode == "higher_is_better":
            if value <= self.critical_value:
                return "red"
            if value <= self.warning_value:
                return "yellow"
            return "green"
        if value >= self.critical_value:
            return "red"
        if value >= self.warning_value:
            return "yellow"
        return "green"

    def _group_label(self, group_value):
        self.ensure_one()
        key_parts = (self.groupby_key or "").split(":")
        field_name = key_parts[0]
        granularity = key_parts[1] if len(key_parts) > 1 else None
        model = self.env[self.source_id.model_name]
        field = model._fields.get(field_name)
        if group_value is None or group_value is False:
            return _("Undefined")
        if isinstance(group_value, models.BaseModel):
            return group_value.display_name or _("Undefined")
        if granularity in ("month", "quarter", "year") and isinstance(group_value, (date, datetime)):
            value = group_value.date() if isinstance(group_value, datetime) else group_value
            if granularity == "year":
                return format_date(self.env, value, date_format="yyyy")
            if granularity == "month":
                return format_date(self.env, value, date_format="MMMM yyyy")
            return format_date(self.env, value)
        if field is None:
            return str(group_value)
        if field.type == "selection":
            labels = dict(field._description_selection(self.env))
            return labels.get(group_value, str(group_value))
        if field.type == "date":
            return format_date(self.env, group_value)
        if field.type == "datetime":
            return format_datetime(self.env, group_value)
        if field.type == "boolean":
            return _("Yes") if group_value else _("No")
        return str(group_value)

    def _record_extra(self, record):
        if "state" in record._fields:
            labels = dict(record._fields["state"]._description_selection(self.env))
            state = record.state
            return labels.get(state, state)
        return ""

    @api.model
    def _to_number(self, value):
        if value is None or value is False:
            return 0.0
        if isinstance(value, models.BaseModel):
            return float(len(value))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
