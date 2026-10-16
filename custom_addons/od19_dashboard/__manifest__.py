{
    "name": "OD19 Dashboard Builder",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Role-based dashboards with an in-browser drag & drop builder",
    "description": """
OD19 Dashboard Builder
======================
Delivers the role-based dashboard baseline (Owner / Management / Operational
Lead) defined in ``role-based-dashboard-blueprint.md`` and adds a web based
builder so each audience can customise and design its own dashboard.

Features
--------
* Pre-built Owner, Management and Operational dashboards matching the
  blueprint zones (summary, alerts, trend, detail).
* In-browser builder: add, edit, remove, drag to reorder and resize widgets.
* Widget types: KPI value (with period-over-period delta), bar, line, pie
  chart and list.
* KPI widgets inherit the red / yellow / green / grey status model from
  ``kpi-reporting-baseline.md`` through per-widget thresholds.
* Data is read only from a curated whitelist of models and measures
  (``od19.dashboard.source``) so no arbitrary model can be queried.
""",
    "depends": [
        "web",
        "account",
        "sale_management",
        "purchase",
        "stock",
        "project",
        "mail",
    ],
    "data": [
        "security/dashboard_security.xml",
        "security/ir.model.access.csv",
        "data/dashboard_source_data.xml",
        "data/dashboard_data.xml",
        "views/dashboard_views.xml",
        "views/dashboard_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_dashboard/static/src/dashboard/dashboard_action.js",
            "od19_dashboard/static/src/dashboard/builder_dialog.js",
            "od19_dashboard/static/src/dashboard/dashboard_action.xml",
            "od19_dashboard/static/src/dashboard/builder_dialog.xml",
            "od19_dashboard/static/src/dashboard/dashboard_action.scss",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
