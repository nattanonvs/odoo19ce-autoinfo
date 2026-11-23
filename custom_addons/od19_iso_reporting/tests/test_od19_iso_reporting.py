from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestIsoReporting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env["od19.iso.document.category"].search([], limit=1)
        if not cls.category:
            cls.category = cls.env["od19.iso.document.category"].create(
                {"name": "Reporting Test Category"}
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _dar(self, **kw):
        vals = {"request_type": "other", "reason": "report test"}
        vals.update(kw)
        return self.env["od19.iso.dar"].create(vals)

    def _doc(self, **kw):
        vals = {"document_title": "ทดสอบเอกสารรายงาน ISO", "category_id": self.category.id}
        vals.update(kw)
        return self.env["od19.iso.document"].create(vals)

    # ------------------------------------------------------------------
    # report menu
    # ------------------------------------------------------------------
    def test_report_actions_exist(self):
        expected = {
            "action_od19_iso_report_pending_dar": "od19.iso.dar",
            "action_od19_iso_report_active_dar": "od19.iso.dar",
            "action_od19_iso_report_registered_docs": "od19.iso.document",
            "action_od19_iso_report_all_docs": "od19.iso.document",
            "action_od19_iso_report_document_register": "od19.iso.document",
            "action_od19_iso_report_revision": "od19.iso.document.revision",
            "action_od19_iso_report_distribution": "od19.iso.distribution.line",
            "action_od19_iso_report_print_register": "od19.iso.print.copy",
        }
        for xmlid, model in expected.items():
            action = self.env.ref("od19_iso_reporting.%s" % xmlid)
            self.assertEqual(action.res_model, model, xmlid)

    def test_report_action_domains(self):
        pending = self.env.ref("od19_iso_reporting.action_od19_iso_report_pending_dar")
        self.assertEqual(
            safe_eval(pending.domain),
            [("status", "in", ["review", "approval", "final_approval"])],
        )
        registered = self.env.ref(
            "od19_iso_reporting.action_od19_iso_report_registered_docs"
        )
        self.assertEqual(safe_eval(registered.domain), [("status", "=", "approved")])

    def test_report_menu_has_eight_children(self):
        menu = self.env.ref("od19_iso_reporting.menu_iso_reporting")
        children = self.env["ir.ui.menu"].search([("parent_id", "=", menu.id)])
        self.assertEqual(len(children), 8)
        self.assertTrue(all(child.action for child in children))

    def test_document_register_view_is_read_only(self):
        view = self.env.ref(
            "od19_iso_reporting.view_od19_iso_document_register_list"
        )
        arch = view.arch
        self.assertIn('create="0"', arch)
        self.assertIn('edit="0"', arch)
        self.assertIn('delete="0"', arch)

    # ------------------------------------------------------------------
    # dashboard configuration
    # ------------------------------------------------------------------
    def test_dashboard_sources_whitelist_iso_models(self):
        expected = {
            "od19.iso.dar",
            "od19.iso.document",
            "od19.iso.document.revision",
            "od19.iso.distribution.line",
            "od19.iso.print.copy",
        }
        sources = self.env["od19.dashboard.source"].search(
            [("model_name", "in", list(expected))]
        )
        self.assertEqual(set(sources.mapped("model_name")), expected)

    def test_dashboard_has_eleven_widgets_in_four_zones(self):
        dashboard = self.env.ref("od19_iso_reporting.dashboard_iso_control")
        self.assertEqual(len(dashboard.widget_ids), 11)
        sequences = sorted(dashboard.widget_ids.mapped("sequence"))
        self.assertEqual(sequences, [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110])

    def test_dashboard_widget_sources_are_declared(self):
        dashboard = self.env.ref("od19_iso_reporting.dashboard_iso_control")
        for widget in dashboard.widget_ids:
            # Re-runs the whitelist check performed by the create constraint.
            widget._check_source_fields()

    def test_next_30_days_date_range_is_available(self):
        from odoo.addons.od19_dashboard.models.dashboard import DATE_RANGES

        keys = [key for key, _label in DATE_RANGES]
        self.assertIn("next_30_days", keys)

        widget = self.env.ref("od19_iso_reporting.dashboard_iso_docs_due_review")
        today = fields.Date.context_today(widget)
        start, end, _field_type = widget._period_bounds()
        self.assertEqual(start, today)
        self.assertEqual(end, today + timedelta(days=30))

    def test_dashboard_client_action_targets_builder(self):
        action = self.env.ref(
            "od19_iso_reporting.action_od19_iso_control_dashboard"
        )
        self.assertEqual(action.tag, "od19_dashboard.builder")
        params = action.params
        if isinstance(params, str):
            params = safe_eval(params)
        dashboard = self.env.ref("od19_iso_reporting.dashboard_iso_control")
        self.assertEqual(params["dashboard_id"], dashboard.id)

    # ------------------------------------------------------------------
    # DAR SLA helper
    # ------------------------------------------------------------------
    def test_sla_due_date_is_create_date_plus_sla_days(self):
        dar = self._dar()
        expected = fields.Date.to_date(dar.create_date) + timedelta(days=dar.SLA_DAYS)
        self.assertEqual(dar.SLA_DAYS, 5)
        self.assertEqual(dar.sla_due_date, expected)

    # ------------------------------------------------------------------
    # engine smoke test
    # ------------------------------------------------------------------
    def test_get_dashboard_data_runs(self):
        dashboard = self.env.ref("od19_iso_reporting.dashboard_iso_control")
        self._doc(status="approved")
        self._dar()
        data = self.env["od19.dashboard"].get_dashboard_data(dashboard.id)
        self.assertEqual(data["dashboard"]["id"], dashboard.id)
        self.assertEqual(len(data["widgets"]), 11)
        for widget in data["widgets"]:
            self.assertIn("config", widget)
