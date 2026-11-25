# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    od19_last_mileage_odometer = fields.Integer(
        string='Last Mileage Odometer (km) / เลขไมล์สิ้นสุดล่าสุด',
        help='Last mileage odometer reading recorded for this employee. '
             'It is offered as the starting odometer of the next mileage '
             'line so the employee does not have to remember the number. '
             'The suggestion stays editable.',
    )
