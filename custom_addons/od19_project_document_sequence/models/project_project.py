from odoo import api, fields, models
from odoo.exceptions import ValidationError


# Mapping of project type to (type_prefix, sequence field name on hr.department)
PROJECT_TYPE_SEQUENCE_MAP = {
    "job": ("J", "project_job_sequence_id"),
    "server": ("SV", "project_server_sequence_id"),
    "pm": ("PM", "project_pm_sequence_id"),
    "service": ("S", "project_service_sequence_id"),
}


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
        string="Department",
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
        """Generate the job number by inserting sales initials into the sequence.

        The sequence produces: type_prefix + dept_code + year + '-' + number
        We insert the salesperson initials between dept_code and year.
        """
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

        type_prefix = PROJECT_TYPE_SEQUENCE_MAP.get(self.od19_project_type, ("", None))[0]
        dept_code = self.od19_department_id.od19_dept_code or ""
        initials = ""
        if sale_person:
            initials = sale_person.od19_initials or ""
        elif self.od19_sale_person_id:
            initials = self.od19_sale_person_id.od19_initials or ""

        # Insert initials after type_prefix + dept_code
        split_pos = len(type_prefix) + len(dept_code)
        return generated[:split_pos] + initials + generated[split_pos:]

    @api.model
    def create(self, vals):
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
                    type_prefix = PROJECT_TYPE_SEQUENCE_MAP[project_type][0]
                    dept_code = department.od19_dept_code or ""
                    initials = sale_person.od19_initials if sale_person else ""
                    seq_date = None
                    if vals.get("date_start"):
                        seq_date = fields.Date.to_date(vals["date_start"])
                    generated = sequence.next_by_id(sequence_date=seq_date)
                    if generated:
                        split_pos = len(type_prefix) + len(dept_code)
                        vals["job_no"] = (
                            generated[:split_pos] + initials + generated[split_pos:]
                        )
        return super().create(vals)

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

    @api.constrains("job_no")
    def _check_job_no_uniqueness(self):
        for project in self:
            if project.job_no:
                duplicate = self.search(
                    [("job_no", "=", project.job_no), ("id", "!=", project.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError("Job Number must be unique.")
