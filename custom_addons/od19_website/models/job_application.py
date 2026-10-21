from odoo import api, fields, models


class Od19JobApplication(models.Model):
    """An application (candidate) submitted for a job opening."""

    _name = "od19.job.application"
    _description = "Job Application"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    job_id = fields.Many2one(
        "od19.job.opening",
        string="Job Position",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    department = fields.Selection(
        related="job_id.department", string="Department", store=True
    )
    reference = fields.Char(string="Reference", readonly=True, copy=False)

    # --- Candidate details -------------------------------------------------
    name = fields.Char(string="Full Name", required=True, tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Phone")
    current_company = fields.Char(string="Current Company")
    current_position = fields.Char(string="Current Position")
    years_experience = fields.Float(string="Years of Experience")
    expected_salary = fields.Char(string="Expected Salary")
    available_date = fields.Date(string="Available From")
    source = fields.Char(
        string="How did you hear about us?",
        help="e.g. JobThai, LinkedIn, Referral ...",
    )
    cover_letter = fields.Text(string="Cover Letter / Message")

    # --- Documents ---------------------------------------------------------
    resume = fields.Binary(
        string="Resume / CV",
        attachment=True,
        help="Main resume or curriculum vitae of the candidate.",
    )
    resume_filename = fields.Char(string="Resume Filename")
    document_ids = fields.Many2many(
        "ir.attachment",
        "od19_job_application_ir_attachment_rel",
        "application_id",
        "attachment_id",
        string="Supporting Documents",
        help="Transcripts, certificates, portfolio and other supporting files.",
    )
    document_count = fields.Integer(
        string="Documents", compute="_compute_document_count"
    )

    # --- Recruitment workflow ---------------------------------------------
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("shortlisted", "Shortlisted"),
            ("interview", "Interview"),
            ("offer", "Offer Sent"),
            ("hired", "Hired"),
            ("refused", "Not Selected"),
        ],
        string="Status",
        default="new",
        tracking=True,
        group_expand="_group_expand_state",
    )
    note = fields.Text(string="Internal Notes")

    @api.depends("document_ids")
    def _compute_document_count(self):
        for application in self:
            application.document_count = len(application.document_ids)

    @api.model
    def _group_expand_state(self, states, domain):
        return [key for key, _label in self._fields["state"].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference") or vals.get("reference") == self.env._("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "od19.job.application"
                ) or self.env._("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Recruitment workflow
    # ------------------------------------------------------------------
    def action_shortlist(self):
        self.write({"state": "shortlisted"})

    def action_interview(self):
        self.write({"state": "interview"})

    def action_offer(self):
        self.write({"state": "offer"})

    def action_hired(self):
        self.write({"state": "hired"})

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset(self):
        self.write({"state": "new"})
