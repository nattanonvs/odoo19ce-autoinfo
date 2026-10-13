from odoo.tests.common import TransactionCase


class TestWebsite(TransactionCase):
    """Basic tests for website company configuration fields."""

    def test_company_has_website_fields(self):
        company = self.env.user.company_id
        # Check default values are set
        self.assertEqual(company.od19_website_primary_color, "#9E2424")
        self.assertEqual(company.od19_website_secondary_color, "#f39200")
        self.assertTrue(company.od19_website_tagline)
        self.assertTrue(company.od19_website_hero_title)

    def test_company_website_fields_writable(self):
        company = self.env.user.company_id
        company.write({
            "od19_website_tagline": "New Tagline",
            "od19_website_primary_color": "#123456",
            "od19_website_secondary_color": "#654321",
            "od19_website_hero_title": "New Hero Title",
            "od19_website_hero_subtitle": "New Hero Subtitle",
            "od19_website_facebook_url": "https://facebook.com/test",
            "od19_website_linkedin_url": "https://linkedin.com/test",
            "od19_website_youtube_url": "https://youtube.com/test",
        })
        self.assertEqual(company.od19_website_tagline, "New Tagline")
        self.assertEqual(company.od19_website_primary_color, "#123456")
        self.assertEqual(company.od19_website_facebook_url, "https://facebook.com/test")
