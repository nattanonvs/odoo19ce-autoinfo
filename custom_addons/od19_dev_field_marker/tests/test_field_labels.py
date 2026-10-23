# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
from unittest import mock

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models import fields_marker
from ..models.fields_marker import MARKER, mark_custom_field_labels


@tagged("post_install", "-at_install")
class TestFieldLabels(TransactionCase):
    def test_marks_od19_fields(self):
        description = {"od19_flow_class": {"string": "Flow Class"}}
        result = mark_custom_field_labels(description)
        self.assertEqual(result["od19_flow_class"]["string"], "[od19] Flow Class")

    def test_leaves_standard_fields_untouched(self):
        description = {"name": {"string": "Name"}}
        result = mark_custom_field_labels(description)
        self.assertEqual(result["name"]["string"], "Name")

    def test_does_not_mark_twice(self):
        description = {"od19_flow_class": {"string": MARKER + "Flow Class"}}
        result = mark_custom_field_labels(description)
        self.assertEqual(result["od19_flow_class"]["string"], MARKER + "Flow Class")

    def test_skips_fields_without_label(self):
        description = {"od19_flow_class": {"string": False}}
        result = mark_custom_field_labels(description)
        self.assertFalse(result["od19_flow_class"]["string"])

    def test_wrapper_marks_labels_while_debug_is_on(self):
        sample = {"od19_flow_class": {"string": "Flow Class"}}
        with mock.patch.object(fields_marker, "_original_fields_get", lambda *a, **kw: copy.deepcopy(sample)):
            with mock.patch.object(fields_marker, "request", mock.Mock(session=mock.Mock(debug="1"))):
                result = fields_marker._fields_get_with_marker(self.env["res.partner"])
        self.assertEqual(result["od19_flow_class"]["string"], "[od19] Flow Class")

    def test_wrapper_keeps_labels_clean_without_debug(self):
        sample = {"od19_flow_class": {"string": "Flow Class"}}
        with mock.patch.object(fields_marker, "_original_fields_get", lambda *a, **kw: copy.deepcopy(sample)):
            with mock.patch.object(fields_marker, "request", mock.Mock(session=mock.Mock(debug=False))):
                result = fields_marker._fields_get_with_marker(self.env["res.partner"])
        self.assertEqual(result["od19_flow_class"]["string"], "Flow Class")

    def test_wrapper_is_safe_outside_an_http_request(self):
        sample = {"od19_flow_class": {"string": "Flow Class"}}
        with mock.patch.object(fields_marker, "_original_fields_get", lambda *a, **kw: copy.deepcopy(sample)):
            with mock.patch.object(fields_marker, "request", None):
                result = fields_marker._fields_get_with_marker(self.env["res.partner"])
        self.assertEqual(result["od19_flow_class"]["string"], "Flow Class")

    def test_no_od19_field_relies_on_an_auto_generated_label(self):
        """Governance: every ``od19_`` field must declare an explicit ``string``."""
        offenders = []
        for model_name, model in self.env.registry.items():
            for fname, field in model._fields.items():
                if not fname.startswith("od19_"):
                    continue
                label = field.string or ""
                if label.startswith("Od19 "):
                    offenders.append(f"{model_name}.{fname} -> {label}")
        self.assertFalse(
            offenders,
            "od19_ fields must set an explicit string= (found auto-generated labels):\n"
            + "\n".join(sorted(offenders)),
        )
