from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.od19_project_document_sequence.models.project_project import (
    _insert_initials_before_year,
)


class TestProjectDocumentSequence(TransactionCase):
    """Basic tests for project document sequence generation."""

    def test_insert_initials_before_year(self):
        # Sequence: JB26-0001, initials: NV -> JBNV26-0001
        result = _insert_initials_before_year("JB26-0001", "NV")
        self.assertEqual(result, "JBNV26-0001")

    def test_insert_initials_no_year_match(self):
        # No 2-digit year found -> return unchanged
        result = _insert_initials_before_year("JOB-0001", "NV")
        self.assertEqual(result, "JOB-0001")

    def test_insert_initials_empty_generated(self):
        result = _insert_initials_before_year("", "NV")
        self.assertEqual(result, "")

    def test_insert_initials_none_generated(self):
        result = _insert_initials_before_year(None, "NV")
        self.assertIsNone(result)

    def test_insert_initials_empty_initials(self):
        result = _insert_initials_before_year("JB26-0001", "")
        self.assertEqual(result, "JB26-0001")

    def test_user_has_initials_field(self):
        user = self.env["res.users"].create({
            "name": "Test User",
            "login": "test_initials_user",
            "od19_initials": "TV",
        })
        self.assertEqual(user.od19_initials, "TV")

    def test_department_has_project_sequence_fields(self):
        department = self.env["hr.department"].create({"name": "Test Dept"})
        self.assertFalse(department.project_job_sequence_id)
        self.assertFalse(department.project_pm_sequence_id)
        self.assertFalse(department.project_service_sequence_id)

    def test_project_has_type_and_department_fields(self):
        department = self.env["hr.department"].create({"name": "Test Project Dept"})
        project = self.env["project.project"].create({
            "name": "Test Project",
            "od19_department_id": department.id,
        })
        self.assertEqual(project.od19_project_type, "job")
        self.assertEqual(project.od19_department_id, department)

    def test_project_type_selection_matches_legacy(self):
        # Legacy set: job, pm, service, sale - never 'server'
        selection = dict(self.env["project.project"]._fields["od19_project_type"].selection)
        self.assertEqual(
            sorted(selection.keys()), ["job", "pm", "sale", "service"]
        )

    def _sale_sequence(self, prefix="S%(y)s-"):
        return self.env["ir.sequence"].create({
            "name": "OD19 Sale Job No",
            "code": "od19.sale.job",
            "prefix": prefix,
            "padding": 4,
            "company_id": self.env.company.id,
        })

    def _sale_user(self, login, initials=None, sequence=None, name=None):
        return self.env["res.users"].create({
            "name": name or login,
            "login": login,
            "od19_initials": initials,
            "project_sale_sequence_id": sequence.id if sequence else False,
        })

    def _create_sale_project(self, user, **vals):
        return self.env["project.project"].create(dict({
            "name": "Sale Project",
            "od19_project_type": "sale",
            "od19_sale_person_id": user.id,
        }, **vals))

    def test_sale_job_no_uses_manual_initials(self):
        user = self._sale_user(
            "od19_sale_rep", "NV", self._sale_sequence(), name="Nattanai Vinyangkoon"
        )
        project = self._create_sale_project(user)
        # S + initials + YY + running number
        self.assertRegex(project.job_no, r"^SNV\d{2}-\d{4}$")

    def test_sale_job_no_derives_initials_from_user_name(self):
        # No manual initials -> first letter of the first and last name (NV)
        user = self._sale_user(
            "od19_sale_rep_name",
            None,
            self._sale_sequence(),
            name="Nattanai Vinyangkoon",
        )
        project = self._create_sale_project(user)
        self.assertRegex(project.job_no, r"^SNV\d{2}-\d{4}$")

    def test_sale_job_no_manual_initials_override_derived(self):
        user = self._sale_user(
            "od19_sale_rep_override",
            "xy",
            self._sale_sequence(),
            name="Nattanai Vinyangkoon",
        )
        project = self._create_sale_project(user)
        self.assertTrue(project.job_no.startswith("SXY"))

    def test_sale_job_no_ignores_sequence_prefix(self):
        # The salesperson sequence only supplies the running number; S is fixed
        user = self._sale_user(
            "od19_sale_rep_prefix", "NV", self._sale_sequence(prefix="JS%(y)s-")
        )
        project = self._create_sale_project(user)
        self.assertTrue(project.job_no.startswith("SNV"))
        self.assertFalse(project.job_no.startswith("JS"))

    def test_sale_job_no_uses_project_start_year(self):
        user = self._sale_user(
            "od19_sale_rep_year",
            "NV",
            self._sale_sequence(),
            name="Nattanai Vinyangkoon",
        )
        project = self._create_sale_project(user, date_start="2027-03-01")
        self.assertEqual(project.job_no, "SNV27-0001")

    def test_sale_initials_derived_from_name_helpers(self):
        user = self._sale_user(
            "od19_sale_rep_helper", None, name="Nattanai Vinyangkoon"
        )
        self.assertEqual(user._od19_derive_initials(), "NV")
        self.assertEqual(user._od19_job_no_initials(), "NV")
        single_word = self._sale_user("od19_sale_rep_single", None, name="Somchai")
        self.assertEqual(single_word._od19_derive_initials(), "S")

    def test_sale_project_without_sequence_raises(self):
        user = self._sale_user("od19_sale_rep_noseq", "NS", name="Somchai Jaidee")
        with self.assertRaises(ValidationError):
            self._create_sale_project(user)

    def test_sale_project_with_explicit_job_no_does_not_raise(self):
        user = self._sale_user("od19_sale_rep_import", "IM", name="Somchai Jaidee")
        project = self._create_sale_project(user, job_no="SIM26-9999")
        self.assertEqual(project.job_no, "SIM26-9999")

    def test_job_type_other_than_sale_does_not_require_sequence(self):
        # No department and no sequence -> empty job number, no raise
        project = self.env["project.project"].create({
            "name": "No Dept Project",
            "od19_project_type": "pm",
        })
        self.assertFalse(project.job_no)

    def test_job_no_is_not_regenerated_on_write(self):
        user = self._sale_user("od19_sale_rep_write", "WR", self._sale_sequence())
        project = self._create_sale_project(user)
        original = project.job_no
        project.write({"od19_sale_person_id": self.env.uid})
        self.assertEqual(project.job_no, original)
