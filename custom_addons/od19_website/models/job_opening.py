from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19JobOpening(models.Model):
    """A job vacancy published on the corporate website."""

    _name = "od19.job.opening"
    _description = "Job Opening"
    _order = "sequence, id desc"

    name = fields.Char(string="Job Title", required=True, translate=True)
    department = fields.Selection(
        selection=[
            ("industrial", "Industrial Automation"),
            ("building", "Building Automation"),
            ("terminal", "Terminal Automation"),
            ("support", "Sales & Administration"),
        ],
        string="Department",
        required=True,
        default="industrial",
    )
    job_type = fields.Selection(
        selection=[
            ("full_time", "Full-time"),
            ("part_time", "Part-time"),
            ("contract", "Contract"),
            ("internship", "Internship"),
        ],
        string="Employment Type",
        required=True,
        default="full_time",
    )
    experience_level = fields.Selection(
        selection=[
            ("entry", "Entry Level"),
            ("mid", "Mid Level"),
            ("senior", "Senior Level"),
        ],
        string="Experience Level",
        default="mid",
    )
    work_location = fields.Char(string="Work Location", default="Bangkok Head Office")
    vacancies = fields.Integer(string="Number of Vacancies", default=1)
    salary_range = fields.Char(
        string="Salary Range",
        help="Free text, e.g. 'THB 35,000 - 55,000 / month'. Leave empty to hide.",
    )
    short_description = fields.Text(
        string="Short Description",
        translate=True,
        help="One or two lines shown on the careers listing page.",
    )
    description = fields.Html(string="Job Description", translate=True)
    responsibilities = fields.Html(string="Responsibilities", translate=True)
    qualifications = fields.Html(string="Qualifications", translate=True)
    benefits = fields.Html(string="Benefits & Welfare", translate=True)
    publish_date = fields.Date(
        string="Publish Date", default=fields.Date.context_today
    )
    closing_date = fields.Date(string="Closing Date")
    is_published = fields.Boolean(string="Published on Website", default=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    application_ids = fields.One2many(
        "od19.job.application", "job_id", string="Applications"
    )
    application_count = fields.Integer(
        string="Number of Applications", compute="_compute_application_count"
    )
    is_open = fields.Boolean(
        string="Accepting Applications", compute="_compute_is_open"
    )
    website_url = fields.Char(string="Website URL", compute="_compute_website_url")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("application_ids")
    def _compute_application_count(self):
        for opening in self:
            opening.application_count = len(opening.application_ids)

    @api.depends("is_published", "closing_date")
    def _compute_is_open(self):
        today = fields.Date.context_today(self)
        for opening in self:
            opening.is_open = bool(
                opening.is_published
                and (not opening.closing_date or opening.closing_date >= today)
            )

    @api.depends("name")
    def _compute_website_url(self):
        for opening in self:
            opening.website_url = "/careers/%s" % (opening.id or "")

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("vacancies")
    def _check_vacancies(self):
        for opening in self:
            if opening.vacancies < 1:
                raise ValidationError(
                    "The number of vacancies must be at least 1."
                )

    @api.constrains("publish_date", "closing_date")
    def _check_dates(self):
        for opening in self:
            if (
                opening.publish_date
                and opening.closing_date
                and opening.closing_date < opening.publish_date
            ):
                raise ValidationError(
                    "The closing date cannot be earlier than the publish date."
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def department_label(self):
        """Return the human readable department label for the website."""
        self.ensure_one()
        return dict(self._fields["department"].selection).get(self.department, "")

    def job_type_label(self):
        self.ensure_one()
        return dict(self._fields["job_type"].selection).get(self.job_type, "")

    def experience_label(self):
        self.ensure_one()
        return dict(self._fields["experience_level"].selection).get(
            self.experience_level, ""
        )

    def action_view_applications(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "od19_website.action_od19_job_application"
        )
        action["domain"] = [("job_id", "=", self.id)]
        action["context"] = {"default_job_id": self.id}
        return action
