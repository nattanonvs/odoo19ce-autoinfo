from odoo import api, fields, models


class Od19ProjectType(models.Model):
    _name = "od19.project.type"
    _description = "OD19 Project Type"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    parent_id = fields.Many2one(
        "od19.project.type",
        string="Parent Type",
        ondelete="restrict",
        index=True,
    )
    child_ids = fields.One2many(
        "od19.project.type",
        "parent_id",
        string="Child Types",
    )
    project_ok = fields.Boolean(
        string="Usable on Projects",
        default=True,
        help="If checked, this type can be selected on projects.",
    )
    task_ok = fields.Boolean(
        string="Usable on Tasks",
        default=True,
        help="If checked, this type can be selected on tasks.",
    )
    complete_name = fields.Char(
        string="Complete Name",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
    )
    parent_path = fields.Char(index=True, unaccent=False)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.complete_name:
                rec.complete_name = "%s / %s" % (rec.parent_id.complete_name, rec.name)
            else:
                rec.complete_name = rec.name
