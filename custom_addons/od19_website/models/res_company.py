from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_website_tagline = fields.Char(
        string="Website Tagline",
        translate=True,
        default="Total Integrated Automation Solutions",
        help="Short tagline shown on the website homepage hero section.",
    )
    od19_website_primary_color = fields.Char(
        string="Primary Color",
        default="#0056b3",
        help="Primary brand color used across the website (hex).",
    )
    od19_website_secondary_color = fields.Char(
        string="Secondary Color",
        default="#f39200",
        help="Secondary / accent brand color used across the website (hex).",
    )
    od19_website_hero_title = fields.Char(
        string="Hero Title",
        translate=True,
        default="Automation Solutions for a Smarter Future",
    )
    od19_website_hero_subtitle = fields.Char(
        string="Hero Subtitle",
        translate=True,
        default="Industrial · Building · Terminal Automation",
    )
    od19_website_facebook_url = fields.Char(string="Facebook URL")
    od19_website_linkedin_url = fields.Char(string="LinkedIn URL")
    od19_website_youtube_url = fields.Char(string="YouTube URL")
