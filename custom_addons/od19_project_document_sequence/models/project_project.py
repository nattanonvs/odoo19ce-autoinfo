import re

from odoo import api, fields, models


# Mapping of project type to (type_prefix, sequence field name on hr.department)
PROJECT_TYPE_SEQUENCE_MAP = {
    "job": ("J", "project_job_sequence_id"),
    "server": ("SV", "project_server_sequence_id"),
    "pm": ("PM", "project_pm_sequence_id"),
    "service": ("S", "project_service_sequence_id"),
}


def _insert_initials_before_year(generated, initials):
    """Insert sales initials right before the 2-digit year in a sequence value.

    Sequence produces: <prefix><YY>-<number>  e.g. JB26-0001
    Result:            <prefix><initials><YY>-<number>  e.g. JBNV26-0001
    """
    if not generated:
        return generated
    match = re.search(r'\d{2}', generated)
    if match:
        pos = match.start()
        return generated[:pos] + initials + generated[pos:]
    return generated


class ProjectProject(models.Model):
    _inherit = "project.project"

    od19_project_type = fields.Selection(
        [
            ("job", "Job"),
            ("server", "Server"),
            ("pm", "Preventive Maintenance"),
            ("service", "Service"),
        ],
        string="Project Type",
        default="job",
        required=True,
        tracking=True,
        help="Determines the prefix used in the Job Number.",
    )
    od19_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="OD19 Department",
        tracking=True,
        index=True,
    )
    od19_sale_person_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        tracking=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "od19_department_id" not in res or not res.get("od19_department_id"):
            user = self.env["res.users"].browse(self.env.uid)
            if user.employee_id and user.employee_id.department_id:
                res["od19_department_id"] = user.employee_id.department_id.id
        if "od19_sale_person_id" not in res:
            res["od19_sale_person_id"] = self.env.uid
        return res

    def _get_project_sequence(self):
        """Return the ir.sequence for this project's type and department."""
        self.ensure_one()
        if not self.od19_department_id:
            return False
        seq_field = PROJECT_TYPE_SEQUENCE_MAP.get(self.od19_project_type, (None, None))[1]
        if not seq_field:
            return False
        return getattr(self.od19_department_id, seq_field)

    def _generate_job_no(self, sequence=None, sale_person=None):
        """Generate the job number by inserting sales initials before the year."""
        self.ensure_one()
        sequence = sequence or self._get_project_sequence()
        if not sequence:
            return False

        seq_date = None
        if self.date_start:
            seq_date = fields.Date.to_date(self.date_start)
        generated = sequence.next_by_id(sequence_date=seq_date)
        if not generated:
            return False

        initials = ""
        if sale_person:
            initials = sale_person.od19_initials or ""
        elif self.od19_sale_person_id:
            initials = self.od19_sale_person_id.od19_initials or ""

        return _insert_initials_before_year(generated, initials)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate job number if not provided
            if not vals.get("job_no"):
                department_id = vals.get("od19_department_id")
                project_type = vals.get("od19_project_type", "job")
                if department_id and project_type in PROJECT_TYPE_SEQUENCE_MAP:
                    department = self.env["hr.department"].browse(department_id)
                    seq_field = PROJECT_TYPE_SEQUENCE_MAP[project_type][1]
                    sequence = getattr(department, seq_field)
                    if sequence:
                        sale_person_id = vals.get("od19_sale_person_id")
                        sale_person = (
                            self.env["res.users"].browse(sale_person_id)
                            if sale_person_id
                            else False
                        )
                        initials = sale_person.od19_initials if sale_person else ""
                        seq_date = None
                        if vals.get("date_start"):
                            seq_date = fields.Date.to_date(vals["date_start"])
                        generated = sequence.next_by_id(sequence_date=seq_date)
                        if generated:
                            vals["job_no"] = _insert_initials_before_year(
                                generated, initials
                            )
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # Regenerate job number if department, project type, or salesperson changes
        # and the current job number is empty
        if any(
            k in vals
            for k in ("od19_department_id", "od19_project_type", "od19_sale_person_id")
        ):
            for rec in self:
                if not rec.job_no:
                    new_job_no = rec._generate_job_no()
                    if new_job_no:
                        rec.job_no = new_job_no
        return res
