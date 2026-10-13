# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase


class TestThaiLocalizationBase(TransactionCase):
    """Basic tests for Thai localization base fields."""

    def test_company_has_buddhist_year_flag(self):
        company = self.env.user.company_id
        # Default should be True
        self.assertTrue(company.l10n_th_buddhist_year)

    def test_company_font_has_sarabun_option(self):
        company = self.env.user.company_id
        # The font selection should include 'Sarabun'
        field = company._fields["font"]
        self.assertIn("Sarabun", dict(field.selection).keys())

    def test_toggle_buddhist_year(self):
        company = self.env.user.company_id
        company.l10n_th_buddhist_year = False
        self.assertFalse(company.l10n_th_buddhist_year)
        company.l10n_th_buddhist_year = True
        self.assertTrue(company.l10n_th_buddhist_year)

    def test_config_settings_has_buddhist_year(self):
        # The config settings should expose the related field
        config = self.env["res.config.settings"].create({})
        self.assertTrue(hasattr(config, "l10n_th_buddhist_year"))
