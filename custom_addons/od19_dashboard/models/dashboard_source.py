from odoo import _, fields, models

# Aggregation functions exposed to the builder. They are the PostgreSQL
# aggregates supported by ``Model._read_group``.
AGGREGATIONS = [
    ("sum", "Sum"),
    ("avg", "Average"),
    ("count", "Count"),
    ("count_distinct", "Count Distinct"),
    ("max", "Max"),
    ("min", "Min"),
]

# Granularity used when a group by field is a date/datetime.
GRANULARITIES = [
    ("day", "Day"),
    ("week", "Week"),
    ("month", "Month"),
    ("quarter", "Quarter"),
    ("year", "Year"),
]


class Od19DashboardSource(models.Model):
    """Whitelist of models the dashboard builder is allowed to read.

    Only measures, group by fields and date fields declared here can be used
    by a widget, which keeps the builder safe (no arbitrary model / field
    selection from the front-end).
    """

    _name = "od19.dashboard.source"
    _description = "Dashboard Data Source"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    model_name = fields.Char(
        required=True,
        index=True,
        help="Technical name of the Odoo model, e.g. sale.order.",
    )
    description = fields.Char(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    field_ids = fields.One2many(
        "od19.dashboard.source.field",
        "source_id",
        string="Available Fields",
    )
    field_count = fields.Integer(compute="_compute_field_count")

    _model_name_unique = models.Constraint(
        "unique(model_name)",
        "Each dashboard data source must use a unique model.",
    )

    def _compute_field_count(self):
        for source in self:
            source.field_count = len(source.field_ids)

    def _to_meta(self):
        """Return the configuration payload consumed by the builder dialog."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "model_name": self.model_name,
            "available": self.model_name in self.env,
            "measures": [
                {"key": "__count", "label": _("Record Count"), "agg": "count"},
            ]
            + [
                {"key": field.field_name, "label": field.label, "agg": field.agg}
                for field in self.field_ids
                if field.kind == "measure"
            ],
            "groupbys": [
                {"key": field.field_name, "label": field.label}
                for field in self.field_ids
                if field.kind == "groupby"
            ],
            "dates": [
                {"key": field.field_name, "label": field.label}
                for field in self.field_ids
                if field.kind == "date"
            ],
        }

    def _measure_field(self, measure_key):
        """Return the source field record matching ``measure_key`` (or empty)."""
        self.ensure_one()
        if not measure_key or measure_key == "__count":
            return self.env["od19.dashboard.source.field"]
        return self.field_ids.filtered(
            lambda field: field.kind == "measure" and field.field_name == measure_key
        )[:1]

    def _groupby_field(self, groupby_key):
        self.ensure_one()
        if not groupby_key:
            return self.env["od19.dashboard.source.field"]
        return self.field_ids.filtered(
            lambda field: field.kind == "groupby" and field.field_name == groupby_key
        )[:1]

    def _date_field(self, date_key):
        self.ensure_one()
        if not date_key:
            return self.env["od19.dashboard.source.field"]
        return self.field_ids.filtered(
            lambda field: field.kind == "date" and field.field_name == date_key
        )[:1]

    def _aggregate_spec(self, measure_key):
        """Return the ``_read_group`` aggregate specification."""
        self.ensure_one()
        if not measure_key:
            return False
        if measure_key == "__count":
            return "__count"
        field = self._measure_field(measure_key)
        if not field:
            return False
        return "%s:%s" % (field.field_name, field.agg or "sum")


class Od19DashboardSourceField(models.Model):
    _name = "od19.dashboard.source.field"
    _description = "Dashboard Data Source Field"
    _order = "kind, sequence, id"

    source_id = fields.Many2one(
        "od19.dashboard.source",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True, translate=True)
    field_name = fields.Char(
        required=True,
        help="Technical field name on the source model. Use '__count' for a record count measure.",
    )
    kind = fields.Selection(
        selection=[
            ("measure", "Measure"),
            ("groupby", "Group By"),
            ("date", "Date Field"),
        ],
        required=True,
        default="measure",
    )
    agg = fields.Selection(
        selection=AGGREGATIONS,
        default="sum",
        help="Aggregation applied when the field is used as a measure.",
    )
    granularity = fields.Selection(
        selection=GRANULARITIES,
        help="Optional date granularity applied when the field is used as a group by.",
    )
