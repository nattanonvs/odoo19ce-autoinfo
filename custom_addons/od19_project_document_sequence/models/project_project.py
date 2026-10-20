import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# Mapping of project type to (type_prefix, sequence field name on hr.department)
PROJECT_TYPE_SEQUENCE_MAP = {
    "job": ("J", "project_job_sequence_id"),
    "pm": ("PM", "project_pm_sequence_id"),
    "service": ("S", "project_service_sequence_id"),
    # 'sale' uses the salesperson sequence, not a department sequence (D1)
    "sale": ("S", None),
}

# Sales-type job numbers are always built as S + initials + YY + running number,
# so the prefix configured on the salesperson sequence is ignored.
SALE_TYPE_PREFIX = "S"


def _insert_initials_before_year(generated, initials):
    """Insert sales initials right before the 2-digit year in a sequence value.

    Sequence produces: <prefix><YY>-<number>  e.g. JB26-0001
    Result:            <prefix><initials><YY>-<number>  e.g. JBNV26-0001
    """
    if not generated:
        return generated
    match = re.search(r'\d{2}(?=-)', generated)
    if match:
        pos = match.start()
        return generated[:pos] + initials + generated[pos:]
    return generated


def _build_sale_job_no(generated, initials, sequence_date=None):
    """Build a Sales-type job number: S + initials + YY + running number.

    The salesperson sequence only supplies the running counter, so its own prefix
    is ignored: 'JS26-0001' with initials NV becomes 'SNV26-0001'.
    """
    if not generated:
        return generated
    match = re.search(r'\d+\s*$', generated)
    running = match.group(0) if match else generated
    year = (sequence_date or fields.Date.today()).strftime("%y")
    return "%s%s%s-%s" % (SALE_TYPE_PREFIX, initials or "", year, running)


class ProjectProject(models.Model):
    _inherit = "project.project"

    od19_project_type = fields.Selection(
        [
            ("job", "Job"),
            ("pm", "Preventive Maintenance"),
            ("service", "Service"),
            ("sale", "Sales"),
        ],
        string="Project Type",
        default="job",
        required=True,
        tracking=True,
        help="Determines the prefix used in the Job Number. "
             "od19_department_id is declared by od19_project_analytic.",
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
        """Return the ir.sequence for this project's type.

        Sales-type projects use the salesperson's own sequence; the other
        types use the department sequence for that project type.
        """
        self.ensure_one()
        if self.od19_project_type == "sale":
            return self.od19_sale_person_id.project_sale_sequence_id or False
        if not self.od19_department_id:
            return False
        seq_field = PROJECT_TYPE_SEQUENCE_MAP.get(self.od19_project_type, (None, None))[1]
        if not seq_field:
            return False
        return getattr(self.od19_department_id, seq_field)

    def _generate_job_no(self, sequence=None, sale_person=None):
        """Generate the job number of this project from its type sequence."""
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

        sale_person = sale_person or self.od19_sale_person_id
        if self.od19_project_type == "sale":
            initials = sale_person._od19_job_no_initials() if sale_person else ""
            return _build_sale_job_no(generated, initials, seq_date)

        initials = (sale_person.od19_initials or "") if sale_person else ""
        return _insert_initials_before_year(generated, initials)

    @staticmethod
    def _od19_sequence_date(vals):
        if vals.get("date_start"):
            return fields.Date.to_date(vals["date_start"])
        return None

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate job number if not provided
            if vals.get("job_no"):
                continue
            project_type = vals.get("od19_project_type", "job")
            if project_type == "sale":
                # Sales-type projects always take the number from the
                # salesperson sequence; never fall back silently (DD-4).
                sale_person = (
                    self.env["res.users"].browse(vals["od19_sale_person_id"])
                    if vals.get("od19_sale_person_id")
                    else self.env["res.users"]
                )
                sequence = sale_person.project_sale_sequence_id
                if not sequence:
                    raise ValidationError(
                        _("Set a Sale Project Job No. Sequence on the salesperson "
                          "before creating a Sales-type project.")
                    )
                seq_date = self._od19_sequence_date(vals)
                generated = sequence.next_by_id(sequence_date=seq_date)
                if generated:
                    vals["job_no"] = _build_sale_job_no(
                        generated, sale_person._od19_job_no_initials(), seq_date
                    )
                continue
            department_id = vals.get("od19_department_id")
            if department_id and project_type in PROJECT_TYPE_SEQUENCE_MAP:
                department = self.env["hr.department"].browse(department_id)
                seq_field = PROJECT_TYPE_SEQUENCE_MAP[project_type][1]
                sequence = getattr(department, seq_field) if seq_field else False
                if sequence:
                    sale_person_id = vals.get("od19_sale_person_id")
                    sale_person = (
                        self.env["res.users"].browse(sale_person_id)
                        if sale_person_id
                        else False
                    )
                    initials = sale_person.od19_initials if sale_person else ""
                    generated = sequence.next_by_id(
                        sequence_date=self._od19_sequence_date(vals)
                    )
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
