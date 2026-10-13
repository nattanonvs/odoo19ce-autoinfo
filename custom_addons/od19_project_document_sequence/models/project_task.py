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
        """Generate task code: T + dept_code + initials + '-' + padded_number.

        Uses the project's department and salesperson for the prefix.
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
                dept_code = self.project_id.od19_department_id.od19_dept_code or ""
            if self.project_id.od19_sale_person_id:
                initials = self.project_id.od19_sale_person_id.od19_initials or ""

        # Insert dept_code + initials after the 'T' prefix
        return generated[:1] + dept_code + initials + generated[1:]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("od19_task_code"):
                # We need the project to get dept and salesperson
                # So generate after create if project is set
                pass
        records = super().create(vals_list)
        for record in records:
            if not record.od19_task_code and record.project_id:
                record.od19_task_code = record._generate_task_code()
        return records
