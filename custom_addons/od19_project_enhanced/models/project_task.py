from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class ProjectTask(models.Model):
    _inherit = "project.task"

    od19_project_type_id = fields.Many2one(
        "od19.project.type",
        string="Project Type",
        domain=[("task_ok", "=", True)],
        tracking=True,
        ondelete="restrict",
    )

    # ------------------------------------------------------------------
    # No backward stage change
    # ------------------------------------------------------------------
    def write(self, vals):
        if "stage_id" in vals and not self.env.is_admin():
            new_stage_id = vals.get("stage_id")
            for task in self:
                old_stage = task.stage_id
                if not old_stage or not new_stage_id:
                    continue
                new_stage = self.env["project.task.type"].browse(new_stage_id)
                if new_stage.exists() and new_stage.sequence < old_stage.sequence:
                    raise UserError(
                        _(
                            "You cannot move task '%(task)s' backward from stage "
                            "'%(old)s' (sequence %(old_seq)s) to '%(new)s' "
                            "(sequence %(new_seq)s). Only administrators can "
                            "perform this action.",
                            task=task.name,
                            old=old_stage.name,
                            old_seq=old_stage.sequence,
                            new=new_stage.name,
                            new_seq=new_stage.sequence,
                        )
                    )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Task deadline notification cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_task_deadline_notification(self):
        """Find tasks whose deadline is within 3 days (and not closed) and
        notify the responsible users by email."""
        now = fields.Datetime.now()
        upper_bound = now + timedelta(days=3)
        tasks = self.search(
            [
                ("date_deadline", ">=", now),
                ("date_deadline", "<=", upper_bound),
                ("is_closed", "=", False),
            ]
        )
        template = self.env.ref(
            "od19_project_enhanced.mail_template_task_deadline_notification",
            raise_if_not_found=False,
        )
        if not template:
            return
        for task in tasks:
            assignees = task.user_ids.filtered(lambda u: u.partner_id.email)
            for user in assignees:
                template.with_context(
                    lang=user.partner_id.lang or self.env.user.lang,
                    od19_recipient_name=user.name,
                ).send_mail(
                    task.id,
                    email_values={
                        "email_to": user.partner_id.email,
                    },
                    force_send=False,
                )
        return True

    def _get_deadline_formatted(self):
        self.ensure_one()
        if not self.date_deadline:
            return ""
        return format_date(self.env, self.date_deadline.date())
