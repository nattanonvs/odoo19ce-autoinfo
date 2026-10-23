import re

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    od19_task_code = fields.Char(
        string="Task Code",
        copy=False,
        tracking=True,
        index=True,
    )

    def _get_task_sequence(self):
        """Return the global task sequence."""
        return self.env.ref(
            "od19_project_document_sequence.seq_project_task_default",
            raise_if_not_found=False,
        )

    def _generate_task_code(self):
        """Generate task code: T + dept_code + initials + padded_number.

        Sequence produces: T + <number>  e.g. T0001
        Result:             T + <dept_code> + <initials> + <number>  e.g. TBANV0001
        """
        self.ensure_one()
        sequence = self._get_task_sequence()
        if not sequence:
            return False

        generated = sequence.next_by_id()
        if not generated:
            return False

        # Get department code and salesperson initials from project
        dept_code = ""
        initials = ""
        if self.project_id:
            if self.project_id.od19_department_id:
                dept_code = self.project_id.od19_department_id.code or ""
            if self.project_id.od19_sale_person_id:
                # Same initials rule as the project job number: manual
                # od19_initials wins, otherwise derive from the user name.
                initials = (
                    self.project_id.od19_sale_person_id._od19_job_no_initials()
                )

        # Insert dept_code + initials after the 'T' prefix (first char)
        return generated[:1] + dept_code + initials + generated[1:]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.od19_task_code and record.project_id:
                record.od19_task_code = record._generate_task_code()
        return records
