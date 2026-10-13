# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIsoTraining(TransactionCase):
    """Basic tests for ISO Training & Competence management."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})

    def _create_course(self, **overrides):
        vals = {
            "name": "Test Training Course",
            "course_type": "internal",
            "date": fields.Date.today(),
        }
        vals.update(overrides)
        return self.env["od19.iso.training.course"].create(vals)

    def test_create_course_with_minimal_fields(self):
        course = self._create_course()
        self.assertTrue(course)
        self.assertEqual(course.name, "Test Training Course")
        self.assertEqual(course.state, "draft")

    def test_course_state_transitions(self):
        course = self._create_course()
        self.assertEqual(course.state, "draft")

        course.action_plan()
        self.assertEqual(course.state, "planned")

        course.action_start()
        self.assertEqual(course.state, "in_progress")

        course.action_complete()
        self.assertEqual(course.state, "completed")

        course.action_reset_to_draft()
        self.assertEqual(course.state, "draft")

        course.action_cancel()
        self.assertEqual(course.state, "cancelled")

    def test_max_participants_constraint(self):
        with self.assertRaises(ValidationError):
            self._create_course(max_participants=-1)

    def test_max_participants_zero_allowed(self):
        course = self._create_course(max_participants=0)
        self.assertEqual(course.max_participants, 0)

    def test_create_participant(self):
        course = self._create_course()
        participant = self.env["od19.iso.training.participant"].create({
            "course_id": course.id,
            "employee_id": self.employee.id,
        })
        self.assertEqual(participant.course_id, course)
        self.assertTrue(participant.attended)
        self.assertEqual(participant.department_id, self.employee.department_id)

    def test_create_competence(self):
        competence = self.env["od19.iso.competence"].create({
            "name": "Test Competence",
            "category": "technical",
        })
        self.assertTrue(competence)
        self.assertTrue(competence.active)

    def test_create_employee_competence(self):
        competence = self.env["od19.iso.competence"].create({
            "name": "Test Skill",
        })
        emp_comp = self.env["od19.iso.employee.competence"].create({
            "employee_id": self.employee.id,
            "competence_id": competence.id,
            "level": 3,
        })
        self.assertEqual(emp_comp.level, "3")
        self.assertEqual(emp_comp.department_id, self.employee.department_id)
