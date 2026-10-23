# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_etax_street_name = fields.Char(
        string="e-Tax Street Name",
        help="Street name reported in PostalTradeAddress/StreetName.",
    )
    od19_etax_building_number = fields.Char(
        string="e-Tax Building Number",
        help="Building number reported in PostalTradeAddress/BuildingNumber.",
    )
    od19_etax_city_code = fields.Char(
        string="e-Tax City Code",
        size=4,
        help="TISI city code reported in PostalTradeAddress/CityName.",
    )
    od19_etax_subdivision_code = fields.Char(
        string="e-Tax Sub-Division Code",
        size=6,
        help="TISI city sub-division code reported in "
        "PostalTradeAddress/CitySubDivisionName.",
    )
    od19_etax_province_code = fields.Char(
        string="e-Tax Province Code",
        size=2,
        help="Thai province code reported in "
        "PostalTradeAddress/CountrySubDivisionID.",
    )
